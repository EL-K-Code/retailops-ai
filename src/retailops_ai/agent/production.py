"""Production runtime factory for the RetailOps decision agent."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google.cloud import bigquery

from retailops_ai.agent.analytics import AnalyticsConfig, RetailAnalyticsTool
from retailops_ai.agent.checkpointing import (
    CheckpointerConfig,
    CheckpointerHandle,
    open_checkpointer,
)
from retailops_ai.agent.clients import ForecastServiceClient
from retailops_ai.agent.graph import AgentGraphDependencies, build_agent_graph
from retailops_ai.agent.knowledge import LexicalKnowledgeRetriever, load_markdown_chunks
from retailops_ai.agent.llm import GeminiDecisionLLM
from retailops_ai.agent.runtime import AgentRuntime, AgentRuntimeConfig
from retailops_ai.agent.schemas import AgentRunResult, AnalyticsRequest, ForecastToolRequest
from retailops_ai.agent.tools import AgentToolbox
from retailops_ai.decision.inventory import (
    InventoryScenario,
    recommend_inventory_counterfactuals,
    simulate_inventory,
)
from retailops_ai.decision.reorder import ReorderEconomics, optimize_reorder_scenario
from retailops_ai.decision.uncertainty import (
    band_as_forecast_points,
    poisson_predictive_band,
)
from retailops_ai.monitoring.drift import demand_distribution_drift


@dataclass
class ProductionAgentRuntime:
    runtime: AgentRuntime
    checkpoint: CheckpointerHandle
    analytics_tool: RetailAnalyticsTool
    forecast_client: ForecastServiceClient
    knowledge_dir: Path

    @property
    def checkpointer_backend(self) -> str:
        return self.checkpoint.backend

    @property
    def durable_state(self) -> bool:
        return self.checkpoint.durable

    def ask(
        self,
        *,
        question: str,
        user_context: dict[str, Any] | None = None,
        thread_id: str | None = None,
    ) -> AgentRunResult:
        return self.runtime.ask(
            question=question,
            user_context=user_context,
            thread_id=thread_id,
        )

    def resume(
        self,
        *,
        thread_id: str,
        approved: bool,
        reviewer_note: str | None = None,
    ) -> AgentRunResult:
        return self.runtime.resume(
            thread_id=thread_id,
            approved=approved,
            reviewer_note=reviewer_note,
        )

    def analytics(self, request: AnalyticsRequest) -> dict[str, Any]:
        return self.analytics_tool.run(request)

    def forecast(self, request: ForecastToolRequest, *, request_id: str) -> dict[str, Any]:
        return self.forecast_client.forecast(
            entities=request.entities,
            split=request.split,
            request_id=request_id,
        )

    def explain_forecast(
        self,
        request: ForecastToolRequest,
        *,
        request_id: str,
        top_n: int = 6,
    ) -> dict[str, Any]:
        return self.forecast_client.explain(
            entities=request.entities,
            split=request.split,
            request_id=request_id,
            top_n=top_n,
        )

    def inventory_scenario(
        self,
        request: ForecastToolRequest,
        scenario: InventoryScenario,
        *,
        request_id: str,
        economics: ReorderEconomics | None = None,
    ) -> dict[str, Any]:
        forecast = self.forecast(request, request_id=request_id)
        forecasts = forecast.get("forecasts") or []
        if len(forecasts) != 1:
            raise ValueError("Inventory scenario requires exactly one item/store entity")
        points = forecasts[0].get("points") or forecasts[0].get("predictions") or []
        simulation = simulate_inventory(points, scenario)
        uncertainty = poisson_predictive_band(points)
        stress = simulate_inventory(
            band_as_forecast_points(uncertainty, level="upper"),
            scenario,
        )
        response: dict[str, Any] = {
            "request_id": forecast.get("request_id", request_id),
            "split": forecast.get("split", request.split),
            "forecast_origin": forecast.get("forecast_origin"),
            "horizon_days": forecast.get("horizon_days", len(points)),
            "model": forecast.get("model", {}),
            "entity": {
                "series_id": forecasts[0].get("series_id"),
                "item_id": forecasts[0].get("item_id"),
                "store_id": forecasts[0].get("store_id"),
            },
            "scenario": {
                "current_stock": scenario.current_stock,
                "incoming_units": scenario.incoming_units,
                "lead_time_days": scenario.lead_time_days,
                "safety_stock": scenario.safety_stock,
            },
            **simulation,
            "counterfactuals": recommend_inventory_counterfactuals(points, scenario),
            "uncertainty": uncertainty,
            "upper_demand_stress": {
                "risk_level": stress["risk_level"],
                "projected_end_inventory": stress["projected_end_inventory"],
                "stockout_day": stress["stockout_day"],
                "safety_breach_day": stress["safety_breach_day"],
            },
        }
        if economics is not None:
            response["reorder_optimization"] = optimize_reorder_scenario(
                points,
                scenario,
                economics,
            )
        return response

    def demand_drift(
        self,
        *,
        item_id: str | None = None,
        store_id: str | None = None,
    ) -> dict[str, Any]:
        reference = self.analytics(
            AnalyticsRequest(
                operation="daily_demand",
                split="validation",
                item_id=item_id,
                store_id=store_id,
            )
        )
        current = self.analytics(
            AnalyticsRequest(
                operation="daily_demand",
                split="test",
                item_id=item_id,
                store_id=store_id,
            )
        )
        reference_values = [
            float(row["daily_units"])
            for row in reference.get("rows", [])
            if row.get("daily_units") is not None
        ]
        current_values = [
            float(row["daily_units"])
            for row in current.get("rows", [])
            if row.get("daily_units") is not None
        ]
        return demand_distribution_drift(reference_values, current_values)

    def morning_brief(
        self,
        *,
        split: str,
        request_id: str,
    ) -> dict[str, Any]:
        anomalies = self.analytics(
            AnalyticsRequest(operation="demand_anomalies", split=split, top_n=8)
        )
        top_products = self.analytics(
            AnalyticsRequest(operation="top_products", split=split, top_n=5)
        )
        priorities: list[dict[str, Any]] = []
        for row in anomalies.get("rows", []):
            z_score = float(row.get("anomaly_z") or 0.0)
            magnitude = abs(z_score)
            severity = "critical" if magnitude >= 5 else "high" if magnitude >= 4 else "watch"
            priorities.append(
                {
                    "severity": severity,
                    "type": "demand_spike" if z_score > 0 else "demand_drop",
                    "item_id": row.get("item_id"),
                    "store_id": row.get("store_id"),
                    "date": row.get("date"),
                    "units_sold": row.get("units_sold"),
                    "rolling_mean_28": row.get("rolling_mean_28"),
                    "anomaly_z": z_score,
                }
            )
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "split": split,
            "priorities": priorities,
            "top_products": top_products,
            "demand_drift": self.demand_drift(),
            "model": self.model_info(request_id=request_id),
            "limitations": [
                (
                    "Inventory risk is not ranked automatically because M5 has no true "
                    "operational stock, purchase orders or supplier lead times."
                ),
                (
                    "Use Decision Lab or the Copilot with explicit scenario inputs for "
                    "stockout and replenishment analysis."
                ),
            ],
        }

    def model_info(self, *, request_id: str) -> dict[str, Any]:
        return self.forecast_client.model_info(request_id=request_id)

    def knowledge_documents(self) -> list[dict[str, Any]]:
        documents: list[dict[str, Any]] = []
        for path in sorted(self.knowledge_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8").strip()
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            title = next(
                (line.lstrip("# ").strip() for line in lines if line.startswith("#")),
                path.stem.replace("_", " ").title(),
            )
            excerpt_lines = [line for line in lines if not line.startswith("#")]
            documents.append(
                {
                    "slug": path.stem,
                    "title": title,
                    "excerpt": " ".join(excerpt_lines)[:900],
                    "characters": len(text),
                }
            )
        return documents

    def close(self) -> None:
        self.checkpoint.close()


def build_production_runtime(config: AgentRuntimeConfig | None = None) -> ProductionAgentRuntime:
    resolved = config or AgentRuntimeConfig.from_env()
    retriever = LexicalKnowledgeRetriever(load_markdown_chunks(resolved.knowledge_dir))
    forecast_client = ForecastServiceClient(
        base_url=resolved.forecast_api_url,
        timeout_seconds=resolved.forecast_timeout_seconds,
        auth_mode=resolved.forecast_auth,
        audience=resolved.forecast_audience,
    )
    analytics = RetailAnalyticsTool(
        bigquery.Client(project=resolved.project, location=resolved.location),
        AnalyticsConfig(
            project=resolved.project,
            location=resolved.location,
            dbt_dataset=resolved.dbt_dataset,
            maximum_bytes_billed=resolved.bq_maximum_bytes_billed,
        ),
    )
    toolbox = AgentToolbox(
        forecast_client=forecast_client,
        analytics_tool=analytics,
        knowledge_retriever=retriever,
        rag_top_k=resolved.rag_top_k,
    )
    checkpoint = open_checkpointer(CheckpointerConfig.from_env())
    graph = build_agent_graph(
        AgentGraphDependencies(
            llm=GeminiDecisionLLM(
                project=resolved.project,
                location=resolved.location,
                model=resolved.model,
            ),
            toolbox=toolbox,
            max_tool_steps=resolved.max_tool_steps,
        ),
        checkpointer=checkpoint.saver,
    )
    return ProductionAgentRuntime(
        runtime=AgentRuntime(graph),
        checkpoint=checkpoint,
        analytics_tool=analytics,
        forecast_client=forecast_client,
        knowledge_dir=resolved.knowledge_dir,
    )
