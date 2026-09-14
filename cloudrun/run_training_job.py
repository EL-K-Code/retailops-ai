"""Execute RetailOps LightGBM training on Cloud Run Jobs and verify artifacts."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime

from retailops_ai.mlops.artifacts import load_json_from_gcs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--region", default=os.getenv("CLOUD_RUN_REGION", "us-central1"))
    parser.add_argument(
        "--job",
        default=os.getenv("CLOUD_RUN_TRAINING_JOB", "retailops-lightgbm-training"),
    )
    parser.add_argument(
        "--output-root",
        default=(
            os.getenv("CLOUD_RUN_TRAINING_OUTPUT_ROOT")
            or os.getenv("VERTEX_OUTPUT_ROOT")
        ),
    )
    parser.add_argument("--dbt-dataset", default=os.getenv("BQ_DBT_DATASET", "retailops"))
    parser.add_argument(
        "--experiment",
        default=os.getenv(
            "CLOUD_RUN_TRAINING_EXPERIMENT",
            os.getenv("VERTEX_EXPERIMENT", "retailops-demand-forecasting"),
        ),
    )
    parser.add_argument(
        "--train-lookback-days",
        type=int,
        default=int(
            os.getenv(
                "CLOUD_RUN_TRAIN_LOOKBACK_DAYS",
                os.getenv("VERTEX_TRAIN_LOOKBACK_DAYS", "90"),
            )
        ),
    )
    parser.add_argument(
        "--num-boost-round",
        type=int,
        default=int(
            os.getenv(
                "CLOUD_RUN_NUM_BOOST_ROUND",
                os.getenv("VERTEX_NUM_BOOST_ROUND", "100"),
            )
        ),
    )
    parser.add_argument(
        "--task-timeout",
        default=os.getenv("CLOUD_RUN_TRAINING_TIMEOUT", "3600s"),
    )
    parser.add_argument("--run-name", default=None)
    parser.add_argument(
        "--confirm-cost",
        action="store_true",
        help="Required because executing the Cloud Run Job can incur charges.",
    )
    return parser.parse_args()


def _resolve_gcloud() -> str:
    executable = shutil.which("gcloud") or shutil.which("gcloud.cmd")
    if not executable:
        raise SystemExit(
            "gcloud CLI was not found on PATH. Verify the Google Cloud SDK installation."
        )
    return executable


def main() -> None:
    args = parse_args()
    missing = [
        name
        for name, value in {
            "GOOGLE_CLOUD_PROJECT/--project": args.project,
            "CLOUD_RUN_TRAINING_OUTPUT_ROOT/--output-root": args.output_root,
        }.items()
        if not value
    ]
    if missing:
        raise SystemExit("Missing required configuration: " + ", ".join(missing))
    if not args.confirm_cost:
        raise SystemExit(
            "Refusing to execute without --confirm-cost. "
            "Cloud Run Job execution and BigQuery usage may incur charges."
        )
    if args.train_lookback_days <= 0:
        raise SystemExit("--train-lookback-days must be positive")
    if args.num_boost_round <= 0:
        raise SystemExit("--num-boost-round must be positive")

    run_name = args.run_name or f"lightgbm-v1-{datetime.now(UTC):%Y%m%d-%H%M%S}"
    artifact_uri = f"{args.output_root.rstrip('/')}/cloudrun-training/{run_name}/model"

    training_args = [
        "--project",
        args.project,
        "--location",
        args.region,
        "--dbt-dataset",
        args.dbt_dataset,
        "--train-lookback-days",
        str(args.train_lookback_days),
        "--num-boost-round",
        str(args.num_boost_round),
        "--artifact-uri",
        artifact_uri,
        "--run-name",
        run_name,
    ]
    if args.experiment:
        training_args.extend(["--experiment", args.experiment])

    gcloud = _resolve_gcloud()
    command = [
        gcloud,
        "run",
        "jobs",
        "execute",
        args.job,
        "--project",
        args.project,
        "--region",
        args.region,
        "--wait",
        "--task-timeout",
        args.task_timeout,
        "--args=" + ",".join(training_args),
    ]
    print("$ " + " ".join(command))
    subprocess.run(command, check=True)

    metrics_uri = f"{artifact_uri}/metrics.json"
    metrics = load_json_from_gcs(metrics_uri)
    print(
        json.dumps(
            {
                "backend": "cloud-run-jobs",
                "job": args.job,
                "run_name": run_name,
                "artifact_uri": artifact_uri,
                "metrics_uri": metrics_uri,
                "metrics": metrics,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
