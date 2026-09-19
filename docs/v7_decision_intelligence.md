# V7 Decision Intelligence

V7 turns RetailOps AI from a forecasting/agent demo into a more explicit decision-intelligence
product. The model produces forecast evidence, deterministic code computes business risk, Gemini
orchestrates and explains, and humans remain responsible for action.

## P0 — Decision workflow

### Thread-scoped scenario memory

The LangGraph state stores the latest explicit inventory scenario associated with a conversation
thread. Reusing the same thread passes that active scenario back to the planner so an operator can
ask a natural follow-up without repeating unchanged values.

Scenario memory is never shared across threads and must never infer missing operational facts.

### Counterfactual UI

The deterministic counterfactual engine is surfaced in Decision Lab. It can expose:
- additional immediately available units;
- an increase to an incoming PO;
- an earlier arrival for an existing PO.

These are scenario comparisons, not purchase orders.

## P1 — Uncertainty, latency and morning brief

### Model-assumption demand stress

Because the active forecasting model uses a Poisson objective, V7 exposes an approximate q10/q90
predictive stress band derived from the Poisson mean/variance assumption.

This is **not** an empirically calibrated confidence interval. It does not capture parameter
uncertainty, over-dispersion or future regime shifts. Decision Lab also reruns the inventory scenario
against the upper-demand path to expose decision sensitivity.

### Latency trace

Agent tools and Gemini planning/synthesis attach latency_ms to the trace. This supports bottleneck
analysis across LLM planning, Forecast API, BigQuery tools and final synthesis.

### Morning Decision Brief

The brief prioritizes observed demand exceptions and displays drift context. It deliberately avoids
fabricating stockout risk because M5 has no true operational inventory.

## P2 — Anomalies, drift and deployment smoke tests

### Demand anomaly detection

An allowlisted BigQuery query compares each item/store daily observation with its preceding 28-day
rolling mean and standard deviation and surfaces absolute z-scores of at least 3.

This is an operational exception signal, not causal anomaly detection.

### Drift monitoring

A lightweight diagnostic compares validation and test daily-demand distributions using PSI plus a
standardized mean shift. With 28-day windows this is a monitoring signal, not proof of model
degradation.

### Post-deploy smoke boundary

The CD workflow performs an authenticated readiness check and a real 28-point forecast against the
private Forecast API after rollout.

The Agent Console is protected by IAP. CI must not bypass that boundary merely to simplify smoke
testing. A future automated IAP smoke test should use a dedicated authorized test principal and the
correct OAuth audience.

## P3 — Cost-aware reorder scenario optimization

Decision Lab can compare extra incoming quantities under explicit economic assumptions:
- unit order cost;
- holding cost;
- stockout penalty;
- safety-stock-breach penalty;
- minimum order quantity;
- order increment;
- maximum additional quantity.

The deterministic objective ranks candidates by scenario cost. It is advisory only and does not
infer supplier capacity, substitution, taxes, multi-echelon constraints or purchasing rules.
