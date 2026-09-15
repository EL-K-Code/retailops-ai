"""Tests for recursive local feature attribution."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from retailops_ai.ml.lightgbm_pipeline import MODEL_FEATURES, fit_category_levels
from retailops_ai.serving.explainability import recursive_tree_shap_summary


class SyntheticExplainablePredictor:
    """Small predictor exposing deterministic LightGBM-like contributions."""

    def predict(self, data: pd.DataFrame, pred_contrib: bool = False) -> np.ndarray:
        if pred_contrib:
            values = np.zeros((len(data), len(MODEL_FEATURES) + 1), dtype=float)
            values[:, MODEL_FEATURES.index("lag_1")] = 2.0
            values[:, MODEL_FEATURES.index("rolling_mean_7")] = -1.0
            values[:, MODEL_FEATURES.index("sell_price")] = 0.5
            values[:, -1] = 0.25
            return values
        return data["lag_1"].to_numpy(dtype=float) + 1.0


def _feature_row() -> dict[str, object]:
    return {
        "item_id": "FOODS_1_001",
        "store_id": "CA_1",
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
        "is_weekend": 0,
        "snap_active": 0,
        "day_of_week": 1,
        "day_of_month": 1,
        "week_of_year": 13,
        "month": 3,
        "year": 2016,
        "lag_1": 1.0,
        "lag_7": 1.0,
        "lag_14": 1.0,
        "lag_28": 1.0,
        "rolling_mean_7": 1.0,
        "rolling_mean_28": 1.0,
        "rolling_std_28": 0.0,
    }


def test_recursive_tree_shap_summary_ranks_local_drivers() -> None:
    start = date(2016, 2, 29)
    seed = pd.DataFrame(
        {
            "series_id": "FOODS_1_001_CA_1_evaluation",
            "date": [start + timedelta(days=index) for index in range(28)],
            "units_sold": [float(index + 1) for index in range(28)],
        }
    )

    covariates = []
    for horizon in range(1, 4):
        row = _feature_row()
        for feature in (
            "lag_1",
            "lag_7",
            "lag_14",
            "lag_28",
            "rolling_mean_7",
            "rolling_mean_28",
            "rolling_std_28",
        ):
            row.pop(feature)
        row.update(
            {
                "series_id": "FOODS_1_001_CA_1_evaluation",
                "date": date(2016, 3, 27) + timedelta(days=horizon),
            }
        )
        covariates.append(row)

    category_levels = fit_category_levels(pd.DataFrame([_feature_row()]))
    result = recursive_tree_shap_summary(
        SyntheticExplainablePredictor(),
        seed,
        pd.DataFrame(covariates),
        category_levels,
        top_n=3,
    )

    features = result["FOODS_1_001_CA_1_evaluation"]
    assert [feature["feature"] for feature in features] == [
        "lag_1",
        "rolling_mean_7",
        "sell_price",
    ]
    assert features[0]["direction"] == "up"
    assert features[1]["direction"] == "down"
    assert features[0]["share"] > features[1]["share"] > features[2]["share"]
