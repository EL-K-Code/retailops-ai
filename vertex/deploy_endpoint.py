"""Deploy RetailOps model to a Vertex AI endpoint."""

import os
from google.cloud import aiplatform

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "retailops-ai-2026")
REGION = os.getenv("VERTEX_REGION", "us-central1")
MODEL_RESOURCE = os.environ["VERTEX_MODEL_RESOURCE"]


def main():
    aiplatform.init(project=PROJECT_ID, location=REGION)

    model = aiplatform.Model(model_name=MODEL_RESOURCE)
    endpoint = model.deploy(
        deployed_model_display_name="retailops-lightgbm-endpoint",
        machine_type="n1-standard-4",
    )

    print(endpoint.resource_name)


if __name__ == "__main__":
    main()
