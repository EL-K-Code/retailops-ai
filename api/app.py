"""FastAPI business API for RetailOps demand forecasting."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field

from retailops_ai.serving.repository import EntityKey
from retailops_ai.serving.runtime import ServingRuntime, build_runtime
from retailops_ai.serving.service import ForecastBatch, UnknownSeriesError

LOGGER = logging.getLogger("uvicorn.error").getChild("retailops.api")
LOGGER.setLevel(logging.INFO)
RuntimeFactory = Callable[[], ServingRuntime]


class ForecastEntityRequest(BaseModel):
    item_id: str = Field(min_length=1, max_length=128)
    store_id: str = Field(min_length=1, max_length=128)


class ForecastRequest(BaseModel):
    entities: list[ForecastEntityRequest] = Field(min_length=1, max_length=100)
    split: Literal["validation", "test"] = "test"


class ForecastPointResponse(BaseModel):
    date: str
    horizon: int
    prediction: float


class SeriesForecastResponse(BaseModel):
    series_id: str
    item_id: str
    store_id: str
    points: list[ForecastPointResponse]


class ForecastResponse(BaseModel):
    request_id: str
    split: str
    forecast_origin: str
    horizon_days: int
    generated_at: str
    model: dict[str, object]
    forecasts: list[SeriesForecastResponse]


def _serialize_forecast(batch: ForecastBatch, request_id: str) -> ForecastResponse:
    return ForecastResponse(
        request_id=request_id,
        split=batch.split,
        forecast_origin=batch.forecast_origin.isoformat(),
        horizon_days=batch.horizon_days,
        generated_at=batch.generated_at.isoformat(),
        model=batch.model,
        forecasts=[
            SeriesForecastResponse(
                series_id=forecast.series_id,
                item_id=forecast.item_id,
                store_id=forecast.store_id,
                points=[
                    ForecastPointResponse(
                        date=point.date.isoformat(),
                        horizon=point.horizon,
                        prediction=point.prediction,
                    )
                    for point in forecast.points
                ],
            )
            for forecast in batch.forecasts
        ],
    )


def create_app(runtime_factory: RuntimeFactory = build_runtime) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            app.state.runtime = runtime_factory()
            app.state.startup_error = None
            LOGGER.info("RetailOps API runtime initialized")
        except Exception as exc:  # pragma: no cover - exercised in deployed runtime
            app.state.runtime = None
            app.state.startup_error = str(exc)
            LOGGER.exception("RetailOps API runtime initialization failed")
        yield
        app.state.runtime = None

    application = FastAPI(
        title="RetailOps AI Forecasting API",
        version="1.0.0",
        description=(
            "Business-facing 28-day demand forecasting API backed by BigQuery "
            "features and a versioned LightGBM model artifact."
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
        elapsed_ms = (time.perf_counter() - started) * 1000
        LOGGER.info(
            "request method=%s path=%s status=%s latency_ms=%.2f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
        )
        return response

    def require_runtime(request: Request) -> ServingRuntime:
        runtime = getattr(request.app.state, "runtime", None)
        if runtime is None:
            raise HTTPException(status_code=503, detail="Service not ready")
        return runtime

    @application.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/readyz")
    def readyz(request: Request) -> dict[str, str]:
        require_runtime(request)
        return {"status": "ready"}

    @application.get("/v1/model")
    def model_info(request: Request) -> dict[str, object]:
        runtime = require_runtime(request)
        return runtime.model.summary()

    @application.post("/v1/forecast", response_model=ForecastResponse)
    def forecast(payload: ForecastRequest, request: Request) -> ForecastResponse:
        runtime = require_runtime(request)
        entities = [
            EntityKey(item_id=entity.item_id, store_id=entity.store_id)
            for entity in payload.entities
        ]
        try:
            result = runtime.service.forecast(entities, split=payload.split)
        except UnknownSeriesError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return _serialize_forecast(result, request.state.request_id)

    return application


app = create_app()
