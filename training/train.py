"""RetailOps AI - Vertex AI LightGBM training entrypoint.

Runs the validated forecasting pipeline in a cloud training environment.
The business logic remains shared with the existing retailops_ai.ml package.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from google.cloud import storage

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


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--location", default="us-central1")
    parser.add_argument("--dbt-dataset", default="retailops")
    parser.add_argument("--train-lookback-days", type=int, default=90)
    parser.add_argument("--num-boost-round", type=int, default=100)
    parser.add_argument("--model-dir", default="/tmp/model")
    parser.add_argument("--gcs-model-bucket", default=os.getenv("MODEL_BUCKET"))
    parser.add_argument("--gcs-model-prefix", default="lightgbm_global_v1")
    return parser.parse_args()


def upload_directory(local_dir: str, bucket_name: str, prefix: str):
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    for file in Path(local_dir).iterdir():
        blob = bucket.blob(f"{prefix}/{file.name}")
        blob.upload_from_filename(str(file))


def main():
    args = parse_args()
    if not args.project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is required")

    from google.cloud import bigquery

    client = bigquery.Client(project=args.project, location=args.location)

    config = BigQueryMLConfig(
        project=args.project,
        location=args.location,
        dbt_dataset=args.dbt_dataset,
        train_lookback_days=args.train_lookback_days,
        use_storage_api=False,
    )

    training_start, training_end = training_window(config)
    print(f"Training window: {training_start} -> {training_end}")

    training = load_training_frame(client, config)
    print(f"Training rows: {len(training):,}")

    trained = train_global_lightgbm(
        training,
        num_boost_round=args.num_boost_round,
    )

    seed_history = load_seed_history(client, config)
    covariates = load_forecast_covariates(client, config, split="validation")

    predictions = recursive_forecast(
        trained.booster,
        seed_history,
        covariates,
        trained.category_levels,
    )

    actuals = load_validation_actuals(client, config)
    scales = load_rmsse_scales(client, config)
    metrics = evaluate_recursive_forecast(predictions, actuals, scales)

    run_time = datetime.now(UTC)
    metadata = {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "training_start": training_start,
        "training_end": training_end,
        "training_rows": len(training),
        "train_lookback_days": args.train_lookback_days,
        "num_boost_round": args.num_boost_round,
        "mae": metrics.mae,
        "rmse": metrics.rmse,
        "mean_rmsse": metrics.mean_rmsse,
        "validation_start": M5_DEMAND_FORECAST_CONTRACT.validation.start,
        "validation_end": M5_DEMAND_FORECAST_CONTRACT.validation.end,
        "created_at": run_time.isoformat(),
    }

    output_dir = Path(args.model_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    save_model_artifacts(trained, output_dir, metadata)

    with open(output_dir / "metrics.json", "w") as f:
        json.dump(metadata, f, indent=2)

    if args.gcs_model_bucket:
        upload_directory(
            str(output_dir),
            args.gcs_model_bucket,
            args.gcs_model_prefix,
        )

    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
