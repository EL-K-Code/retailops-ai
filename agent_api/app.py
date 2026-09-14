"""FastAPI surface for the RetailOps LangGraph decision-support agent."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field

from retailops_ai.agent.runtime import AgentRuntime, build_agent_runtime
from retailops_ai.agent.schemas import AgentRunResult

LOGGER = logging.getLogger("uvicorn.error").getChild("retailops.agent_api")
LOGGER.setLevel(logging.INFO)
RuntimeFactory = Callable[[], AgentRuntime]


class AgentQueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    user_context: dict[str, Any] = Field(default_factory=dict)
    thread_id: str | None = Field(default=None, max_length=128)


class AgentResumeRequest(BaseModel):
    thread_id: str = Field(min_length=1, max_length=128)
    approved: bool
    reviewer_note: str | None = Field(default=None, max_length=1000)


def create_app(runtime_factory: RuntimeFactory = build_agent_runtime) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            app.state.runtime = runtime_factory()
            app.state.startup_error = None
            LOGGER.info("RetailOps Agent runtime initialized")
        except Exception as exc:  # pragma: no cover - deployed environment path
            app.state.runtime = None
            app.state.startup_error = str(exc)
            LOGGER.exception("RetailOps Agent runtime initialization failed")
        yield
        app.state.runtime = None

    application = FastAPI(
        title="RetailOps AI Decision Agent",
        version="1.0.0",
        description=(
            "Grounded LangGraph decision-support agent using the RetailOps forecasting API, "
            "allowlisted BigQuery analytics, curated RAG context, and human approval gates."
        ),
        lifespan=lifespan,
    )

    @application.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response: Response = await call_next(request)
        response.headers["x-request-id"] = request_id
        LOGGER.info(
            "agent_request method=%s path=%s status=%s latency_ms=%.2f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
            request_id,
        )
        return response

    def require_runtime(request: Request) -> AgentRuntime:
        runtime = getattr(request.app.state, "runtime", None)
        if runtime is None:
            raise HTTPException(status_code=503, detail="Agent service not ready")
        return runtime

    @application.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/readyz")
    def readyz(request: Request) -> dict[str, str]:
        require_runtime(request)
        return {"status": "ready"}

    @application.get("/v1/agent/capabilities")
    def capabilities() -> dict[str, Any]:
        return {
            "agent": "retailops-decision-agent",
            "mode": "read-only decision support",
            "tools": ["forecast_api", "bigquery_analytics", "model_info", "knowledge_rag"],
            "analytics_sql": "allowlisted templates only",
            "human_in_the_loop": True,
            "mutating_actions": False,
        }

    @application.post("/v1/agent/query", response_model=AgentRunResult)
    def query(payload: AgentQueryRequest, request: Request) -> AgentRunResult:
        runtime = require_runtime(request)
        try:
            return runtime.ask(
                question=payload.question,
                user_context=payload.user_context,
                thread_id=payload.thread_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @application.post("/v1/agent/resume", response_model=AgentRunResult)
    def resume(payload: AgentResumeRequest, request: Request) -> AgentRunResult:
        runtime = require_runtime(request)
        try:
            return runtime.resume(
                thread_id=payload.thread_id,
                approved=payload.approved,
                reviewer_note=payload.reviewer_note,
            )
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=409, detail="Unable to resume agent thread") from exc

    return application


app = create_app()
