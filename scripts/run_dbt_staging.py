#!/usr/bin/env python
"""Build and validate the dbt STAGING layer."""

from __future__ import annotations

from _common import prepare_dbt_environment, run_dbt


def main() -> None:
    prepare_dbt_environment()

    print("Checking dbt/BigQuery connectivity...")
    run_dbt("debug")

    print("Testing RAW source contracts...")
    run_dbt("test", "--select", "source:raw", "--fail-fast")

    print("Building and testing STAGING models...")
    run_dbt("build", "--select", "path:models/staging", "--fail-fast")

    print("dbt STAGING build completed successfully.")


if __name__ == "__main__":
    main()
