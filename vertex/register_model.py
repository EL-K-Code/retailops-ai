"""Register RetailOps model artifacts in Vertex AI Model Registry."""

import os
from google.cloud import aiplatform

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "retailops-ai-2026")
REGION = os.getenv("VERTEX_REGION", "us-central1")
MODEL_ARTIFACT_URI = os.environ["MODEL_ARTIFACT_URI"]
SERVING_IMAGE = os.environ.get("VERTEX_SERVING_IMAGE_URI")


def main():
    aiplatform.init(project=PROJECT_ID, location=REGION)

    model = aiplatform.Model.upload(
        display_name="retailops-lightgbm-global",
        artifact_uri=MODEL_ARTIFACT_URI,
        serving_container_image_uri=SERVING_IMAGE,
    )

    print(model.resource_name)


if __name__ == "__main__":
    main()
