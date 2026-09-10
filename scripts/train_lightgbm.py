#!/usr/bin/env python
"""Train and evaluate the first global LightGBM demand model."""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from google.cloud import bigquery

from retailops_ai.ml.bigquery_io import (
    BigQueryMLConfig,
    load_baseline_metrics,
    load_forecast_covariates,
    load_rmsse_scales,
    load_seed_history,
    load_training_frame,
    load_validation_actuals,
    training_window,
    write_evaluation,
    write_predictions,
)
from retailops_ai.ml.contracts import M5_DEMAND_FORECAST_CONTRACT
from retailops_ai.ml.lightgbm_pipeline import (
    MODEL_NAME,
    MODEL_VERSION,
    evaluate_recursive_forecast,
    recursive_forecast,
    save_model_artifacts,
    train_global_lightgbm,
)


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--location", default=os.getenv("BQ_LOCATION", "us-central1"))
    parser.add_argument("--dbt-dataset", default=os.getenv("BQ_DBT_DATASET", "retailops"))
    parser.add_argument(
        "--train-lookback-days",
        type=int,
        default=int(os.getenv("ML_TRAIN_LOOKBACK_DAYS", "180")),
    )
    parser.add_argument(
        "--num-boost-round",
        type=int,
        default=int(os.getenv("ML_NUM_BOOST_ROUND", "300")),
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path(os.getenv("ML_ARTIFACT_DIR", "artifacts/models/lightgbm_global_v1")),
    )
    parser.add_argument(
        "--use-storage-api",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("ML_USE_BQ_STORAGE_API", False),
    )
    parser.add_argument(
        "--write-bigquery",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("ML_WRITE_BIGQUERY", False),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.project:
        raise SystemExit("GOOGLE_CLOUD_PROJECT or --project is required")

    config = BigQueryMLConfig(
        project=args.project,
        location=args.location,
        dbt_dataset=args.dbt_dataset,
        train_lookback_days=args.train_lookback_days,
        use_storage_api=args.use_storage_api,
    )
    client = bigquery.Client(project=config.project, location=config.location)
    run_time = datetime.now(UTC)
    run_id = f"{MODEL_NAME}_{MODEL_VERSION}_{run_time:%Y%m%dT%H%M%SZ}"
    training_start, training_end = training_window(config)

    print(f"Loading training features: {training_start} -> {training_end}")
    training = load_training_frame(client, config)
    print(f"Training rows loaded: {len(training):,}")

    print(f"Training {MODEL_NAME} {MODEL_VERSION} with {args.num_boost_round} boosting rounds...")
    trained = train_global_lightgbm(training, num_boost_round=args.num_boost_round)

    print("Loading 28-day seed history and target-free validation covariates...")
    seed_history = load_seed_history(client, config)
    validation_covariates = load_forecast_covariates(client, config, split="validation")

    print("Generating recursive 28-day validation forecast...")
    predictions = recursive_forecast(
        trained.booster,
        seed_history,
        validation_covariates,
        trained.category_levels,
    )

    print("Loading validation labels only after forecasts are complete...")
    actuals = load_validation_actuals(client, config)
    scales = load_rmsse_scales(client, config)
    metrics = evaluate_recursive_forecast(predictions, actuals, scales)

    metadata = {
        "run_id": run_id,
        "training_start": training_start,
        "training_end": training_end,
        "train_lookback_days": config.train_lookback_days,
        "training_rows": len(training),
        "evaluation_split": "validation",
        "validation_start": M5_DEMAND_FORECAST_CONTRACT.validation.start,
        "validation_end": M5_DEMAND_FORECAST_CONTRACT.validation.end,
        "mae": metrics.mae,
        "rmse": metrics.rmse,
        "mean_rmsse": metrics.mean_rmsse,
        "created_at": run_time,
    }
    model_path, metadata_path = save_model_artifacts(trained, args.artifact_dir, metadata)

    print("\nValidation metrics")
    print(f"MAE:        {metrics.mae:.6f}")
    print(f"RMSE:       {metrics.rmse:.6f}")
    print(f"mean RMSSE: {metrics.mean_rmsse:.6f}")
    print(f"Model artifact: {model_path}")
    print(f"Metadata:       {metadata_path}")

    try:
        baselines = load_baseline_metrics(client, config)
    except Exception as exc:
        print(f"Baseline comparison unavailable: {exc}")
    else:
        print("\nExisting validation baselines")
        print(baselines.to_string(index=False))

    if args.write_bigquery:
        created_at = pd.Timestamp(run_time)
        output = predictions.copy()
        output["run_id"] = run_id
        output["model_name"] = MODEL_NAME
        output["model_version"] = MODEL_VERSION
        output["evaluation_split"] = "validation"
        output["forecast_origin"] = M5_DEMAND_FORECAST_CONTRACT.train.end
        output["created_at"] = created_at
        output["forecast_date"] = pd.to_datetime(output["forecast_date"]).dt.date
        output = output[
            [
                "run_id",
                "model_name",
                "model_version",
                "evaluation_split",
                "forecast_origin",
                "forecast_date",
                "horizon",
                "series_id",
                "item_id",
                "store_id",
                "prediction",
                "created_at",
            ]
        ]

        evaluation = pd.DataFrame(
            [
                {
                    "run_id": run_id,
                    "model_name": MODEL_NAME,
                    "model_version": MODEL_VERSION,
                    "evaluation_split": "validation",
                    "training_start": training_start,
                    "training_end": training_end,
                    "train_lookback_days": config.train_lookback_days,
                    "training_rows": len(training),
                    "evaluated_observations": metrics.evaluated_observations,
                    "evaluated_series": metrics.evaluated_series,
                    "mae": metrics.mae,
                    "rmse": metrics.rmse,
                    "mean_rmsse": metrics.mean_rmsse,
                    "created_at": created_at,
                }
            ]
        )
        print("\nWriting predictions and evaluation to BigQuery...")
        write_predictions(client, config, output)
        write_evaluation(client, config, evaluation)
        print(f"BigQuery write complete for run_id={run_id}")
    else:
        print("\nBigQuery writes disabled. Set ML_WRITE_BIGQUERY=true to persist this run.")


if __name__ == "__main__":
    main()
