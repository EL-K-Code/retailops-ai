"""Vertex-compatible prediction container for the RetailOps LightGBM model."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

import numpy as np
import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from retailops_ai.ml.lightgbm_pipeline import prepare_model_frame
from retailops_ai.serving.model import LoadedForecastModel, load_forecast_model


class PredictionRequest(BaseModel):
    instances: list[dict[str, Any]] = Field(min_length=1)


_MODEL: LoadedForecastModel | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _MODEL
    _MODEL = load_forecast_model(
        artifact_uri=os.getenv("AIP_STORAGE_URI"),
        local_dir=os.getenv("MODEL_LOCAL_DIR"),
        cache_dir=os.getenv("MODEL_CACHE_DIR", "/tmp/retailops-model"),
    )
    yield
    _MODEL = None


app = FastAPI(
    title="RetailOps LightGBM Prediction Container",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok" if _MODEL is not None else "loading"}


@app.post("/predict")
def predict(request: PredictionRequest) -> dict[str, list[float]]:
    if _MODEL is None:
        raise HTTPException(status_code=503, detail="Model is not loaded")

    frame = pd.DataFrame(request.instances)
    try:
        model_frame, _ = prepare_model_frame(frame, _MODEL.category_levels)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    predictions = np.asarray(_MODEL.booster.predict(model_frame), dtype="float64")
    predictions = np.clip(predictions, 0.0, None)
    return {"predictions": predictions.tolist()}


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("AIP_HTTP_PORT", "8080")),
    )
