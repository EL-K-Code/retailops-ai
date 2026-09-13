# RetailOps AI

**End-to-End Data, ML & Agentic AI Platform**

RetailOps AI is a portfolio project that progressively builds a production-like Data & AI platform for retail, e-commerce, and supply-chain decision support.

The project is intentionally developed in milestones. Each capability is added only after the previous layer has been implemented, tested, and validated.

## Target architecture

```text
Public retail data
      |
      v
Python ingestion
      |
      v
Google Cloud Storage
      |
      v
BigQuery RAW
      |
      v
dbt: STAGING -> SILVER -> GOLD / MARTS
      |
      v
ML-ready datasets
      |
      +--> Demand forecasting
      +--> Stockout risk
      |
      v
Vertex AI MLOps
      |
      v
FastAPI / Cloud Run
      |
      v
Agentic AI
```

## Roadmap

- **V0 — Foundation:** repository, Python project, configuration, dependency management, initial documentation.
- **V1 — Data Engineering:** public retail dataset, ingestion, GCS, BigQuery, dbt layers, tests, documentation and marts.
- **V2 — Machine Learning:** demand forecasting, temporal validation, baselines, ML models, stockout-risk logic and error analysis.
- **V3 — MLOps:** cloud training, experiment tracking, artifacts, quality-gated model versioning and Vertex AI Model Registry.
- **V4 — Serving & Cloud:** FastAPI business API, recursive forecasting service, Cloud Run, Artifact Registry and CI/CD.
- **V5 — Agentic AI:** LangGraph, warehouse/model tools, RAG and human-in-the-loop workflows.
- **V6 — Production Quality:** orchestration, observability, monitoring, infrastructure as code and portfolio demo.

## Current milestone

**V4 — Serving & Cloud**

Implemented so far:

- reproducible M5 dataset acquisition workflow;
- immutable GCS landing uploader with SHA-256 traceability and create-only upload semantics;
- BigQuery RAW ingestion with explicit schemas and row-count validation;
- dbt STAGING, SILVER and GOLD transformations with data tests, partitioning and clustering;
- leakage-aware 28-day forecasting contract with fixed train, validation and test windows;
- last-value, seasonal-7 and seasonal-28 baselines with MAE, RMSE and bottom-level mean RMSSE;
- leakage-safe training features and target-free validation/test covariates;
- global LightGBM Poisson model with recursive 28-day inference;
- real 90-day / 100-round local validation run over 2,744,100 rows;
- Vertex AI custom-training container and orchestration code;
- Vertex AI Experiment logging and run-scoped GCS artifacts;
- RMSSE quality gate before Model Registry promotion;
- Vertex AI Model Registry versioning workflow;
- shared model-artifact loader used by both Vertex and Cloud Run serving;
- business-facing FastAPI forecasting API;
- series-scoped BigQuery reads for item/store requests;
- leakage-safe validation/test seed-history selection;
- in-process recursive 28-day serving without 28 remote model calls;
- Cloud Run Docker image, Cloud Build workflow and guarded deployment helper;
- health, readiness, model-info and forecasting API contracts;
- bounded batch requests and request-ID propagation;
- GitHub Actions CI and manual Workload Identity Federation deployment workflow.

The V3 and V4 code paths are implemented. They must not be described as cloud-validated until the real Vertex AI and Cloud Run executions complete successfully in GCP.

## Engineering principles

- Raw source data stays as close as possible to the original source.
- Business transformations belong in explicit transformation layers.
- Temporal ML problems use temporal validation rather than random splits.
- Forecast features respect as-of-time availability and never use future target information.
- Simple baselines establish a minimum performance bar before learned models are promoted.
- Learned multi-step forecasts append predictions, not hidden future labels, to recursive state.
- Local, Vertex and Cloud Run paths share the same forecasting implementation.
- Model artifacts are run-specific and versioned through the MLOps layer.
- Online requests fetch only the requested item/store series from BigQuery.
- The API never invents unknown future prices, promotions or calendar covariates.
- Secrets and credentials are never committed to Git.
- Cloud deployment is private and scale-to-zero by default.
- A technology is considered part of the validated stack only after it has actually been executed successfully.

## Implemented data, ML and serving architecture

```text
M5 dataset
  -> GCS landing
  -> BigQuery RAW
  -> dbt STAGING
  -> dbt SILVER
  -> dbt GOLD / MARTS
  -> dbt ML temporal contract
  -> validation baselines
  -> leakage-safe training features / future covariates
  -> Python LightGBM training / recursive inference
  -> Vertex AI Custom Training (V3 code path)
  -> Vertex AI Experiments
  -> GCS run artifacts
  -> RMSSE quality gate
  -> Vertex AI Model Registry
  -> FastAPI / Cloud Run (V4 code path)
  -> future V5 agent tools
```

The public dataset is the **M5 Forecasting** retail dataset because it provides daily item-store sales, prices, and calendar information suitable for the demand-forecasting use case.

## Forecasting evaluation contract

The primary forecasting horizon is 28 days:

```text
Train:      2011-01-29 -> 2016-03-27
Validation: 2016-03-28 -> 2016-04-24
Test:       2016-04-25 -> 2016-05-22
```

Current validation baselines:

```text
naive_last         MAE 1.350344 | RMSE 3.300666 | mean RMSSE 0.952306
seasonal_naive_7   MAE 1.232355 | RMSE 2.759459 | mean RMSSE 0.975596
seasonal_naive_28  MAE 1.258023 | RMSE 2.836503 | mean RMSSE 1.005899
```

### Validated 90-day LightGBM run

```text
Training rows: 2,744,100
Boosting rounds: 100
MAE:        1.076782
RMSE:       2.175634
mean RMSSE: 0.771130
```

This run beats all implemented baselines. The project reports unweighted mean bottom-level RMSSE, not the official hierarchical M5 WRMSSE.

## V3 MLOps flow

```text
Repository code
      |
      v
Cloud Build
      |
      v
Artifact Registry training image
      |
      v
Vertex AI Custom Training
      |
      +--> BigQuery ML features
      +--> Vertex AI Experiment
      |
      v
GCS model artifacts
      |
      v
RMSSE quality gate
      |
      v
Vertex AI Model Registry
```

See `docs/mlops_vertex.md`.

## V4 serving flow

```text
Client / future Agent
      |
      v
FastAPI on Cloud Run
      |
      +--> promoted model artifact from GCS
      |
      +--> BigQuery requested series only
      |      +--> 28 observed seed days
      |      +--> target-free horizon covariates
      |
      v
shared recursive_forecast()
      |
      v
28-day demand forecast
```

The Cloud Run layer deliberately executes the complete recursive forecast in-process instead of calling a raw model endpoint 28 times. The service is private by default, uses `min-instances=0`, and caps instance count and batch size for cost control.

See `docs/serving_cloudrun.md`.

## API surface

```text
GET  /healthz
GET  /readyz
GET  /v1/model
POST /v1/forecast
```

Example request:

```json
{
  "entities": [
    {"item_id": "FOODS_1_001", "store_id": "CA_1"}
  ],
  "split": "test"
}
```

## Status

- **V1 Data Engineering:** real GCP execution validated end to end.
- **V2 Machine Learning:** real BigQuery-backed LightGBM validation run completed and beats all implemented baselines.
- **V3 MLOps:** code implemented; real Vertex AI cloud execution pending GCP configuration and validation.
- **V4 Serving & Cloud:** code implemented; real Cloud Build / Artifact Registry / Cloud Run validation pending.
- **V5 Agentic AI:** next development milestone after V3/V4 cloud validation.
