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
        v
RMSSE quality gate
  candidate must beat the best validated baseline
        |
        +--> FAIL: keep run + artifacts, do not register
        |
        v PASS
Artifact Registry serving image
        |
        v
Vertex AI Model Registry
  version 1 / version 2 / ...
```

## Design decisions

- **One training implementation:** local and Vertex runs reuse `retailops_ai.ml`; there is no second forecasting algorithm in the cloud.
- **Run-specific artifacts:** every Vertex job receives a unique `base_output_dir`; Vertex exposes its model directory as `AIP_MODEL_DIR`.
- **Experiment tracking:** model parameters and validation metrics are logged to Vertex AI Experiments.
- **Quality-gated registration:** successful compute is not enough. A candidate is registered only when its mean RMSSE is strictly below the configured baseline ceiling. The initial ceiling is the best validated baseline, `naive_last = 0.952306197699721`.
- **Registry versioning:** the first promoted model creates the registry model; later promoted runs become new versions with a movable `candidate` alias.
- **Valid custom-model registration:** LightGBM uses a small custom prediction container when imported into Model Registry.
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
VERTEX_MACHINE_TYPE=n1-standard-4
VERTEX_TRAIN_LOOKBACK_DAYS=90
VERTEX_NUM_BOOST_ROUND=100
VERTEX_MAX_MEAN_RMSSE=0.952306197699721
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
python scripts/check.py
python vertex/build_training_image.py --tag v1
python vertex/build_serving_image.py --tag v1
python -m vertex.run_training_pipeline
```

The pipeline waits for training to finish, reads the run's `metrics.json`, applies the quality gate, and only then registers a passing artifact directory as a new model version.

## Artifact contract

Each training run writes:

```text
gs://<model-bucket>/vertex-training/<run-name>/model/
├── model.txt
├── metadata.json
└── metrics.json
```

`metadata.json` includes the exact LightGBM feature order, category levels, training configuration, dates, and run identity. The Model Registry prediction container uses those category levels to reconstruct the same model frame used during training.

## Promotion contract

For the first V3 validation, the registry threshold is tied to the strongest validated baseline on mean RMSSE:

```text
naive_last mean RMSSE = 0.952306197699721
```

A cloud candidate with `mean_rmsse >= 0.952306197699721` is retained in Vertex Experiments and GCS for diagnosis, but it is **not** promoted to Model Registry. The threshold is configurable through `VERTEX_MAX_MEAN_RMSSE` for later experiments.

## Cost guardrails

The first validation run uses one `n1-standard-4` worker, no GPU, 90 training days, and 100 boosting rounds—the same budget that already beat the baselines locally. Increase the history or boosting budget only after that cloud path is verified. V3 creates no online endpoint, so it avoids persistent prediction-compute charges.

`vertex/deploy_endpoint.py` belongs to V4 and refuses to deploy unless `--confirm-cost` is explicitly supplied.

## Validation status

The V3 code path is implemented. It must not be presented as cloud-validated until a real Vertex AI Custom Training run completes and its experiment, GCS artifacts, quality gate, and Model Registry version are verified in GCP.
