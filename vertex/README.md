# Vertex AI MLOps

This directory contains the V3 orchestration layer for RetailOps AI.

## V3 responsibilities

1. Build the custom LightGBM training image with Cloud Build.
2. Build a Vertex-compatible LightGBM prediction image for Model Registry.
3. Run the validated training/evaluation code on Vertex AI Custom Training.
4. Store each run under a unique GCS artifact directory.
5. Log parameters and MAE/RMSE/mean-RMSSE in Vertex AI Experiments.
6. Apply an RMSSE quality gate against the best validated baseline.
7. Register only passing artifacts as versions in Vertex AI Model Registry.

The serving image is attached to the registry model because Vertex requires a
prediction container for custom model upload. **V3 does not create an endpoint.**
Business-facing online serving and recursive 28-day inference remain V4.

The promotion step is backend-neutral: an artifact produced by Vertex AI Custom
Training or by the Cloud Run Jobs fallback can be evaluated with the same RMSSE
gate and registered through the same Model Registry path.

## Main commands

Synchronize the Python 3.12 environment and run local checks:

```bash
uv sync
python scripts/check.py
```

Build the two images through the project environment:

```bash
uv run python vertex/build_training_image.py --tag v1
uv run python vertex/build_serving_image.py --tag v1
```

Run Vertex training only:

```bash
uv run python -m vertex.submit_training_job
```

Run Vertex training, apply the quality gate, and register a passing model version:

```bash
uv run python -m vertex.run_training_pipeline
```

Quality-gate and register an already-trained artifact, including one produced by
Cloud Run Jobs:

```bash
uv run python -m vertex.promote_artifact \
  --artifact-uri gs://<model-bucket>/cloudrun-training/<run-name>/model \
  --run-name <run-name> \
  --serving-image-uri <vertex-serving-image-uri>
```

The candidate must have `mean_rmsse` strictly below the configured
`VERTEX_MAX_MEAN_RMSSE`. A failing artifact remains in GCS but is not registered.

The cloud resources and IAM prerequisites are documented in `docs/mlops_vertex.md`.
