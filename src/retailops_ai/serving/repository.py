"""BigQuery repository used by the online forecasting service."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import pandas as pd

from retailops_ai.ml.contracts import M5_DEMAND_FORECAST_CONTRACT


@dataclass(frozen=True)
class EntityKey:
    """Business-facing item/store key."""

    item_id: str
    store_id: str


@dataclass(frozen=True)
class ServingRepositoryConfig:
    project: str
    location: str
    dbt_dataset: str
    use_storage_api: bool = False

    def __post_init__(self) -> None:
        if not self.project:
            raise ValueError("project is required")
        if not self.location:
            raise ValueError("location is required")
        if not self.dbt_dataset:
            raise ValueError("dbt_dataset is required")

    @property
    def ml_dataset(self) -> str:
        return f"{self.dbt_dataset}_ml"

    def table(self, name: str) -> str:
        return f"{self.project}.{self.ml_dataset}.{name}"


def seed_window_for_split(split: str) -> tuple[str, date, date]:
    """Return observed-history split and 28-day seed window for a forecast split."""
    contract = M5_DEMAND_FORECAST_CONTRACT
    if split == "validation":
        seed_split = "train"
        seed_end = contract.train.end
    elif split == "test":
        seed_split = "validation"
        seed_end = contract.validation.end
    else:
        raise ValueError("split must be validation or test")

    seed_start = seed_end - timedelta(days=contract.horizon_days - 1)
    return seed_split, seed_start, seed_end


def _bigquery() -> Any:
    from google.cloud import bigquery

    return bigquery


def _query_dataframe(
    client: Any,
    query: str,
    parameters: list[Any],
    *,
    location: str,
    use_storage_api: bool,
) -> pd.DataFrame:
    bq = _bigquery()
    job_config = bq.QueryJobConfig(query_parameters=parameters)
    rows = client.query(query, job_config=job_config, location=location).result()
    return rows.to_dataframe(create_bqstorage_client=use_storage_api)


class BigQueryForecastRepository:
    """Read only the series and time windows required by one API request."""

    def __init__(self, client: Any, config: ServingRepositoryConfig) -> None:
        self.client = client
        self.config = config

    def resolve_series(self, entities: Sequence[EntityKey], split: str) -> pd.DataFrame:
        if not entities:
            raise ValueError("At least one entity is required")
        if split not in {"validation", "test"}:
            raise ValueError("split must be validation or test")

        bq = _bigquery()
        conditions: list[str] = []
        parameters: list[Any] = [bq.ScalarQueryParameter("split", "STRING", split)]
        for index, entity in enumerate(entities):
            item_parameter = f"item_{index}"
            store_parameter = f"store_{index}"
            conditions.append(
                f"(item_id = @{item_parameter} and store_id = @{store_parameter})"
            )
            parameters.extend(
                [
                    bq.ScalarQueryParameter(item_parameter, "STRING", entity.item_id),
                    bq.ScalarQueryParameter(store_parameter, "STRING", entity.store_id),
                ]
            )

        query = f"""
select distinct series_id, item_id, store_id
from `{self.config.table('ml_forecast_covariates')}`
where dataset_split = @split
  and ({' or '.join(conditions)})
order by store_id, item_id
""".strip()
        return _query_dataframe(
            self.client,
            query,
            parameters,
            location=self.config.location,
            use_storage_api=self.config.use_storage_api,
        )

    def load_seed_history(self, series_ids: Sequence[str], split: str) -> pd.DataFrame:
        if not series_ids:
            raise ValueError("At least one series_id is required")

        bq = _bigquery()
        seed_split, seed_start, seed_end = seed_window_for_split(split)
        query = f"""
select series_id, date, units_sold
from `{self.config.table('ml_demand_split')}`
where dataset_split = @seed_split
  and date between @seed_start and @seed_end
  and series_id in unnest(@series_ids)
order by series_id, date
""".strip()
        parameters = [
            bq.ScalarQueryParameter("seed_split", "STRING", seed_split),
            bq.ScalarQueryParameter("seed_start", "DATE", seed_start),
            bq.ScalarQueryParameter("seed_end", "DATE", seed_end),
            bq.ArrayQueryParameter("series_ids", "STRING", list(series_ids)),
        ]
        return _query_dataframe(
            self.client,
            query,
            parameters,
            location=self.config.location,
            use_storage_api=self.config.use_storage_api,
        )

    def load_forecast_covariates(self, series_ids: Sequence[str], split: str) -> pd.DataFrame:
        if not series_ids:
            raise ValueError("At least one series_id is required")
        if split not in {"validation", "test"}:
            raise ValueError("split must be validation or test")

        bq = _bigquery()
        query = f"""
select *
from `{self.config.table('ml_forecast_covariates')}`
where dataset_split = @split
  and series_id in unnest(@series_ids)
order by date, series_id
""".strip()
        parameters = [
            bq.ScalarQueryParameter("split", "STRING", split),
            bq.ArrayQueryParameter("series_ids", "STRING", list(series_ids)),
        ]
        return _query_dataframe(
            self.client,
            query,
            parameters,
            location=self.config.location,
            use_storage_api=self.config.use_storage_api,
        )
