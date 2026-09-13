# Vertex Model Registry serving container

This container exists in V3 so a custom LightGBM artifact can be imported into Vertex AI Model Registry with a valid custom prediction container contract.

It exposes:

- `GET /health`
- `POST /predict`

At Vertex startup, `AIP_STORAGE_URI` points to the registered model artifact directory. The container downloads `model.txt` and `metadata.json`, restores the training category levels, and accepts already-engineered model feature rows.

The business-facing forecast API and recursive 28-day serving workflow remain a V4 concern. This container is **not deployed to an endpoint during V3**.
