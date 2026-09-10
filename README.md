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
ML serving / MLOps / Agentic AI (later milestones)
```

## Roadmap

- **V0 — Foundation:** repository, Python project, configuration, dependency management, initial documentation.
- **V1 — Data Engineering:** public retail dataset, ingestion, GCS, BigQuery, dbt layers, tests, documentation and marts.
- **V2 — Machine Learning:** demand forecasting, temporal validation, baselines, ML models, stockout-risk logic and error analysis.
- **V3 — MLOps:** experiment tracking, artifacts, model versioning and registry.
- **V4 — Serving & Cloud:** FastAPI, Docker, Artifact Registry, Cloud Run and CI/CD.
- **V5 — Agentic AI:** LangGraph, warehouse/model tools, RAG and human-in-the-loop workflows.
- **V6 — Production Quality:** orchestration, observability, monitoring, infrastructure as code and portfolio demo.

## Current milestone

**V2 — Machine Learning**

Implemented so far:

- reproducible M5 dataset acquisition workflow;
- source contract validation and structural profiling;
- immutable GCS landing uploader with SHA-256 traceability and create-only upload semantics;
- BigQuery RAW loader with explicit schemas, deterministic table rebuilds and row-count validation;
- dbt STAGING transformations with long-format sales, data tests, partitioning and clustering;
- dbt SILVER warehouse model with reusable date/product/store dimensions and daily-sales/weekly-price facts;
- dbt GOLD marts for item-store demand, store-day summaries, and product-day summaries with explicit price-coverage semantics;
- leakage-aware 28-day demand-forecasting contract with fixed chronological train, validation, and test windows.

Cloud-side execution remains an environment-specific validation step.

## Engineering principles

- Raw source data is kept as close as possible to the original source.
- Business transformations belong in explicit transformation layers.
- Temporal ML problems use temporal validation rather than random splits.
- Forecast features respect as-of-time availability and must not use future target information.
- Secrets and credentials are never committed to Git.
- New infrastructure is introduced only when it solves a concrete problem.
- A technology is considered part of the implemented stack only after it has actually been used and validated in the project.

## Implemented data architecture

```text
Dataset
  -> GCS landing
  -> BigQuery RAW
  -> dbt STAGING
  -> dbt SILVER
  -> dbt GOLD / MARTS
  -> dbt ML temporal contract
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

## Status

V1 Data Engineering code complete. V2.1 forecasting dataset contract implemented; end-to-end cloud execution validation pending.
