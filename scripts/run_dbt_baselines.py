#!/usr/bin/env python
"""Build and validate leakage-safe forecasting baselines."""

from __future__ import annotations

from _common import prepare_dbt_environment, run_dbt


def main() -> None:
    prepare_dbt_environment()

    print("Checking dbt/BigQuery connectivity...")
    run_dbt("debug")

    print("Building leakage-safe validation baselines...")
    run_dbt("build", "--select", "path:models/ml/baselines", "--fail-fast")

    print("Running baseline integrity tests...")
    run_dbt("test", "--select", "tag:baseline", "--fail-fast")

    print("Baseline evaluation completed. Inspect retailops_ml.ml_baseline_metrics for scores.")


if __name__ == "__main__":
    main()
