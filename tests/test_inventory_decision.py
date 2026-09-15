"""Tests for deterministic inventory scenario simulation."""

from __future__ import annotations

import pytest

from retailops_ai.decision.inventory import (
    InventoryScenario,
    recommend_inventory_counterfactuals,
    simulate_inventory,
)


def _points(values: list[float]) -> list[dict[str, object]]:
    return [
        {
            "date": f"2016-05-{index:02d}",
            "horizon": index,
            "prediction": value,
        }
        for index, value in enumerate(values, start=1)
    ]


def test_inventory_scenario_flags_stockout_and_review_quantity() -> None:
    result = simulate_inventory(
        _points([4.0, 4.0, 4.0, 4.0]),
        InventoryScenario(
            current_stock=8.0,
            incoming_units=3.0,
            lead_time_days=3,
            safety_stock=2.0,
        ),
    )

    assert result["scenario_mode"] is True
    assert result["forecast_total"] == pytest.approx(16.0)
    assert result["available_units"] == pytest.approx(11.0)
    assert result["projected_end_inventory"] == pytest.approx(-5.0)
    assert result["shortage_units"] == pytest.approx(5.0)
    assert result["stockout_day"] == 3
    assert result["risk_level"] == "high"
    assert result["recommended_action"] == "review_reorder"
    assert result["review_quantity"] == pytest.approx(7.0)


def test_inventory_scenario_preserves_safe_position() -> None:
    result = simulate_inventory(
        _points([2.0, 2.0, 2.0]),
        InventoryScenario(
            current_stock=20.0,
            incoming_units=0.0,
            lead_time_days=0,
            safety_stock=5.0,
        ),
    )

    assert result["projected_end_inventory"] == pytest.approx(14.0)
    assert result["stockout_day"] is None
    assert result["safety_breach_day"] is None
    assert result["risk_level"] == "low"
    assert result["recommended_action"] == "monitor"


def test_purchase_order_after_decision_horizon_is_not_counted_as_available() -> None:
    result = simulate_inventory(
        _points([2.0, 2.0, 2.0]),
        InventoryScenario(
            current_stock=5.0,
            incoming_units=20.0,
            lead_time_days=7,
            safety_stock=0.0,
        ),
    )

    assert result["available_units"] == pytest.approx(5.0)
    assert result["projected_end_inventory"] == pytest.approx(-1.0)
    assert result["stockout_day"] == 3


def test_counterfactuals_find_minimum_immediate_units() -> None:
    result = recommend_inventory_counterfactuals(
        _points([3.0, 3.0, 3.0, 3.0]),
        InventoryScenario(
            current_stock=8.0,
            incoming_units=0.0,
            lead_time_days=0,
            safety_stock=2.0,
        ),
    )

    assert result["baseline_risk"] == "high"
    assert result["minimum_immediate_units"] == 6
    immediate = next(
        option
        for option in result["options"]
        if option["kind"] == "add_immediate_units"
    )
    assert immediate["result"]["risk_level"] == "low"
    assert immediate["scenario"]["current_stock"] == pytest.approx(14.0)


def test_counterfactuals_can_recommend_earlier_purchase_order_arrival() -> None:
    result = recommend_inventory_counterfactuals(
        _points([4.0, 4.0, 1.0, 1.0]),
        InventoryScenario(
            current_stock=8.0,
            incoming_units=5.0,
            lead_time_days=4,
            safety_stock=1.0,
        ),
    )

    assert result["baseline_risk"] in {"high", "medium"}
    assert result["latest_safe_arrival_day"] is not None
    expedite = [
        option
        for option in result["options"]
        if option["kind"] == "expedite_po"
    ]
    assert expedite
    assert expedite[0]["result"]["risk_level"] == "low"
