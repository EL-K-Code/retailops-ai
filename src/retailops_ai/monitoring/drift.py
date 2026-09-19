"""Distribution-drift diagnostics for production-style monitoring."""

from __future__ import annotations

from typing import Any

import numpy as np


def _as_array(values: list[float]) -> np.ndarray:
    array = np.asarray(values, dtype="float64")
    array = array[np.isfinite(array)]
    if array.size < 2:
        raise ValueError("at least two finite observations are required")
    return array


def population_stability_index(
    reference: list[float],
    current: list[float],
    *,
    bins: int = 10,
) -> float:
    if bins < 2:
        raise ValueError("bins must be at least 2")
    ref = _as_array(reference)
    cur = _as_array(current)

    edges = np.unique(np.quantile(ref, np.linspace(0.0, 1.0, bins + 1)))
    if edges.size < 3:
        low = min(float(ref.min()), float(cur.min()))
        high = max(float(ref.max()), float(cur.max()))
        if low == high:
            return 0.0
        edges = np.linspace(low, high, bins + 1)

    edges[0] = -np.inf
    edges[-1] = np.inf
    ref_counts, _ = np.histogram(ref, bins=edges)
    cur_counts, _ = np.histogram(cur, bins=edges)
    epsilon = 1e-6
    ref_share = np.maximum(ref_counts / ref.size, epsilon)
    cur_share = np.maximum(cur_counts / cur.size, epsilon)
    return float(np.sum((cur_share - ref_share) * np.log(cur_share / ref_share)))


def demand_distribution_drift(
    reference: list[float],
    current: list[float],
) -> dict[str, Any]:
    ref = _as_array(reference)
    cur = _as_array(current)
    psi = population_stability_index(ref.tolist(), cur.tolist())
    reference_std = float(np.std(ref, ddof=1))
    mean_shift_std = (
        abs(float(np.mean(cur)) - float(np.mean(ref))) / reference_std
        if reference_std > 0
        else 0.0
    )
    status = "stable" if psi < 0.10 else "watch" if psi < 0.25 else "shifted"
    return {
        "metric": "daily_demand_distribution",
        "psi": psi,
        "mean_shift_std": mean_shift_std,
        "status": status,
        "reference_observations": int(ref.size),
        "current_observations": int(cur.size),
        "reference_mean": float(np.mean(ref)),
        "current_mean": float(np.mean(cur)),
        "notice": (
            "PSI is a lightweight distribution diagnostic. With 28-day windows "
            "it is a monitoring signal, not proof of model degradation."
        ),
    }
