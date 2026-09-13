"""RetailOps AI Vertex AI entrypoint for global LightGBM demand forecasting.

The model logic is shared with ``retailops_ai.ml`` so local and cloud training
use the same leakage-safe feature contract, recursive validation forecast, and
evaluation implementation.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime
from pathlib import Path

from google.cloud import aiplatform, bigquery

from retailops_ai.ml.bigquery_io import (
    BigQueryMLConfig,
    load_forecast_covariates,
    load_rmsse_scales,
    load_seed_history,
    load_training_frame,
    load_validation_actuals,
    training_window,
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
from retailops_ai.mlops.artifacts import upload_directory_to_gcs


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--location", default=os.getenv("VERTEX_REGION", "us-central1"))
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
        "--local-model-dir",
        type=Path,
        default=Path(os.getenv("VERTEX_LOCAL_MODEL_DIR", "/tmp/retailops-model")),
    )
    parser.add_argument(
        "--artifact-uri",
        default=os.getenv("AIP_MODEL_DIR") or os.getenv("VERTEX_MODEL_ARTIFACT_URI"),
        help="GCS directory for model artifacts. Vertex sets AIP_MODEL_DIR automatically.",
    )
    parser.add_argument(
        "--experiment",
        default=os.getenv("VERTEX_EXPERIMENT", "retailops-demand-forecasting"),
    )
    parser.add_argument("--run-name", default=os.getenv("VERTEX_RUN_NAME"))
    parser.add_argument(
        "--use-storage-api",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("ML_USE_BQ_STORAGE_API", False),
    )
    return parser.parse_args()


def _experiment_context(
    *,
    project: str,
    location: str,
    experiment: str | None,
    run_name: str,
) -> AbstractContextManager[object]:
    if not experiment:
        return nullcontext()

    aiplatform.init(
        project=project,
        location=location,
        experiment=experiment,
        experiment_description="RetailOps AI demand forecasting experiments",
    )
    return aiplatform.start_run(run=run_name)


def main() -> None:
    args = parse_args()
    if not args.project:
        raise SystemExit("GOOGLE_CLOUD_PROJECT or --project is required")
    if args.train_lookback_days <= 0:
        raise SystemExit("--train-lookback-days must be positive")
    if args.num_boost_round <= 0:
        raise SystemExit("--num-boost-round must be positive")

    run_time = datetime.now(UTC)
    run_name = args.run_name or f"lightgbm-v1-{run_time:%Y%m%d-%H%M%S}"
    config = BigQueryMLConfig(
        project=args.project,
        location=args.location,
        dbt_dataset=args.dbt_dataset,
        train_lookback_days=args.train_lookback_days,
        use_storage_api=args.use_storage_api,
    )
    client = bigquery.Client(project=config.project, location=config.location)
    training_start, training_end = training_window(config)

    with _experiment_context(
        project=args.project,
        location=args.location,
        experiment=args.experiment,
        run_name=run_name,
    ):
        if args.experiment:
            aiplatform.log_params(
                {
                    "model_name": MODEL_NAME,
                    "model_version": MODEL_VERSION,
                    "train_lookback_days": args.train_lookback_days,
                    "num_boost_round": args.num_boost_round,
                    "training_start": str(training_start),
                    "training_end": str(training_end),
                    "evaluation_split": "validation",
                }
            )

        print(f"Loading training features: {training_start} -> {training_end}")
        training = load_training_frame(client, config)
        training_rows = len(training)
        print(f"Training rows loaded: {training_rows:,}")

        print(
            f"Training {MODEL_NAME} {MODEL_VERSION} "
            f"with {args.num_boost_round} boosting rounds..."
        )
        trained = train_global_lightgbm(
            training,
            num_boost_round=args.num_boost_round,
        )

        del training
        gc.collect()

        print("Loading 28-day seed history and target-free validation covariates...")
        seed_history = load_seed_history(client, config)
        validation_covariates = load_forecast_covariates(
            client,
            config,
            split="validation",
        )

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

        metrics_payload = {
            "mae": metrics.mae,
            "rmse": metrics.rmse,
            "mean_rmsse": metrics.mean_rmsse,
            "evaluated_observations": metrics.evaluated_observations,
            "evaluated_series": metrics.evaluated_series,
        }
        metadata = {
            "run_name": run_name,
            "model_name": MODEL_NAME,
            "model_version": MODEL_VERSION,
            "project": args.project,
            "location": args.location,
            "dbt_dataset": args.dbt_dataset,
            "training_start": training_start,
            "training_end": training_end,
            "training_rows": training_rows,
            "train_lookback_days": args.train_lookback_days,
            "num_boost_round": args.num_boost_round,
            "evaluation_split": "validation",
            "validation_start": M5_DEMAND_FORECAST_CONTRACT.validation.start,
            "validation_end": M5_DEMAND_FORECAST_CONTRACT.validation.end,
            "artifact_uri": args.artifact_uri,
            "experiment": args.experiment,
            "created_at": run_time,
            **metrics_payload,
        }

        args.local_model_dir.mkdir(parents=True, exist_ok=True)
        model_path, metadata_path = save_model_artifacts(
            trained,
            args.local_model_dir,
            metadata,
        )
        metrics_path = args.local_model_dir / "metrics.json"
        metrics_path.write_text(
            json.dumps(metrics_payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        if args.artifact_uri:
            uploaded = upload_directory_to_gcs(args.local_model_dir, args.artifact_uri)
            print(f"Uploaded {len(uploaded)} artifact files to {args.artifact_uri}")

        if args.experiment:
            aiplatform.log_metrics(metrics_payload)

        print("\nValidation metrics")
        print(f"MAE:        {metrics.mae:.6f}")
        print(f"RMSE:       {metrics.rmse:.6f}")
        print(f"mean RMSSE: {metrics.mean_rmsse:.6f}")
        print(f"Model artifact: {model_path}")
        print(f"Metadata:       {metadata_path}")
        print(f"Metrics:        {metrics_path}")
        if args.artifact_uri:
            print(f"VERTEX_ARTIFACT_URI={args.artifact_uri}")
        print(f"VERTEX_RUN_NAME={run_name}")


if __name__ == "__main__":
    main()
