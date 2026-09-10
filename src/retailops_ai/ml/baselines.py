"""Leakage-safe forecasting baselines and metrics for RetailOps AI."""

from __future__ import annotations

from collections.abc import Sequence
from math import sqrt


def _validate_horizon(horizon: int) -> None:
    if horizon <= 0:
        raise ValueError("Forecast horizon must be positive")


def _validate_pair(actual: Sequence[float], predicted: Sequence[float]) -> None:
    if not actual:
        raise ValueError("Actual values must not be empty")
    if len(actual) != len(predicted):
        raise ValueError("Actual and predicted values must have the same length")


def naive_last_forecast(history: Sequence[float], horizon: int) -> tuple[float, ...]:
    """Repeat the final observed training value across the full forecast horizon."""
    _validate_horizon(horizon)
    if not history:
        raise ValueError("History must not be empty")

    value = float(history[-1])
    return tuple(value for _ in range(horizon))


def seasonal_naive_forecast(
    history: Sequence[float],
    horizon: int,
    period: int,
) -> tuple[float, ...]:
    """Repeat the last complete seasonal pattern without reading future observations."""
    _validate_horizon(horizon)
    if period <= 0:
        raise ValueError("Seasonal period must be positive")
    if len(history) < period:
        raise ValueError("History must contain at least one complete seasonal period")

    cycle = tuple(float(value) for value in history[-period:])
    return tuple(cycle[index % period] for index in range(horizon))


def mae(actual: Sequence[float], predicted: Sequence[float]) -> float:
    """Mean absolute error."""
    _validate_pair(actual, predicted)
    return sum(
        abs(float(observed) - float(forecast))
        for observed, forecast in zip(actual, predicted, strict=True)
    ) / len(actual)


def rmse(actual: Sequence[float], predicted: Sequence[float]) -> float:
    """Root mean squared error."""
    _validate_pair(actual, predicted)
    squared_error = sum(
        (float(observed) - float(forecast)) ** 2
        for observed, forecast in zip(actual, predicted, strict=True)
    )
    return sqrt(squared_error / len(actual))


def rmsse_scale(training_values: Sequence[float]) -> float:
    """Return the M5-style RMSSE scale after the first non-zero demand observation."""
    first_nonzero_index = next(
        (index for index, value in enumerate(training_values) if float(value) > 0.0),
        None,
    )
    if first_nonzero_index is None:
        raise ValueError("RMSSE scale is undefined for an all-zero training series")

    active_history = training_values[first_nonzero_index:]
    if len(active_history) < 2:
        raise ValueError("RMSSE scale requires at least two active-history observations")

    squared_differences = [
        (float(current) - float(previous)) ** 2
        for previous, current in zip(active_history[:-1], active_history[1:], strict=True)
    ]
    scale = sum(squared_differences) / len(squared_differences)
    if scale <= 0.0:
        raise ValueError("RMSSE scale must be strictly positive")
    return scale


def rmsse(
    training_values: Sequence[float],
    actual: Sequence[float],
    predicted: Sequence[float],
) -> float:
    """Root mean squared scaled error for one series."""
    _validate_pair(actual, predicted)
    mean_squared_error = rmse(actual, predicted) ** 2
    return sqrt(mean_squared_error / rmsse_scale(training_values))
