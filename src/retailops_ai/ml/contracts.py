"""Demand-forecasting contracts used by RetailOps AI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class TimeWindow:
    """Closed interval used for one temporal dataset split."""

    name: str
    start: date
    end: date

    @property
    def days(self) -> int:
        """Return the number of calendar days in the inclusive interval."""
        return (self.end - self.start).days + 1

    def contains(self, value: date) -> bool:
        """Return whether a date belongs to this interval."""
        return self.start <= value <= self.end


@dataclass(frozen=True)
class DemandForecastContract:
    """Forecast target, horizon, covariates, and leakage-safe temporal splits."""

    target: str
    series_key: str
    entity_keys: tuple[str, ...]
    time_key: str
    horizon_days: int
    train: TimeWindow
    validation: TimeWindow
    test: TimeWindow
    future_known_covariates: tuple[str, ...]
    forbidden_features: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate horizon length and strict chronological ordering."""
        if self.horizon_days <= 0:
            raise ValueError("Forecast horizon must be positive")
        if self.validation.days != self.horizon_days:
            raise ValueError("Validation window must match the forecast horizon")
        if self.test.days != self.horizon_days:
            raise ValueError("Test window must match the forecast horizon")
        if self.validation.start != self.train.end + timedelta(days=1):
            raise ValueError("Validation must start immediately after training")
        if self.test.start != self.validation.end + timedelta(days=1):
            raise ValueError("Test must start immediately after validation")

    def split_for_date(self, value: date) -> str | None:
        """Map one observation date to its temporal split."""
        for window in (self.train, self.validation, self.test):
            if window.contains(value):
                return window.name
        return None


M5_DEMAND_FORECAST_CONTRACT = DemandForecastContract(
    target="units_sold",
    series_key="series_id",
    entity_keys=("item_id", "store_id"),
    time_key="date",
    horizon_days=28,
    train=TimeWindow("train", date(2011, 1, 29), date(2016, 3, 27)),
    validation=TimeWindow("validation", date(2016, 3, 28), date(2016, 4, 24)),
    test=TimeWindow("test", date(2016, 4, 25), date(2016, 5, 22)),
    future_known_covariates=(
        "is_weekend",
        "event_name_1",
        "event_type_1",
        "event_name_2",
        "event_type_2",
        "snap_active",
        "sell_price",
        "price_available",
    ),
    forbidden_features=(
        "estimated_sales_value",
        "total_units_sold",
        "active_item_count",
        "stores_with_sales",
    ),
)
