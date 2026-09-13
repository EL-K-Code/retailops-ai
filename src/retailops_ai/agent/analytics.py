"""Allowlisted BigQuery analytics tools for the RetailOps agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from google.cloud import bigquery

from retailops_ai.agent.schemas import AnalyticsRequest
from retailops_ai.ml.contracts import M5_DEMAND_FORECAST_CONTRACT


@dataclass(frozen=True)
class AnalyticsConfig:
    project: str
    location: str
    dbt_dataset: str
    maximum_bytes_billed: int = 500_000_000

    @property
    def gold_dataset(self) -> str:
        return f"{self.dbt_dataset}_gold"

    @property
    def ml_dataset(self) -> str:
        return f"{self.dbt_dataset}_ml"


@dataclass(frozen=True)
class AnalyticsQuerySpec:
    sql: str
    parameters: list[tuple[str, str, Any]]


def _window(split: str) -> tuple[Any, Any]:
    contract = M5_DEMAND_FORECAST_CONTRACT
    window = contract.validation if split == "validation" else contract.test
    return window.start, window.end


def build_query_spec(request: AnalyticsRequest, config: AnalyticsConfig) -> AnalyticsQuerySpec:
    """Build only predefined SQL templates. No LLM-generated SQL is accepted."""
    start_date, end_date = _window(request.split)
    parameters: list[tuple[str, str, Any]] = [
        ("start_date", "DATE", start_date),
        ("end_date", "DATE", end_date),
    ]

    if request.operation == "sales_summary":
        sql = f"""
with daily as (
  select
    date,
    sum(units_sold) as daily_units,
    sum(estimated_sales_value) as estimated_sales_value
  from `{config.project}.{config.gold_dataset}.mart_demand_daily`
  where date between @start_date and @end_date
    and (@item_id is null or item_id = @item_id)
    and (@store_id is null or store_id = @store_id)
  group by date
)
select
  min(date) as start_date,
  max(date) as end_date,
  count(*) as observed_days,
  sum(daily_units) as total_units_sold,
  avg(daily_units) as average_daily_units,
  max(daily_units) as peak_daily_units,
  sum(estimated_sales_value) as estimated_sales_value
from daily
""".strip()
        parameters.extend(
            [
                ("item_id", "STRING", request.item_id),
                ("store_id", "STRING", request.store_id),
            ]
        )
    elif request.operation == "store_summary":
        sql = f"""
select
  store_id,
  min(date) as start_date,
  max(date) as end_date,
  sum(total_units_sold) as total_units_sold,
  avg(active_item_count) as average_active_items,
  sum(estimated_sales_value) as estimated_sales_value,
  avg(price_coverage_rate) as average_price_coverage_rate
from `{config.project}.{config.gold_dataset}.mart_store_daily_sales`
where date between @start_date and @end_date
  and (@store_id is null or store_id = @store_id)
group by store_id
order by total_units_sold desc
limit 20
""".strip()
        parameters.append(("store_id", "STRING", request.store_id))
    elif request.operation == "top_products":
        sql = f"""
select
  item_id,
  sum(total_units_sold) as total_units_sold,
  sum(estimated_sales_value) as estimated_sales_value,
  avg(price_coverage_rate) as average_price_coverage_rate
from `{config.project}.{config.gold_dataset}.mart_product_daily_sales`
where date between @start_date and @end_date
group by item_id
order by total_units_sold desc
limit @top_n
""".strip()
        parameters.append(("top_n", "INT64", request.top_n))
    elif request.operation == "baseline_metrics":
        sql = f"""
select baseline, mae, rmse, mean_rmsse
from `{config.project}.{config.ml_dataset}.ml_baseline_metrics`
order by mean_rmsse
limit 20
""".strip()
        parameters = []
    else:  # pragma: no cover - protected by the Pydantic Literal
        raise ValueError(f"Unsupported analytics operation: {request.operation}")

    return AnalyticsQuerySpec(sql=sql, parameters=parameters)


class RetailAnalyticsTool:
    """Execute allowlisted read-only BigQuery analytics with a cost ceiling."""

    def __init__(self, client: bigquery.Client, config: AnalyticsConfig) -> None:
        self.client = client
        self.config = config

    def run(self, request: AnalyticsRequest) -> dict[str, Any]:
        spec = build_query_spec(request, self.config)
        query_parameters = [
            bigquery.ScalarQueryParameter(name, field_type, value)
            for name, field_type, value in spec.parameters
        ]
        job_config = bigquery.QueryJobConfig(
            query_parameters=query_parameters,
            maximum_bytes_billed=self.config.maximum_bytes_billed,
            use_query_cache=True,
        )
        job = self.client.query(
            spec.sql,
            job_config=job_config,
            location=self.config.location,
        )
        rows = [dict(row) for row in job.result()]
        return {
            "operation": request.operation,
            "split": request.split,
            "rows": rows,
            "bytes_processed": int(job.total_bytes_processed or 0),
            "maximum_bytes_billed": self.config.maximum_bytes_billed,
        }
