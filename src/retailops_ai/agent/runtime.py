"""Environment-backed runtime for the RetailOps LangGraph agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from google.cloud import bigquery
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from retailops_ai.agent.analytics import AnalyticsConfig, RetailAnalyticsTool
from retailops_ai.agent.clients import ForecastServiceClient
from retailops_ai.agent.graph import AgentGraphDependencies, build_agent_graph
from retailops_ai.agent.knowledge import (
    LexicalKnowledgeRetriever,
    VertexEmbeddingKnowledgeRetriever,
    load_markdown_chunks,
)
from retailops_ai.agent.llm import GeminiDecisionLLM
from retailops_ai.agent.schemas import AgentRunResult
from retailops_ai.agent.tools import AgentToolbox


@dataclass(frozen=True)
class AgentRuntimeConfig:
    project: str
    location: str
    dbt_dataset: str
    model: str
    forecast_api_url: str
    forecast_auth: str
    forecast_audience: str | None
    forecast_timeout_seconds: float
    knowledge_dir: Path
    rag_backend: str
    embedding_model: str
    rag_top_k: int
    bq_maximum_bytes_billed: int
    max_tool_steps: int

    @classmethod
    def from_env(cls) -> AgentRuntimeConfig:
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
        forecast_api_url = os.getenv("AGENT_FORECAST_API_URL", "")
        if not project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is required")
        if not forecast_api_url:
            raise RuntimeError("AGENT_FORECAST_API_URL is required")

        rag_backend = os.getenv("AGENT_RAG_BACKEND", "lexical").lower()
        if rag_backend not in {"lexical", "vertex"}:
            raise RuntimeError("AGENT_RAG_BACKEND must be lexical or vertex")

        return cls(
            project=project,
            location=os.getenv("AGENT_VERTEX_LOCATION", "us-central1"),
            dbt_dataset=os.getenv("BQ_DBT_DATASET", "retailops"),
            model=os.getenv("AGENT_MODEL", "gemini-2.5-flash"),
            forecast_api_url=forecast_api_url,
            forecast_auth=os.getenv("AGENT_FORECAST_AUTH", "cloud-run"),
            forecast_audience=os.getenv("AGENT_FORECAST_AUDIENCE") or None,
            forecast_timeout_seconds=float(os.getenv("AGENT_FORECAST_TIMEOUT_SECONDS", "20")),
            knowledge_dir=Path(os.getenv("AGENT_KNOWLEDGE_DIR", "knowledge")),
            rag_backend=rag_backend,
            embedding_model=os.getenv("AGENT_EMBEDDING_MODEL", "gemini-embedding-001"),
            rag_top_k=int(os.getenv("AGENT_RAG_TOP_K", "4")),
            bq_maximum_bytes_billed=int(
                os.getenv("AGENT_BQ_MAX_BYTES_BILLED", "500000000")
            ),
            max_tool_steps=int(os.getenv("AGENT_MAX_TOOL_STEPS", "3")),
        )


class AgentRuntime:
    def __init__(self, graph: Any) -> None:
        self.graph = graph

    @staticmethod
    def _config(thread_id: str) -> dict[str, Any]:
        return {"configurable": {"thread_id": thread_id}}

    @staticmethod
    def _format_result(thread_id: str, result: dict[str, Any]) -> AgentRunResult:
        interrupts = result.get("__interrupt__", [])
        evidence_sources = sorted(
            {
                str(item.get("source"))
                for item in result.get("evidence", [])
                if item.get("source")
            }
        )
        tool_trace = list(result.get("tool_trace", []))
        if interrupts:
            first = interrupts[0]
            payload = getattr(first, "value", first)
            return AgentRunResult(
                status="approval_required",
                thread_id=thread_id,
                approval_request=payload,
                evidence_sources=evidence_sources,
                tool_trace=tool_trace,
                active_scenario=result.get("active_scenario"),
            )
        return AgentRunResult(
            status="completed",
            thread_id=thread_id,
            answer=result.get("final_answer"),
            evidence_sources=evidence_sources,
            tool_trace=tool_trace,
            active_scenario=result.get("active_scenario"),
        )

    def ask(
        self,
        *,
        question: str,
        user_context: dict[str, Any] | None = None,
        thread_id: str | None = None,
    ) -> AgentRunResult:
        resolved_thread_id = thread_id or str(uuid4())
        initial_state = {
            "question": question,
            "thread_id": resolved_thread_id,
            "user_context": user_context or {},
            "step_count": 0,
            "evidence": [],
            "executed_signatures": [],
            "tool_trace": [],
        }
        if thread_id:
            snapshot = self.graph.get_state(self._config(resolved_thread_id))
            values = getattr(snapshot, "values", {}) or {}
            if values.get("active_scenario"):
                initial_state["active_scenario"] = values["active_scenario"]
        result = self.graph.invoke(initial_state, config=self._config(resolved_thread_id))
        return self._format_result(resolved_thread_id, result)

    def resume(
        self,
        *,
        thread_id: str,
        approved: bool,
        reviewer_note: str | None = None,
    ) -> AgentRunResult:
        result = self.graph.invoke(
            Command(resume={"approved": approved, "reviewer_note": reviewer_note}),
            config=self._config(thread_id),
        )
        return self._format_result(thread_id, result)


def build_agent_runtime(config: AgentRuntimeConfig | None = None) -> AgentRuntime:
    resolved = config or AgentRuntimeConfig.from_env()
    chunks = load_markdown_chunks(resolved.knowledge_dir)
    if resolved.rag_backend == "vertex":
        retriever = VertexEmbeddingKnowledgeRetriever(
            chunks,
            project=resolved.project,
            location=resolved.location,
            model=resolved.embedding_model,
        )
    else:
        retriever = LexicalKnowledgeRetriever(chunks)

    forecast_client = ForecastServiceClient(
        base_url=resolved.forecast_api_url,
        timeout_seconds=resolved.forecast_timeout_seconds,
        auth_mode=resolved.forecast_auth,
        audience=resolved.forecast_audience,
    )
    analytics_tool = RetailAnalyticsTool(
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
        analytics_tool=analytics_tool,
        knowledge_retriever=retriever,
        rag_top_k=resolved.rag_top_k,
    )
    llm = GeminiDecisionLLM(
        project=resolved.project,
        location=resolved.location,
        model=resolved.model,
    )
    graph = build_agent_graph(
        AgentGraphDependencies(
            llm=llm,
            toolbox=toolbox,
            max_tool_steps=resolved.max_tool_steps,
        ),
        checkpointer=InMemorySaver(),
    )
    return AgentRuntime(graph)
