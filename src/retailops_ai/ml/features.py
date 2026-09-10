"""Leakage-safe demand feature helpers for RetailOps AI."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import mean, stdev


@dataclass(frozen=True)
class DemandHistoryFeatures:
    """Target-history features available strictly before one forecast date."""

    lag_1: float
    lag_7: float
    lag_14: float
    lag_28: float
    rolling_mean_7: float
    rolling_mean_28: float
    rolling_std_28: float


def build_history_features(history: Sequence[float]) -> DemandHistoryFeatures:
    """Build lag and rolling features from observations available before prediction time."""
    if len(history) < 28:
        raise ValueError("At least 28 historical observations are required")

    values = [float(value) for value in history]
    last_7 = values[-7:]
    last_28 = values[-28:]

    return DemandHistoryFeatures(
        lag_1=values[-1],
        lag_7=values[-7],
        lag_14=values[-14],
        lag_28=values[-28],
        rolling_mean_7=mean(last_7),
        rolling_mean_28=mean(last_28),
        rolling_std_28=stdev(last_28),
    )


def price_change_7d(current_price: float | None, previous_price: float | None) -> float | None:
    """Return relative price change versus seven days earlier when both prices are usable."""
    if current_price is None or previous_price is None:
        return None

    previous = float(previous_price)
    if previous == 0.0:
        return None

    return (float(current_price) - previous) / previous
