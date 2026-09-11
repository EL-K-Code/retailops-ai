# Demand forecasting dataset contract

V2.1 starts the machine-learning layer by defining a reproducible, leakage-aware evaluation contract before any model is trained.

## Forecasting task

Target: `units_sold`.

Series grain: `item x store x date`.

Primary forecast horizon: 28 days.

The contract uses `series_id` as the stable time-series identifier, with `item_id` and `store_id` retained as explicit entity keys.

## Temporal split

RetailOps AI never uses a random split for this forecasting task.

| Split | M5 days | Dates | Days |
| --- | --- | --- | ---: |
| Train | `d_1 ... d_1885` | 2011-01-29 to 2016-03-27 | 1,885 |
| Validation | `d_1886 ... d_1913` | 2016-03-28 to 2016-04-24 | 28 |
| Test | `d_1914 ... d_1941` | 2016-04-25 to 2016-05-22 | 28 |

Expected observation counts at 30,490 item-store series:

```text
train      57,473,650
validation    853,720
test          853,720
```

The test window is not used for model selection, feature selection, threshold choice, or hyperparameter tuning.

## dbt ML contract view

`ml_demand_split` is a view over `mart_demand_daily`. It exposes the forecasting target, entity identifiers, and covariates while adding `dataset_split in {train, validation, test}`.

It deliberately excludes target-derived GOLD fields such as `estimated_sales_value`, because that field already contains `units_sold` and would create direct target leakage.

## Covariate availability

Calendar attributes such as weekend flags, planned events, and SNAP indicators are treated as future-known because they can be known before the forecast horizon begins.

`sell_price` and `price_available` are valid future covariates only when a future price plan is genuinely available at prediction time.

## Leakage rules

For a forecast origin `T`:

- target-derived historical features may only use observations available at or before `T`;
- actual sales inside the 28-day forecast horizon must never be used to build features for that same forecast;
- test labels remain untouched until final evaluation;
- same-day aggregates containing the target are forbidden as item-level model features;
- target-derived GOLD metrics are not exposed by the ML contract view.

## Run

After GOLD exists:

```bash
python scripts/run_dbt_ml_contract.py
```

The command builds/tests the ML contract view and validates expected split counts and date boundaries. These checks can scan BigQuery data, so review the active billing/free-tier context before cloud execution.

## Scope boundary

V2.1 does not train a forecasting model and does not create lags, rolling statistics, encodings, or predictions.
