"""Cost-aware scenario optimizer for advisory replenishment analysis."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from math import ceil
from typing import Any

from retailops_ai.decision.inventory import InventoryScenario, simulate_inventory


@dataclass(frozen=True)
class ReorderEconomics:
    """User-provided economic assumptions for one what-if optimization."""

    unit_order_cost: float
    holding_cost_per_unit: float
    stockout_penalty_per_unit: float
    safety_breach_penalty_per_unit: float = 0.0
    min_order_quantity: int = 0
    order_increment: int = 1
    max_additional_units: int = 100

    def validate(self) -> None:
        costs = (
            self.unit_order_cost,
            self.holding_cost_per_unit,
            self.stockout_penalty_per_unit,
            self.safety_breach_penalty_per_unit,
        )
        if any(value < 0 for value in costs):
            raise ValueError("economic cost assumptions must be non-negative")
        if self.min_order_quantity < 0:
            raise ValueError("min_order_quantity must be non-negative")
        if self.order_increment <= 0:
            raise ValueError("order_increment must be positive")
        if self.max_additional_units < 0:
            raise ValueError("max_additional_units must be non-negative")


def _candidate_quantities(economics: ReorderEconomics) -> list[int]:
    quantities = [0]
    start = max(economics.min_order_quantity, economics.order_increment)
    start = int(ceil(start / economics.order_increment) * economics.order_increment)
    quantities.extend(
        range(start, economics.max_additional_units + 1, economics.order_increment)
    )
    return quantities


def optimize_reorder_scenario(
    points: Sequence[dict[str, Any]],
    scenario: InventoryScenario,
    economics: ReorderEconomics,
) -> dict[str, Any]:
    """Find the lowest-cost additional PO quantity under explicit assumptions."""
    economics.validate()
    candidates: list[dict[str, Any]] = []

    for additional_units in _candidate_quantities(economics):
        candidate = InventoryScenario(
            current_stock=scenario.current_stock,
            incoming_units=scenario.incoming_units + additional_units,
            lead_time_days=scenario.lead_time_days,
            safety_stock=scenario.safety_stock,
        )
        result = simulate_inventory(points, candidate)
        excess = max(
            0.0,
            float(result["projected_end_inventory"]) - scenario.safety_stock,
        )
        order_cost = additional_units * economics.unit_order_cost
        holding_cost = excess * economics.holding_cost_per_unit
        stockout_cost = (
            float(result["shortage_units"])
            * economics.stockout_penalty_per_unit
        )
        safety_cost = (
            float(result["safety_stock_gap"])
            * economics.safety_breach_penalty_per_unit
        )
        total_cost = order_cost + holding_cost + stockout_cost + safety_cost
        candidates.append(
            {
                "additional_units": additional_units,
                "total_scenario_cost": total_cost,
                "order_cost": order_cost,
                "holding_cost": holding_cost,
                "stockout_penalty": stockout_cost,
                "safety_breach_penalty": safety_cost,
                "risk_level": result["risk_level"],
                "projected_end_inventory": result["projected_end_inventory"],
                "stockout_day": result["stockout_day"],
                "safety_breach_day": result["safety_breach_day"],
            }
        )

    best = min(
        candidates,
        key=lambda candidate: (
            float(candidate["total_scenario_cost"]),
            int(candidate["additional_units"]),
        ),
    )
    return {
        "economics": asdict(economics),
        "recommended_additional_units": best["additional_units"],
        "best_candidate": best,
        "candidates_evaluated": len(candidates),
        "notice": (
            "Advisory scenario optimization using explicit economic assumptions. "
            "It does not infer supplier capacity, substitutions, taxes, multi-echelon "
            "constraints, or execute an operational order."
        ),
    }
