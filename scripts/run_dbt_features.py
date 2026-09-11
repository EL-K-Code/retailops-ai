#!/usr/bin/env python
"""Build and validate leakage-safe ML feature contracts."""

from __future__ import annotations

from _common import prepare_dbt_environment, run_dbt


def main() -> None:
    prepare_dbt_environment()

    print("Checking dbt/BigQuery connectivity...")
    run_dbt("debug")

    print("Building leakage-safe ML feature contracts...")
    run_dbt("build", "--select", "path:models/ml/features", "--fail-fast")

    print("Running ML feature integrity tests...")
    run_dbt("test", "--select", "tag:feature", "--fail-fast")

    print("ML feature engineering completed successfully.")


if __name__ == "__main__":
    main()
