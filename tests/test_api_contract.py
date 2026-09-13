from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from api.app import create_app
from retailops_ai.serving.service import ForecastBatch, ForecastPoint, SeriesForecast


class FakeModel:
    def summary(self) -> dict[str, object]:
        return {
            "model_name": "lightgbm_global",
            "model_version": "v1",
            "run_name": "test-run",
            "mean_rmsse": 0.77,
        }


class FakeService:
    def forecast(self, entities, *, split: str = "test") -> ForecastBatch:
        entity = entities[0]
        return ForecastBatch(
            split=split,
            forecast_origin=date(2016, 4, 25),
            horizon_days=28,
            generated_at=datetime(2026, 9, 13, tzinfo=UTC),
            model=FakeModel().summary(),
            forecasts=(
                SeriesForecast(
                    series_id="ITEM_1_CA_1_evaluation",
                    item_id=entity.item_id,
                    store_id=entity.store_id,
                    points=(
                        ForecastPoint(
                            date=date(2016, 4, 25),
                            horizon=1,
                            prediction=2.5,
                        ),
                    ),
                ),
            ),
        )


def _runtime():
    return SimpleNamespace(model=FakeModel(), service=FakeService())


def test_health_and_readiness_endpoints() -> None:
    app = create_app(runtime_factory=_runtime)
    with TestClient(app) as client:
        assert client.get("/healthz").json() == {"status": "ok"}
        assert client.get("/readyz").json() == {"status": "ready"}


def test_forecast_contract_and_request_id() -> None:
    app = create_app(runtime_factory=_runtime)
    with TestClient(app) as client:
        response = client.post(
            "/v1/forecast",
            headers={"x-request-id": "req-123"},
            json={
                "entities": [{"item_id": "ITEM_1", "store_id": "CA_1"}],
                "split": "test",
            },
        )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-123"
    payload = response.json()
    assert payload["request_id"] == "req-123"
    assert payload["horizon_days"] == 28
    assert payload["forecasts"][0]["points"][0]["prediction"] == 2.5


def test_model_metadata_endpoint() -> None:
    app = create_app(runtime_factory=_runtime)
    with TestClient(app) as client:
        response = client.get("/v1/model")
    assert response.status_code == 200
    assert response.json()["run_name"] == "test-run"
