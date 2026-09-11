"""Global LightGBM demand forecasting for RetailOps AI."""

from __future__ import annotations

from dataclasses import dataclass
from json import dumps
from math import sqrt
from pathlib import Path
from typing import Any, Protocol

import lightgbm as lgb
import numpy as np
import pandas as pd

MODEL_NAME = "lightgbm_global"
MODEL_VERSION = "v1"
DEFAULT_NUM_BOOST_ROUND = 300

CATEGORICAL_FEATURES = (
    "item_id",
    "store_id",
    "department",
    "category",
    "state",
    "event_name_1",
    "event_type_1",
    "event_name_2",
    "event_type_2",
)

NUMERIC_FEATURES = (
    "sell_price",
    "price_available",
    "price_change_7d",
    "is_weekend",
    "snap_active",
    "day_of_week",
    "day_of_month",
    "week_of_year",
    "month",
    "year",
    "lag_1",
    "lag_7",
    "lag_14",
    "lag_28",
    "rolling_mean_7",
    "rolling_mean_28",
    "rolling_std_28",
)

MODEL_FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES

DEFAULT_PARAMS: dict[str, Any] = {
    "objective": "poisson",
    "metric": "rmse",
    "learning_rate": 0.05,
    "num_leaves": 63,
    "min_data_in_leaf": 100,
    "feature_fraction": 0.9,
    "bagging_fraction": 0.9,
    "bagging_freq": 1,
    "seed": 42,
    "feature_fraction_seed": 42,
    "bagging_seed": 42,
    "verbosity": -1,
    "num_threads": -1,
}


class Predictor(Protocol):
    """Minimal prediction protocol used by recursive inference."""

    def predict(self, data: pd.DataFrame) -> Any:
        """Return one prediction per input row."""


@dataclass(frozen=True)
class TrainedLightGBM:
    """LightGBM booster plus the categorical levels required at inference."""

    booster: lgb.Booster
    category_levels: dict[str, tuple[str, ...]]
    params: dict[str, Any]
    num_boost_round: int


@dataclass(frozen=True)
class ForecastMetrics:
    """Validation metrics for one recursive forecast run."""

    mae: float
    rmse: float
    mean_rmsse: float
    evaluated_observations: int
    evaluated_series: int


def fit_category_levels(frame: pd.DataFrame) -> dict[str, tuple[str, ...]]:
    """Learn stable categorical levels from the training data."""
    missing = [column for column in CATEGORICAL_FEATURES if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing categorical feature columns: {', '.join(missing)}")

    levels: dict[str, tuple[str, ...]] = {}
    for column in CATEGORICAL_FEATURES:
        values = frame[column].astype("string").dropna().unique().tolist()
        levels[column] = tuple(sorted(str(value) for value in values))
    return levels


def prepare_model_frame(
    frame: pd.DataFrame,
    category_levels: dict[str, tuple[str, ...]] | None = None,
) -> tuple[pd.DataFrame, dict[str, tuple[str, ...]]]:
    """Return a memory-conscious LightGBM feature frame with aligned categories."""
    missing = [column for column in MODEL_FEATURES if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing model feature columns: {', '.join(missing)}")

    levels = category_levels or fit_category_levels(frame)
    prepared = frame.loc[:, MODEL_FEATURES].copy()

    for column in CATEGORICAL_FEATURES:
        categories = levels.get(column)
        if categories is None:
            raise ValueError(f"Missing categorical levels for {column}")
        prepared[column] = pd.Categorical(
            prepared[column].astype("string"),
            categories=list(categories),
        )

    for column in NUMERIC_FEATURES:
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce").astype("float32")

    return prepared, levels


def train_global_lightgbm(
    training_frame: pd.DataFrame,
    *,
    params: dict[str, Any] | None = None,
    num_boost_round: int = DEFAULT_NUM_BOOST_ROUND,
) -> TrainedLightGBM:
    """Train the first global LightGBM count-demand model."""
    if training_frame.empty:
        raise ValueError("Training frame must not be empty")
    if "units_sold" not in training_frame.columns:
        raise ValueError("Training frame must contain units_sold")
    if num_boost_round <= 0:
        raise ValueError("num_boost_round must be positive")

    features, levels = prepare_model_frame(training_frame)
    target = pd.to_numeric(training_frame["units_sold"], errors="raise").astype("float32")
    if (target < 0).any():
        raise ValueError("Poisson demand target must be non-negative")

    training_params = dict(DEFAULT_PARAMS)
    if params:
        training_params.update(params)

    dataset = lgb.Dataset(
        features,
        label=target,
        categorical_feature=list(CATEGORICAL_FEATURES),
        free_raw_data=False,
    )
    booster = lgb.train(
        training_params,
        dataset,
        num_boost_round=num_boost_round,
    )
    return TrainedLightGBM(
        booster=booster,
        category_levels=levels,
        params=training_params,
        num_boost_round=num_boost_round,
    )


def _prepare_seed_history(seed_history: pd.DataFrame) -> tuple[list[str], np.ndarray]:
    required = {"series_id", "date", "units_sold"}
    missing = required.difference(seed_history.columns)
    if missing:
        raise ValueError(f"Seed history missing columns: {', '.join(sorted(missing))}")

    seed = seed_history.copy()
    seed["series_id"] = seed["series_id"].astype(str)
    seed["date"] = pd.to_datetime(seed["date"])
    pivot = seed.pivot(index="series_id", columns="date", values="units_sold").sort_index(axis=1)

    if pivot.shape[1] < 28:
        raise ValueError("Recursive inference requires at least 28 seed-history days")
    pivot = pivot.iloc[:, -28:]
    if pivot.isna().any().any():
        raise ValueError("Every series must have a complete 28-day seed history")

    series_ids = pivot.index.astype(str).tolist()
    values = pivot.to_numpy(dtype="float32", copy=True)
    return series_ids, values


def recursive_forecast(
    predictor: Predictor,
    seed_history: pd.DataFrame,
    forecast_covariates: pd.DataFrame,
    category_levels: dict[str, tuple[str, ...]],
) -> pd.DataFrame:
    """Generate a recursive forecast, appending predictions instead of future labels."""
    if forecast_covariates.empty:
        raise ValueError("Forecast covariates must not be empty")

    series_ids, history = _prepare_seed_history(seed_history)
    covariates = forecast_covariates.copy()
    covariates["series_id"] = covariates["series_id"].astype(str)
    covariates["date"] = pd.to_datetime(covariates["date"])

    forecast_dates = sorted(covariates["date"].drop_duplicates().tolist())
    output_frames: list[pd.DataFrame] = []

    for horizon, forecast_date in enumerate(forecast_dates, start=1):
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
        predictions = np.asarray(predictor.predict(model_frame), dtype="float64")
        if predictions.shape[0] != len(series_ids):
            raise ValueError("Predictor returned an unexpected number of predictions")
        if not np.isfinite(predictions).all():
            raise ValueError("Predictor returned non-finite predictions")
        predictions = np.clip(predictions, 0.0, None)

        output_frames.append(
            pd.DataFrame(
                {
                    "series_id": series_ids,
                    "item_id": day["item_id"].astype("string").to_numpy(),
                    "store_id": day["store_id"].astype("string").to_numpy(),
                    "forecast_date": forecast_date,
                    "horizon": horizon,
                    "prediction": predictions,
                }
            )
        )
        history = np.concatenate(
            [history[:, 1:], predictions.astype("float32").reshape(-1, 1)],
            axis=1,
        )

    return pd.concat(output_frames, ignore_index=True)


def evaluate_recursive_forecast(
    predictions: pd.DataFrame,
    actuals: pd.DataFrame,
    rmsse_scales: pd.DataFrame,
) -> ForecastMetrics:
    """Evaluate recursive predictions with MAE, RMSE and bottom-level mean RMSSE."""
    prediction_frame = predictions[["series_id", "forecast_date", "prediction"]].copy()
    actual_frame = actuals[["series_id", "date", "units_sold"]].copy()
    prediction_frame["series_id"] = prediction_frame["series_id"].astype(str)
    actual_frame["series_id"] = actual_frame["series_id"].astype(str)
    prediction_frame["forecast_date"] = pd.to_datetime(prediction_frame["forecast_date"])
    actual_frame["date"] = pd.to_datetime(actual_frame["date"])

    merged = prediction_frame.merge(
        actual_frame,
        left_on=["series_id", "forecast_date"],
        right_on=["series_id", "date"],
        how="inner",
        validate="one_to_one",
    )
    if len(merged) != len(prediction_frame) or len(merged) != len(actual_frame):
        raise ValueError("Predictions and actuals do not cover the same series-date observations")

    error = merged["prediction"].astype(float) - merged["units_sold"].astype(float)
    mae_value = float(error.abs().mean())
    mse_value = float((error**2).mean())

    series_mse = (
        merged.assign(squared_error=error**2)
        .groupby("series_id", as_index=False)["squared_error"]
        .mean()
        .rename(columns={"squared_error": "mse"})
    )
    scale_frame = rmsse_scales[["series_id", "rmsse_scale"]].copy()
    scale_frame["series_id"] = scale_frame["series_id"].astype(str)
    scaled = series_mse.merge(scale_frame, on="series_id", how="left", validate="one_to_one")
    valid = scaled["rmsse_scale"].notna() & (scaled["rmsse_scale"] > 0)
    if not valid.any():
        raise ValueError("No valid RMSSE scales are available")

    mean_rmsse = float(np.sqrt(scaled.loc[valid, "mse"] / scaled.loc[valid, "rmsse_scale"]).mean())
    return ForecastMetrics(
        mae=mae_value,
        rmse=sqrt(mse_value),
        mean_rmsse=mean_rmsse,
        evaluated_observations=len(merged),
        evaluated_series=int(merged["series_id"].nunique()),
    )


def save_model_artifacts(
    trained: TrainedLightGBM,
    output_dir: Path,
    metadata: dict[str, Any],
) -> tuple[Path, Path]:
    """Persist the native LightGBM model and reproducibility metadata locally."""
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "model.txt"
    metadata_path = output_dir / "metadata.json"

    trained.booster.save_model(str(model_path))
    payload = {
        **metadata,
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "model_features": list(MODEL_FEATURES),
        "categorical_features": list(CATEGORICAL_FEATURES),
        "category_levels": {key: list(values) for key, values in trained.category_levels.items()},
        "lightgbm_params": trained.params,
        "num_boost_round": trained.num_boost_round,
    }
    metadata_path.write_text(
        dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    return model_path, metadata_path
