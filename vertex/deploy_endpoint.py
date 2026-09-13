"""V4-only: deploy a registered RetailOps model to a paid Vertex AI endpoint.

This command is intentionally guarded because an online endpoint provisions
persistent prediction compute and can incur charges while deployed.
"""

from __future__ import annotations

import argparse
import os

from google.cloud import aiplatform


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--region", default=os.getenv("VERTEX_REGION", "us-central1"))
    parser.add_argument("--model-resource", default=os.getenv("VERTEX_MODEL_RESOURCE"))
    parser.add_argument(
        "--machine-type",
        default=os.getenv("VERTEX_ENDPOINT_MACHINE_TYPE", "e2-standard-2"),
    )
    parser.add_argument(
        "--confirm-cost",
        action="store_true",
        help="Required acknowledgement that an online endpoint can incur persistent charges.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.project:
        raise SystemExit("GOOGLE_CLOUD_PROJECT or --project is required")
    if not args.model_resource:
        raise SystemExit("VERTEX_MODEL_RESOURCE or --model-resource is required")
    if not args.confirm_cost:
        raise SystemExit(
            "Endpoint deployment is a V4 paid operation. Re-run with --confirm-cost "
            "only when you intentionally want to provision online prediction compute."
        )

    aiplatform.init(project=args.project, location=args.region)
    model = aiplatform.Model(model_name=args.model_resource)
    endpoint = model.deploy(
        deployed_model_display_name="retailops-lightgbm-endpoint",
        machine_type=args.machine_type,
        min_replica_count=1,
        max_replica_count=1,
    )
    print(f"VERTEX_ENDPOINT_RESOURCE={endpoint.resource_name}")


if __name__ == "__main__":
    main()
