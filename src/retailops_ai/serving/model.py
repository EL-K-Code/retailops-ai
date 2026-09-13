"""Shared model-artifact loading for Vertex and Cloud Run serving."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import lightgbm as lgb

from retailops_ai.mlops.artifacts import download_directory_from_gcs


@dataclass(frozen=True)
class LoadedForecastModel:
    """Loaded LightGBM booster and the metadata required for inference."""

    booster: lgb.Booster
    category_levels: dict[str, tuple[str, ...]]
    metadata: dict[str, Any]

    def summary(self) -> dict[str, Any]:
        """Return non-sensitive model metadata safe to expose through an API."""
        keys = (
            "model_name",
            "model_version",
            "run_name",
            "created_at",
            "training_start",
            "training_end",
            "train_lookback_days",
            "num_boost_round",
            "mae",
            "rmse",
            "mean_rmsse",
        )
        return {key: self.metadata.get(key) for key in keys if key in self.metadata}


def _resolve_artifact_directory(
    *,
    artifact_uri: str | None,
    local_dir: str | Path | None,
    cache_dir: str | Path,
) -> Path:
    if local_dir:
        path = Path(local_dir)
        if not path.is_dir():
            raise RuntimeError(f"MODEL_LOCAL_DIR does not exist: {path}")
        return path

    if not artifact_uri:
        raise RuntimeError("MODEL_ARTIFACT_URI/AIP_STORAGE_URI or MODEL_LOCAL_DIR is required")

    if artifact_uri.startswith("gs://"):
        destination = Path(cache_dir)
        shutil.rmtree(destination, ignore_errors=True)
        destination.mkdir(parents=True, exist_ok=True)
        downloaded = download_directory_from_gcs(artifact_uri, destination)
        if not downloaded:
            raise RuntimeError(f"No model artifacts found under {artifact_uri}")
        return destination

    path = Path(artifact_uri)
    if not path.is_dir():
        raise RuntimeError(f"Model artifact directory does not exist: {path}")
    return path


def load_forecast_model(
    *,
    artifact_uri: str | None = None,
    local_dir: str | Path | None = None,
    cache_dir: str | Path = "/tmp/retailops-model",
) -> LoadedForecastModel:
    """Load a model from GCS or a local artifact directory."""
    artifact_dir = _resolve_artifact_directory(
        artifact_uri=artifact_uri,
        local_dir=local_dir,
        cache_dir=cache_dir,
    )
    model_path = artifact_dir / "model.txt"
    metadata_path = artifact_dir / "metadata.json"
    if not model_path.is_file() or not metadata_path.is_file():
        raise RuntimeError(f"Expected model.txt and metadata.json under {artifact_dir}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    raw_levels = metadata.get("category_levels")
    if not isinstance(raw_levels, dict):
        raise RuntimeError("metadata.json is missing category_levels")

    category_levels: dict[str, tuple[str, ...]] = {}
    for column, values in raw_levels.items():
        if not isinstance(values, list):
            raise RuntimeError(f"Invalid category_levels entry for {column}")
        category_levels[str(column)] = tuple(str(value) for value in values)

    return LoadedForecastModel(
        booster=lgb.Booster(model_file=str(model_path)),
        category_levels=category_levels,
        metadata=metadata,
    )
