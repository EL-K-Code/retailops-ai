"""Model-assumption uncertainty helpers for RetailOps demand forecasts."""

from __future__ import annotations

from collections.abc import Sequence
from math import sqrt
from statistics import NormalDist
from typing import Any


def _poisson_quantile_approx(mean: float, quantile: float) -> float:
    """Approximate a Poisson quantile with a variance-stabilizing transform."""
    if not 0 < quantile < 1:
        raise ValueError("quantile must be between 0 and 1")
    if mean <= 0:
        return 0.0
    z_score = NormalDist().inv_cdf(quantile)
    root = sqrt(mean + 0.375) + (z_score / 2.0)
    return max(0.0, root * root - 0.375)


def poisson_predictive_band(
    points: Sequence[dict[str, Any]],
    *,
    lower_quantile: float = 0.10,
    upper_quantile: float = 0.90,
) -> dict[str, Any]:
    """Return an approximate predictive stress band implied by the Poisson objective.

    The band is not empirically calibrated and therefore must not be presented as
    a service-level guarantee.
    """
    if lower_quantile >= upper_quantile:
        raise ValueError("lower_quantile must be below upper_quantile")

    band: list[dict[str, Any]] = []
    for index, point in enumerate(points, start=1):
        prediction = max(
            0.0,
            float(point.get("prediction", point.get("value", 0.0))),
        )
        band.append(
            {
                "date": point.get("date"),
                "horizon": int(point.get("horizon", index)),
                "prediction": prediction,
                "lower": _poisson_quantile_approx(prediction, lower_quantile),
                "upper": _poisson_quantile_approx(prediction, upper_quantile),
            }
        )

    return {
        "method": "poisson_variance_stabilized_approximation",
        "lower_quantile": lower_quantile,
        "upper_quantile": upper_quantile,
        "points": band,
        "total_prediction": sum(point["prediction"] for point in band),
        "total_lower": sum(point["lower"] for point in band),
        "total_upper": sum(point["upper"] for point in band),
        "notice": (
            "Model-assumption predictive stress band; not a calibrated coverage "
            "guarantee. Calibrate on production-like residuals before using it "
            "for service-level commitments."
        ),
    }


def band_as_forecast_points(
    band: dict[str, Any],
    *,
    level: str,
) -> list[dict[str, Any]]:
    if level not in {"lower", "prediction", "upper"}:
        raise ValueError("level must be lower, prediction or upper")
    return [
        {
            "date": point.get("date"),
            "horizon": point["horizon"],
            "prediction": float(point[level]),
        }
        for point in band.get("points", [])
    ]
