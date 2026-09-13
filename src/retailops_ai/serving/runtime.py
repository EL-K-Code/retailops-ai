"""Runtime assembly for the Cloud Run forecasting API."""

from __future__ import annotations

import os
from dataclasses import dataclass

from retailops_ai.serving.model import LoadedForecastModel, load_forecast_model
from retailops_ai.serving.repository import BigQueryForecastRepository, ServingRepositoryConfig
from retailops_ai.serving.service import ForecastService


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ServingRuntimeConfig:
    project: str
    location: str
    dbt_dataset: str
    model_artifact_uri: str | None
    model_local_dir: str | None
    model_cache_dir: str
    max_entities: int
    use_storage_api: bool

    @classmethod
    def from_env(cls) -> ServingRuntimeConfig:
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
        if not project:
            raise RuntimeError("GOOGLE_CLOUD_PROJECT is required")

        model_artifact_uri = os.getenv("MODEL_ARTIFACT_URI")
        model_local_dir = os.getenv("MODEL_LOCAL_DIR")
        if not model_artifact_uri and not model_local_dir:
            raise RuntimeError("MODEL_ARTIFACT_URI or MODEL_LOCAL_DIR is required")

        max_entities = int(os.getenv("SERVING_MAX_ENTITIES", "50"))
        if max_entities <= 0:
            raise RuntimeError("SERVING_MAX_ENTITIES must be positive")

        return cls(
            project=project,
            location=os.getenv("BQ_LOCATION", "us-central1"),
            dbt_dataset=os.getenv("BQ_DBT_DATASET", "retailops"),
            model_artifact_uri=model_artifact_uri,
            model_local_dir=model_local_dir,
            model_cache_dir=os.getenv("MODEL_CACHE_DIR", "/tmp/retailops-model"),
            max_entities=max_entities,
            use_storage_api=_env_bool("ML_USE_BQ_STORAGE_API", False),
        )


@dataclass(frozen=True)
class ServingRuntime:
    config: ServingRuntimeConfig
    model: LoadedForecastModel
    service: ForecastService


def build_runtime(config: ServingRuntimeConfig | None = None) -> ServingRuntime:
    """Build the long-lived model and BigQuery clients once per container instance."""
    from google.cloud import bigquery

    resolved = config or ServingRuntimeConfig.from_env()
    model = load_forecast_model(
        artifact_uri=resolved.model_artifact_uri,
        local_dir=resolved.model_local_dir,
        cache_dir=resolved.model_cache_dir,
    )
    client = bigquery.Client(project=resolved.project, location=resolved.location)
    repository = BigQueryForecastRepository(
        client,
        ServingRepositoryConfig(
            project=resolved.project,
            location=resolved.location,
            dbt_dataset=resolved.dbt_dataset,
            use_storage_api=resolved.use_storage_api,
        ),
    )
    service = ForecastService(
        model=model,
        repository=repository,
        max_entities=resolved.max_entities,
    )
    return ServingRuntime(config=resolved, model=model, service=service)
