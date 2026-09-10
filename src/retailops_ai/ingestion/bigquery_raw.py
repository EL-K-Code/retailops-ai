"""Load immutable M5 landing files from GCS into BigQuery RAW tables."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Any

DEFAULT_DATASET = "retailops_raw"
DEFAULT_LOCATION = "us-central1"
DEFAULT_LANDING_PREFIX = "landing/m5/v1"


@dataclass(frozen=True)
class FieldSpec:
    """Warehouse-agnostic BigQuery field definition."""

    name: str
    field_type: str
    mode: str = "NULLABLE"


@dataclass(frozen=True)
class RawTableSpec:
    """Definition of one M5 RAW table."""

    source_file: str
    table_name: str
    expected_rows: int
    schema: tuple[FieldSpec, ...]


CALENDAR_SCHEMA = (
    FieldSpec("date", "DATE", "REQUIRED"),
    FieldSpec("wm_yr_wk", "INTEGER", "REQUIRED"),
    FieldSpec("weekday", "STRING", "REQUIRED"),
    FieldSpec("wday", "INTEGER", "REQUIRED"),
    FieldSpec("month", "INTEGER", "REQUIRED"),
    FieldSpec("year", "INTEGER", "REQUIRED"),
    FieldSpec("d", "STRING", "REQUIRED"),
    FieldSpec("event_name_1", "STRING"),
    FieldSpec("event_type_1", "STRING"),
    FieldSpec("event_name_2", "STRING"),
    FieldSpec("event_type_2", "STRING"),
    FieldSpec("snap_CA", "INTEGER", "REQUIRED"),
    FieldSpec("snap_TX", "INTEGER", "REQUIRED"),
    FieldSpec("snap_WI", "INTEGER", "REQUIRED"),
)

SELL_PRICES_SCHEMA = (
    FieldSpec("store_id", "STRING", "REQUIRED"),
    FieldSpec("item_id", "STRING", "REQUIRED"),
    FieldSpec("wm_yr_wk", "INTEGER", "REQUIRED"),
    FieldSpec("sell_price", "NUMERIC", "REQUIRED"),
)

SALES_SCHEMA = (
    FieldSpec("id", "STRING", "REQUIRED"),
    FieldSpec("item_id", "STRING", "REQUIRED"),
    FieldSpec("dept_id", "STRING", "REQUIRED"),
    FieldSpec("cat_id", "STRING", "REQUIRED"),
    FieldSpec("store_id", "STRING", "REQUIRED"),
    FieldSpec("state_id", "STRING", "REQUIRED"),
    *(FieldSpec(f"d_{day}", "INTEGER", "REQUIRED") for day in range(1, 1942)),
)

RAW_TABLES = (
    RawTableSpec("calendar.csv", "raw_calendar", 1_969, CALENDAR_SCHEMA),
    RawTableSpec("sell_prices.csv", "raw_sell_prices", 6_841_121, SELL_PRICES_SCHEMA),
    RawTableSpec("sales_train_evaluation.csv", "raw_sales", 30_490, SALES_SCHEMA),
)


def build_gcs_uri(bucket: str, prefix: str, source_file: str) -> str:
    """Build the fully qualified GCS URI for one landing object."""
    normalized_bucket = bucket.removeprefix("gs://").strip("/")
    normalized_prefix = prefix.strip("/")
    if not normalized_bucket:
        raise ValueError("GCS bucket must not be empty")
    if not normalized_prefix:
        return f"gs://{normalized_bucket}/{source_file}"
    return f"gs://{normalized_bucket}/{normalized_prefix}/{source_file}"


def ensure_raw_dataset(
    client: Any,
    bigquery: Any,
    project: str,
    dataset: str,
    location: str,
) -> str:
    """Create the RAW dataset if needed and enforce its configured location."""
    dataset_id = f"{project}.{dataset}"
    dataset_obj = bigquery.Dataset(dataset_id)
    dataset_obj.location = location
    client.create_dataset(dataset_obj, exists_ok=True)
    remote = client.get_dataset(dataset_id)

    remote_location = (getattr(remote, "location", "") or "").lower()
    if remote_location != location.lower():
        raise RuntimeError(
            f"BigQuery dataset {dataset_id} is in {remote.location!r}, "
            f"expected {location!r}. Dataset locations cannot be changed in place."
        )
    return dataset_id


def _build_job_config(bigquery: Any, schema: tuple[FieldSpec, ...]) -> Any:
    """Create an explicit CSV load configuration for one RAW table."""
    return bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField(field.name, field.field_type, mode=field.mode)
            for field in schema
        ],
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        max_bad_records=0,
    )


def load_raw_table(
    client: Any,
    bigquery: Any,
    *,
    project: str,
    dataset: str,
    location: str,
    bucket: str,
    prefix: str,
    spec: RawTableSpec,
) -> int:
    """Load one immutable GCS CSV into its deterministic BigQuery RAW table."""
    table_id = f"{project}.{dataset}.{spec.table_name}"
    uri = build_gcs_uri(bucket, prefix, spec.source_file)
    job_config = _build_job_config(bigquery, spec.schema)

    job = client.load_table_from_uri(
        uri,
        table_id,
        job_config=job_config,
        location=location,
    )
    job.result()

    table = client.get_table(table_id)
    row_count = int(table.num_rows)
    if row_count != spec.expected_rows:
        raise RuntimeError(
            f"Row-count validation failed for {table_id}: "
            f"loaded {row_count:,}, expected {spec.expected_rows:,}."
        )
    return row_count


def load_m5_raw(
    client: Any,
    bigquery: Any,
    *,
    project: str,
    dataset: str,
    location: str,
    bucket: str,
    prefix: str,
) -> dict[str, int]:
    """Create/validate the RAW dataset and load all M5 source tables."""
    ensure_raw_dataset(client, bigquery, project, dataset, location)
    return {
        spec.table_name: load_raw_table(
            client,
            bigquery,
            project=project,
            dataset=dataset,
            location=location,
            bucket=bucket,
            prefix=prefix,
            spec=spec,
        )
        for spec in RAW_TABLES
    }


def build_bigquery_client(project: str) -> tuple[Any, Any]:
    """Build the real BigQuery client with Application Default Credentials."""
    try:
        from google.cloud import bigquery
    except ImportError as exc:
        raise RuntimeError(
            "google-cloud-bigquery is not installed. Run `uv sync` before this command."
        ) from exc

    return bigquery.Client(project=project), bigquery


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load M5 GCS landing files into BigQuery RAW.")
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--dataset", default=os.getenv("BQ_RAW_DATASET", DEFAULT_DATASET))
    parser.add_argument("--location", default=os.getenv("BQ_LOCATION", DEFAULT_LOCATION))
    parser.add_argument("--bucket", default=os.getenv("GCS_BUCKET"))
    parser.add_argument(
        "--prefix",
        default=os.getenv("GCS_LANDING_PREFIX", DEFAULT_LANDING_PREFIX),
    )
    args = parser.parse_args(argv)

    if not args.project:
        parser.error("--project or GOOGLE_CLOUD_PROJECT is required")
    if not args.bucket:
        parser.error("--bucket or GCS_BUCKET is required")
    return args


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the M5 BigQuery RAW load."""
    args = _parse_args(argv)
    client, bigquery = build_bigquery_client(args.project)
    results = load_m5_raw(
        client,
        bigquery,
        project=args.project,
        dataset=args.dataset,
        location=args.location,
        bucket=args.bucket,
        prefix=args.prefix,
    )
    for table_name, row_count in results.items():
        print(f"LOADED   {args.project}.{args.dataset}.{table_name}: {row_count:,} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
