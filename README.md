# RetailOps AI

**End-to-End Data, ML & Agentic AI Platform**

RetailOps AI is a portfolio project that progressively builds a production-like Data & AI platform
for retail, e-commerce, and supply-chain decision support. Each layer is implemented, tested, and
validated before its technology is claimed as part of the executed stack.

## Target architecture

```text
M5 retail data
      |
      v
GCS -> BigQuery RAW -> dbt STAGING -> SILVER -> GOLD
      |
      v
Leakage-safe ML features
      |
      v
LightGBM recursive demand forecasting
      |
      v
Portable cloud training container
      |
      +--> Cloud Run Jobs       [current quota-friendly backend]
      +--> Vertex AI Training   [target backend when quota-eligible]
      |
      v
GCS artifacts + Vertex AI Experiments
      |
      v
FastAPI / Cloud Run forecasting service
      |
      v
LangGraph + Gemini decision agent
      |
      +--> Forecast API
      +--> BigQuery analytics
      +--> Model info
      +--> RAG knowledge
      +--> Human approval
```

## Roadmap

- **V0 — Foundation:** repository, Python project, configuration and dependency management.
- **V1 — Data Engineering:** GCS, BigQuery, dbt layers, tests and marts.
- **V2 — Machine Learning:** temporal validation, baselines, LightGBM and recursive forecasting.
- **V3 — MLOps:** portable cloud training, experiments, artifacts, quality gate and Model Registry;
  Vertex AI remains the target training backend and Cloud Run Jobs is the quota-friendly fallback.
- **V4 — Serving & Cloud:** FastAPI, Cloud Run contract, Artifact Registry and CI/CD.
- **V5 — Agentic AI:** LangGraph, Gemini, safe tools, RAG and human-in-the-loop workflows.
- **V6 — Production Quality:** durable agent state, observability, orchestration, monitoring, IaC
  and final portfolio demo.

## Current milestone

**V5 — Agentic AI**

Implemented code paths now include:

- immutable GCS landing and BigQuery RAW ingestion;
- dbt STAGING, SILVER and GOLD warehouse layers;
- leakage-aware 28-day forecasting contract;
- naive and seasonal baselines with MAE, RMSE and bottom-level mean RMSSE;
- global LightGBM Poisson model with recursive inference;
- backend-agnostic LightGBM training container shared by local, Cloud Run Jobs and Vertex AI;
- Vertex AI custom-training, experiment, artifact and quality-gated registry code;
- Cloud Run Jobs deployment/execution helpers for quota-friendly cloud training;
- FastAPI business forecasting API with series-scoped BigQuery reads;
- Cloud Run container/build/deployment contracts and GitHub Actions CI;
- LangGraph bounded plan-execute-synthesize workflow;
- schema-constrained Gemini planner and grounded answer synthesis;
- authenticated Forecast API tool for private Cloud Run;
- allowlisted, parameterized BigQuery analytics tools with a bytes-billed ceiling;
- model-info tool;
- curated RAG with lexical and Vertex-embedding retrieval backends;
- tool-call deduplication and a maximum tool-step budget;
- LangGraph human approval interrupts for business action proposals;
- separate Agent API with query/resume endpoints;
- container build contract for the V5 service;
- GitHub Actions validation under Python 3.12 with Ruff and 62 passing tests.

V3, V4 and V5 cloud code must not be described as cloud-validated until their real GCP executions
complete successfully.

## Engineering principles

- LLMs orchestrate and explain; they are never the source of retail facts or model predictions.
- The agent cannot generate arbitrary SQL; analytics are allowlisted and parameterized.
- Demand forecasts are not automatically order quantities.
- M5 does not contain true inventory; simulated inventory must always be labelled as simulated.
- Temporal ML features respect as-of-time availability and never use future target information.
- Recursive forecasts append model predictions, not hidden future labels.
- Model promotion is gated by measured validation quality.
- Local, Vertex and Cloud Run paths share the forecasting implementation.
- Training compute is decoupled from the Forecast API contract consumed by the agent.
- Secrets and service-account keys are never committed.
- Expensive or mutating actions require explicit guardrails.
- Human approval does not imply that the V5 agent changed an external system; it has no mutation
  tool.

## Validated forecasting result

A real BigQuery-backed local run used a 90-day lookback, 100 LightGBM boosting rounds, and
2,744,100 training rows:

```text
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

The project reports unweighted bottom-level mean RMSSE, not official hierarchical M5 WRMSSE.

## V5 agent flow

```text
Question
  |
  v
Gemini structured planner
  |
  v
LangGraph (max 3 tool rounds)
  |
  +--> POST /v1/forecast          [deterministic ML]
  +--> BigQuery allowlisted tools [warehouse facts]
  +--> GET /v1/model              [model metadata]
  +--> RAG                        [policy / limitations]
  |
  v
Gemini grounded synthesis
  |
  +--> answer only ------------------------------> response
  |
  +--> business action proposal -> HITL interrupt
                                      |
                               approve / reject
                                      |
                                      v
                                   response
```

The V5 graph deliberately has no write/action tool. The first HITL implementation uses an in-memory
LangGraph checkpointer for local/CI validation; durable resumable state across Cloud Run instances is
a V6 requirement.

See `docs/agentic_ai.md` for the full trust and tool contract.

## API surfaces

Forecasting service:

```text
GET  /healthz
GET  /readyz
GET  /v1/model
POST /v1/forecast
```

Agent service:

```text
GET  /healthz
GET  /readyz
GET  /v1/agent/capabilities
POST /v1/agent/query
POST /v1/agent/resume
```

## Status

- **V1 Data Engineering:** real GCP execution validated end to end.
- **V2 Machine Learning:** real BigQuery-backed LightGBM run validated and beats all implemented
  baselines.
- **V3 MLOps:** portable training code implemented; Cloud Run Jobs fallback added for current quota
  constraints; real cloud training execution and Vertex AI Custom Training validation remain pending.
- **V4 Serving & Cloud:** code and CI validated; real Cloud Run execution pending.
- **V5 Agentic AI:** code and CI validated (Ruff + 62 tests under Python 3.12); real Gemini,
  Vertex-embedding, private Cloud Run tool calls, BigQuery agent queries, and cloud HITL execution
  remain pending.
