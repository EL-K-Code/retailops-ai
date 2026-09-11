#!/usr/bin/env python
"""Load immutable M5 landing files into BigQuery RAW."""

from __future__ import annotations

import os

from _common import load_env, require_env, run_python_module


def main() -> None:
    load_env()
    values = require_env(("GOOGLE_CLOUD_PROJECT", "GCS_BUCKET", "BQ_LOCATION", "BQ_RAW_DATASET"))
    prefix = os.getenv("GCS_LANDING_PREFIX", "landing/m5/v1")

    print("Loading immutable M5 landing files into BigQuery RAW...")
    run_python_module(
        "retailops_ai.ingestion.bigquery_raw",
        "--project",
        values["GOOGLE_CLOUD_PROJECT"],
        "--dataset",
        values["BQ_RAW_DATASET"],
        "--location",
        values["BQ_LOCATION"],
        "--bucket",
        values["GCS_BUCKET"],
        "--prefix",
        prefix,
    )


if __name__ == "__main__":
    main()
