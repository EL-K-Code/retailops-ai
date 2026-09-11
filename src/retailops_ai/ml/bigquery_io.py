"""BigQuery input/output helpers for RetailOps AI machine learning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import pandas as pd

from retailops_ai.ml.contracts import M5_DEMAND_FORECAST_CONTRACT
from retailops_ai.ml.lightgbm_pipeline import MODEL_FEATURES

TRAINING_QUERY_COLUMNS = (
    "series_id",
    "date",
    "units_sold",
    *MODEL_FEATURES,
)


@dataclass(frozen=True)
class BigQueryMLConfig:
    """BigQuery locations and resource controls used by the Python ML pipeline."""

    project: str
    location: str
    dbt_dataset: str
    train_lookback_days: int = 180
    use_storage_api: bool = False

    def __post_init__(self) -> None:
        if not self.project:
            raise ValueError("project is required")
        if not self.location:
            raise ValueError("location is required")
        if not self.dbt_dataset:
            raise ValueError("dbt_dataset is required")
        if self.train_lookback_days < 28:
            raise ValueError("train_lookback_days must be at least 28")

    @property
    def ml_dataset(self) -> str:
        return f"{self.dbt_dataset}_ml"

    def table(self, name: str) -> str:
        return f"{self.project}.{self.ml_dataset}.{name}"


def training_window(config: BigQueryMLConfig) -> tuple[date, date]:
    """Return the bounded recent training window used by the first local model."""
    train_end = M5_DEMAND_FORECAST_CONTRACT.train.end
    train_start = train_end - timedelta(days=config.train_lookback_days - 1)
    return max(train_start, M5_DEMAND_FORECAST_CONTRACT.train.start), train_end


def build_training_query(config: BigQueryMLConfig) -> str:
    """Build the partition-prunable training query."""
    columns = ",\n    ".join(TRAINING_QUERY_COLUMNS)
    return f"""
select
    {columns}
from `{config.table('ml_training_features')}`
where date between @train_start and @train_end
order by date, series_id
""".strip()


def _bigquery() -> Any:
    from google.cloud import bigquery

    return bigquery


def _query_dataframe(
    client: Any,
    query: str,
    parameters: list[Any] | None,
    *,
    location: str,
    use_storage_api: bool,
) -> pd.DataFrame:
    bq = _bigquery()
    job_config = bq.QueryJobConfig(query_parameters=parameters or [])
    rows = client.query(query, job_config=job_config, location=location).result()
    return rows.to_dataframe(create_bqstorage_client=use_storage_api)


def load_training_frame(client: Any, config: BigQueryMLConfig) -> pd.DataFrame:
    """Load the bounded training feature window from BigQuery."""
    bq = _bigquery()
    start, end = training_window(config)
    return _query_dataframe(
        client,
        build_training_query(config),
        [
            bq.ScalarQueryParameter("train_start", "DATE", start),
            bq.ScalarQueryParameter("train_end", "DATE", end),
        ],
        location=config.location,
        use_storage_api=config.use_storage_api,
    )


def load_seed_history(client: Any, config: BigQueryMLConfig) -> pd.DataFrame:
    """Load the final 28 observed training days required by recursive inference."""
    bq = _bigquery()
    train_end = M5_DEMAND_FORECAST_CONTRACT.train.end
    seed_start = train_end - timedelta(days=27)
    query = f"""
select series_id, date, units_sold
from `{config.table('ml_demand_split')}`
where dataset_split = 'train'
  and date between @seed_start and @train_end
order by series_id, date
""".strip()
    return _query_dataframe(
        client,
        query,
        [
            bq.ScalarQueryParameter("seed_start", "DATE", seed_start),
            bq.ScalarQueryParameter("train_end", "DATE", train_end),
        ],
        location=config.location,
        use_storage_api=config.use_storage_api,
    )


def load_forecast_covariates(
    client: Any,
    config: BigQueryMLConfig,
    split: str = "validation",
) -> pd.DataFrame:
    """Load target-free covariates for validation or test inference."""
    bq = _bigquery()
    if split not in {"validation", "test"}:
        raise ValueError("split must be validation or test")
    query = f"""
select *
from `{config.table('ml_forecast_covariates')}`
where dataset_split = @split
order by date, series_id
""".strip()
    return _query_dataframe(
        client,
        query,
        [bq.ScalarQueryParameter("split", "STRING", split)],
        location=config.location,
        use_storage_api=config.use_storage_api,
    )


def load_validation_actuals(client: Any, config: BigQueryMLConfig) -> pd.DataFrame:
    """Load validation labels only after recursive predictions have been generated."""
    query = f"""
select series_id, date, units_sold
from `{config.table('ml_demand_split')}`
where dataset_split = 'validation'
order by date, series_id
""".strip()
    return _query_dataframe(
        client,
        query,
        None,
        location=config.location,
        use_storage_api=config.use_storage_api,
    )


def load_rmsse_scales(client: Any, config: BigQueryMLConfig) -> pd.DataFrame:
    """Load the train-only RMSSE denominator for each bottom-level series."""
    query = f"select series_id, rmsse_scale from `{config.table('ml_rmsse_scale')}`"
    return _query_dataframe(
        client,
        query,
        None,
        location=config.location,
        use_storage_api=config.use_storage_api,
    )


def load_baseline_metrics(client: Any, config: BigQueryMLConfig) -> pd.DataFrame:
    """Load the existing baseline comparison table for console reporting."""
    query = f"""
select baseline, mae, rmse, mean_rmsse
from `{config.table('ml_baseline_metrics')}`
order by mean_rmsse
""".strip()
    return _query_dataframe(
        client,
        query,
        None,
        location=config.location,
        use_storage_api=config.use_storage_api,
    )


def write_predictions(client: Any, config: BigQueryMLConfig, predictions: pd.DataFrame) -> None:
    """Append one versioned prediction run to BigQuery."""
    bq = _bigquery()
    table_id = config.table("ml_forecast_predictions")
    schema = [
        bq.SchemaField("run_id", "STRING", mode="REQUIRED"),
        bq.SchemaField("model_name", "STRING", mode="REQUIRED"),
        bq.SchemaField("model_version", "STRING", mode="REQUIRED"),
        bq.SchemaField("evaluation_split", "STRING", mode="REQUIRED"),
        bq.SchemaField("forecast_origin", "DATE", mode="REQUIRED"),
        bq.SchemaField("forecast_date", "DATE", mode="REQUIRED"),
        bq.SchemaField("horizon", "INTEGER", mode="REQUIRED"),
        bq.SchemaField("series_id", "STRING", mode="REQUIRED"),
        bq.SchemaField("item_id", "STRING", mode="REQUIRED"),
        bq.SchemaField("store_id", "STRING", mode="REQUIRED"),
        bq.SchemaField("prediction", "FLOAT", mode="REQUIRED"),
        bq.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    job_config = bq.LoadJobConfig(
        schema=schema,
        create_disposition=bq.CreateDisposition.CREATE_IF_NEEDED,
        write_disposition=bq.WriteDisposition.WRITE_APPEND,
    )
    client.load_table_from_dataframe(
        predictions,
        table_id,
        job_config=job_config,
        location=config.location,
    ).result()


def write_evaluation(client: Any, config: BigQueryMLConfig, evaluation: pd.DataFrame) -> None:
    """Append one model-evaluation row to BigQuery."""
    bq = _bigquery()
    table_id = config.table("ml_model_evaluation")
    schema = [
        bq.SchemaField("run_id", "STRING", mode="REQUIRED"),
        bq.SchemaField("model_name", "STRING", mode="REQUIRED"),
        bq.SchemaField("model_version", "STRING", mode="REQUIRED"),
        bq.SchemaField("evaluation_split", "STRING", mode="REQUIRED"),
        bq.SchemaField("training_start", "DATE", mode="REQUIRED"),
        bq.SchemaField("training_end", "DATE", mode="REQUIRED"),
        bq.SchemaField("train_lookback_days", "INTEGER", mode="REQUIRED"),
        bq.SchemaField("training_rows", "INTEGER", mode="REQUIRED"),
        bq.SchemaField("evaluated_observations", "INTEGER", mode="REQUIRED"),
        bq.SchemaField("evaluated_series", "INTEGER", mode="REQUIRED"),
        bq.SchemaField("mae", "FLOAT", mode="REQUIRED"),
        bq.SchemaField("rmse", "FLOAT", mode="REQUIRED"),
        bq.SchemaField("mean_rmsse", "FLOAT", mode="REQUIRED"),
        bq.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    job_config = bq.LoadJobConfig(
        schema=schema,
        create_disposition=bq.CreateDisposition.CREATE_IF_NEEDED,
        write_disposition=bq.WriteDisposition.WRITE_APPEND,
    )
    client.load_table_from_dataframe(
        evaluation,
        table_id,
        job_config=job_config,
        location=config.location,
    ).result()
