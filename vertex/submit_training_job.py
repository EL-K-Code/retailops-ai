"""Submit RetailOps LightGBM training to Vertex AI."""

import os
from google.cloud import aiplatform

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "retailops-ai-2026")
REGION = os.getenv("VERTEX_REGION", "us-central1")
IMAGE_URI = os.environ["VERTEX_TRAINING_IMAGE_URI"]


def main():
    aiplatform.init(project=PROJECT_ID, location=REGION)

    job = aiplatform.CustomContainerTrainingJob(
        display_name="retailops-lightgbm-training",
        container_uri=IMAGE_URI,
    )

    job.run(
        args=[
            "--train-lookback-days", "90",
            "--num-boost-round", "100",
        ],
        replica_count=1,
        machine_type="n1-standard-4",
    )


if __name__ == "__main__":
    main()
