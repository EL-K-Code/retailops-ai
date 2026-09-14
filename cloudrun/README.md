# Cloud Run workloads

This directory contains helpers for two distinct RetailOps AI workloads:

1. **Training fallback with Cloud Run Jobs** when Vertex AI Custom Training
   quota is unavailable.
2. **V4 business-facing forecasting API serving** on Cloud Run services.

Both training backends reuse the same `training/Dockerfile` and
`training/train.py`. Cloud Run Jobs does not replace Vertex AI; it provides a
quota-friendly execution path while preserving the same BigQuery inputs, GCS
artifact contract, LightGBM implementation, and optional Vertex AI Experiment
logging.

## Training job

Deploy the reusable job definition:

```bash
uv run python cloudrun/deploy_training_job.py --confirm-cost
```

Run a small smoke test:

```bash
uv run python cloudrun/run_training_job.py \
  --train-lookback-days 30 \
  --num-boost-round 20 \
  --confirm-cost
```

Each execution writes artifacts under:

```text
gs://<model-bucket>/cloudrun-training/<run-name>/model/
├── model.txt
├── metadata.json
└── metrics.json
```

The deployment helper uses one CPU, 4 GiB memory, one task, zero retries, and a
one-hour timeout by default. The job is deployed with `--help` as its default
argument so an accidental manual execution does not start a full training run;
the runner supplies explicit execution overrides.

## Forecast API serving

The API container lives under `api/`. It loads one promoted LightGBM artifact
at container startup, queries only the requested item/store series from
BigQuery, and executes the full 28-day recursive forecast in-process.

Serving defaults are intentionally conservative: one CPU, 1 GiB memory,
`min-instances=0`, `max-instances=2`, and a private service. Public access
requires an explicit `--public` flag, and deployment requires
`--confirm-cost`.

```bash
uv run python cloudrun/build_api_image.py --tag v4
uv run python cloudrun/deploy_api.py --confirm-cost
```

The agent contract is unchanged: it continues to call the forecasting API and
does not depend on whether the model was trained by Vertex AI or Cloud Run Jobs.
