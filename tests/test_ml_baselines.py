"""Tests for leakage-safe demand-forecasting baselines."""

from math import sqrt
from pathlib import Path

import pytest

from retailops_ai.ml.baselines import (
    mae,
    naive_last_forecast,
    rmse,
    rmsse,
    rmsse_scale,
    seasonal_naive_forecast,
)


ROOT = Path(__file__).resolve().parents[1]


def test_naive_last_repeats_only_last_training_value() -> None:
    assert naive_last_forecast([2, 4, 3], 4) == (3.0, 3.0, 3.0, 3.0)


def test_seasonal_naive_repeats_last_season_without_future_labels() -> None:
    history = list(range(1, 29))
    forecast = seasonal_naive_forecast(history, horizon=10, period=7)

    assert forecast == (22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 22.0, 23.0, 24.0)


def test_seasonal_naive_28_reuses_last_training_window() -> None:
    history = list(range(1, 29))
    assert seasonal_naive_forecast(history, horizon=28, period=28) == tuple(
        float(value) for value in history
    )


def test_error_metrics_are_computed_consistently() -> None:
    actual = [1, 2, 3]
    predicted = [2, 2, 1]

    assert mae(actual, predicted) == pytest.approx(1.0)
    assert rmse(actual, predicted) == pytest.approx(sqrt(5 / 3))


def test_rmsse_scale_ignores_leading_zero_demand() -> None:
    training = [0, 0, 1, 3, 2]

    assert rmsse_scale(training) == pytest.approx(2.5)
    assert rmsse(training, actual=[2], predicted=[3]) == pytest.approx(sqrt(1 / 2.5))


def test_rmsse_rejects_zero_scale_series() -> None:
    with pytest.raises(ValueError, match="strictly positive"):
        rmsse_scale([0, 1, 1, 1])


def test_sql_baselines_use_validation_only_and_auditable_source_dates() -> None:
    sql = (
        ROOT
        / "warehouse"
        / "dbt"
        / "models"
        / "ml"
        / "baselines"
        / "ml_baseline_predictions.sql"
    ).read_text(encoding="utf-8").lower()

    assert "dataset_split = 'validation'" in sql
    assert "last_value_source_date" in sql
    assert "seasonal_7_source_date" in sql
    assert "seasonal_28_source_date" in sql
    assert "dataset_split = 'test'" not in sql
