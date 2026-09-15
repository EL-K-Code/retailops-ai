"""Local feature attribution for recursive LightGBM demand forecasts."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from retailops_ai.ml.lightgbm_pipeline import MODEL_FEATURES, prepare_model_frame


def _seed_matrix(seed_history: pd.DataFrame) -> tuple[list[str], np.ndarray]:
    required = {"series_id", "date", "units_sold"}
    missing = required.difference(seed_history.columns)
    if missing:
        raise ValueError(f"Seed history missing columns: {', '.join(sorted(missing))}")

    seed = seed_history.copy()
    seed["series_id"] = seed["series_id"].astype(str)
    seed["date"] = pd.to_datetime(seed["date"])
    pivot = seed.pivot(index="series_id", columns="date", values="units_sold").sort_index(axis=1)
    if pivot.shape[1] < 28:
        raise ValueError("Explainability requires at least 28 seed-history days")
    pivot = pivot.iloc[:, -28:]
    if pivot.isna().any().any():
        raise ValueError("Every series must have a complete 28-day seed history")
    return pivot.index.astype(str).tolist(), pivot.to_numpy(dtype="float32", copy=True)


def recursive_tree_shap_summary(
    booster: Any,
    seed_history: pd.DataFrame,
    forecast_covariates: pd.DataFrame,
    category_levels: dict[str, tuple[str, ...]],
    *,
    top_n: int = 6,
) -> dict[str, list[dict[str, Any]]]:
    """Aggregate LightGBM TreeSHAP contributions across the recursive horizon.

    ``pred_contrib=True`` is LightGBM's native TreeSHAP implementation.  For a
    Poisson objective, the contributions sum to the raw model score rather than
    demand units, so the API deliberately labels the attribution space.
    """

    if top_n <= 0:
        raise ValueError("top_n must be positive")
    if forecast_covariates.empty:
        raise ValueError("Forecast covariates must not be empty")

    series_ids, history = _seed_matrix(seed_history)
    covariates = forecast_covariates.copy()
    covariates["series_id"] = covariates["series_id"].astype(str)
    covariates["date"] = pd.to_datetime(covariates["date"])
    forecast_dates = sorted(covariates["date"].drop_duplicates().tolist())

    feature_count = len(MODEL_FEATURES)
    abs_totals = np.zeros((len(series_ids), feature_count), dtype="float64")
    signed_totals = np.zeros((len(series_ids), feature_count), dtype="float64")
    steps = 0

    for forecast_date in forecast_dates:
        day = covariates.loc[covariates["date"] == forecast_date].copy()
        if day["series_id"].duplicated().any() or set(day["series_id"]) != set(series_ids):
            raise ValueError("Forecast covariates must contain exactly one row per series and date")
        day = day.set_index("series_id").reindex(series_ids)

        day["lag_1"] = history[:, -1]
        day["lag_7"] = history[:, -7]
        day["lag_14"] = history[:, -14]
        day["lag_28"] = history[:, -28]
        day["rolling_mean_7"] = history[:, -7:].mean(axis=1)
        day["rolling_mean_28"] = history.mean(axis=1)
        day["rolling_std_28"] = history.std(axis=1, ddof=1)

        model_frame, _ = prepare_model_frame(day.reset_index(), category_levels)
        predictions = np.asarray(booster.predict(model_frame), dtype="float64")
        contributions = np.asarray(
            booster.predict(model_frame, pred_contrib=True),
            dtype="float64",
        )

        if predictions.shape[0] != len(series_ids):
            raise ValueError("Predictor returned an unexpected number of predictions")
        if contributions.ndim != 2 or contributions.shape[1] < feature_count:
            raise ValueError("LightGBM returned an unexpected contribution matrix")
        if not np.isfinite(predictions).all() or not np.isfinite(contributions).all():
            raise ValueError("Model returned non-finite explanation values")

        feature_contributions = contributions[:, :feature_count]
        abs_totals += np.abs(feature_contributions)
        signed_totals += feature_contributions
        steps += 1

        predictions = np.clip(predictions, 0.0, None)
        history = np.concatenate(
            [history[:, 1:], predictions.astype("float32").reshape(-1, 1)],
            axis=1,
        )

    if steps == 0:
        raise ValueError("No forecast dates were available for explanation")

    result: dict[str, list[dict[str, Any]]] = {}
    for series_index, series_id in enumerate(series_ids):
        mean_abs = abs_totals[series_index] / steps
        mean_signed = signed_totals[series_index] / steps
        denominator = float(mean_abs.sum()) or 1.0
        ranked = np.argsort(-mean_abs)[: min(top_n, feature_count)]
        result[series_id] = [
            {
                "feature": str(MODEL_FEATURES[index]),
                "mean_abs_contribution": float(mean_abs[index]),
                "mean_contribution": float(mean_signed[index]),
                "share": float(mean_abs[index] / denominator),
                "direction": "up" if mean_signed[index] >= 0 else "down",
            }
            for index in ranked
        ]
    return result
