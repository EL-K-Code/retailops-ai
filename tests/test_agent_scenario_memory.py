from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from retailops_ai.agent.graph import AgentGraphDependencies, build_agent_graph
from retailops_ai.agent.runtime import AgentRuntime
from retailops_ai.agent.schemas import (
    AgentDraft,
    AgentPlan,
    EntityRef,
    InventoryDecisionRequest,
)
from retailops_ai.agent.tools import ToolExecutionBatch


class MemoryLLM:
    def __init__(self) -> None:
        self.plan_calls = 0
        self.contexts: list[dict[str, Any]] = []

    def plan(self, **kwargs: Any) -> AgentPlan:
        self.contexts.append(dict(kwargs["user_context"]))
        self.plan_calls += 1
        if self.plan_calls == 1:
            return AgentPlan(
                status="execute",
                inventory_decision=InventoryDecisionRequest(
                    entity=EntityRef(item_id="FOODS_1_001", store_id="CA_1"),
                    current_stock=20,
                    incoming_units=10,
                    lead_time_days=3,
                    safety_stock=6,
                    horizon_days=5,
                ),
            )
        return AgentPlan(status="answer")

    def synthesize(self, **_: Any) -> AgentDraft:
        return AgentDraft(
            answer="Grounded scenario response.",
            confidence="high",
            evidence_sources=["inventory_decision"],
        )


class MemoryToolbox:
    def execute_plan(
        self,
        plan: AgentPlan,
        *,
        existing_signatures: list[str],
        request_id: str,
    ) -> ToolExecutionBatch:
        del plan, existing_signatures, request_id
        return ToolExecutionBatch(
            evidence=[
                {
                    "source": "inventory_decision",
                    "kind": "tool_result",
                    "data": {
                        "split": "test",
                        "decision_horizon_days": 5,
                        "entity": {
                            "item_id": "FOODS_1_001",
                            "store_id": "CA_1",
                        },
                        "scenario": {
                            "current_stock": 20.0,
                            "incoming_units": 10.0,
                            "lead_time_days": 3,
                            "safety_stock": 6.0,
                        },
                    },
                }
            ],
            trace=[{"tool": "inventory_decision", "status": "ok"}],
            signatures=["inventory-1"],
        )


def test_agent_runtime_reuses_thread_scoped_active_scenario() -> None:
    llm = MemoryLLM()
    graph = build_agent_graph(
        AgentGraphDependencies(llm=llm, toolbox=MemoryToolbox()),
        checkpointer=InMemorySaver(),
    )
    runtime = AgentRuntime(graph)

    first = runtime.ask(
        question="I have 20 units and 10 arrive in 3 days.",
        thread_id="scenario-thread",
    )
    second = runtime.ask(
        question="Using the same scenario, what if delivery is delayed?",
        thread_id="scenario-thread",
    )

    assert first.active_scenario is not None
    assert second.active_scenario is not None
    assert llm.contexts[-1]["active_scenario"]["current_stock"] == 20.0
    assert llm.contexts[-1]["active_scenario"]["incoming_units"] == 10.0
