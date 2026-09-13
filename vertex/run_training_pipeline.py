"""Run the V3 RetailOps Vertex training workflow and register the resulting model."""

from __future__ import annotations

import argparse
import json
import os

from vertex.register_model import register_model
from vertex.submit_training_job import submit_training_job


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--region", default=os.getenv("VERTEX_REGION", "us-central1"))
    parser.add_argument("--image-uri", default=os.getenv("VERTEX_TRAINING_IMAGE_URI"))
    parser.add_argument("--output-root", default=os.getenv("VERTEX_OUTPUT_ROOT"))
    parser.add_argument("--service-account", default=os.getenv("VERTEX_SERVICE_ACCOUNT"))
    parser.add_argument(
        "--machine-type",
        default=os.getenv("VERTEX_MACHINE_TYPE", "e2-standard-4"),
    )
    parser.add_argument(
        "--experiment",
        default=os.getenv("VERTEX_EXPERIMENT", "retailops-demand-forecasting"),
    )
    parser.add_argument("--dbt-dataset", default=os.getenv("BQ_DBT_DATASET", "retailops"))
    parser.add_argument(
        "--train-lookback-days",
        type=int,
        default=int(os.getenv("ML_TRAIN_LOOKBACK_DAYS", "180")),
    )
    parser.add_argument(
        "--num-boost-round",
        type=int,
        default=int(os.getenv("ML_NUM_BOOST_ROUND", "300")),
    )
    parser.add_argument(
        "--model-display-name",
        default=os.getenv("VERTEX_MODEL_DISPLAY_NAME", "retailops-lightgbm-global"),
    )
    parser.add_argument(
        "--model-id",
        default=os.getenv("VERTEX_MODEL_ID", "retailops-lightgbm-global"),
    )
    parser.add_argument(
        "--version-alias",
        default=os.getenv("VERTEX_MODEL_ALIAS", "candidate"),
    )
    parser.add_argument("--serving-image-uri", default=os.getenv("VERTEX_SERVING_IMAGE_URI"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    missing = [
        name
        for name, value in {
            "GOOGLE_CLOUD_PROJECT/--project": args.project,
            "VERTEX_TRAINING_IMAGE_URI/--image-uri": args.image_uri,
            "VERTEX_SERVING_IMAGE_URI/--serving-image-uri": args.serving_image_uri,
            "VERTEX_OUTPUT_ROOT/--output-root": args.output_root,
        }.items()
        if not value
    ]
    if missing:
        raise SystemExit("Missing required configuration: " + ", ".join(missing))

    training = submit_training_job(
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
    )

    model = register_model(
        project=args.project,
        region=args.region,
        artifact_uri=training.artifact_uri,
        display_name=args.model_display_name,
        model_id=args.model_id,
        version_alias=args.version_alias,
        run_name=training.run_name,
        serving_image_uri=args.serving_image_uri,
    )

    print(
        json.dumps(
            {
                "run_name": training.run_name,
                "training_job": training.job_resource_name,
                "artifact_uri": training.artifact_uri,
                "model_resource": model.resource_name,
                "model_version": model.version_id,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
