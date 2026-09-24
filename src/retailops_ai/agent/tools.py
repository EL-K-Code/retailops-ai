"""Deterministic tool execution layer for the RetailOps LangGraph agent."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Protocol

from retailops_ai.agent.knowledge import KnowledgeRetriever
from retailops_ai.agent.schemas import (
    AgentPlan,
    AnalyticsRequest,
    EntityRef,
    InventoryDecisionRequest,
)
from retailops_ai.decision.inventory import (
    InventoryScenario,
    recommend_inventory_counterfactuals,
    simulate_inventory,
)
from retailops_ai.decision.reorder import ReorderEconomics, optimize_reorder_scenario
from retailops_ai.decision.uncertainty import band_as_forecast_points, poisson_predictive_band


class ForecastToolClient(Protocol):
    def forecast(
        self,
        *,
        entities: list[EntityRef],
        split: str,
        request_id: str,
    ) -> dict[str, Any]: ...

    def model_info(self, *, request_id: str) -> dict[str, Any]: ...


class AnalyticsTool(Protocol):
    def run(self, request: AnalyticsRequest) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ToolExecutionBatch:
    evidence: list[dict[str, Any]]
    trace: list[dict[str, Any]]
    signatures: list[str]


def _signature(tool: str, payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(f"{tool}:{canonical}".encode()).hexdigest()[:20]


def _jsonable(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def _extract_forecast_points(
    forecast: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    forecasts = forecast.get("forecasts") or []
    if len(forecasts) != 1:
        raise ValueError("inventory decision requires exactly one item/store entity")
    series = forecasts[0]
    points = series.get("points") or series.get("predictions") or []
    if not points:
        raise ValueError("forecast service returned no forecast points")
    return series, list(points)


def _run_inventory_decision(
    client: ForecastToolClient,
    request: InventoryDecisionRequest,
    *,
    request_id: str,
) -> dict[str, Any]:
    """Combine live forecast evidence with explicit inventory scenario inputs."""

    forecast = client.forecast(
        entities=[request.entity],
        split=request.split,
        request_id=request_id,
    )
    series, all_points = _extract_forecast_points(forecast)
    points = all_points[: request.horizon_days]
    if len(points) < request.horizon_days:
        raise ValueError(
            f"forecast service returned only {len(points)} points for a "
            f"{request.horizon_days}-day decision horizon"
        )

    scenario = InventoryScenario(
        current_stock=request.current_stock,
        incoming_units=request.incoming_units,
        lead_time_days=request.lead_time_days,
        safety_stock=request.safety_stock,
    )
    simulation = simulate_inventory(points, scenario)
    result: dict[str, Any] = {
        "request_id": forecast.get("request_id", request_id),
        "split": forecast.get("split", request.split),
        "forecast_origin": forecast.get("forecast_origin"),
        "decision_horizon_days": request.horizon_days,
        "entity": {
            "series_id": series.get("series_id"),
            "item_id": series.get("item_id", request.entity.item_id),
            "store_id": series.get("store_id", request.entity.store_id),
        },
        "scenario": {
            "current_stock": request.current_stock,
            "incoming_units": request.incoming_units,
            "lead_time_days": request.lead_time_days,
            "safety_stock": request.safety_stock,
        },
        "forecast_points": points,
        **simulation,
    }
    uncertainty = poisson_predictive_band(points)
    upper_stress = simulate_inventory(
        band_as_forecast_points(uncertainty, level="upper"),
        scenario,
    )
    result["uncertainty"] = uncertainty
    result["upper_demand_stress"] = {
        "risk_level": upper_stress["risk_level"],
        "projected_end_inventory": upper_stress["projected_end_inventory"],
        "stockout_day": upper_stress["stockout_day"],
        "safety_breach_day": upper_stress["safety_breach_day"],
    }
    if request.include_counterfactuals:
        result["counterfactuals"] = recommend_inventory_counterfactuals(points, scenario)
    if request.economics is not None:
        economics_payload = request.economics.model_dump(mode="json")
        result["economics"] = economics_payload
        result["reorder_optimization"] = optimize_reorder_scenario(
            points,
            scenario,
            ReorderEconomics(**economics_payload),
        )
    return result


class AgentToolbox:
    def __init__(
        self,
        *,
        forecast_client: ForecastToolClient,
        analytics_tool: AnalyticsTool,
        knowledge_retriever: KnowledgeRetriever,
        rag_top_k: int = 4,
    ) -> None:
        self.forecast_client = forecast_client
        self.analytics_tool = analytics_tool
        self.knowledge_retriever = knowledge_retriever
        self.rag_top_k = rag_top_k

    def execute_plan(
        self,
        plan: AgentPlan,
        *,
        existing_signatures: list[str],
        request_id: str,
    ) -> ToolExecutionBatch:
        evidence: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        signatures = list(existing_signatures)

        def run_once(tool: str, payload: Any, callback: Any) -> None:
            signature = _signature(tool, payload)
            if signature in signatures:
                trace.append({
                    "tool": tool,
                    "status": "skipped_duplicate",
                    "signature": signature,
                    "latency_ms": 0.0,
                })
                return
            signatures.append(signature)
            started = time.perf_counter()
            try:
                result = callback()
                evidence.append(
                    {
                        "source": tool,
                        "kind": "tool_result",
                        "data": _jsonable(result),
                    }
                )
                trace.append({
                    "tool": tool,
                    "status": "ok",
                    "signature": signature,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                })
            except Exception as exc:  # deterministic failure is evidence, not fabricated data
                evidence.append(
                    {
                        "source": f"{tool}:error",
                        "kind": "tool_error",
                        "data": {"message": str(exc)},
                    }
                )
                trace.append({
                    "tool": tool,
                    "status": "error",
                    "signature": signature,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                })

        if plan.inventory_decision is not None:
            inventory_request = plan.inventory_decision
            payload = inventory_request.model_dump(mode="json")
            run_once(
                "inventory_decision",
                payload,
                lambda: _run_inventory_decision(
                    self.forecast_client,
                    inventory_request,
                    request_id=request_id,
                ),
            )

        if plan.forecast is not None:
            forecast = plan.forecast
            payload = forecast.model_dump(mode="json")
            run_once(
                "forecast_api",
                payload,
                lambda: self.forecast_client.forecast(
                    entities=forecast.entities,
                    split=forecast.split,
                    request_id=request_id,
                ),
            )

        for request in plan.analytics:
            payload = request.model_dump(mode="json")
            run_once(
                f"bigquery:{request.operation}",
                payload,
                lambda request=request: self.analytics_tool.run(request),
            )

        if plan.need_model_info:
            run_once(
                "model_info_api",
                {},
                lambda: self.forecast_client.model_info(request_id=request_id),
            )

        if plan.knowledge_query:
            query = plan.knowledge_query
            run_once(
                "knowledge_rag",
                {"query": query, "top_k": self.rag_top_k},
                lambda: [
                    hit.as_dict()
                    for hit in self.knowledge_retriever.search(query, top_k=self.rag_top_k)
                ],
            )

        return ToolExecutionBatch(evidence=evidence, trace=trace, signatures=signatures)
