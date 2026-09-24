# RetailOps AI

**End-to-End Data, ML, Decision Intelligence & Agentic AI Platform**

RetailOps AI is a production-oriented portfolio platform that turns retail data into governed
operational decisions. It combines leakage-safe demand forecasting, explainability, deterministic
inventory scenarios, grounded generative AI, human approval, cloud deployment and an operator
console.

> **Core design rule:** forecasts are evidence, business risk is deterministic logic, scenario
> inventory is explicitly supplied by the user, and the human remains responsible for the final
> action.

## Platform flow

~~~text
M5 retail data
      |
      v
GCS -> BigQuery RAW -> dbt STAGING -> SILVER -> GOLD
      |
      v
Leakage-safe ML features
      |
      v
Global LightGBM Poisson model -> recursive 28-day forecast
      |                         -> TreeSHAP explanation
      |                         -> model-assumption demand stress band
      v
FastAPI Forecast Service (private Cloud Run)
      |
      v
Decision Intelligence
      |--> inventory scenario simulation
      |--> deterministic stockout / safety-stock risk
      |--> counterfactual scenario comparison
      |--> cost-aware reorder scenario optimization
      v
Gemini + LangGraph Decision Copilot
      |--> Forecast API
      |--> allowlisted BigQuery analytics
      |--> demand anomaly detection
      |--> model metadata + curated RAG
      |--> thread-scoped scenario memory
      |--> human approval
      v
React Operator Console
Morning Brief | Forecasts | Decision Lab | Copilot | Approvals | Monitoring
~~~

The product journey is:

**Observe -> Forecast -> Explain -> Stress -> Simulate -> Compare -> Recommend -> Human decision**

## What an operator can ask

- “What demand exceptions deserve attention today?”
- “For FOODS_1_001 in CA_1, I have 20 units and 10 arrive in 3 days. Is that enough?”
- “Using the same scenario, what if delivery is delayed by 5 days?”
- “What is the smallest grounded change that removes the stockout risk?”
- “Given these explicit cost assumptions and MOQ, which additional quantity has the lowest
  scenario cost?”

M5 does **not** contain true inventory positions, purchase orders or supplier lead times. RetailOps
AI therefore treats those values as explicit scenario inputs and never presents them as observed
retailer facts.

## Implemented capabilities

### Data engineering
- immutable GCS landing;
- BigQuery RAW ingestion;
- dbt STAGING, SILVER and GOLD layers;
- warehouse integrity tests and analytical marts;
- leakage-aware temporal ML contracts.

### Machine learning
- fixed temporal train / validation / test windows;
- naive, seasonal-7 and seasonal-28 baselines;
- global LightGBM Poisson model;
- recursive 28-day inference without hidden future labels;
- MAE, RMSE and bottom-level mean RMSSE;
- TreeSHAP using the same recursive feature state as the forecast.

### Decision intelligence
- current stock, incoming PO, lead time and safety stock as explicit scenario inputs;
- projected inventory trajectory;
- stockout and safety-stock-breach detection;
- deterministic counterfactuals for more units, a larger PO or earlier PO arrival;
- approximate q10/q90 Poisson model-assumption demand stress band;
- optional cost-aware scenario optimizer using explicit order/holding/stockout costs, MOQ and
  order increments.

The uncertainty band is a **stress band**, not an empirically calibrated coverage guarantee. The
cost optimizer is advisory and is not an ERP purchasing engine.

### Agentic AI
- Gemini structured planning and grounded synthesis;
- LangGraph bounded plan -> execute -> synthesize workflow;
- private authenticated Forecast API tool;
- allowlisted parameterized BigQuery tools with no arbitrary LLM SQL;
- curated RAG;
- deterministic inventory-decision tool;
- thread-scoped active-scenario memory for conversational what-if analysis;
- demand-anomaly analytics;
- per-tool and Gemini-stage latency traces;
- human-in-the-loop approval;
- no mutating operational tool.

### Operator console
- React / TypeScript;
- Morning Decision Brief for demand exceptions and drift context;
- 28-day Forecast workspace;
- Decision Lab with TreeSHAP, inventory trajectory, uncertainty stress and counterfactuals;
- cost-aware scenario optimization;
- AI Copilot and approval center;
- monitoring and architecture views.

### Production / MLOps
- Docker, Artifact Registry and Cloud Build;
- Cloud Run Jobs for quota-friendly model training;
- private FastAPI services on Cloud Run;
- GCS model artifacts and quality-gated Vertex AI Model Registry versions;
- Cloud SQL PostgreSQL checkpointer backend;
- Secret Manager, IAM, Workload Identity Federation and IAP;
- GitHub Actions CI and dual-service Cloud Run CD;
- Terraform for core IAM, WIF, Cloud SQL and monitoring resources;
- request IDs and latency logging;
- authenticated post-deploy Forecast API smoke test.

## Validated forecasting result

A real BigQuery-backed run used a 90-day lookback, 100 LightGBM boosting rounds and
2,744,100 training rows:

~~~text
MAE:        1.076782
RMSE:       2.175634
mean RMSSE: 0.771130
~~~

Reference baselines on the same 28-day validation window:

~~~text
naive_last         MAE 1.350344 | RMSE 3.300666 | mean RMSSE 0.952306
seasonal_naive_7   MAE 1.232355 | RMSE 2.759459 | mean RMSSE 0.975596
seasonal_naive_28  MAE 1.258023 | RMSE 2.836503 | mean RMSSE 1.005899
~~~

The project reports unweighted bottom-level mean RMSSE, not official hierarchical M5 WRMSSE.

## Cloud validation status

Validated on GCP before V7:

- BigQuery/dbt data platform executed end to end;
- real BigQuery-backed LightGBM training/evaluation;
- full Cloud Run Jobs training run;
- quality-gated Vertex AI Model Registry version registration;
- private Forecast API with real 28-day BigQuery-backed inference;
- Gemini/LangGraph Agent with Forecast API, BigQuery analytics, RAG and HITL;
- request-ID correlation and API latency in Cloud Logging;
- PostgreSQL checkpointer backend active through Cloud SQL;
- React console and Decision Lab deployed and browser-validated;
- dual-service GitHub Actions -> Cloud Build -> Cloud Run deployment validated;
- IAP enabled for the operator console.

Important boundaries:

- **Vertex AI Custom Training is not claimed as validated** because project quota is insufficient;
  Cloud Run Jobs is the validated training backend.
- **Cross-revision interrupt -> deploy -> resume durability is not claimed as validated** until the
  dedicated restart-resume test succeeds.
- V7 additions are implemented in code and must pass CI and cloud rollout before being described as
  cloud-validated.

## V7 — Decision Intelligence

V7 adds:
- conversational scenario memory;
- visible counterfactuals;
- demand stress bands;
- demand-anomaly analytics;
- validation-vs-test demand-distribution drift;
- Morning Decision Brief;
- detailed latency traces;
- explicit cost-aware reorder scenario optimization;
- post-deploy Forecast API smoke testing.

See **docs/v7_decision_intelligence.md** for design boundaries.

## Trust boundaries

- LLMs orchestrate and explain; they do not produce retail facts or ML predictions.
- The agent cannot generate arbitrary SQL.
- Demand forecasts are not automatically order quantities.
- Inventory, PO, lead time and safety stock are scenario inputs, never M5 inventory facts.
- Economic optimization inputs are scenario assumptions, never inferred business truth.
- Recursive forecasts append predictions, not future labels.
- Model promotion is quality-gated.
- Secrets and service-account keys are never committed.
- Human approval authorizes human follow-up only; no operational system is mutated.

## API surfaces

Forecast service:

~~~text
GET  /healthz
GET  /readyz
GET  /v1/model
POST /v1/forecast
POST /v1/explain
~~~

Agent / console service:

~~~text
GET  /healthz
GET  /readyz
GET  /v1/agent/capabilities
POST /v1/agent/query
POST /v1/agent/resume

GET  /v1/console/overview
POST /v1/console/analytics
POST /v1/console/forecast
POST /v1/console/inventory-scenario
POST /v1/console/explain
GET  /v1/console/morning-brief
GET  /v1/console/drift
GET  /v1/console/scenarios
POST /v1/console/scenarios
DELETE /v1/console/scenarios/{id}
POST /v1/console/scenarios/{id}/run
GET  /v1/console/decision-history
POST /v1/console/batch-scenarios
GET  /v1/ops/status
~~~

## V8 — Premium SaaS Workspace

V8 focuses on operator usability rather than adding another model:

- quieter, denser SaaS visual hierarchy with reduced explanatory copy;
- richer dashboard analytics: daily demand pulse, category mix, weekday profile,
  store contribution, demand variability and demand-context indicators;
- parallel loading of dashboard analytics to limit home-screen latency;
- functional top-bar navigation instead of decorative controls;
- saved planning scenarios scoped to the authenticated operator;
- PostgreSQL-backed scenario persistence when the durable Cloud SQL backend is enabled;
- server-side decision history for saved scenario runs;
- CSV portfolio scan for up to 25 explicit inventory scenarios at once;
- reusable Decision Lab scenarios with the same human-governance boundary.

The portfolio scanner is intentionally scenario-driven: M5 still does not provide real inventory,
purchase orders or supplier lead times. Those values always come from the operator or uploaded CSV.

See **docs/v8_premium_workspace.md** for the product and data contract.

## Engineering discipline

CI validates Python 3.12 with Ruff/Pytest and builds the React console with TypeScript/Vite.
Production CD only runs from a CI-successful main revision, builds immutable images and rolls out
both Cloud Run services. The Forecast API then receives an authenticated post-deploy readiness and
real 28-point inference smoke test. The Agent Console remains behind IAP; automated HTTP smoke
testing should use a dedicated IAP-authorized test principal rather than weakening that boundary.
