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

The initial model is a **global** model: one LightGBM booster is trained across all item-store series rather than fitting 30,490 independent estimators.

The target is non-negative count demand, so the first configuration uses LightGBM's Poisson objective. Model performance is still reported with the same model-agnostic validation metrics as the baselines.

No validation labels are used to construct recursive forecast features.

## Local resource guardrail

The full feature table contains more than 56 million training rows. Pulling the entire table into a developer laptop would be unnecessarily expensive and memory intensive for a first model.

The Python loader therefore uses a configurable recent training window:

```text
ML_TRAIN_LOOKBACK_DAYS=180
```

With 30,490 bottom-level series, 180 days corresponds to approximately 5.49 million rows before any source irregularity. This is a pragmatic V1 training budget, not a claim that 180 days is the optimal statistical lookback.

The window is selected with a BigQuery date predicate so the partitioned feature table can prune older partitions.

## Features

Categorical features:

```text
item_id
store_id
department
category
state
event_name_1
event_type_1
event_name_2
event_type_2
```

Numeric / binary features:

```text
sell_price
price_available
price_change_7d
is_weekend
snap_active
day_of_week
day_of_month
week_of_year
month
year
lag_1
lag_7
lag_14
lag_28
rolling_mean_7
rolling_mean_28
rolling_std_28
```

Category vocabularies are learned from the training frame and reused during recursive inference. Unseen future values become missing categories instead of silently receiving arbitrary integer identities.

## Recursive 28-day inference

The model is trained as a global one-step predictor. Validation inference is recursive:

```text
real train history
    -> predict validation day 1
    -> append prediction 1 to history
    -> recompute lag / rolling features
    -> predict validation day 2
    -> ...
    -> predict validation day 28
```

The Python inference state retains only the final 28 values per series because the current history-derived features require at most 28 days.

Validation labels are loaded only **after** the recursive predictions have been generated.

## Outputs

Local artifacts are written beneath the ignored directory:

```text
artifacts/models/lightgbm_global_v1/
├── model.txt
└── metadata.json
```

The metadata records feature names, categorical vocabularies, training dates, row count, parameters, model version, and validation metrics.

When explicitly enabled with:

```text
ML_WRITE_BIGQUERY=true
```

Python appends run-versioned outputs to:

```text
retailops_ml.ml_forecast_predictions
retailops_ml.ml_model_evaluation
```

Predictions are not written back by default, which avoids accidental cloud mutations while developing locally.

## BigQuery reading mode

Standard BigQuery DataFrame downloads are used by default:

```text
ML_USE_BQ_STORAGE_API=false
```

The BigQuery Storage Read API can be enabled for faster reads:

```text
ML_USE_BQ_STORAGE_API=true
```

Storage Read API usage has its own pricing and outbound network considerations. Review the active Google Cloud billing context before enabling it.

## Run

After the dbt feature layer and baseline tables have been built in the real GCP environment:

```bash
chmod +x scripts/train_lightgbm.sh
./scripts/train_lightgbm.sh
```

To persist predictions and evaluation rows:

```bash
ML_WRITE_BIGQUERY=true ./scripts/train_lightgbm.sh
```

## Validation discipline

V2.4 evaluates only the fixed validation window. The final test split stays untouched while the first model, feature set, and training-budget decisions are still being developed.

A real M5 score must not be claimed until this pipeline has been executed against the actual BigQuery feature tables.
