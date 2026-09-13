# V4 Serving & Cloud — FastAPI + Cloud Run

## Goal

V4 turns the validated forecasting model into a business-facing service without changing the forecasting methodology or hiding data dependencies behind an LLM.

```text
Client / future Agent
        |
        v
FastAPI / Cloud Run
        |
        +--> model artifact loaded once from GCS
        |
        +--> BigQuery: resolve item/store series
        |       +--> 28 observed seed days
        |       +--> target-free future covariates
        |
        v
shared recursive_forecast()
        |
        v
28-day demand forecast
```

## Why Cloud Run owns the recursive forecast

The LightGBM booster predicts one feature row at a time, but RetailOps forecasting is stateful across the 28-day horizon: predictions from earlier horizons become later lag and rolling features. Calling a raw Vertex prediction endpoint once per horizon would add network latency and cost while still leaving feature-state management elsewhere.

V4 therefore loads the promoted LightGBM artifact into the Cloud Run container and executes the existing `recursive_forecast()` implementation in-process. Vertex AI remains responsible for V3 training, experiments, quality-gated promotion, and model versioning. Cloud Run becomes the business API and is the natural tool boundary for the V5 agent.

## API contract

### `GET /healthz`

Process liveness. It does not query BigQuery.

### `GET /readyz`

Returns ready only after the model artifact and runtime clients have initialized.

### `GET /v1/model`

Returns non-sensitive model metadata such as model/version/run identity and validation metrics. GCS artifact paths and categorical levels are intentionally not exposed.

### `POST /v1/forecast`

Example request:

```json
{
  "entities": [
    {"item_id": "FOODS_1_001", "store_id": "CA_1"}
  ],
  "split": "test"
}
```

The response contains one 28-day series per requested item/store combination plus the model identity and a request ID.

Batch requests are deliberately bounded by `SERVING_MAX_ENTITIES` to prevent accidental full-dataset scans through an online endpoint.

## Leakage and temporal contract

V4 supports only the existing `validation` and `test` forecast windows because those windows have target-free covariates already materialized in BigQuery.

- `validation` forecasting seeds the recursion with the final 28 observed TRAIN days.
- `test` forecasting seeds the recursion with the 28 observed VALIDATION days.
- neither path reads target values from the horizon being predicted.

The service does **not** invent prices, promotions, events, SNAP indicators, or calendar covariates beyond the M5 data contract. A real live-retail deployment would need upstream systems to supply those future-known covariates.

## Runtime model contract

At container startup:

1. `MODEL_ARTIFACT_URI` identifies the promoted run directory in GCS.
2. `model.txt` and `metadata.json` are downloaded once into `/tmp`.
3. LightGBM is loaded once per Cloud Run instance.
4. category levels from training metadata are reused exactly at inference.
5. request-time BigQuery reads are restricted to the requested series.

This keeps training and serving feature contracts aligned.

## Cloud Run defaults

The Python deployment helper uses conservative portfolio defaults:

```text
CPU:             1
Memory:          1 GiB
Min instances:   0
Max instances:   2
Concurrency:     10
Timeout:         120 s
Authentication:  private by default
```

`min-instances=0` allows scale-to-zero. Public access requires `--public`; deployment itself requires `--confirm-cost`.

## Build and deploy

After V3 has produced a real promoted artifact and V4 IAM is configured:

```bash
uv sync
uv run python scripts/check.py
uv run python cloudrun/build_api_image.py --tag v4
uv run python cloudrun/deploy_api.py --confirm-cost
```

No deployment should be described as validated until a real Cloud Run revision passes `/readyz` and a real `/v1/forecast` request against BigQuery.

## CI/CD

`.github/workflows/ci.yml` runs Ruff and pytest on Python 3.12 for pushes and pull requests.

`.github/workflows/deploy-cloudrun.yml` is deliberately manual (`workflow_dispatch`). It authenticates through Google Workload Identity Federation, builds the API image with Cloud Build, and deploys a private Cloud Run revision. No long-lived GCP service-account key is required in GitHub.

Required GitHub repository variables for deployment are documented in the workflow and will be configured only when the cloud execution phase starts.

## V4 validation boundary

Code-complete does not mean cloud-validated. V4 is complete only after all of the following have happened on GCP:

```text
Cloud Build image succeeds
Artifact Registry contains the image
Cloud Run revision becomes ready
/v1/model returns the promoted model identity
/v1/forecast returns 28 predictions for a real M5 series
Cloud Logging shows the request ID and latency
```
