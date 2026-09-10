# Demand forecasting dataset contract

V2.1 starts the machine-learning layer by defining a reproducible, leakage-aware evaluation contract before any model is trained.

## Forecasting task

Target:

```text
units_sold
```

Series grain:

```text
item x store x date
```

Primary forecast horizon:

```text
28 days
```

The contract uses `series_id` as the stable time-series identifier, with `item_id` and `store_id` retained as explicit entity keys.

## Temporal split

RetailOps AI never uses a random split for this forecasting task.

The M5 evaluation source contains sales through `d_1941`. The final 28 observed days are reserved as the untouched test window, while the immediately preceding 28 days are used for validation.

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

`ml_demand_split` is a view over `mart_demand_daily`. It exposes the forecasting target, entity identifiers, and covariates while adding:

```text
dataset_split in {train, validation, test}
```

It deliberately excludes target-derived GOLD fields such as:

```text
estimated_sales_value
```

because that field already contains `units_sold` and would create direct target leakage.

## Covariate availability

Calendar attributes such as weekend flags, planned events, and SNAP indicators are treated as future-known because they can be known before the forecast horizon begins.

`sell_price` and `price_available` are only valid future covariates when a future price plan is genuinely available at prediction time. M5 provides future prices for the competition setting, but a production deployment must preserve this same as-of-time requirement. If future price information is unavailable operationally, these fields must be excluded from the deployed feature set.

## Leakage rules

For a forecast origin `T`:

- target-derived historical features may only use observations available at or before `T`;
- actual sales inside the 28-day forecast horizon must never be used to build features for that same forecast;
- test labels remain untouched until the final evaluation;
- same-day aggregates containing the target are forbidden as item-level model features;
- target-derived GOLD metrics are not exposed by the ML contract view.

Examples of forbidden fields include:

```text
estimated_sales_value
total_units_sold
active_item_count
stores_with_sales
```

These fields are useful for descriptive analytics, but they contain information derived from observed demand and therefore cannot be blindly reused as predictive features.

## Why this precedes model training

Without a fixed evaluation contract, model scores are not comparable and leakage can make a weak model appear strong. V2.1 therefore freezes the target, grain, horizon, split dates, and feature-availability rules before the first baseline is implemented.

## Run

After GOLD exists:

```bash
chmod +x scripts/run_dbt_ml_contract.sh
./scripts/run_dbt_ml_contract.sh
```

The command builds/tests the ML contract view and validates expected split counts and date boundaries.

Because the checks operate on the detailed demand mart, they can scan BigQuery data. Review the active project billing/free-tier context before cloud execution.

## Scope boundary

V2.1 does not train a forecasting model and does not create lags, rolling statistics, encodings, or predictions.

Those begin with the next forecasting milestone, starting from simple leakage-safe baselines before more complex global models.
