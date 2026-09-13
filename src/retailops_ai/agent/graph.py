"""Bounded plan-execute-synthesize LangGraph for RetailOps AI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from retailops_ai.agent.llm import DecisionLLM
from retailops_ai.agent.schemas import AgentDraft, AgentPlan, ApprovalDecision
from retailops_ai.agent.state import AgentState
from retailops_ai.agent.tools import ToolExecutionBatch


class ToolExecutor(Protocol):
    def execute_plan(
        self,
        plan: AgentPlan,
        *,
        existing_signatures: list[str],
        request_id: str,
    ) -> ToolExecutionBatch: ...


@dataclass(frozen=True)
class AgentGraphDependencies:
    llm: DecisionLLM
    toolbox: ToolExecutor
    max_tool_steps: int = 3


def _plan_has_tools(plan: AgentPlan) -> bool:
    return bool(
        plan.forecast
        or plan.analytics
        or plan.need_model_info
        or plan.knowledge_query
    )


def build_agent_graph(deps: AgentGraphDependencies, *, checkpointer: Any) -> Any:
    def plan_node(state: AgentState) -> dict[str, Any]:
        plan = deps.llm.plan(
            question=state["question"],
            evidence=state.get("evidence", []),
            user_context=state.get("user_context", {}),
            step_count=state.get("step_count", 0),
            max_steps=deps.max_tool_steps,
        )
        return {"plan": plan.model_dump(mode="json")}

    def route_after_plan(state: AgentState) -> str:
        plan = AgentPlan.model_validate(state["plan"])
        if plan.status == "answer":
            return "synthesize"
        if state.get("step_count", 0) >= deps.max_tool_steps:
            return "synthesize"
        return "execute_tools" if _plan_has_tools(plan) else "synthesize"

    def execute_tools_node(state: AgentState) -> dict[str, Any]:
        plan = AgentPlan.model_validate(state["plan"])
        batch = deps.toolbox.execute_plan(
            plan,
            existing_signatures=state.get("executed_signatures", []),
            request_id=state["thread_id"],
        )
        return {
            "evidence": [*state.get("evidence", []), *batch.evidence],
            "tool_trace": [*state.get("tool_trace", []), *batch.trace],
            "executed_signatures": batch.signatures,
            "step_count": state.get("step_count", 0) + 1,
        }

    def synthesize_node(state: AgentState) -> dict[str, Any]:
        draft = deps.llm.synthesize(
            question=state["question"],
            evidence=state.get("evidence", []),
            user_context=state.get("user_context", {}),
        )
        return {
            "draft": draft.model_dump(mode="json"),
            "approval_required": draft.proposed_action is not None,
        }

    def route_after_synthesis(state: AgentState) -> str:
        return "approval" if state.get("approval_required", False) else "finalize"

    def approval_node(state: AgentState) -> dict[str, Any]:
        draft = AgentDraft.model_validate(state["draft"])
        proposal = draft.proposed_action
        if proposal is None:
            return {"approval": {"approved": True, "reviewer_note": None}}

        decision = interrupt(
            {
                "type": "business_action_approval",
                "question": state["question"],
                "proposal": proposal.model_dump(mode="json"),
                "answer_preview": draft.answer,
                "evidence_sources": draft.evidence_sources,
                "notice": (
                    "Approval authorizes human follow-up only; "
                    "no external system is mutated."
                ),
            }
        )
        validated = ApprovalDecision.model_validate(decision)
        return {"approval": validated.model_dump(mode="json")}

    def finalize_node(state: AgentState) -> dict[str, Any]:
        draft = AgentDraft.model_validate(state["draft"])
        answer = draft.answer
        if draft.limitations:
            answer += "\n\nLimitations: " + "; ".join(draft.limitations)

        if draft.proposed_action is not None:
            approval = ApprovalDecision.model_validate(state["approval"])
            if approval.approved:
                answer += (
                    "\n\nHuman review: approved for follow-up. "
                    "RetailOps AI did not mutate any operational system."
                )
            else:
                answer += (
                    "\n\nHuman review: the proposed action was rejected. "
                    "The analysis remains advisory only."
                )
            if approval.reviewer_note:
                answer += f" Reviewer note: {approval.reviewer_note}"

        return {"final_answer": answer, "status": "completed"}

    builder = StateGraph(AgentState)
    builder.add_node("plan", plan_node)
    builder.add_node("execute_tools", execute_tools_node)
    builder.add_node("synthesize", synthesize_node)
    builder.add_node("approval", approval_node)
    builder.add_node("finalize", finalize_node)
    builder.add_edge(START, "plan")
    builder.add_conditional_edges(
        "plan",
        route_after_plan,
        {"execute_tools": "execute_tools", "synthesize": "synthesize"},
    )
    builder.add_edge("execute_tools", "plan")
    builder.add_conditional_edges(
        "synthesize",
        route_after_synthesis,
        {"approval": "approval", "finalize": "finalize"},
    )
    builder.add_edge("approval", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile(checkpointer=checkpointer)
