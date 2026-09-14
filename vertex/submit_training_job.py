"""Submit RetailOps LightGBM training to Vertex AI."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from google.cloud import aiplatform


@dataclass(frozen=True)
class TrainingResult:
    run_name: str
    job_resource_name: str
    artifact_uri: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--region", default=os.getenv("VERTEX_REGION", "us-central1"))
    parser.add_argument("--image-uri", default=os.getenv("VERTEX_TRAINING_IMAGE_URI"))
    parser.add_argument("--output-root", default=os.getenv("VERTEX_OUTPUT_ROOT"))
    parser.add_argument(
        "--service-account",
        default=os.getenv("VERTEX_SERVICE_ACCOUNT"),
    )
    parser.add_argument(
        "--machine-type",
        default=os.getenv("VERTEX_MACHINE_TYPE", "n1-standard-4"),
    )
    parser.add_argument(
        "--experiment",
        default=os.getenv("VERTEX_EXPERIMENT", "retailops-demand-forecasting"),
    )
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--dbt-dataset", default=os.getenv("BQ_DBT_DATASET", "retailops"))
    parser.add_argument(
        "--train-lookback-days",
        type=int,
        default=int(os.getenv("VERTEX_TRAIN_LOOKBACK_DAYS", "90")),
    )
    parser.add_argument(
        "--num-boost-round",
        type=int,
        default=int(os.getenv("VERTEX_NUM_BOOST_ROUND", "100")),
    )
    return parser.parse_args()


def submit_training_job(
    *,
    project: str,
    region: str,
    image_uri: str,
    output_root: str,
    service_account: str | None,
    machine_type: str,
    experiment: str,
    dbt_dataset: str,
    train_lookback_days: int,
    num_boost_round: int,
    run_name: str | None = None,
) -> TrainingResult:
    resolved_run_name = run_name or f"lightgbm-v1-{datetime.now(UTC):%Y%m%d-%H%M%S}"
    base_output_dir = f"{output_root.rstrip('/')}/vertex-training/{resolved_run_name}"
    artifact_uri = f"{base_output_dir}/model"

    aiplatform.init(
        project=project,
        location=region,
        staging_bucket=output_root,
    )

    job = aiplatform.CustomContainerTrainingJob(
        display_name=resolved_run_name,
        container_uri=image_uri,
    )

    try:
        job.run(
            args=[
                "--project",
                project,
                "--location",
                region,
                "--dbt-dataset",
                dbt_dataset,
                "--train-lookback-days",
                str(train_lookback_days),
                "--num-boost-round",
                str(num_boost_round),
                "--experiment",
                experiment,
                "--run-name",
                resolved_run_name,
            ],
            replica_count=1,
            machine_type=machine_type,
            base_output_dir=base_output_dir,
            service_account=service_account,
            sync=True,
        )
    except RuntimeError as exc:
        if "custom_model_training_cpus" in str(exc):
            raise SystemExit(
                "Vertex AI custom-training CPU quota is insufficient for "
                f"machine type {machine_type!r} in region {region!r}. "
                "Increase the 'Custom model training CPUs per project per region' "
                "quota before retrying."
            ) from exc
        raise

    return TrainingResult(
        run_name=resolved_run_name,
        job_resource_name=job.resource_name,
        artifact_uri=artifact_uri,
    )


def main() -> None:
    args = parse_args()
    if not args.project:
        raise SystemExit("GOOGLE_CLOUD_PROJECT or --project is required")
    if not args.image_uri:
        raise SystemExit("VERTEX_TRAINING_IMAGE_URI or --image-uri is required")
    if not args.output_root:
        raise SystemExit("VERTEX_OUTPUT_ROOT or --output-root is required")

    result = submit_training_job(
        project=args.project,
        region=args.region,
        image_uri=args.image_uri,
        output_root=args.output_root,
        service_account=args.service_account,
        machine_type=args.machine_type,
        experiment=args.experiment,
        dbt_dataset=args.dbt_dataset,
        train_lookback_days=args.train_lookback_days,
        num_boost_round=args.num_boost_round,
        run_name=args.run_name,
    )
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
