"""Tests for deterministic inventory scenario simulation."""

from __future__ import annotations

import pytest

from retailops_ai.decision.inventory import InventoryScenario, simulate_inventory


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


def test_inventory_scenario_rejects_invalid_lead_time() -> None:
    with pytest.raises(ValueError, match="lead_time_days"):
        simulate_inventory(
            _points([1.0, 1.0]),
            InventoryScenario(current_stock=2.0, lead_time_days=3),
        )
