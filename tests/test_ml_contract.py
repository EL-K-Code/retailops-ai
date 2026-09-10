"""Tests for the demand-forecasting dataset contract."""

from datetime import date
from pathlib import Path

from retailops_ai.ml.contracts import M5_DEMAND_FORECAST_CONTRACT


ROOT = Path(__file__).resolve().parents[1]


def test_m5_forecast_windows_are_contiguous() -> None:
    contract = M5_DEMAND_FORECAST_CONTRACT

    assert contract.horizon_days == 28
    assert contract.validation.days == 28
    assert contract.test.days == 28
    assert contract.train.end < contract.validation.start < contract.test.start


def test_m5_forecast_split_assignment() -> None:
    contract = M5_DEMAND_FORECAST_CONTRACT

    assert contract.split_for_date(date(2011, 1, 29)) == "train"
    assert contract.split_for_date(date(2016, 3, 27)) == "train"
    assert contract.split_for_date(date(2016, 3, 28)) == "validation"
    assert contract.split_for_date(date(2016, 4, 24)) == "validation"
    assert contract.split_for_date(date(2016, 4, 25)) == "test"
    assert contract.split_for_date(date(2016, 5, 22)) == "test"
    assert contract.split_for_date(date(2016, 5, 23)) is None


def test_target_derived_gold_metrics_are_forbidden() -> None:
    contract = M5_DEMAND_FORECAST_CONTRACT

    assert "estimated_sales_value" in contract.forbidden_features
    assert "total_units_sold" in contract.forbidden_features


def test_dbt_ml_view_excludes_target_derived_value() -> None:
    sql_path = ROOT / "warehouse" / "dbt" / "models" / "ml" / "ml_demand_split.sql"
    sql = sql_path.read_text(encoding="utf-8")

    assert "estimated_sales_value" not in sql
    assert "dataset_split" in sql


def test_dbt_split_dates_match_python_contract() -> None:
    project = (ROOT / "warehouse" / "dbt" / "dbt_project.yml").read_text(encoding="utf-8")
    contract = M5_DEMAND_FORECAST_CONTRACT

    expected_dates = (
        contract.train.start,
        contract.train.end,
        contract.validation.start,
        contract.validation.end,
        contract.test.start,
        contract.test.end,
    )
    for value in expected_dates:
        assert value.isoformat() in project
