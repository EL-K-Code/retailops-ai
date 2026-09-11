#!/usr/bin/env python
"""Build and validate the leakage-aware ML temporal contract."""

from __future__ import annotations

from _common import prepare_dbt_environment, run_dbt


def main() -> None:
    prepare_dbt_environment()

    print("Checking dbt/BigQuery connectivity...")
    run_dbt("debug")

    print("Building the leakage-aware ML dataset contract...")
    run_dbt("build", "--select", "ml_demand_split", "--fail-fast")

    print("Validating temporal split counts and boundaries...")
    run_dbt(
        "test",
        "--select",
        "ml_split_boundaries",
        "ml_split_row_counts",
        "--fail-fast",
    )

    print("ML dataset contract validation completed successfully.")


if __name__ == "__main__":
    main()
