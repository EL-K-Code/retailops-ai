"""Register a trained RetailOps artifact as a version in Vertex AI Model Registry."""

from __future__ import annotations

import argparse
import os

from google.cloud import aiplatform


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--region", default=os.getenv("VERTEX_REGION", "us-central1"))
    parser.add_argument("--artifact-uri", default=os.getenv("VERTEX_MODEL_ARTIFACT_URI"))
    parser.add_argument(
        "--display-name",
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
    parser.add_argument(
        "--serving-image-uri",
        default=os.getenv("VERTEX_SERVING_IMAGE_URI"),
    )
    parser.add_argument("--run-name", default=os.getenv("VERTEX_RUN_NAME"))
    return parser.parse_args()


def _find_parent_model(display_name: str) -> str | None:
    models = aiplatform.Model.list(
        filter=f'display_name="{display_name}"',
        order_by="create_time asc",
    )
    return models[0].resource_name if models else None


def register_model(
    *,
    project: str,
    region: str,
    artifact_uri: str,
    display_name: str,
    model_id: str,
    version_alias: str,
    run_name: str | None,
    serving_image_uri: str,
) -> aiplatform.Model:
    aiplatform.init(project=project, location=region)
    parent_model = _find_parent_model(display_name)

    kwargs: dict[str, object] = {
        "display_name": display_name,
        "artifact_uri": artifact_uri,
        "serving_container_image_uri": serving_image_uri,
        "serving_container_predict_route": "/predict",
        "serving_container_health_route": "/health",
        "serving_container_ports": [8080],
        "description": "RetailOps AI global LightGBM 28-day demand forecasting model",
        "labels": {
            "framework": "lightgbm",
            "workload": "demand-forecasting",
            "stage": "candidate",
        },
        "version_aliases": [version_alias],
        "version_description": (
            f"Vertex training run {run_name or 'unknown'}; artifacts: {artifact_uri}"
        ),
        "sync": True,
    }

    if parent_model:
        kwargs["parent_model"] = parent_model
        kwargs["is_default_version"] = False
    else:
        kwargs["model_id"] = model_id
        kwargs["is_default_version"] = True

    return aiplatform.Model.upload(**kwargs)


def main() -> None:
    args = parse_args()
    if not args.project:
        raise SystemExit("GOOGLE_CLOUD_PROJECT or --project is required")
    if not args.artifact_uri:
        raise SystemExit("VERTEX_MODEL_ARTIFACT_URI or --artifact-uri is required")
    if not args.serving_image_uri:
        raise SystemExit("VERTEX_SERVING_IMAGE_URI or --serving-image-uri is required")

    model = register_model(
        project=args.project,
        region=args.region,
        artifact_uri=args.artifact_uri,
        display_name=args.display_name,
        model_id=args.model_id,
        version_alias=args.version_alias,
        run_name=args.run_name,
        serving_image_uri=args.serving_image_uri,
    )
    print(f"VERTEX_MODEL_RESOURCE={model.resource_name}")
    print(f"VERTEX_MODEL_VERSION={model.version_id}")


if __name__ == "__main__":
    main()
