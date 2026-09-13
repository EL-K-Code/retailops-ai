# RetailOps V5 Agent API

This service exposes the LangGraph decision-support workflow.

```text
POST /v1/agent/query
POST /v1/agent/resume
GET  /v1/agent/capabilities
GET  /healthz
GET  /readyz
```

The V5 graph uses an in-memory LangGraph checkpointer so local development and CI can validate
human-in-the-loop interrupts without external infrastructure. That checkpointer is intentionally
**not described as production durable**: Cloud Run deployment with resumable approvals requires a
durable checkpoint backend, which belongs to V6 Production Quality.

The agent never directly changes inventory, orders, prices, or warehouse data.
