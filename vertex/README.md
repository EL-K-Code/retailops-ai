# Vertex AI MLOps

This directory contains the V3 orchestration layer for RetailOps AI.

## V3 responsibilities

1. Build the custom LightGBM training image with Cloud Build.
2. Build a Vertex-compatible LightGBM prediction image for Model Registry.
3. Run the validated training/evaluation code on Vertex AI Custom Training.
4. Store each run under a unique GCS artifact directory.
5. Log parameters and MAE/RMSE/mean-RMSSE in Vertex AI Experiments.
6. Register the resulting artifact as a version in Vertex AI Model Registry.

The serving image is attached to the registry model because Vertex requires a prediction container for custom model upload. **V3 does not create an endpoint.** Business-facing online serving and recursive 28-day inference remain V4.

## Main commands

Build the two images:

```bash
python vertex/build_training_image.py --tag v1
python vertex/build_serving_image.py --tag v1
```

Run training only:

```bash
python -m vertex.submit_training_job
```

Run training and register the resulting model version:

```bash
python -m vertex.run_training_pipeline
```

The cloud resources and IAM prerequisites are documented in `docs/mlops_vertex.md`.
