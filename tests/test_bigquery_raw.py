"""Tests for the M5 BigQuery RAW loader."""

from types import SimpleNamespace

import pytest

from retailops_ai.ingestion.bigquery_raw import (
    CALENDAR_SCHEMA,
    RAW_TABLES,
    SALES_SCHEMA,
    SELL_PRICES_SCHEMA,
    build_gcs_uri,
    ensure_raw_dataset,
    load_raw_table,
)


class FakeSchemaField:
    def __init__(self, name: str, field_type: str, mode: str = "NULLABLE") -> None:
        self.name = name
        self.field_type = field_type
        self.mode = mode


class FakeLoadJobConfig:
    def __init__(self, **kwargs: object) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeDataset:
    def __init__(self, dataset_id: str) -> None:
        self.dataset_id = dataset_id
        self.location: str | None = None


class FakeBigQuery:
    Dataset = FakeDataset
    SchemaField = FakeSchemaField
    LoadJobConfig = FakeLoadJobConfig
    SourceFormat = SimpleNamespace(CSV="CSV")
    WriteDisposition = SimpleNamespace(WRITE_TRUNCATE="WRITE_TRUNCATE")


class FakeJob:
    def __init__(self) -> None:
        self.result_called = False

    def result(self) -> None:
        self.result_called = True


class FakeClient:
    def __init__(self, dataset_location: str = "us-central1") -> None:
        self.dataset_location = dataset_location
        self.created_datasets: list[tuple[FakeDataset, bool]] = []
        self.load_calls: list[dict[str, object]] = []
        self.tables: dict[str, int] = {}
        self.last_job: FakeJob | None = None

    def create_dataset(self, dataset: FakeDataset, exists_ok: bool) -> None:
        self.created_datasets.append((dataset, exists_ok))

    def get_dataset(self, dataset_id: str) -> object:
        return SimpleNamespace(location=self.dataset_location)

    def load_table_from_uri(
        self,
        uri: str,
        table_id: str,
        *,
        job_config: FakeLoadJobConfig,
        location: str,
    ) -> FakeJob:
        self.load_calls.append(
            {
                "uri": uri,
                "table_id": table_id,
                "job_config": job_config,
                "location": location,
            }
        )
        self.last_job = FakeJob()
        return self.last_job

    def get_table(self, table_id: str) -> object:
        return SimpleNamespace(num_rows=self.tables[table_id])


def test_raw_schema_widths_match_m5_contract() -> None:
    assert len(CALENDAR_SCHEMA) == 14
    assert len(SELL_PRICES_SCHEMA) == 4
    assert len(SALES_SCHEMA) == 1947
    assert SALES_SCHEMA[-1].name == "d_1941"


def test_build_gcs_uri_normalizes_bucket_and_prefix() -> None:
    assert (
        build_gcs_uri("gs://retailops-data/", "/landing/m5/v1/", "calendar.csv")
        == "gs://retailops-data/landing/m5/v1/calendar.csv"
    )


def test_ensure_raw_dataset_rejects_location_mismatch() -> None:
    client = FakeClient(dataset_location="US")

    with pytest.raises(RuntimeError, match="locations cannot be changed"):
        ensure_raw_dataset(
            client,
            FakeBigQuery,
            project="retailops",
            dataset="retailops_raw",
            location="us-central1",
        )


def test_load_raw_table_uses_explicit_schema_and_truncate_write() -> None:
    spec = RAW_TABLES[0]
    client = FakeClient()
    table_id = "retailops.retailops_raw.raw_calendar"
    client.tables[table_id] = spec.expected_rows

    row_count = load_raw_table(
        client,
        FakeBigQuery,
        project="retailops",
        dataset="retailops_raw",
        location="us-central1",
        bucket="retailops-data",
        prefix="landing/m5/v1",
        spec=spec,
    )

    assert row_count == spec.expected_rows
    assert client.last_job is not None and client.last_job.result_called
    call = client.load_calls[0]
    config = call["job_config"]
    assert call["uri"] == "gs://retailops-data/landing/m5/v1/calendar.csv"
    assert call["location"] == "us-central1"
    assert config.write_disposition == "WRITE_TRUNCATE"
    assert config.skip_leading_rows == 1
    assert len(config.schema) == 14


def test_load_raw_table_rejects_unexpected_row_count() -> None:
    spec = RAW_TABLES[1]
    client = FakeClient()
    table_id = "retailops.retailops_raw.raw_sell_prices"
    client.tables[table_id] = spec.expected_rows - 1

    with pytest.raises(RuntimeError, match="Row-count validation failed"):
        load_raw_table(
            client,
            FakeBigQuery,
            project="retailops",
            dataset="retailops_raw",
            location="us-central1",
            bucket="retailops-data",
            prefix="landing/m5/v1",
            spec=spec,
        )
