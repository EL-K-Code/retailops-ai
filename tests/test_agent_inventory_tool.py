"""Tests for the agent inventory-decision tool."""

from __future__ import annotations

from typing import Any

from retailops_ai.agent.schemas import AgentPlan, EntityRef, InventoryDecisionRequest
from retailops_ai.agent.tools import AgentToolbox


class FakeForecastClient:
    def forecast(self, *, entities, split, request_id):
        entity = entities[0]
        return {
            "request_id": request_id,
            "split": split,
            "forecast_origin": "2016-04-24",
            "forecasts": [
                {
                    "series_id": f"{entity.item_id}_{entity.store_id}",
                    "item_id": entity.item_id,
                    "store_id": entity.store_id,
                    "points": [
                        {
                            "date": f"2016-04-{24 + day:02d}",
                            "horizon": day,
                            "prediction": 3.0,
                        }
                        for day in range(1, 6)
                    ],
                }
            ],
        }

    def model_info(self, *, request_id):
        return {"request_id": request_id, "model": "fake"}


class FakeAnalytics:
    def run(self, request):
        return {"operation": request.operation}


class FakeKnowledge:
    def search(self, query: str, *, top_k: int):
        return []


def test_agent_inventory_tool_uses_live_forecast_and_scenario_inputs() -> None:
    toolbox = AgentToolbox(
        forecast_client=FakeForecastClient(),
        analytics_tool=FakeAnalytics(),
        knowledge_retriever=FakeKnowledge(),
    )
    plan = AgentPlan(
        status="execute",
        inventory_decision=InventoryDecisionRequest(
            entity=EntityRef(item_id="FOODS_1_001", store_id="CA_1"),
            split="test",
            current_stock=10,
            incoming_units=8,
            lead_time_days=3,
            safety_stock=2,
            horizon_days=5,
            include_counterfactuals=True,
        ),
    )

    batch = toolbox.execute_plan(plan, existing_signatures=[], request_id="decision-1")

    assert batch.trace[0]["tool"] == "inventory_decision"
    assert batch.trace[0]["status"] == "ok"
    result: dict[str, Any] = batch.evidence[0]["data"]
    assert result["decision_horizon_days"] == 5
    assert result["scenario"]["current_stock"] == 10
    assert result["scenario"]["incoming_units"] == 8
    assert result["forecast_total"] == 15
    assert result["counterfactuals"]["decision_horizon_days"] == 5
    assert batch.evidence[0]["source"] == "inventory_decision"


def test_agent_inventory_tool_respects_short_decision_horizon() -> None:
    toolbox = AgentToolbox(
        forecast_client=FakeForecastClient(),
        analytics_tool=FakeAnalytics(),
        knowledge_retriever=FakeKnowledge(),
    )
    plan = AgentPlan(
        status="execute",
        inventory_decision=InventoryDecisionRequest(
            entity=EntityRef(item_id="FOODS_1_001", store_id="CA_1"),
            current_stock=5,
            incoming_units=20,
            lead_time_days=7,
            horizon_days=5,
            safety_stock=0,
        ),
    )

    batch = toolbox.execute_plan(plan, existing_signatures=[], request_id="decision-2")
    result = batch.evidence[0]["data"]

    assert result["available_units"] == 5
    assert result["stockout_day"] == 2
    assert result["risk_level"] == "high"
