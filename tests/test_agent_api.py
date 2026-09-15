from fastapi.testclient import TestClient

from agent_api.app import create_app
from retailops_ai.agent.schemas import AgentRunResult


class FakeRuntime:
    def __init__(self) -> None:
        self.closed = False

    def ask(self, *, question, user_context=None, thread_id=None):
        return AgentRunResult(
            status="completed",
            thread_id=thread_id or "thread-1",
            answer=f"Grounded answer for: {question}",
            evidence_sources=["bigquery:sales_summary"],
            tool_trace=[{"tool": "bigquery:sales_summary", "status": "ok"}],
        )

    def resume(self, *, thread_id, approved, reviewer_note=None):
        return AgentRunResult(
            status="completed",
            thread_id=thread_id,
            answer="Approved." if approved else "Rejected.",
        )

    def close(self) -> None:
        self.closed = True


def test_agent_query_endpoint_returns_grounded_result():
    app = create_app(runtime_factory=FakeRuntime)
    with TestClient(app) as client:
        response = client.post("/v1/agent/query", json={"question": "Summarize demand."})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["evidence_sources"] == ["bigquery:sales_summary"]
    assert response.headers["x-request-id"]


def test_agent_resume_endpoint_passes_human_decision():
    app = create_app(runtime_factory=FakeRuntime)
    with TestClient(app) as client:
        response = client.post(
            "/v1/agent/resume",
            json={"thread_id": "thread-1", "approved": False},
        )

    assert response.status_code == 200
    assert response.json()["answer"] == "Rejected."


def test_agent_capabilities_are_read_only():
    app = create_app(runtime_factory=FakeRuntime)
    with TestClient(app) as client:
        response = client.get("/v1/agent/capabilities")

    assert response.status_code == 200
    assert response.json()["mutating_actions"] is False
    assert response.json()["analytics_sql"] == "allowlisted templates only"


def test_agent_runtime_is_closed_on_shutdown():
    runtime = FakeRuntime()
    app = create_app(runtime_factory=lambda: runtime)

    with TestClient(app) as client:
        assert client.get("/readyz").status_code == 200
        assert not runtime.closed

    assert runtime.closed
