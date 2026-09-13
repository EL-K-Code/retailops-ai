# V3 MLOps — Vertex AI

## Goal

Move RetailOps AI from laptop-bound training to a reproducible cloud workflow without changing the validated forecasting methodology.

```text
BigQuery ML features
        |
        v
Artifact Registry training image
        |
        v
Vertex AI Custom Training
        |
        +--> Vertex AI Experiment
        |      params + MAE/RMSE/mean-RMSSE
        |
        v
GCS run artifacts
  model.txt
  metadata.json
  metrics.json
        |
        +--> Artifact Registry serving image
        |
        v
Vertex AI Model Registry
  version 1 / version 2 / ...
```

## Design decisions

- **One training implementation:** local and Vertex runs reuse `retailops_ai.ml`; there is no second forecasting algorithm in the cloud.
- **Run-specific artifacts:** every Vertex job receives a unique `base_output_dir`; Vertex exposes its model directory as `AIP_MODEL_DIR`.
- **Experiment tracking:** model parameters and validation metrics are logged to Vertex AI Experiments.
- **Registry versioning:** the first successful model creates the registry model; later successful runs become new versions with a `candidate` alias.
- **Valid custom-model registration:** LightGBM is not one of Vertex AI's prebuilt prediction frameworks, so V3 builds a small custom prediction container and attaches it when importing the model.
- **Serving separation:** the V3 serving image satisfies Model Registry's custom container contract but no endpoint is created. Business-facing serving, recursive 28-day forecasting, autoscaling, and Cloud Run/Vertex endpoint decisions belong to V4.

## Required environment

```env
GOOGLE_CLOUD_PROJECT=retailops-ai-2026
VERTEX_REGION=us-central1
VERTEX_ARTIFACT_REPOSITORY=retailops-ml
VERTEX_TRAINING_IMAGE_URI=us-central1-docker.pkg.dev/retailops-ai-2026/retailops-ml/retailops-lightgbm-training:v1
VERTEX_SERVING_IMAGE_URI=us-central1-docker.pkg.dev/retailops-ai-2026/retailops-ml/retailops-lightgbm-serving:v1
VERTEX_OUTPUT_ROOT=gs://retailops-ai-2026-models
VERTEX_SERVICE_ACCOUNT=retailops-vertex-sa@retailops-ai-2026.iam.gserviceaccount.com
VERTEX_MACHINE_TYPE=e2-standard-4
VERTEX_EXPERIMENT=retailops-demand-forecasting
VERTEX_MODEL_DISPLAY_NAME=retailops-lightgbm-global
VERTEX_MODEL_ID=retailops-lightgbm-global
VERTEX_MODEL_ALIAS=candidate
```

No credentials or service-account keys belong in Git. Local submission uses Application Default Credentials; the Vertex workload itself uses its service account.

## Execution sequence

After GCP APIs, IAM, the Artifact Registry repository, and the model bucket are configured:

```bash
uv sync
python vertex/build_training_image.py --tag v1
python vertex/build_serving_image.py --tag v1
python -m vertex.run_training_pipeline
```

The pipeline waits for training to finish and only then registers the successful artifact directory as a new model version.

## Artifact contract

Each training run writes:

```text
gs://<model-bucket>/vertex-training/<run-name>/model/
├── model.txt
├── metadata.json
└── metrics.json
```

`metadata.json` includes the exact LightGBM feature order, category levels, training configuration, dates, and run identity. The serving container uses those category levels to reconstruct the same model frame used during training.

## Cost guardrails

The default machine is `e2-standard-4`, with one replica and no GPU. Keep the first cloud validation run at the already proven 90-day / 100-round budget before increasing training history or boosting rounds. V3 creates no online endpoint, so it avoids persistent prediction compute charges.

## Validation status

The V3 code path is implemented. It must not be presented as cloud-validated until a real Vertex AI Custom Training run completes and its experiment, artifacts, and Model Registry version are verified in GCP.
