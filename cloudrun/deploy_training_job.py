"""Deploy the RetailOps LightGBM training container as a Cloud Run Job."""

from __future__ import annotations

import argparse
import os
import subprocess


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--region", default=os.getenv("CLOUD_RUN_REGION", "us-central1"))
    parser.add_argument(
        "--job",
        default=os.getenv("CLOUD_RUN_TRAINING_JOB", "retailops-lightgbm-training"),
    )
    parser.add_argument(
        "--image-uri",
        default=(
            os.getenv("CLOUD_RUN_TRAINING_IMAGE_URI")
            or os.getenv("VERTEX_TRAINING_IMAGE_URI")
        ),
    )
    parser.add_argument(
        "--service-account",
        default=(
            os.getenv("CLOUD_RUN_TRAINING_SERVICE_ACCOUNT")
            or os.getenv("VERTEX_SERVICE_ACCOUNT")
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
        "--cpu",
        default=os.getenv("CLOUD_RUN_TRAINING_CPU", "1"),
    )
    parser.add_argument(
        "--memory",
        default=os.getenv("CLOUD_RUN_TRAINING_MEMORY", "4Gi"),
    )
    parser.add_argument(
        "--task-timeout",
        default=os.getenv("CLOUD_RUN_TRAINING_TIMEOUT", "3600s"),
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=int(os.getenv("CLOUD_RUN_TRAINING_MAX_RETRIES", "0")),
    )
    parser.add_argument(
        "--confirm-cost",
        action="store_true",
        help="Required because Cloud Run Job executions can incur charges.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    missing = [
        name
        for name, value in {
            "GOOGLE_CLOUD_PROJECT/--project": args.project,
            "CLOUD_RUN_TRAINING_IMAGE_URI/--image-uri": args.image_uri,
            "CLOUD_RUN_TRAINING_SERVICE_ACCOUNT/--service-account": args.service_account,
        }.items()
        if not value
    ]
    if missing:
        raise SystemExit("Missing required configuration: " + ", ".join(missing))
    if not args.confirm_cost:
        raise SystemExit(
            "Refusing to deploy without --confirm-cost. "
            "Cloud Run Job deployment and executions may incur charges."
        )
    if args.max_retries < 0:
        raise SystemExit("--max-retries must be non-negative")

    env_vars = ",".join(
        [
            f"GOOGLE_CLOUD_PROJECT={args.project}",
            f"BQ_LOCATION={args.region}",
            f"BQ_DBT_DATASET={args.dbt_dataset}",
            f"TRAINING_REGION={args.region}",
            f"TRAINING_EXPERIMENT={args.experiment}",
            "ML_USE_BQ_STORAGE_API=false",
        ]
    )
    command = [
        "gcloud",
        "run",
        "jobs",
        "deploy",
        args.job,
        "--project",
        args.project,
        "--region",
        args.region,
        "--image",
        args.image_uri,
        "--service-account",
        args.service_account,
        "--cpu",
        args.cpu,
        "--memory",
        args.memory,
        "--tasks",
        "1",
        "--max-retries",
        str(args.max_retries),
        "--task-timeout",
        args.task_timeout,
        "--set-env-vars",
        env_vars,
        "--args=--help",
    ]
    print("$ " + " ".join(command))
    subprocess.run(command, check=True)

    describe = [
        "gcloud",
        "run",
        "jobs",
        "describe",
        args.job,
        "--project",
        args.project,
        "--region",
        args.region,
        "--format=value(metadata.name)",
    ]
    subprocess.run(describe, check=True)


if __name__ == "__main__":
    main()
