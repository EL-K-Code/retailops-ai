#!/usr/bin/env python
"""Build and validate the dbt GOLD marts."""

from __future__ import annotations

from _common import prepare_dbt_environment, run_dbt


def main() -> None:
    prepare_dbt_environment()

    print("Checking dbt/BigQuery connectivity...")
    run_dbt("debug")

    print("Building and testing GOLD marts...")
    run_dbt("build", "--select", "path:models/gold", "--fail-fast")

    print("Running GOLD cross-mart integrity tests...")
    run_dbt("test", "--select", "path:tests/gold", "--fail-fast")

    print("dbt GOLD build completed successfully.")


if __name__ == "__main__":
    main()
