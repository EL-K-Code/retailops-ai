"""Tests for leakage-safe demand feature engineering."""

from pathlib import Path

import pytest

from retailops_ai.ml.features import build_history_features, price_change_7d


ROOT = Path(__file__).resolve().parents[1]


def test_history_features_use_only_prior_observations() -> None:
    features = build_history_features(list(range(1, 29)))

    assert features.lag_1 == 28.0
    assert features.lag_7 == 22.0
    assert features.lag_14 == 15.0
    assert features.lag_28 == 1.0
    assert features.rolling_mean_7 == pytest.approx(25.0)
    assert features.rolling_mean_28 == pytest.approx(14.5)
    assert features.rolling_std_28 == pytest.approx(8.225975119502044)


def test_history_features_require_28_days() -> None:
    with pytest.raises(ValueError, match="28 historical observations"):
        build_history_features([1.0] * 27)


def test_price_change_handles_missing_and_zero_reference() -> None:
    assert price_change_7d(12.0, 10.0) == pytest.approx(0.2)
    assert price_change_7d(None, 10.0) is None
    assert price_change_7d(10.0, None) is None
    assert price_change_7d(10.0, 0.0) is None


def test_training_sql_excludes_current_target_from_rolling_windows() -> None:
    sql = (
        ROOT
        / "warehouse"
        / "dbt"
        / "models"
        / "ml"
        / "features"
        / "ml_training_features.sql"
    ).read_text(encoding="utf-8").lower()

    assert "rows between 7 preceding and 1 preceding" in sql
    assert "rows between 28 preceding and 1 preceding" in sql
    assert "where dataset_split = 'train'" in sql


def test_forecast_covariates_do_not_expose_observed_target() -> None:
    sql = (
        ROOT
        / "warehouse"
        / "dbt"
        / "models"
        / "ml"
        / "features"
        / "ml_forecast_covariates.sql"
    ).read_text(encoding="utf-8").lower()

    assert "units_sold" not in sql
    assert "lag_1" not in sql
    assert "rolling_mean" not in sql
    assert "dataset_split in ('validation', 'test')" in sql
