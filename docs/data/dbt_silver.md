# dbt SILVER layer

V1.6 introduces the business-oriented warehouse layer built on top of dbt STAGING.

## Purpose

STAGING answers: "What do the cleaned source records look like?"

SILVER answers: "What is the stable analytical model of the retail business?"

The layer separates reusable dimensions from facts and keeps source-specific implementation details out of future marts and ML datasets.

## Models

```text
stg_calendar -------> dim_date -------------------┐
                                                 |
stg_sales ----------> dim_product ---------------+--> future GOLD marts
        |              dim_store ----------------+--> future ML datasets
        |                                        |
        +-------------> fact_sales_daily --------+

stg_sell_prices -----> fact_prices_weekly -------+
                         ^
                         |
                      dim_date
```

### `dim_date`

One row per calendar date. It preserves M5 calendar attributes and adds `quarter` and `is_weekend`. The natural key is `date`.

### `dim_product`

One row per M5 item with its department and category. The natural key is `item_id`.

### `dim_store`

One row per store with its state. The natural key is `store_id`.

### `fact_sales_daily`

Grain:

```text
item x store x date
```

It is intentionally materialized as a view over the already materialized and partitioned `stg_sales` table to avoid copying roughly 59 million rows without a concrete optimization benefit.

### `fact_prices_weekly`

Grain:

```text
store x item x Walmart week
```

The model maps each `wm_yr_wk` to the earliest represented calendar date, exposed as `week_start_date`, and is materialized as a BigQuery table partitioned by `week_start_date` and clustered by `store_id, item_id`.

## Natural keys instead of surrogate keys

This milestone intentionally keeps M5's stable identifiers (`item_id`, `store_id`, `date`) as warehouse keys. Surrogate keys can be introduced later if slowly-changing dimensions or multi-source key collisions create a real requirement.

## Data quality

Silver tests validate uniqueness/non-nullness of dimension keys, expected cardinalities, referential integrity, and uniqueness of the weekly price grain.

## BigQuery datasets

With `BQ_DBT_DATASET=retailops`, dbt creates the Silver models under `retailops_silver`.

## Run

V1.5 STAGING must already be built successfully. Then run:

```bash
python scripts/run_dbt_silver.py
```

The script runs `dbt debug`, builds/tests the Silver models, then executes Silver-specific warehouse integrity tests.

## Scope boundary

SILVER provides reusable facts and dimensions. It does not yet contain dashboard-oriented aggregations, forecasting features, lags, rolling statistics, predictions, or stockout logic.
