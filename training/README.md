# Cloud training container

This directory packages the same global LightGBM forecasting logic used by the
validated local pipeline.

The container is intentionally backend-agnostic: the same image can run on
Vertex AI Custom Training or Cloud Run Jobs without changing the forecasting
implementation.

The Docker build context must be the repository root because the container
copies the shared `src/retailops_ai` package:

```bash
docker build -f training/Dockerfile -t retailops-lightgbm-training:local .
```

The entrypoint writes `model.txt`, `metadata.json`, and `metrics.json` locally,
then uploads them to the run-specific GCS directory supplied through
`--artifact-uri`.

Vertex AI sets `AIP_MODEL_DIR` automatically when a custom training job uses a
`base_output_dir`. Cloud Run Jobs passes the same artifact contract explicitly.

When an experiment is configured, parameters and validation metrics are still
logged to Vertex AI Experiments regardless of which compute backend executes the
container.

The image is intended for training only. Business-facing online serving remains
a separate Cloud Run workload.
