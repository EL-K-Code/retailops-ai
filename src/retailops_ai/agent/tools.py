"""Deterministic tool execution layer for the RetailOps LangGraph agent."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Protocol

from retailops_ai.agent.knowledge import KnowledgeRetriever
from retailops_ai.agent.schemas import AgentPlan, AnalyticsRequest, EntityRef


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
                trace.append({"tool": tool, "status": "skipped_duplicate", "signature": signature})
                return
            signatures.append(signature)
            try:
                result = callback()
                evidence.append(
                    {
                        "source": tool,
                        "kind": "tool_result",
                        "data": _jsonable(result),
                    }
                )
                trace.append({"tool": tool, "status": "ok", "signature": signature})
            except Exception as exc:  # deterministic failure is evidence, not fabricated data
                evidence.append(
                    {
                        "source": f"{tool}:error",
                        "kind": "tool_error",
                        "data": {"message": str(exc)},
                    }
                )
                trace.append({"tool": tool, "status": "error", "signature": signature})

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
