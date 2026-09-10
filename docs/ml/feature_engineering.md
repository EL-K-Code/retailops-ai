# Leakage-safe demand feature engineering

V2.3 prepares the first learned forecasting model without exposing validation or test targets to feature generation.

## Modeling strategy

RetailOps AI uses a global one-step model as the first learned forecasting approach.

For a target date `t`, the model learns:

```text
units_sold(t) = f(history through t-1, known covariates at t)
```

The 28-day validation forecast will later be produced recursively in Python. After each predicted day, that prediction is appended to the series history and becomes available to construct the next day's lag and rolling features.

This avoids reading observed validation labels for later horizons.

## Training feature table

`ml_training_features` is built only from rows where:

```text
dataset_split = train
```

It is materialized as a BigQuery table because lag and rolling-window computation over tens of millions of rows is expensive and will be reused by model training.

Physical layout:

```text
partition: date
cluster: store_id, item_id
```

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

Rolling windows explicitly use:

```text
... rows between N preceding and 1 preceding
```

so the current target is never included.

`feature_history_end_date = t - 1 day` is retained as an audit field.

## Calendar and entity features

The training table also exposes:

```text
item_id
store_id
department
category
state
day_of_week
day_of_month
week_of_year
month
year
is_weekend
event fields
snap_active
```

These variables are known from the row context or calendar.

## Price features

The table includes:

```text
sell_price
price_available
price_change_7d
```

`price_change_7d` compares the current price with the price seven days earlier using safe division.

Price variables are only valid for future forecasting when the future price plan is genuinely known at prediction time. They remain optional deployment covariates rather than universally assumed information.

## Forecast covariates

`ml_forecast_covariates` contains validation and test rows but deliberately excludes:

```text
units_sold
lag_*
rolling_*
estimated_sales_value
```

The view contains only entity identifiers and future-known/conditionally-known covariates required by recursive inference.

Expected rows:

```text
2 x 28 days x 30,490 series = 1,707,440
```

## Why validation features are not precomputed from observed demand

A tempting implementation would compute `lag_1`, `lag_7`, and rolling means directly for validation rows using SQL window functions over the full observed dataset.

That would be wrong for a true 28-day forecast. For example, the `lag_1` feature for validation day 2 would contain the real demand from validation day 1, which would not be known when all 28 days are forecast from the same origin.

RetailOps AI therefore separates:

```text
observed TRAIN history -> SQL training features
future validation/test calendar context -> forecast covariates
recursive predicted history -> Python inference features (next milestone)
```

## Run

After the ML split contract exists:

```bash
chmod +x scripts/run_dbt_features.sh
./scripts/run_dbt_features.sh
```

Building the physical training feature table can scan and store tens of millions of BigQuery rows. Check the active billing/free-tier context before cloud execution.

## Scope boundary

V2.3 does not fit a learned model. The next milestone introduces Python + LightGBM, reads the training feature table, trains a global regressor, and evaluates a recursive 28-day forecast against the existing baselines.
