"""Production FastAPI entrypoint for the durable RetailOps agent."""

from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException, Request

from agent_api.app import create_app
from retailops_ai.agent.production import build_production_runtime

app = create_app(runtime_factory=build_production_runtime)


@app.get("/v1/ops/status")
def ops_status(request: Request) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None:
        raise HTTPException(status_code=503, detail="Agent service not ready")
    return {
        "service": "retailops-agent",
        "environment": os.getenv("RETAILOPS_ENV", "local"),
        "release": os.getenv("RETAILOPS_RELEASE", "dev"),
        "checkpoint_backend": runtime.checkpointer_backend,
        "durable_state": runtime.durable_state,
        "ready": True,
    }
