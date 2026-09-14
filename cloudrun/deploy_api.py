"""Deploy the RetailOps forecasting API to Cloud Run with conservative defaults."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--region", default=os.getenv("CLOUD_RUN_REGION", "us-central1"))
    parser.add_argument("--service", default=os.getenv("CLOUD_RUN_SERVICE", "retailops-api"))
    parser.add_argument("--image-uri", default=os.getenv("CLOUD_RUN_IMAGE_URI"))
    parser.add_argument("--model-artifact-uri", default=os.getenv("MODEL_ARTIFACT_URI"))
    parser.add_argument("--service-account", default=os.getenv("CLOUD_RUN_SERVICE_ACCOUNT"))
    parser.add_argument("--dbt-dataset", default=os.getenv("BQ_DBT_DATASET", "retailops"))
    parser.add_argument(
        "--max-entities",
        type=int,
        default=int(os.getenv("SERVING_MAX_ENTITIES", "50")),
    )
    parser.add_argument("--min-instances", type=int, default=0)
    parser.add_argument("--max-instances", type=int, default=2)
    parser.add_argument("--cpu", default="1")
    parser.add_argument("--memory", default="1Gi")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--public", action="store_true")
    parser.add_argument(
        "--confirm-cost",
        action="store_true",
        help=(
            "Required because Cloud Build, Artifact Registry and Cloud Run usage "
            "can incur charges."
        ),
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
            "CLOUD_RUN_IMAGE_URI/--image-uri": args.image_uri,
            "MODEL_ARTIFACT_URI/--model-artifact-uri": args.model_artifact_uri,
            "CLOUD_RUN_SERVICE_ACCOUNT/--service-account": args.service_account,
        }.items()
        if not value
    ]
    if missing:
        raise SystemExit("Missing required configuration: " + ", ".join(missing))
    if not args.confirm_cost:
        raise SystemExit(
            "Refusing to deploy without --confirm-cost. "
            "Cloud Run is configured with min-instances=0, but deployment and usage "
            "may still incur charges."
        )
    if args.min_instances < 0 or args.max_instances <= 0:
        raise SystemExit("Instance limits must be non-negative and max-instances must be positive")
    if args.min_instances > args.max_instances:
        raise SystemExit("min-instances cannot exceed max-instances")

    env_vars = ",".join(
        [
            f"GOOGLE_CLOUD_PROJECT={args.project}",
            f"BQ_LOCATION={args.region}",
            f"BQ_DBT_DATASET={args.dbt_dataset}",
            f"MODEL_ARTIFACT_URI={args.model_artifact_uri}",
            f"SERVING_MAX_ENTITIES={args.max_entities}",
            "ML_USE_BQ_STORAGE_API=false",
        ]
    )
    gcloud = _resolve_gcloud()
    command = [
        gcloud,
        "run",
        "deploy",
        args.service,
        "--project",
        args.project,
        "--region",
        args.region,
        "--image",
        args.image_uri,
        "--service-account",
        args.service_account,
        "--set-env-vars",
        env_vars,
        "--min-instances",
        str(args.min_instances),
        "--max-instances",
        str(args.max_instances),
        "--cpu",
        args.cpu,
        "--memory",
        args.memory,
        "--concurrency",
        str(args.concurrency),
        "--timeout",
        str(args.timeout),
        "--allow-unauthenticated" if args.public else "--no-allow-unauthenticated",
    ]
    print("$ " + " ".join(command))
    subprocess.run(command, check=True)

    describe = [
        gcloud,
        "run",
        "services",
        "describe",
        args.service,
        "--project",
        args.project,
        "--region",
        args.region,
        "--format=value(status.url)",
    ]
    subprocess.run(describe, check=True)


if __name__ == "__main__":
    main()
