"""Run V3 Vertex training, quality-gate the run, and register a model version."""

from __future__ import annotations

import argparse
import json
import os

from retailops_ai.mlops.artifacts import load_json_from_gcs
from retailops_ai.mlops.quality import evaluate_mean_rmsse_gate
from vertex.register_model import register_model
from vertex.submit_training_job import submit_training_job

BEST_VALIDATED_BASELINE_MEAN_RMSSE = 0.952306197699721


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--region", default=os.getenv("VERTEX_REGION", "us-central1"))
    parser.add_argument("--image-uri", default=os.getenv("VERTEX_TRAINING_IMAGE_URI"))
    parser.add_argument("--output-root", default=os.getenv("VERTEX_OUTPUT_ROOT"))
    parser.add_argument("--service-account", default=os.getenv("VERTEX_SERVICE_ACCOUNT"))
    parser.add_argument(
        "--machine-type",
        default=os.getenv("VERTEX_MACHINE_TYPE", "n1-standard-4"),
    )
    parser.add_argument(
        "--experiment",
        default=os.getenv("VERTEX_EXPERIMENT", "retailops-demand-forecasting"),
    )
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
    parser.add_argument(
        "--max-mean-rmsse",
        type=float,
        default=float(
            os.getenv(
                "VERTEX_MAX_MEAN_RMSSE",
                str(BEST_VALIDATED_BASELINE_MEAN_RMSSE),
            )
        ),
        help="Candidate must be strictly below this RMSSE before registration.",
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

    metrics_uri = f"{training.artifact_uri.rstrip('/')}/metrics.json"
    metrics = load_json_from_gcs(metrics_uri)
    if "mean_rmsse" not in metrics:
        raise SystemExit(f"Training metrics are missing mean_rmsse: {metrics_uri}")

    gate = evaluate_mean_rmsse_gate(
        observed_mean_rmsse=float(metrics["mean_rmsse"]),
        maximum_mean_rmsse=args.max_mean_rmsse,
    )
    print(
        "Quality gate: "
        f"mean RMSSE={gate.observed_mean_rmsse:.6f} < "
        f"{gate.maximum_mean_rmsse:.6f} -> "
        f"{'PASS' if gate.passed else 'FAIL'}"
    )
    if not gate.passed:
        raise SystemExit(
            "Training completed, but the candidate did not beat the validated baseline. "
            "Artifacts and experiment metrics were kept; Model Registry was not updated."
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
                "mean_rmsse": gate.observed_mean_rmsse,
                "quality_gate_max_mean_rmsse": gate.maximum_mean_rmsse,
                "quality_gate_improvement_fraction": gate.improvement_fraction,
                "model_resource": model.resource_name,
                "model_version": model.version_id,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
