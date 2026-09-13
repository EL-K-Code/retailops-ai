from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from retailops_ai.agent.graph import AgentGraphDependencies, build_agent_graph
from retailops_ai.agent.schemas import ActionProposal, AgentDraft, AgentPlan
from retailops_ai.agent.tools import ToolExecutionBatch


class FakeLLM:
    def __init__(self, plans: list[AgentPlan], draft: AgentDraft) -> None:
        self.plans = list(plans)
        self.draft = draft

    def plan(self, **_: Any) -> AgentPlan:
        return self.plans.pop(0)

    def synthesize(self, **_: Any) -> AgentDraft:
        return self.draft


class FakeToolbox:
    def execute_plan(
        self,
        plan: AgentPlan,
        *,
        existing_signatures: list[str],
        request_id: str,
    ) -> ToolExecutionBatch:
        signature = f"fake-{len(existing_signatures)}"
        return ToolExecutionBatch(
            evidence=[
                {
                    "source": "knowledge_rag",
                    "kind": "tool_result",
                    "data": {"fact": "Forecasts do not directly equal order quantities."},
                }
            ],
            trace=[{"tool": "knowledge_rag", "status": "ok", "signature": signature}],
            signatures=[*existing_signatures, signature],
        )


def _initial(thread_id: str) -> dict[str, Any]:
    return {
        "question": "Should I reorder this item?",
        "thread_id": thread_id,
        "user_context": {},
        "step_count": 0,
        "evidence": [],
        "executed_signatures": [],
        "tool_trace": [],
    }


def test_graph_executes_tools_then_answers_without_approval():
    graph = build_agent_graph(
        AgentGraphDependencies(
            llm=FakeLLM(
                plans=[
                    AgentPlan(status="execute", knowledge_query="reorder policy"),
                    AgentPlan(status="answer"),
                ],
                draft=AgentDraft(
                    answer="Use the forecast as one input, not as an automatic order quantity.",
                    confidence="high",
                    evidence_sources=["knowledge_rag"],
                ),
            ),
            toolbox=FakeToolbox(),
        ),
        checkpointer=InMemorySaver(),
    )
    config = {"configurable": {"thread_id": "thread-no-approval"}}

    result = graph.invoke(_initial("thread-no-approval"), config=config)

    assert result["status"] == "completed"
    assert "automatic order quantity" in result["final_answer"]
    assert result["step_count"] == 1
    assert result["tool_trace"][0]["status"] == "ok"


def test_graph_interrupts_and_resumes_for_business_action():
    graph = build_agent_graph(
        AgentGraphDependencies(
            llm=FakeLLM(
                plans=[AgentPlan(status="answer")],
                draft=AgentDraft(
                    answer="Demand is elevated; a planner should review replenishment.",
                    confidence="medium",
                    evidence_sources=[],
                    proposed_action=ActionProposal(
                        action_type="review_reorder",
                        description="Review reorder quantity with inventory and lead-time context.",
                    ),
                ),
            ),
            toolbox=FakeToolbox(),
        ),
        checkpointer=InMemorySaver(),
    )
    config = {"configurable": {"thread_id": "thread-approval"}}

    interrupted = graph.invoke(_initial("thread-approval"), config=config)
    assert interrupted["__interrupt__"]

    resumed = graph.invoke(
        Command(resume={"approved": True, "reviewer_note": "Planner will review."}),
        config=config,
    )

    assert resumed["status"] == "completed"
    assert "approved for follow-up" in resumed["final_answer"]
    assert "Planner will review." in resumed["final_answer"]


def test_graph_records_rejected_business_action():
    graph = build_agent_graph(
        AgentGraphDependencies(
            llm=FakeLLM(
                plans=[AgentPlan(status="answer")],
                draft=AgentDraft(
                    answer="Investigate the demand spike.",
                    confidence="medium",
                    proposed_action=ActionProposal(
                        action_type="investigate_anomaly",
                        description="Review the unusual demand pattern.",
                    ),
                ),
            ),
            toolbox=FakeToolbox(),
        ),
        checkpointer=InMemorySaver(),
    )
    config = {"configurable": {"thread_id": "thread-reject"}}
    graph.invoke(_initial("thread-reject"), config=config)

    resumed = graph.invoke(
        Command(resume={"approved": False, "reviewer_note": None}),
        config=config,
    )

    assert "proposed action was rejected" in resumed["final_answer"]
