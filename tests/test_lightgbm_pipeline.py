"""Tests for the Python LightGBM forecasting pipeline."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from retailops_ai.ml.bigquery_io import BigQueryMLConfig, build_training_query, training_window
from retailops_ai.ml.lightgbm_pipeline import (
    CATEGORICAL_FEATURES,
    MODEL_FEATURES,
    evaluate_recursive_forecast,
    fit_category_levels,
    recursive_forecast,
    train_global_lightgbm,
)


class LagIncrementPredictor:
    """Synthetic predictor proving recursive history uses previous predictions."""

    def predict(self, data: pd.DataFrame) -> np.ndarray:
        return data["lag_1"].to_numpy(dtype=float) + 1.0


def _base_feature_row(index: int) -> dict[str, object]:
    return {
        "item_id": f"ITEM_{index % 3}",
        "store_id": f"STORE_{index % 2}",
        "department": "FOODS_1",
        "category": "FOODS",
        "state": "CA",
        "event_name_1": None,
        "event_type_1": None,
        "event_name_2": None,
        "event_type_2": None,
        "sell_price": 2.0,
        "price_available": 1,
        "price_change_7d": 0.0,
        "is_weekend": index % 7 in {5, 6},
        "snap_active": 0,
        "day_of_week": (index % 7) + 1,
        "day_of_month": (index % 28) + 1,
        "week_of_year": (index % 52) + 1,
        "month": (index % 12) + 1,
        "year": 2016,
        "lag_1": float(index % 5),
        "lag_7": float((index + 1) % 5),
        "lag_14": float((index + 2) % 5),
        "lag_28": float((index + 3) % 5),
        "rolling_mean_7": 2.0,
        "rolling_mean_28": 2.0,
        "rolling_std_28": 1.0,
        "units_sold": float(index % 6),
    }


def test_first_lightgbm_model_trains_on_synthetic_data() -> None:
    training = pd.DataFrame(_base_feature_row(index) for index in range(120))
    trained = train_global_lightgbm(
        training,
        params={"min_data_in_leaf": 5, "num_leaves": 7},
        num_boost_round=3,
    )

    assert trained.booster.num_trees() == 3
    assert set(trained.category_levels) == set(CATEGORICAL_FEATURES)
    assert tuple(trained.booster.feature_name()) == MODEL_FEATURES


def test_recursive_forecast_appends_predictions_not_future_labels() -> None:
    series_ids = ["SERIES_A", "SERIES_B"]
    seed_rows = []
    start = date(2016, 2, 29)
    for series_index, series_id in enumerate(series_ids):
        for day_index in range(28):
            seed_rows.append(
                {
                    "series_id": series_id,
                    "date": start + timedelta(days=day_index),
                    "units_sold": float(day_index + series_index),
                }
            )
    seed = pd.DataFrame(seed_rows)

    covariate_rows = []
    for horizon in range(1, 4):
        forecast_date = date(2016, 3, 27) + timedelta(days=horizon)
        for series_index, series_id in enumerate(series_ids):
            row = _base_feature_row(series_index)
            for history_feature in (
                "lag_1",
                "lag_7",
                "lag_14",
                "lag_28",
                "rolling_mean_7",
                "rolling_mean_28",
                "rolling_std_28",
                "units_sold",
            ):
                row.pop(history_feature, None)
            row.update(
                {
                    "series_id": series_id,
                    "date": forecast_date,
                    "item_id": f"ITEM_{series_index}",
                    "store_id": f"STORE_{series_index}",
                }
            )
            covariate_rows.append(row)
    covariates = pd.DataFrame(covariate_rows)

    category_source = pd.DataFrame(_base_feature_row(index) for index in range(10))
    category_source.loc[0, "item_id"] = "ITEM_0"
    category_source.loc[1, "item_id"] = "ITEM_1"
    category_source.loc[0, "store_id"] = "STORE_0"
    category_source.loc[1, "store_id"] = "STORE_1"
    levels = fit_category_levels(category_source)

    result = recursive_forecast(LagIncrementPredictor(), seed, covariates, levels)
    series_a = result[result["series_id"] == "SERIES_A"].sort_values("horizon")

    assert series_a["prediction"].tolist() == pytest.approx([28.0, 29.0, 30.0])
    assert series_a["horizon"].tolist() == [1, 2, 3]


def test_recursive_metrics_include_bottom_level_mean_rmsse() -> None:
    predictions = pd.DataFrame(
        {
            "series_id": ["A", "A", "B", "B"],
            "forecast_date": pd.to_datetime(["2016-03-28", "2016-03-29"] * 2),
            "prediction": [2.0, 3.0, 4.0, 5.0],
        }
    )
    actuals = pd.DataFrame(
        {
            "series_id": ["A", "A", "B", "B"],
            "date": pd.to_datetime(["2016-03-28", "2016-03-29"] * 2),
            "units_sold": [1.0, 3.0, 6.0, 5.0],
        }
    )
    scales = pd.DataFrame({"series_id": ["A", "B"], "rmsse_scale": [1.0, 4.0]})

    metrics = evaluate_recursive_forecast(predictions, actuals, scales)

    assert metrics.mae == pytest.approx(0.75)
    assert metrics.rmse == pytest.approx(np.sqrt(1.25))
    assert metrics.mean_rmsse == pytest.approx((np.sqrt(0.5) + np.sqrt(0.5)) / 2)
    assert metrics.evaluated_observations == 4
    assert metrics.evaluated_series == 2


def test_training_query_is_partition_bounded_and_configurable() -> None:
    config = BigQueryMLConfig(
        project="demo-project",
        location="us-central1",
        dbt_dataset="retailops",
        train_lookback_days=180,
    )
    start, end = training_window(config)
    query = build_training_query(config)

    assert (end - start).days + 1 == 180
    assert "ml_training_features" in query
    assert "date between @train_start and @train_end" in query.lower()
    assert "ml_forecast_covariates" not in query
