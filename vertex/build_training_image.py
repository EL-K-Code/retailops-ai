"""Build the RetailOps training container with Cloud Build."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--region", default=os.getenv("VERTEX_REGION", "us-central1"))
    parser.add_argument(
        "--repository",
        default=os.getenv("VERTEX_ARTIFACT_REPOSITORY", "retailops-ml"),
    )
    parser.add_argument("--image", default="retailops-lightgbm-training")
    parser.add_argument("--tag", default="v1")
    parser.add_argument("--image-uri", default=os.getenv("VERTEX_TRAINING_IMAGE_URI"))
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
    if not args.project:
        raise SystemExit("GOOGLE_CLOUD_PROJECT or --project is required")

    image_uri = args.image_uri or (
        f"{args.region}-docker.pkg.dev/{args.project}/"
        f"{args.repository}/{args.image}:{args.tag}"
    )

    command = [
        _resolve_gcloud(),
        "builds",
        "submit",
        "--project",
        args.project,
        "--region",
        args.region,
        "--config",
        "training/cloudbuild.yaml",
        "--substitutions",
        f"_IMAGE_URI={image_uri}",
        ".",
    ]
    print("$ " + " ".join(command))
    subprocess.run(command, check=True)
    print(f"VERTEX_TRAINING_IMAGE_URI={image_uri}")


if __name__ == "__main__":
    main()
