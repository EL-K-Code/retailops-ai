"""Production entrypoint for the RetailOps forecasting API."""

from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException, Request

from api.app import create_app

app = create_app()


@app.get("/v1/ops/status")
def ops_status(request: Request) -> dict[str, Any]:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {
        "service": "retailops-forecast-api",
        "environment": os.getenv("RETAILOPS_ENV", "local"),
        "release": os.getenv("RETAILOPS_RELEASE", "dev"),
        "ready": True,
        "model": runtime.model.summary(),
    }
