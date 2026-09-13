# V4 Cloud Run serving

This directory contains the build and deployment helpers for the business-facing forecasting API.

The API container lives under `api/`. It loads one promoted LightGBM artifact at container startup, queries only the requested item/store series from BigQuery, and executes the full 28-day recursive forecast in-process.

Cloud Run defaults are intentionally conservative: one CPU, 1 GiB memory, `min-instances=0`, `max-instances=2`, and a private service. Public access requires an explicit `--public` flag, and deployment requires `--confirm-cost`.

```bash
uv run python cloudrun/build_api_image.py --tag v4
uv run python cloudrun/deploy_api.py --confirm-cost
```

Do not deploy until V3 has produced a real promoted model artifact and the V4 GCP service account/IAM configuration is ready.
