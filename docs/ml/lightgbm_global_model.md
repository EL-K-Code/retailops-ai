# Global LightGBM demand model

V2.4 introduces the first learned forecasting model in RetailOps AI.

## Boundary between BigQuery and Python

BigQuery/dbt remains responsible for warehouse-scale, reusable offline feature engineering. Python is responsible for fitted model training, recursive multi-step inference, evaluation, and model artifacts.

```text
BigQuery
├── retailops_ml.ml_training_features
├── retailops_ml.ml_forecast_covariates
├── retailops_ml.ml_demand_split
└── retailops_ml.ml_rmsse_scale
        |
        v
Python
├── load bounded training data
├── train global LightGBM
├── recursively forecast 28 validation days
├── evaluate MAE / RMSE / mean RMSSE
└── save model + metadata
        |
        +--> optional BigQuery prediction/evaluation tables
```

## First-model scope

The initial model is global: one LightGBM booster is trained across all item-store series rather than fitting 30,490 independent estimators.

The target is non-negative count demand, so the first configuration uses LightGBM's Poisson objective. No validation labels are used to construct recursive forecast features.

## Local resource guardrail

The full feature table contains more than 56 million training rows. The Python loader therefore uses a configurable recent training window:

```text
ML_TRAIN_LOOKBACK_DAYS=180
```

With 30,490 bottom-level series, 180 days corresponds to approximately 5.49 million rows. This is a pragmatic first training budget, not a claim that 180 days is statistically optimal.

## Features

Categorical features include item/store/product hierarchy, state, and event fields. Numeric/binary features include price/calendar fields plus lags and rolling statistics.

Category vocabularies are learned from the training frame and reused during recursive inference. Unseen future values become missing categories instead of receiving arbitrary integer identities.

## Recursive 28-day inference

```text
real train history
    -> predict validation day 1
    -> append prediction 1 to history
    -> recompute lag / rolling features
    -> predict validation day 2
    -> ...
    -> predict validation day 28
```

Validation labels are loaded only after the recursive predictions have been generated.

## Outputs

Local artifacts are written beneath the ignored directory:

```text
artifacts/models/lightgbm_global_v1/
├── model.txt
└── metadata.json
```

When `ML_WRITE_BIGQUERY=true`, Python appends run-versioned outputs to:

```text
retailops_ml.ml_forecast_predictions
retailops_ml.ml_model_evaluation
```

Predictions are not written back by default.

## BigQuery reading mode

Standard BigQuery DataFrame downloads are used by default with `ML_USE_BQ_STORAGE_API=false`. The BigQuery Storage Read API can be enabled for faster reads, but its pricing and network implications should be reviewed first.

## Run

After the dbt feature layer and baseline tables have been built in GCP:

```bash
python scripts/train_lightgbm_runner.py
```

Example smoke run:

```bash
python scripts/train_lightgbm_runner.py \
  --train-lookback-days 30 \
  --num-boost-round 20 \
  --artifact-dir artifacts/models/lightgbm_global_v1_smoke
```

To persist predictions and evaluation rows, set `ML_WRITE_BIGQUERY=true` in `.env` before running the Python entry point.

## Validation discipline

V2.4 evaluates only the fixed validation window. The final test split stays untouched while the first model, feature set, and training-budget decisions are still being developed.
