# V5 Agentic AI — LangGraph + Gemini + Grounded Retail Tools

## Goal

V5 turns the existing data/ML platform into a conversational decision-support system without
letting the LLM become a source of truth. LangGraph orchestrates; deterministic tools provide the
facts; Gemini plans and synthesizes; humans approve business actions.

```text
User
  |
  v
Agent API
  |
  v
LangGraph bounded loop
  |
  +--> Gemini planner (structured AgentPlan)
  |       |
  |       +--> Forecast API tool ------> V4 FastAPI / LightGBM
  |       +--> BigQuery analytics -----> allowlisted SQL templates
  |       +--> Model info -------------> V4 /v1/model
  |       +--> Knowledge RAG ----------> curated project/business docs
  |
  v
Gemini grounded synthesis
  |
  +--> no proposed business action ----> final answer
  |
  +--> proposed action ----------------> LangGraph interrupt()
                                            |
                                      human approve/reject
                                            |
                                            v
                                         final answer
```

## Trust boundaries

The agent is intentionally **read-only**. It has no tool that can change stock, place an order,
modify prices, write warehouse rows, or deploy a model. The LLM cannot submit arbitrary SQL. It can
only choose among typed analytics operations:

- `sales_summary`
- `store_summary`
- `top_products`
- `baseline_metrics`

The SQL templates are parameterized and each BigQuery job uses `maximum_bytes_billed` as a cost
ceiling. Tool calls are deduplicated and the plan/execute loop is bounded by
`AGENT_MAX_TOOL_STEPS` (default 3).

## Gemini role

Gemini on Vertex AI is used for two constrained stages:

1. **Planning:** produce a schema-validated `AgentPlan`. This is an operational plan, not exposed
   chain-of-thought.
2. **Synthesis:** produce a schema-validated `AgentDraft` from tool evidence only.

The prompt explicitly forbids invented sales, forecasts, inventory, prices, model metrics, or data
source claims. When evidence is insufficient, the agent must say so.

## RAG strategy

The knowledge corpus is deliberately small and curated (`knowledge/*.md`), so V5 does not add a
separate vector database without need.

Two retrieval modes exist:

- `lexical` — deterministic, free, and used by local development / CI;
- `vertex` — Gemini `gemini-embedding-001` embeddings with cosine retrieval for cloud validation.

This is still RAG: retrieved source chunks are passed to the synthesis model as evidence. A vector
database can be introduced later only if corpus size and retrieval requirements justify it.

## Forecast API authentication

When `AGENT_FORECAST_AUTH=cloud-run`, the Forecast tool obtains a Google-signed ID token using ADC
and sends it to the private V4 Cloud Run service. No service-account key file is embedded in the
container.

## Human-in-the-loop

The following action proposals always trigger a LangGraph `interrupt()`:

- reorder review;
- safety-stock review;
- anomaly investigation;
- planner escalation.

The caller receives `approval_required` plus the proposal. It resumes through
`POST /v1/agent/resume`. Approval authorizes human follow-up only; the agent still performs no
mutation.

## API

```text
GET  /healthz
GET  /readyz
GET  /v1/agent/capabilities
POST /v1/agent/query
POST /v1/agent/resume
```

Example query:

```json
{
  "question": "Forecast FOODS_1_001 in CA_1 for the test horizon and tell me whether a planner should review replenishment."
}
```

A proposed reorder review pauses with `status=approval_required`. Resume example:

```json
{
  "thread_id": "<returned-thread-id>",
  "approved": true,
  "reviewer_note": "Planner will review inventory and lead time before any order."
}
```

## Checkpointing boundary

V5 uses LangGraph `InMemorySaver` to validate stateful HITL behavior in one process. This is correct
for local development and CI, but it is **not durable across Cloud Run restarts or multiple
instances**. A durable checkpointer is therefore a V6 Production Quality requirement before the
agent is described as production-deployed with resumable approvals.

This limitation is intentional and documented rather than hidden.

## Validation status

V5 is code-complete only after Ruff and unit/API/graph tests pass in CI. Real Gemini, Vertex
embeddings, private Cloud Run authentication, and BigQuery tool calls remain environment-specific
cloud validation steps and must not be claimed as executed until they actually run.
