"""Inventory scenario simulation grounded on model forecasts.

The M5 source data does not contain operational stock, purchase orders, or
supplier lead times. This module therefore treats inventory values strictly as
user-provided scenario inputs and combines them with a real forecast through a
deterministic decision engine.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import ceil
from typing import Any


@dataclass(frozen=True)
class InventoryScenario:
    current_stock: float
    incoming_units: float = 0.0
    lead_time_days: int = 0
    safety_stock: float = 0.0

    def validate(self, horizon_days: int) -> None:
        if horizon_days <= 0:
            raise ValueError("horizon_days must be positive")
        if self.current_stock < 0:
            raise ValueError("current_stock must be non-negative")
        if self.incoming_units < 0:
            raise ValueError("incoming_units must be non-negative")
        if self.safety_stock < 0:
            raise ValueError("safety_stock must be non-negative")
        if self.lead_time_days < 0:
            raise ValueError("lead_time_days must be non-negative")


def _coerce_points(points: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(points, start=1):
        horizon = int(raw.get("horizon", index))
        prediction = float(raw.get("prediction", raw.get("value", 0.0)))
        if horizon <= 0:
            raise ValueError("forecast horizon values must be positive")
        if prediction < 0:
            prediction = 0.0
        normalized.append(
            {
                "date": raw.get("date"),
                "horizon": horizon,
                "prediction": prediction,
            }
        )
    normalized.sort(key=lambda point: point["horizon"])
    if not normalized:
        raise ValueError("forecast points are required")
    return normalized


def _scenario_payload(scenario: InventoryScenario) -> dict[str, float | int]:
    return {
        "current_stock": float(scenario.current_stock),
        "incoming_units": float(scenario.incoming_units),
        "lead_time_days": int(scenario.lead_time_days),
        "safety_stock": float(scenario.safety_stock),
    }


def simulate_inventory(
    points: Sequence[dict[str, Any]],
    scenario: InventoryScenario,
) -> dict[str, Any]:
    """Project inventory day by day from a real forecast and scenario inputs.

    An incoming purchase order is assumed to arrive at the beginning of the
    configured lead-time day. A lead time of zero means the incoming units are
    available before day one. A lead time beyond the selected decision horizon
    is valid: the purchase order simply does not arrive within that horizon.
    """

    forecast = _coerce_points(points)
    scenario.validate(len(forecast))

    balance = float(scenario.current_stock)
    if scenario.lead_time_days == 0:
        balance += float(scenario.incoming_units)

    trajectory: list[dict[str, Any]] = []
    stockout_day: int | None = None
    safety_breach_day: int | None = None
    forecast_total = 0.0
    demand_before_arrival = 0.0

    for point in forecast:
        horizon = int(point["horizon"])
        if scenario.lead_time_days > 0 and horizon == scenario.lead_time_days:
            balance += float(scenario.incoming_units)

        demand = float(point["prediction"])
        forecast_total += demand
        if scenario.lead_time_days > 0 and horizon < scenario.lead_time_days:
            demand_before_arrival += demand

        balance -= demand
        if safety_breach_day is None and balance < scenario.safety_stock:
            safety_breach_day = horizon
        if stockout_day is None and balance < 0:
            stockout_day = horizon

        trajectory.append(
            {
                "date": point.get("date"),
                "horizon": horizon,
                "forecast_demand": demand,
                "projected_inventory": balance,
                "safety_stock": float(scenario.safety_stock),
            }
        )

    incoming_within_horizon = (
        float(scenario.incoming_units)
        if scenario.lead_time_days <= len(forecast)
        else 0.0
    )
    available_units = float(scenario.current_stock + incoming_within_horizon)
    projected_end_inventory = balance
    shortage_units = max(0.0, -projected_end_inventory)
    safety_stock_gap = max(
        0.0,
        forecast_total + float(scenario.safety_stock) - available_units,
    )
    pre_arrival_gap = max(
        0.0,
        demand_before_arrival + float(scenario.safety_stock) - float(scenario.current_stock),
    )
    review_quantity = float(ceil(max(safety_stock_gap, pre_arrival_gap)))

    if stockout_day is not None:
        risk_level = "high"
        action = "review_reorder"
        recommendation = (
            f"Projected stockout around D+{stockout_day}. Review replenishment inputs "
            f"and at least {int(review_quantity)} additional scenario units."
        )
    elif safety_breach_day is not None:
        risk_level = "medium"
        action = "review_safety_stock"
        recommendation = (
            f"Inventory falls below the safety-stock threshold around D+{safety_breach_day}. "
            "Review service-level and replenishment assumptions."
        )
    else:
        risk_level = "low"
        action = "monitor"
        recommendation = (
            "Projected inventory remains above the configured safety-stock threshold "
            "through the forecast horizon."
        )

    return {
        "scenario_mode": True,
        "scenario_notice": (
            "Inventory values are user-provided simulation inputs. M5 does not contain "
            "operational inventory, purchase orders, or supplier lead times."
        ),
        "forecast_total": forecast_total,
        "available_units": available_units,
        "projected_end_inventory": projected_end_inventory,
        "shortage_units": shortage_units,
        "safety_stock_gap": safety_stock_gap,
        "review_quantity": review_quantity,
        "stockout_day": stockout_day,
        "safety_breach_day": safety_breach_day,
        "risk_level": risk_level,
        "recommended_action": action,
        "recommendation": recommendation,
        "trajectory": trajectory,
    }


def recommend_inventory_counterfactuals(
    points: Sequence[dict[str, Any]],
    scenario: InventoryScenario,
) -> dict[str, Any]:
    """Find small deterministic scenario changes that remove inventory risk.

    The function answers operational "what would need to change?" questions.
    It does not optimize cost or execute a purchase order. All returned options
    remain scenario recommendations for human review.
    """

    forecast = _coerce_points(points)
    baseline = simulate_inventory(forecast, scenario)
    upper_bound = max(
        1,
        int(ceil(baseline["forecast_total"] + scenario.safety_stock + 5)),
    )

    def is_low(candidate: InventoryScenario) -> tuple[bool, dict[str, Any]]:
        result = simulate_inventory(forecast, candidate)
        return result["risk_level"] == "low", result

    options: list[dict[str, Any]] = []

    minimum_immediate_units: int | None = None
    for additional in range(0, upper_bound + 1):
        candidate = InventoryScenario(
            current_stock=scenario.current_stock + additional,
            incoming_units=scenario.incoming_units,
            lead_time_days=scenario.lead_time_days,
            safety_stock=scenario.safety_stock,
        )
        safe, result = is_low(candidate)
        if safe:
            minimum_immediate_units = additional
            options.append(
                {
                    "kind": "add_immediate_units",
                    "label": "Add immediately available units",
                    "change": {"additional_units": additional},
                    "scenario": _scenario_payload(candidate),
                    "result": {
                        "risk_level": result["risk_level"],
                        "projected_end_inventory": result["projected_end_inventory"],
                        "stockout_day": result["stockout_day"],
                        "safety_breach_day": result["safety_breach_day"],
                    },
                }
            )
            break

    minimum_po_increase: int | None = None
    if scenario.lead_time_days <= len(forecast):
        for additional in range(0, upper_bound + 1):
            candidate = InventoryScenario(
                current_stock=scenario.current_stock,
                incoming_units=scenario.incoming_units + additional,
                lead_time_days=scenario.lead_time_days,
                safety_stock=scenario.safety_stock,
            )
            safe, result = is_low(candidate)
            if safe:
                minimum_po_increase = additional
                options.append(
                    {
                        "kind": "increase_incoming_po",
                        "label": "Increase the incoming purchase order",
                        "change": {"additional_po_units": additional},
                        "scenario": _scenario_payload(candidate),
                        "result": {
                            "risk_level": result["risk_level"],
                            "projected_end_inventory": result["projected_end_inventory"],
                            "stockout_day": result["stockout_day"],
                            "safety_breach_day": result["safety_breach_day"],
                        },
                    }
                )
                break

    latest_safe_arrival_day: int | None = None
    if scenario.incoming_units > 0:
        latest_candidate = min(scenario.lead_time_days, len(forecast))
        for lead_time in range(latest_candidate, -1, -1):
            candidate = InventoryScenario(
                current_stock=scenario.current_stock,
                incoming_units=scenario.incoming_units,
                lead_time_days=lead_time,
                safety_stock=scenario.safety_stock,
            )
            safe, result = is_low(candidate)
            if safe:
                latest_safe_arrival_day = lead_time
                if lead_time != scenario.lead_time_days:
                    options.append(
                        {
                            "kind": "expedite_po",
                            "label": "Receive the existing PO earlier",
                            "change": {"lead_time_days": lead_time},
                            "scenario": _scenario_payload(candidate),
                            "result": {
                                "risk_level": result["risk_level"],
                                "projected_end_inventory": result["projected_end_inventory"],
                                "stockout_day": result["stockout_day"],
                                "safety_breach_day": result["safety_breach_day"],
                            },
                        }
                    )
                break

    return {
        "baseline_risk": baseline["risk_level"],
        "decision_horizon_days": len(forecast),
        "minimum_immediate_units": minimum_immediate_units,
        "minimum_po_increase": minimum_po_increase,
        "latest_safe_arrival_day": latest_safe_arrival_day,
        "options": options,
        "notice": (
            "Counterfactuals are deterministic scenario comparisons, not automatic orders. "
            "They do not include supplier constraints, MOQ, carrying cost, margin, or service-level optimization."
        ),
    }
