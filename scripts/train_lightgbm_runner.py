#!/usr/bin/env python
"""Run the LightGBM training pipeline with repository environment loading."""

from __future__ import annotations

import os
import sys

from _common import load_env, require_env, run_python_script


def main() -> None:
    load_env()
    require_env(("GOOGLE_CLOUD_PROJECT", "BQ_LOCATION", "BQ_DBT_DATASET"))

    print("== RetailOps AI: LightGBM global demand model ==")
    print(f"BigQuery Storage API: {os.getenv('ML_USE_BQ_STORAGE_API', 'false')}")
    print(f"Persist outputs to BigQuery: {os.getenv('ML_WRITE_BIGQUERY', 'false')}")
    print()
    print("This command reads BigQuery data and can incur query/network charges.")

    run_python_script("train_lightgbm.py", *sys.argv[1:])


if __name__ == "__main__":
    main()
