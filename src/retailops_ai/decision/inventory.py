"""Inventory scenario simulation grounded on model forecasts.

The M5 source data does not contain operational stock, purchase orders, or
supplier lead times.  This module therefore treats inventory values strictly as
user-provided scenario inputs and combines them with a real forecast through a
small deterministic decision engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any, Sequence


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
        if self.lead_time_days < 0 or self.lead_time_days > horizon_days:
            raise ValueError(f"lead_time_days must be between 0 and {horizon_days}")


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


def simulate_inventory(
    points: Sequence[dict[str, Any]],
    scenario: InventoryScenario,
) -> dict[str, Any]:
    """Project inventory day by day from a real forecast and scenario inputs.

    An incoming purchase order is assumed to arrive at the beginning of the
    configured lead-time day.  A lead time of zero means the incoming units are
    available before day one.  The function never creates or infers inventory
    facts; it only transforms explicitly supplied scenario values.
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

    available_units = float(scenario.current_stock + scenario.incoming_units)
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
