"""Production runtime factory for the RetailOps decision agent."""

from __future__ import annotations

from dataclasses import dataclass
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
from retailops_ai.agent.schemas import AgentRunResult
from retailops_ai.agent.tools import AgentToolbox


@dataclass
class ProductionAgentRuntime:
    runtime: AgentRuntime
    checkpoint: CheckpointerHandle

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
    return ProductionAgentRuntime(runtime=AgentRuntime(graph), checkpoint=checkpoint)
