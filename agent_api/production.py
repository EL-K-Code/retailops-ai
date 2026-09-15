"""Production FastAPI entrypoint for the durable RetailOps agent and operator console."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from agent_api.app import create_app
from retailops_ai.agent.production import ProductionAgentRuntime, build_production_runtime
from retailops_ai.agent.schemas import AnalyticsRequest, ForecastToolRequest

app = create_app(runtime_factory=build_production_runtime)


def _runtime(request: Request) -> ProductionAgentRuntime:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None:
        raise HTTPException(status_code=503, detail="Agent service not ready")
    return runtime


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or str(uuid4())


@app.get("/v1/ops/status")
def ops_status(request: Request) -> dict[str, Any]:
    runtime = _runtime(request)
    return {
        "service": "retailops-agent",
        "environment": os.getenv("RETAILOPS_ENV", "local"),
        "release": os.getenv("RETAILOPS_RELEASE", "dev"),
        "checkpoint_backend": runtime.checkpointer_backend,
        "durable_state": runtime.durable_state,
        "ready": True,
    }


@app.get("/v1/console/overview")
def console_overview(
    request: Request,
    split: Literal["validation", "test"] = "test",
) -> dict[str, Any]:
    """Return live KPI, ranking and model data used by the React dashboard."""
    runtime = _runtime(request)
    request_id = _request_id(request)
    try:
        return {
            "split": split,
            "sales_summary": runtime.analytics(
                AnalyticsRequest(operation="sales_summary", split=split)
            ),
            "store_summary": runtime.analytics(
                AnalyticsRequest(operation="store_summary", split=split)
            ),
            "top_products": runtime.analytics(
                AnalyticsRequest(operation="top_products", split=split, top_n=8)
            ),
            "baseline_metrics": runtime.analytics(
                AnalyticsRequest(operation="baseline_metrics", split=split)
            ),
            "model": runtime.model_info(request_id=request_id),
        }
    except Exception as exc:  # pragma: no cover - deployed dependency path
        raise HTTPException(status_code=502, detail=f"Console overview failed: {exc}") from exc


@app.post("/v1/console/analytics")
def console_analytics(payload: AnalyticsRequest, request: Request) -> dict[str, Any]:
    runtime = _runtime(request)
    try:
        return runtime.analytics(payload)
    except Exception as exc:  # pragma: no cover - deployed dependency path
        raise HTTPException(status_code=502, detail=f"Analytics request failed: {exc}") from exc


@app.post("/v1/console/forecast")
def console_forecast(payload: ForecastToolRequest, request: Request) -> dict[str, Any]:
    runtime = _runtime(request)
    try:
        return runtime.forecast(payload, request_id=_request_id(request))
    except Exception as exc:  # pragma: no cover - deployed dependency path
        raise HTTPException(status_code=502, detail=f"Forecast request failed: {exc}") from exc


@app.get("/v1/console/model")
def console_model(request: Request) -> dict[str, Any]:
    runtime = _runtime(request)
    try:
        return runtime.model_info(request_id=_request_id(request))
    except Exception as exc:  # pragma: no cover - deployed dependency path
        raise HTTPException(status_code=502, detail=f"Model info request failed: {exc}") from exc


@app.get("/v1/console/knowledge")
def console_knowledge(request: Request) -> dict[str, Any]:
    runtime = _runtime(request)
    return {"documents": runtime.knowledge_documents()}


_console_dir = Path(os.getenv("RETAILOPS_CONSOLE_DIR", "web_dist"))
if _console_dir.exists():

    @app.get("/", include_in_schema=False)
    def console_root() -> RedirectResponse:
        return RedirectResponse(url="/console/")

    app.mount(
        "/console",
        StaticFiles(directory=str(_console_dir), html=True),
        name="retailops-console",
    )
