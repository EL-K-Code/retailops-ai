"""Vertex-compatible prediction container for the RetailOps LightGBM model."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from retailops_ai.ml.lightgbm_pipeline import prepare_model_frame
from retailops_ai.mlops.artifacts import download_directory_from_gcs


@dataclass(frozen=True)
class LoadedModel:
    booster: lgb.Booster
    category_levels: dict[str, tuple[str, ...]]


class PredictionRequest(BaseModel):
    instances: list[dict[str, Any]] = Field(min_length=1)


_MODEL: LoadedModel | None = None


def _artifact_directory() -> Path:
    local_override = os.getenv("MODEL_LOCAL_DIR")
    if local_override:
        return Path(local_override)

    storage_uri = os.getenv("AIP_STORAGE_URI")
    if not storage_uri:
        raise RuntimeError("AIP_STORAGE_URI or MODEL_LOCAL_DIR is required")

    local_dir = Path("/tmp/retailops-model")
    download_directory_from_gcs(storage_uri, local_dir)
    return local_dir


def _load_model() -> LoadedModel:
    artifact_dir = _artifact_directory()
    model_path = artifact_dir / "model.txt"
    metadata_path = artifact_dir / "metadata.json"
    if not model_path.exists() or not metadata_path.exists():
        raise RuntimeError(f"Expected model.txt and metadata.json under {artifact_dir}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    raw_levels = metadata.get("category_levels")
    if not isinstance(raw_levels, dict):
        raise RuntimeError("metadata.json is missing category_levels")

    category_levels = {
        str(column): tuple(str(value) for value in values)
        for column, values in raw_levels.items()
    }
    return LoadedModel(
        booster=lgb.Booster(model_file=str(model_path)),
        category_levels=category_levels,
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _MODEL
    _MODEL = _load_model()
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
