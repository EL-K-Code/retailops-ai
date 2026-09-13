"""Business-facing forecasting service built on the validated recursive model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol, Sequence

import pandas as pd

from retailops_ai.ml.contracts import M5_DEMAND_FORECAST_CONTRACT
from retailops_ai.ml.lightgbm_pipeline import recursive_forecast
from retailops_ai.serving.model import LoadedForecastModel
from retailops_ai.serving.repository import EntityKey


class UnknownSeriesError(LookupError):
    """Raised when one or more requested item/store combinations are unknown."""

    def __init__(self, missing: Sequence[EntityKey]) -> None:
        self.missing = tuple(missing)
        detail = ", ".join(f"{entity.item_id}@{entity.store_id}" for entity in self.missing)
        super().__init__(f"Unknown item/store series: {detail}")


class ForecastRepository(Protocol):
    def resolve_series(self, entities: Sequence[EntityKey], split: str) -> pd.DataFrame: ...

    def load_seed_history(self, series_ids: Sequence[str], split: str) -> pd.DataFrame: ...

    def load_forecast_covariates(
        self,
        series_ids: Sequence[str],
        split: str,
    ) -> pd.DataFrame: ...


@dataclass(frozen=True)
class ForecastPoint:
    date: date
    horizon: int
    prediction: float


@dataclass(frozen=True)
class SeriesForecast:
    series_id: str
    item_id: str
    store_id: str
    points: tuple[ForecastPoint, ...]


@dataclass(frozen=True)
class ForecastBatch:
    split: str
    forecast_origin: date
    horizon_days: int
    generated_at: datetime
    model: dict[str, object]
    forecasts: tuple[SeriesForecast, ...]


class ForecastService:
    """Resolve business keys, fetch minimal features, and forecast recursively."""

    def __init__(
        self,
        *,
        model: LoadedForecastModel,
        repository: ForecastRepository,
        max_entities: int = 50,
    ) -> None:
        if max_entities <= 0:
            raise ValueError("max_entities must be positive")
        self.model = model
        self.repository = repository
        self.max_entities = max_entities

    def forecast(
        self,
        entities: Sequence[EntityKey],
        *,
        split: str = "test",
    ) -> ForecastBatch:
        if split not in {"validation", "test"}:
            raise ValueError("split must be validation or test")
        if not entities:
            raise ValueError("At least one entity is required")
        if len(entities) > self.max_entities:
            raise ValueError(f"At most {self.max_entities} entities may be requested")

        unique_entities = tuple(dict.fromkeys(entities))
        resolved = self.repository.resolve_series(unique_entities, split)
        if resolved.empty:
            raise UnknownSeriesError(unique_entities)

        resolved_keys = {
            EntityKey(str(row.item_id), str(row.store_id)): str(row.series_id)
            for row in resolved.itertuples(index=False)
        }
        missing = [entity for entity in unique_entities if entity not in resolved_keys]
        if missing:
            raise UnknownSeriesError(missing)
        if len(resolved_keys) != len(resolved):
            raise RuntimeError("Expected exactly one series_id per item/store combination")

        series_ids = [resolved_keys[entity] for entity in unique_entities]
        seed_history = self.repository.load_seed_history(series_ids, split)
        covariates = self.repository.load_forecast_covariates(series_ids, split)

        predictions = recursive_forecast(
            self.model.booster,
            seed_history,
            covariates,
            self.model.category_levels,
        )

        by_series: dict[str, pd.DataFrame] = {
            str(series_id): frame.sort_values("horizon")
            for series_id, frame in predictions.groupby("series_id", sort=False)
        }
        forecasts: list[SeriesForecast] = []
        expected_horizon = M5_DEMAND_FORECAST_CONTRACT.horizon_days
        for entity in unique_entities:
            series_id = resolved_keys[entity]
            frame = by_series.get(series_id)
            if frame is None or len(frame) != expected_horizon:
                raise RuntimeError(
                    f"Expected {expected_horizon} predictions for {series_id}, "
                    f"got {0 if frame is None else len(frame)}"
                )
            points = tuple(
                ForecastPoint(
                    date=pd.Timestamp(row.forecast_date).date(),
                    horizon=int(row.horizon),
                    prediction=float(row.prediction),
                )
                for row in frame.itertuples(index=False)
            )
            forecasts.append(
                SeriesForecast(
                    series_id=series_id,
                    item_id=entity.item_id,
                    store_id=entity.store_id,
                    points=points,
                )
            )

        window = (
            M5_DEMAND_FORECAST_CONTRACT.validation
            if split == "validation"
            else M5_DEMAND_FORECAST_CONTRACT.test
        )
        return ForecastBatch(
            split=split,
            forecast_origin=window.start,
            horizon_days=expected_horizon,
            generated_at=datetime.now(UTC),
            model=self.model.summary(),
            forecasts=tuple(forecasts),
        )
