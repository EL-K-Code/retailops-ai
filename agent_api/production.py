"""Production FastAPI entrypoint for the RetailOps agent and operator console."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent_api.app import create_app
from retailops_ai.agent.production import ProductionAgentRuntime, build_production_runtime
from retailops_ai.agent.schemas import AnalyticsRequest, EntityRef, ForecastToolRequest
from retailops_ai.decision.inventory import InventoryScenario
from retailops_ai.decision.reorder import ReorderEconomics

app = create_app(runtime_factory=build_production_runtime)


class ReorderEconomicsRequest(BaseModel):
    unit_order_cost: float = Field(ge=0)
    holding_cost_per_unit: float = Field(ge=0)
    stockout_penalty_per_unit: float = Field(ge=0)
    safety_breach_penalty_per_unit: float = Field(default=0, ge=0)
    min_order_quantity: int = Field(default=0, ge=0)
    order_increment: int = Field(default=1, ge=1)
    max_additional_units: int = Field(default=100, ge=0, le=10_000)


class InventoryScenarioRequest(BaseModel):
    item_id: str = Field(min_length=1, max_length=128)
    store_id: str = Field(min_length=1, max_length=128)
    split: Literal["validation", "test"] = "test"
    current_stock: float = Field(ge=0)
    incoming_units: float = Field(default=0, ge=0)
    lead_time_days: int = Field(default=0, ge=0, le=28)
    safety_stock: float = Field(default=0, ge=0)
    economics: ReorderEconomicsRequest | None = None


class SavedScenarioRequest(BaseModel):
    id: str | None = Field(default=None, max_length=128)
    name: str = Field(min_length=1, max_length=160)
    item_id: str = Field(min_length=1, max_length=128)
    store_id: str = Field(min_length=1, max_length=128)
    split: Literal["validation", "test"] = "test"
    current_stock: float = Field(ge=0)
    incoming_units: float = Field(default=0, ge=0)
    lead_time_days: int = Field(default=0, ge=0, le=28)
    safety_stock: float = Field(default=0, ge=0)
    economics: ReorderEconomicsRequest | None = None


class BatchScenarioItem(InventoryScenarioRequest):
    name: str | None = Field(default=None, max_length=160)


class BatchScenarioRequest(BaseModel):
    scenarios: list[BatchScenarioItem] = Field(min_length=1, max_length=25)


class ExplainConsoleRequest(BaseModel):
    item_id: str = Field(min_length=1, max_length=128)
    store_id: str = Field(min_length=1, max_length=128)
    split: Literal["validation", "test"] = "test"
    top_n: int = Field(default=6, ge=1, le=12)


def _runtime(request: Request) -> ProductionAgentRuntime:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None:
        raise HTTPException(status_code=503, detail="Agent service not ready")
    return runtime


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or str(uuid4())


def _actor(request: Request) -> str:
    identity = request.headers.get("x-goog-authenticated-user-email")
    if not identity:
        return "local-operator"
    return identity.split(":", 1)[-1].strip().lower()


def _forecast_request(item_id: str, store_id: str, split: str) -> ForecastToolRequest:
    return ForecastToolRequest(
        entities=[EntityRef(item_id=item_id, store_id=store_id)],
        split=split,
    )


@app.get("/v1/ops/status")
def ops_status(request: Request) -> dict[str, Any]:
    runtime = _runtime(request)
    return {
        "service": "retailops-agent",
        "environment": os.getenv("RETAILOPS_ENV", "local"),
        "release": os.getenv("RETAILOPS_RELEASE", "dev"),
        "checkpoint_backend": runtime.checkpointer_backend,
        "durable_state": runtime.durable_state,
        "ready": True,
    }


@app.get("/v1/console/overview")
def console_overview(
    request: Request,
    split: Literal["validation", "test"] = "test",
) -> dict[str, Any]:
    runtime = _runtime(request)
    request_id = _request_id(request)
    try:
        return runtime.dashboard_overview(split=split, request_id=request_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Console overview failed: {exc}") from exc


@app.post("/v1/console/analytics")
def console_analytics(payload: AnalyticsRequest, request: Request) -> dict[str, Any]:
    try:
        return _runtime(request).analytics(payload)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Analytics request failed: {exc}") from exc


@app.post("/v1/console/forecast")
def console_forecast(payload: ForecastToolRequest, request: Request) -> dict[str, Any]:
    try:
        return _runtime(request).forecast(payload, request_id=_request_id(request))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Forecast request failed: {exc}") from exc


@app.post("/v1/console/inventory-scenario")
def console_inventory_scenario(
    payload: InventoryScenarioRequest,
    request: Request,
) -> dict[str, Any]:
    economics = (
        ReorderEconomics(**payload.economics.model_dump())
        if payload.economics is not None
        else None
    )
    try:
        return _runtime(request).inventory_scenario(
            _forecast_request(payload.item_id, payload.store_id, payload.split),
            InventoryScenario(
                current_stock=payload.current_stock,
                incoming_units=payload.incoming_units,
                lead_time_days=payload.lead_time_days,
                safety_stock=payload.safety_stock,
            ),
            request_id=_request_id(request),
            economics=economics,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Inventory scenario failed: {exc}") from exc


@app.post("/v1/console/explain")
def console_explain(payload: ExplainConsoleRequest, request: Request) -> dict[str, Any]:
    try:
        return _runtime(request).explain_forecast(
            _forecast_request(payload.item_id, payload.store_id, payload.split),
            request_id=_request_id(request),
            top_n=payload.top_n,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Forecast explanation failed: {exc}") from exc


@app.get("/v1/console/morning-brief")
def console_morning_brief(
    request: Request,
    split: Literal["validation", "test"] = "test",
) -> dict[str, Any]:
    try:
        return _runtime(request).morning_brief(
            split=split,
            request_id=_request_id(request),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Morning brief failed: {exc}") from exc


@app.get("/v1/console/drift")
def console_drift(
    request: Request,
    item_id: str | None = None,
    store_id: str | None = None,
) -> dict[str, Any]:
    try:
        return _runtime(request).demand_drift(item_id=item_id, store_id=store_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Drift diagnostic failed: {exc}") from exc


@app.get("/v1/console/scenarios")
def console_scenarios(request: Request) -> dict[str, Any]:
    runtime = _runtime(request)
    return {
        "storage_backend": runtime.scenario_store.backend,
        "scenarios": runtime.saved_scenarios(_actor(request)),
    }


@app.post("/v1/console/scenarios")
def console_save_scenario(
    payload: SavedScenarioRequest,
    request: Request,
) -> dict[str, Any]:
    saved = _runtime(request).save_scenario(
        _actor(request),
        payload.model_dump(mode="json"),
    )
    return {"scenario": saved}


@app.delete("/v1/console/scenarios/{scenario_id}")
def console_delete_scenario(scenario_id: str, request: Request) -> dict[str, Any]:
    deleted = _runtime(request).delete_scenario(_actor(request), scenario_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return {"deleted": True, "id": scenario_id}


@app.post("/v1/console/scenarios/{scenario_id}/run")
def console_run_saved_scenario(scenario_id: str, request: Request) -> dict[str, Any]:
    try:
        return _runtime(request).run_saved_scenario(
            owner=_actor(request),
            scenario_id=scenario_id,
            request_id=_request_id(request),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Scenario not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Scenario run failed: {exc}") from exc


@app.get("/v1/console/decision-history")
def console_decision_history(request: Request, limit: int = 30) -> dict[str, Any]:
    bounded_limit = max(1, min(limit, 100))
    return {"events": _runtime(request).decision_history(_actor(request), limit=bounded_limit)}


@app.post("/v1/console/batch-scenarios")
def console_batch_scenarios(
    payload: BatchScenarioRequest,
    request: Request,
) -> dict[str, Any]:
    rows = [
        item.model_dump(mode="json")
        for item in payload.scenarios
    ]
    try:
        results = _runtime(request).batch_inventory_scenarios(
            rows,
            request_id=_request_id(request),
        )
        return {"count": len(results), "results": results}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Batch scenario evaluation failed: {exc}") from exc


@app.get("/v1/console/model")
def console_model(request: Request) -> dict[str, Any]:
    try:
        return _runtime(request).model_info(request_id=_request_id(request))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model info request failed: {exc}") from exc


@app.get("/v1/console/knowledge")
def console_knowledge(request: Request) -> dict[str, Any]:
    return {"documents": _runtime(request).knowledge_documents()}


_console_dir = Path(os.getenv("RETAILOPS_CONSOLE_DIR", "web_dist"))
if _console_dir.exists():

    @app.get("/", include_in_schema=False)
    def console_root() -> RedirectResponse:
        return RedirectResponse(url="/console/")

    app.mount(
        "/console",
        StaticFiles(directory=str(_console_dir), html=True),
        name="retailops-console",
    )
