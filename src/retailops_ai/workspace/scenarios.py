"""Persistent operator-workspace scenarios and decision history."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from threading import Lock
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(UTC).isoformat()


class MemoryScenarioStore:
    """Local/CI fallback with the same API as the PostgreSQL store."""

    backend = "memory"

    def __init__(self) -> None:
        self._scenarios: dict[tuple[str, str], dict[str, Any]] = {}
        self._history: list[dict[str, Any]] = []
        self._lock = Lock()

    def save(self, owner: str, payload: dict[str, Any]) -> dict[str, Any]:
        now = _now()
        scenario_id = str(payload.get("id") or uuid4())
        key = (owner, scenario_id)
        with self._lock:
            existing = self._scenarios.get(key, {})
            record = {
                **existing,
                **payload,
                "id": scenario_id,
                "owner": owner,
                "created_at": existing.get("created_at", now),
                "updated_at": now,
            }
            self._scenarios[key] = record
        return dict(record)

    def list(self, owner: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = [
                dict(value)
                for (record_owner, _), value in self._scenarios.items()
                if record_owner == owner
            ]
        return sorted(rows, key=lambda row: str(row.get("updated_at", "")), reverse=True)

    def get(self, owner: str, scenario_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._scenarios.get((owner, scenario_id))
            return dict(record) if record is not None else None

    def delete(self, owner: str, scenario_id: str) -> bool:
        with self._lock:
            return self._scenarios.pop((owner, scenario_id), None) is not None

    def record_run(
        self,
        owner: str,
        scenario: dict[str, Any],
        result: dict[str, Any],
    ) -> dict[str, Any]:
        event = {
            "id": str(uuid4()),
            "owner": owner,
            "scenario_id": scenario.get("id"),
            "scenario_name": scenario.get("name"),
            "item_id": scenario.get("item_id"),
            "store_id": scenario.get("store_id"),
            "risk_level": result.get("risk_level"),
            "projected_end_inventory": result.get("projected_end_inventory"),
            "review_quantity": result.get("review_quantity"),
            "stockout_day": result.get("stockout_day"),
            "recommended_action": result.get("recommended_action"),
            "created_at": _now(),
        }
        with self._lock:
            self._history.append(event)
            key = (owner, str(scenario.get("id")))
            if key in self._scenarios:
                self._scenarios[key].update(
                    {
                        "latest_risk": event["risk_level"],
                        "latest_end_inventory": event["projected_end_inventory"],
                        "latest_stockout_day": event["stockout_day"],
                        "last_run_at": event["created_at"],
                        "updated_at": event["created_at"],
                    }
                )
        return dict(event)

    def history(self, owner: str, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = [dict(row) for row in self._history if row["owner"] == owner]
        rows.sort(key=lambda row: row["created_at"], reverse=True)
        return rows[:limit]

    def close(self) -> None:
        return None


class PostgresScenarioStore:
    """Small workspace store colocated with the LangGraph PostgreSQL database."""

    backend = "postgres"

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self._setup()

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row)

    def _setup(self) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                create table if not exists retailops_saved_scenarios (
                    owner text not null,
                    id text not null,
                    name text not null,
                    item_id text not null,
                    store_id text not null,
                    split text not null,
                    current_stock double precision not null,
                    incoming_units double precision not null,
                    lead_time_days integer not null,
                    safety_stock double precision not null,
                    economics jsonb,
                    latest_risk text,
                    latest_end_inventory double precision,
                    latest_stockout_day integer,
                    last_run_at timestamptz,
                    created_at timestamptz not null,
                    updated_at timestamptz not null,
                    primary key (owner, id)
                )
                """
            )
            cursor.execute(
                """
                create table if not exists retailops_decision_history (
                    owner text not null,
                    id text primary key,
                    scenario_id text,
                    scenario_name text,
                    item_id text not null,
                    store_id text not null,
                    risk_level text,
                    projected_end_inventory double precision,
                    review_quantity double precision,
                    stockout_day integer,
                    recommended_action text,
                    created_at timestamptz not null
                )
                """
            )
            cursor.execute(
                """
                create index if not exists retailops_decision_history_owner_created_idx
                on retailops_decision_history (owner, created_at desc)
                """
            )

    @staticmethod
    def _serialize(row: dict[str, Any]) -> dict[str, Any]:
        result = dict(row)
        for key in ("created_at", "updated_at", "last_run_at"):
            if result.get(key) is not None:
                result[key] = result[key].isoformat()
        economics = result.get("economics")
        if isinstance(economics, str):
            result["economics"] = json.loads(economics)
        return result

    def save(self, owner: str, payload: dict[str, Any]) -> dict[str, Any]:
        scenario_id = str(payload.get("id") or uuid4())
        now = datetime.now(UTC)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                insert into retailops_saved_scenarios (
                    owner, id, name, item_id, store_id, split,
                    current_stock, incoming_units, lead_time_days, safety_stock,
                    economics, created_at, updated_at
                )
                values (
                    %(owner)s, %(id)s, %(name)s, %(item_id)s, %(store_id)s, %(split)s,
                    %(current_stock)s, %(incoming_units)s, %(lead_time_days)s, %(safety_stock)s,
                    %(economics)s::jsonb, %(created_at)s, %(updated_at)s
                )
                on conflict (owner, id) do update set
                    name = excluded.name,
                    item_id = excluded.item_id,
                    store_id = excluded.store_id,
                    split = excluded.split,
                    current_stock = excluded.current_stock,
                    incoming_units = excluded.incoming_units,
                    lead_time_days = excluded.lead_time_days,
                    safety_stock = excluded.safety_stock,
                    economics = excluded.economics,
                    updated_at = excluded.updated_at
                returning *
                """,
                {
                    "owner": owner,
                    "id": scenario_id,
                    "name": payload["name"],
                    "item_id": payload["item_id"],
                    "store_id": payload["store_id"],
                    "split": payload["split"],
                    "current_stock": payload["current_stock"],
                    "incoming_units": payload["incoming_units"],
                    "lead_time_days": payload["lead_time_days"],
                    "safety_stock": payload["safety_stock"],
                    "economics": json.dumps(payload.get("economics")),
                    "created_at": now,
                    "updated_at": now,
                },
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("scenario save did not return a row")
        return self._serialize(row)

    def list(self, owner: str) -> list[dict[str, Any]]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                select *
                from retailops_saved_scenarios
                where owner = %s
                order by updated_at desc
                """,
                (owner,),
            )
            rows = cursor.fetchall()
        return [self._serialize(row) for row in rows]

    def get(self, owner: str, scenario_id: str) -> dict[str, Any] | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                select *
                from retailops_saved_scenarios
                where owner = %s and id = %s
                """,
                (owner, scenario_id),
            )
            row = cursor.fetchone()
        return self._serialize(row) if row is not None else None

    def delete(self, owner: str, scenario_id: str) -> bool:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                delete from retailops_saved_scenarios
                where owner = %s and id = %s
                returning id
                """,
                (owner, scenario_id),
            )
            return cursor.fetchone() is not None

    def record_run(
        self,
        owner: str,
        scenario: dict[str, Any],
        result: dict[str, Any],
    ) -> dict[str, Any]:
        event_id = str(uuid4())
        created_at = datetime.now(UTC)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                insert into retailops_decision_history (
                    owner, id, scenario_id, scenario_name, item_id, store_id,
                    risk_level, projected_end_inventory, review_quantity,
                    stockout_day, recommended_action, created_at
                )
                values (
                    %(owner)s, %(id)s, %(scenario_id)s, %(scenario_name)s,
                    %(item_id)s, %(store_id)s, %(risk_level)s,
                    %(projected_end_inventory)s, %(review_quantity)s,
                    %(stockout_day)s, %(recommended_action)s, %(created_at)s
                )
                returning *
                """,
                {
                    "owner": owner,
                    "id": event_id,
                    "scenario_id": scenario.get("id"),
                    "scenario_name": scenario.get("name"),
                    "item_id": scenario["item_id"],
                    "store_id": scenario["store_id"],
                    "risk_level": result.get("risk_level"),
                    "projected_end_inventory": result.get("projected_end_inventory"),
                    "review_quantity": result.get("review_quantity"),
                    "stockout_day": result.get("stockout_day"),
                    "recommended_action": result.get("recommended_action"),
                    "created_at": created_at,
                },
            )
            event = cursor.fetchone()
            if scenario.get("id"):
                cursor.execute(
                    """
                    update retailops_saved_scenarios
                    set latest_risk = %(risk)s,
                        latest_end_inventory = %(end_inventory)s,
                        latest_stockout_day = %(stockout_day)s,
                        last_run_at = %(last_run_at)s,
                        updated_at = %(last_run_at)s
                    where owner = %(owner)s and id = %(scenario_id)s
                    """,
                    {
                        "risk": result.get("risk_level"),
                        "end_inventory": result.get("projected_end_inventory"),
                        "stockout_day": result.get("stockout_day"),
                        "last_run_at": created_at,
                        "owner": owner,
                        "scenario_id": scenario.get("id"),
                    },
                )
        if event is None:
            raise RuntimeError("scenario run did not return a history row")
        return self._serialize(event)

    def history(self, owner: str, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                select *
                from retailops_decision_history
                where owner = %s
                order by created_at desc
                limit %s
                """,
                (owner, limit),
            )
            rows = cursor.fetchall()
        return [self._serialize(row) for row in rows]

    def close(self) -> None:
        return None


def build_scenario_store():
    backend = os.getenv("AGENT_CHECKPOINTER_BACKEND", "memory").lower()
    dsn = os.getenv("AGENT_CHECKPOINTER_DSN")
    if backend == "postgres" and dsn:
        return PostgresScenarioStore(dsn)
    return MemoryScenarioStore()
