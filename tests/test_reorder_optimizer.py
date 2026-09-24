from retailops_ai.decision.inventory import InventoryScenario
from retailops_ai.decision.reorder import ReorderEconomics, optimize_reorder_scenario


def _points(values: list[float]) -> list[dict[str, object]]:
    return [
        {"horizon": index, "date": f"D+{index}", "prediction": value}
        for index, value in enumerate(values, start=1)
    ]


def test_optimizer_prefers_protection_when_stockout_penalty_is_high() -> None:
    result = optimize_reorder_scenario(
        _points([3.0, 3.0, 3.0, 3.0]),
        InventoryScenario(
            current_stock=6.0,
            incoming_units=0.0,
            lead_time_days=0,
            safety_stock=2.0,
        ),
        ReorderEconomics(
            unit_order_cost=1.0,
            holding_cost_per_unit=0.1,
            stockout_penalty_per_unit=10.0,
            safety_breach_penalty_per_unit=2.0,
            max_additional_units=20,
        ),
    )

    assert result["recommended_additional_units"] > 0
    assert result["best_candidate"]["stockout_day"] is None


def test_optimizer_can_choose_zero_when_ordering_is_expensive() -> None:
    result = optimize_reorder_scenario(
        _points([1.0, 1.0]),
        InventoryScenario(current_stock=10.0, safety_stock=0.0),
        ReorderEconomics(
            unit_order_cost=100.0,
            holding_cost_per_unit=1.0,
            stockout_penalty_per_unit=1.0,
            max_additional_units=10,
        ),
    )

    assert result["recommended_additional_units"] == 0
