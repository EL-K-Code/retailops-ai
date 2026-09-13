from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from retailops_ai.ml.contracts import M5_DEMAND_FORECAST_CONTRACT
from retailops_ai.ml.lightgbm_pipeline import CATEGORICAL_FEATURES
from retailops_ai.serving.model import LoadedForecastModel
from retailops_ai.serving.repository import EntityKey
from retailops_ai.serving.service import ForecastService, UnknownSeriesError


class ConstantPredictor:
    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        return np.full(len(frame), 2.0)


class FakeRepository:
    def __init__(self, *, known: bool = True) -> None:
        self.known = known
        self.entity = EntityKey("ITEM_1", "CA_1")
        self.series_id = "ITEM_1_CA_1_evaluation"

    def resolve_series(self, entities, split: str) -> pd.DataFrame:
        assert split in {"validation", "test"}
        if not self.known:
            return pd.DataFrame(columns=["series_id", "item_id", "store_id"])
        return pd.DataFrame(
            [
                {
                    "series_id": self.series_id,
                    "item_id": self.entity.item_id,
                    "store_id": self.entity.store_id,
                }
            ]
        )

    def load_seed_history(self, series_ids, split: str) -> pd.DataFrame:
        assert series_ids == [self.series_id]
        seed_end = (
            M5_DEMAND_FORECAST_CONTRACT.train.end
            if split == "validation"
            else M5_DEMAND_FORECAST_CONTRACT.validation.end
        )
        seed_start = seed_end - timedelta(days=27)
        return pd.DataFrame(
            {
                "series_id": [self.series_id] * 28,
                "date": pd.date_range(seed_start, seed_end),
                "units_sold": np.ones(28),
            }
        )

    def load_forecast_covariates(self, series_ids, split: str) -> pd.DataFrame:
        assert series_ids == [self.series_id]
        window = (
            M5_DEMAND_FORECAST_CONTRACT.validation
            if split == "validation"
            else M5_DEMAND_FORECAST_CONTRACT.test
        )
        rows = []
        for forecast_date in pd.date_range(window.start, window.end):
            rows.append(
                {
                    "series_id": self.series_id,
                    "date": forecast_date,
                    "item_id": "ITEM_1",
                    "store_id": "CA_1",
                    "department": "FOODS_1",
                    "category": "FOODS",
                    "state": "CA",
                    "event_name_1": "none",
                    "event_type_1": "none",
                    "event_name_2": "none",
                    "event_type_2": "none",
                    "sell_price": 1.0,
                    "price_available": 1.0,
                    "price_change_7d": 0.0,
                    "is_weekend": float(forecast_date.weekday() >= 5),
                    "snap_active": 0.0,
                    "day_of_week": forecast_date.weekday(),
                    "day_of_month": forecast_date.day,
                    "week_of_year": int(forecast_date.isocalendar().week),
                    "month": forecast_date.month,
                    "year": forecast_date.year,
                }
            )
        return pd.DataFrame(rows)


def _model() -> LoadedForecastModel:
    levels = {
        "item_id": ("ITEM_1",),
        "store_id": ("CA_1",),
        "department": ("FOODS_1",),
        "category": ("FOODS",),
        "state": ("CA",),
        "event_name_1": ("none",),
        "event_type_1": ("none",),
        "event_name_2": ("none",),
        "event_type_2": ("none",),
    }
    assert set(levels) == set(CATEGORICAL_FEATURES)
    return LoadedForecastModel(
        booster=ConstantPredictor(),  # type: ignore[arg-type]
        category_levels=levels,
        metadata={
            "model_name": "lightgbm_global",
            "model_version": "v1",
            "run_name": "unit-test",
            "mean_rmsse": 0.77,
        },
    )


def test_forecast_service_returns_28_recursive_predictions() -> None:
    entity = EntityKey("ITEM_1", "CA_1")
    service = ForecastService(model=_model(), repository=FakeRepository())

    result = service.forecast([entity], split="test")

    assert result.split == "test"
    assert result.forecast_origin == date(2016, 4, 25)
    assert result.horizon_days == 28
    assert len(result.forecasts) == 1
    forecast = result.forecasts[0]
    assert forecast.series_id == "ITEM_1_CA_1_evaluation"
    assert len(forecast.points) == 28
    assert forecast.points[0].horizon == 1
    assert forecast.points[-1].horizon == 28
    assert {point.prediction for point in forecast.points} == {2.0}


def test_forecast_service_rejects_unknown_series() -> None:
    service = ForecastService(model=_model(), repository=FakeRepository(known=False))
    with pytest.raises(UnknownSeriesError, match="ITEM_1@CA_1"):
        service.forecast([EntityKey("ITEM_1", "CA_1")])


def test_forecast_service_enforces_request_limit() -> None:
    service = ForecastService(model=_model(), repository=FakeRepository(), max_entities=1)
    with pytest.raises(ValueError, match="At most 1"):
        service.forecast(
            [EntityKey("ITEM_1", "CA_1"), EntityKey("ITEM_2", "CA_1")]
        )
