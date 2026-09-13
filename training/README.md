# Vertex AI training container

This directory packages the same global LightGBM forecasting logic used by the validated local pipeline.

The Docker build context must be the repository root because the container copies the shared `src/retailops_ai` package:

```bash
docker build -f training/Dockerfile -t retailops-lightgbm-training:local .
```

Vertex AI sets `AIP_MODEL_DIR` when the custom job is launched with `base_output_dir`. The training entrypoint writes `model.txt`, `metadata.json`, and `metrics.json` locally, then uploads them to that run-specific GCS model directory.

The container also logs parameters and validation metrics to Vertex AI Experiments when `VERTEX_EXPERIMENT` is configured.

The image is intended for training only. Online endpoint deployment remains V4.
