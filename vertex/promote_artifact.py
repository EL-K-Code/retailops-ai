"""Quality-gate an existing training artifact and register a passing model version."""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

from retailops_ai.mlops.artifacts import load_json_from_gcs
from retailops_ai.mlops.quality import QualityGateResult, evaluate_mean_rmsse_gate
from vertex.register_model import register_model

BEST_VALIDATED_BASELINE_MEAN_RMSSE = 0.952306197699721


class PromotionRejectedError(RuntimeError):
    """Raised when a candidate artifact does not pass the quality gate."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--region", default=os.getenv("VERTEX_REGION", "us-central1"))
    parser.add_argument("--artifact-uri", default=os.getenv("TRAINING_ARTIFACT_URI"))
    parser.add_argument("--run-name", default=os.getenv("TRAINING_RUN_NAME"))
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


def evaluate_artifact_quality(
    *,
    artifact_uri: str,
    maximum_mean_rmsse: float,
) -> tuple[dict[str, Any], str, QualityGateResult]:
    """Load artifact metrics and evaluate the configured RMSSE promotion gate."""
    metrics_uri = f"{artifact_uri.rstrip('/')}/metrics.json"
    metrics = load_json_from_gcs(metrics_uri)
    if "mean_rmsse" not in metrics:
        raise ValueError(f"Training metrics are missing mean_rmsse: {metrics_uri}")

    gate = evaluate_mean_rmsse_gate(
        observed_mean_rmsse=float(metrics["mean_rmsse"]),
        maximum_mean_rmsse=maximum_mean_rmsse,
    )
    return metrics, metrics_uri, gate


def promote_artifact(
    *,
    project: str,
    region: str,
    artifact_uri: str,
    display_name: str,
    model_id: str,
    version_alias: str,
    run_name: str | None,
    serving_image_uri: str,
    maximum_mean_rmsse: float,
) -> dict[str, Any]:
    """Register an existing GCS artifact only when its quality gate passes."""
    metrics, metrics_uri, gate = evaluate_artifact_quality(
        artifact_uri=artifact_uri,
        maximum_mean_rmsse=maximum_mean_rmsse,
    )
    print(
        "Quality gate: "
        f"mean RMSSE={gate.observed_mean_rmsse:.6f} < "
        f"{gate.maximum_mean_rmsse:.6f} -> "
        f"{'PASS' if gate.passed else 'FAIL'}"
    )
    if not gate.passed:
        raise PromotionRejectedError(
            "Candidate did not beat the validated baseline. "
            "Artifacts were kept; Model Registry was not updated."
        )

    model = register_model(
        project=project,
        region=region,
        artifact_uri=artifact_uri,
        display_name=display_name,
        model_id=model_id,
        version_alias=version_alias,
        run_name=run_name,
        serving_image_uri=serving_image_uri,
    )
    return {
        "run_name": run_name,
        "artifact_uri": artifact_uri,
        "metrics_uri": metrics_uri,
        "metrics": metrics,
        "mean_rmsse": gate.observed_mean_rmsse,
        "quality_gate_max_mean_rmsse": gate.maximum_mean_rmsse,
        "quality_gate_improvement_fraction": gate.improvement_fraction,
        "model_resource": model.resource_name,
        "model_version": model.version_id,
    }


def main() -> None:
    args = parse_args()
    missing = [
        name
        for name, value in {
            "GOOGLE_CLOUD_PROJECT/--project": args.project,
            "TRAINING_ARTIFACT_URI/--artifact-uri": args.artifact_uri,
            "VERTEX_SERVING_IMAGE_URI/--serving-image-uri": args.serving_image_uri,
        }.items()
        if not value
    ]
    if missing:
        raise SystemExit("Missing required configuration: " + ", ".join(missing))

    try:
        result = promote_artifact(
            project=args.project,
            region=args.region,
            artifact_uri=args.artifact_uri,
            display_name=args.model_display_name,
            model_id=args.model_id,
            version_alias=args.version_alias,
            run_name=args.run_name,
            serving_image_uri=args.serving_image_uri,
            maximum_mean_rmsse=args.max_mean_rmsse,
        )
    except PromotionRejectedError as exc:
        raise SystemExit(str(exc)) from exc

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
