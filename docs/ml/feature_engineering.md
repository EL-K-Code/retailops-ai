# Leakage-safe demand feature engineering

V2.3 prepares the first learned forecasting model without exposing validation or test targets to feature generation.

## Modeling strategy

RetailOps AI uses a global one-step model as the first learned forecasting approach.

For a target date `t`, the model learns:

```text
units_sold(t) = f(history through t-1, known covariates at t)
```

The 28-day validation forecast is produced recursively in Python. After each predicted day, that prediction is appended to the series history and becomes available to construct the next day's lag and rolling features.

## Training feature table

`ml_training_features` is built only from rows where `dataset_split = train` and is materialized as a BigQuery table partitioned by `date` and clustered by `store_id, item_id`.

The first 28 training days are excluded because a complete 28-day target history is not yet available.

Expected rows:

```text
(1,885 train days - 28 warm-up days) x 30,490 series
= 56,619,930 rows
```

## Target-history features

All target-derived features end at `t-1`:

```text
lag_1
lag_7
lag_14
lag_28
rolling_mean_7
rolling_mean_28
rolling_std_28
```

Rolling windows explicitly end at `1 preceding`, so the current target is never included. `feature_history_end_date = t - 1 day` is retained as an audit field.

## Calendar, entity, and price features

The table also exposes entity identifiers, department/category/state, date parts, weekend/event/SNAP fields, `sell_price`, `price_available`, and `price_change_7d`.

Price variables are only valid for future forecasting when the future price plan is genuinely known at prediction time.

## Forecast covariates

`ml_forecast_covariates` contains validation and test rows but deliberately excludes `units_sold`, target lags, target rolling statistics, and target-derived GOLD measures.

Expected rows:

```text
2 x 28 days x 30,490 series = 1,707,440
```

## Run

After the ML split contract exists:

```bash
python scripts/run_dbt_features.py
```

Building the physical training feature table can scan and store tens of millions of BigQuery rows. Check the active billing/free-tier context before cloud execution.

## Scope boundary

V2.3 does not fit a learned model. V2.4 introduces Python + LightGBM, recursive 28-day inference, and evaluation against the existing baselines.
