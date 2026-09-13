# Vertex model serving container

This directory contains the minimal Vertex-compatible prediction container attached to custom LightGBM versions in Model Registry.

It accepts fully prepared feature rows through `/predict`. Model loading is shared with the V4 Cloud Run business API through `retailops_ai.serving.model`, so both runtimes consume the same `model.txt`, `metadata.json`, and categorical-level contract.

This container is **not** the business-facing forecasting API. It does not query BigQuery or manage the 28-day recursive state. Those responsibilities belong to V4 under `api/` and `retailops_ai.serving.service`.

No Vertex endpoint is created during V3. `vertex/deploy_endpoint.py` remains guarded because online Vertex endpoint compute can generate persistent charges.
