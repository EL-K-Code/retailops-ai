#!/usr/bin/env python
"""Build and validate the dbt SILVER layer."""

from __future__ import annotations

from _common import prepare_dbt_environment, run_dbt


def main() -> None:
    prepare_dbt_environment()

    print("Checking dbt/BigQuery connectivity...")
    run_dbt("debug")

    print("Building and testing SILVER models...")
    run_dbt("build", "--select", "path:models/silver", "--fail-fast")

    print("Running SILVER warehouse integrity tests...")
    run_dbt("test", "--select", "path:tests/silver", "--fail-fast")

    print("dbt SILVER build completed successfully.")


if __name__ == "__main__":
    main()
