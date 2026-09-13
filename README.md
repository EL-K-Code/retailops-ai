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
Serving / Agentic AI
```

## Roadmap

- **V0 — Foundation:** repository, Python project, configuration, dependency management, initial documentation.
- **V1 — Data Engineering:** public retail dataset, ingestion, GCS, BigQuery, dbt layers, tests, documentation and marts.
- **V2 — Machine Learning:** demand forecasting, temporal validation, baselines, ML models, stockout-risk logic and error analysis.
- **V3 — MLOps:** cloud training, experiment tracking, artifacts, model versioning and Vertex AI Model Registry.
- **V4 — Serving & Cloud:** FastAPI/custom prediction container, Artifact Registry, Cloud Run or Vertex endpoint, and CI/CD.
- **V5 — Agentic AI:** LangGraph, warehouse/model tools, RAG and human-in-the-loop workflows.
- **V6 — Production Quality:** orchestration, observability, monitoring, infrastructure as code and portfolio demo.

## Current milestone

**V3 — MLOps**

Implemented and locally validated so far:

- reproducible M5 dataset acquisition workflow;
- source contract validation and structural profiling;
- immutable GCS landing uploader with SHA-256 traceability and create-only upload semantics;
- BigQuery RAW loader with explicit schemas, deterministic table rebuilds and row-count validation;
- dbt STAGING transformations with long-format sales, data tests, partitioning and clustering;
- dbt SILVER warehouse model with reusable date/product/store dimensions and daily-sales/weekly-price facts;
- dbt GOLD marts for item-store demand, store-day summaries, and product-day summaries with explicit price-coverage semantics;
- leakage-aware 28-day demand-forecasting contract with fixed chronological train, validation, and test windows;
- leakage-safe last-value, seasonal-7, and seasonal-28 baselines with MAE, RMSE, and bottom-level mean RMSSE evaluation;
- leakage-safe ML feature layer with training-only lag/rolling features and target-free validation/test covariates;
- Python global LightGBM training pipeline with bounded BigQuery reads, recursive 28-day inference, validation metrics, local model artifacts, and optional prediction/evaluation writes back to BigQuery;
- real 90-day / 100-round LightGBM validation run over 2,744,100 training rows;
- Vertex AI custom-training container and orchestration code;
- run-scoped GCS model artifacts;
- Vertex AI Experiment logging for parameters and validation metrics;
- Vertex-compatible custom LightGBM prediction container for model import;
- Vertex AI Model Registry versioning workflow.

The V3 code path is implemented. A real Vertex AI training execution is still an environment-specific validation step and must not be described as cloud-validated until the GCP configuration and first job complete successfully.

## Engineering principles

- Raw source data is kept as close as possible to the original source.
- Business transformations belong in explicit transformation layers.
- Temporal ML problems use temporal validation rather than random splits.
- Forecast features respect as-of-time availability and must not use future target information.
- Simple baselines establish a minimum performance bar before learned models are introduced.
- Validation and test covariate contracts do not expose observed future demand.
- Learned multi-step forecasts append predictions, not hidden future labels, to the recursive history state.
- Local and Vertex training share the same forecasting implementation.
- Model artifacts are run-specific and immutable by convention.
- Secrets and credentials are never committed to Git.
- New infrastructure is introduced only when it solves a concrete problem.
- A technology is considered part of the validated stack only after it has actually been executed successfully.

## Implemented data and ML architecture

```text
Dataset
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
  -> GCS run artifacts
  -> Vertex AI Experiments
  -> Vertex AI Model Registry
```

The public dataset is the **M5 Forecasting** retail dataset because it provides daily item-store sales, prices, and calendar information suitable for the demand-forecasting use case.

## Forecasting evaluation contract

The primary forecasting horizon is 28 days. The current fixed split is:

```text
Train:      2011-01-29 -> 2016-03-27
Validation: 2016-03-28 -> 2016-04-24
Test:       2016-04-25 -> 2016-05-22
```

The final test window remains untouched during model and feature selection.

Current validation baselines:

```text
Last value
Seasonal naive (7 days)
Seasonal naive (28 days)
```

Baseline comparison reports MAE, RMSE, and unweighted mean RMSSE across bottom-level item-store series. The official competition WRMSSE is intentionally deferred because it additionally requires hierarchical aggregation and value-based weighting.

The first learned model is a global LightGBM Poisson regressor trained in Python. Offline lag/rolling features are prepared in BigQuery/dbt for TRAIN. Validation is forecast recursively in Python using only the final observed training history plus earlier model predictions and target-free future covariates.

### Validated 90-day LightGBM run

```text
Training rows: 2,744,100
Boosting rounds: 100
MAE:        1.076782
RMSE:       2.175634
mean RMSSE: 0.771130
```

Reference baselines on the same 28-day validation window:

```text
naive_last         MAE 1.350344 | RMSE 3.300666 | mean RMSSE 0.952306
seasonal_naive_7   MAE 1.232355 | RMSE 2.759459 | mean RMSSE 0.975596
seasonal_naive_28  MAE 1.258023 | RMSE 2.836503 | mean RMSSE 1.005899
```

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
  model.txt
  metadata.json
  metrics.json
      |
      +--> custom LightGBM serving image
      |
      v
Vertex AI Model Registry
```

See `docs/mlops_vertex.md` for the deployment contract and GCP prerequisites.

## Status

- **V1 Data Engineering:** real GCP execution validated end to end.
- **V2 Machine Learning:** real BigQuery-backed LightGBM validation run completed and beats all implemented baselines.
- **V3 MLOps:** code implemented; real Vertex AI cloud execution pending GCP configuration and validation.
- **V4 Serving:** not yet validated.
