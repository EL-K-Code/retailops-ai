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

One row per calendar date. It preserves M5 calendar attributes and adds:

- `quarter`;
- `is_weekend`.

The natural key is `date`. The original `day_key` remains available for source traceability.

### `dim_product`

One row per M5 item with its department and category.

The natural key is `item_id`.

### `dim_store`

One row per store with its state.

The natural key is `store_id`.

### `fact_sales_daily`

Grain:

```text
item x store x date
```

The fact contains the keys needed to join the dimensions plus the observed measure `units_sold`.

It is intentionally materialized as a **view** over the already materialized and partitioned `stg_sales` table. Copying roughly 59 million rows into another physical table would add storage and rebuild cost without introducing a new physical optimization at this milestone.

### `fact_prices_weekly`

Grain:

```text
store x item x Walmart week
```

The model maps each `wm_yr_wk` to the earliest represented calendar date, exposed as `week_start_date` for time-based access. It is materialized as a BigQuery table partitioned by `week_start_date` and clustered by `store_id, item_id`.

A left join is used when attaching the week date so source price rows are not silently dropped. The Silver integrity test fails if a week cannot be mapped to the calendar.

## Natural keys instead of surrogate keys

This milestone intentionally keeps M5's stable identifiers (`item_id`, `store_id`, `date`) as warehouse keys.

Surrogate keys would add complexity without solving a current requirement because this static source has no slowly-changing-dimension history or source-system key collision to resolve. If those requirements appear later, key strategy can evolve explicitly.

## Data quality

Silver tests focus on invariants introduced by the business model instead of repeating all STAGING checks.

They validate:

- uniqueness and non-nullness of dimension keys;
- expected dimension cardinalities: 1,969 dates, 3,049 products, 10 stores;
- fact-to-dimension referential integrity;
- uniqueness of the weekly price fact grain.

The large `fact_sales_daily` view is not given redundant per-column tests because the underlying `stg_sales` model already validates required fields, row count, and non-negative units. This avoids unnecessary repeated scans of the roughly 59 million-row table.

## BigQuery datasets

With the default target dataset:

```text
BQ_DBT_DATASET=retailops
```

dbt creates the Silver models under:

```text
retailops_silver
```

## Run

V1.5 STAGING must already be built successfully.

Then run:

```bash
chmod +x scripts/run_dbt_silver.sh
./scripts/run_dbt_silver.sh
```

The script runs `dbt debug`, builds/tests the Silver models, then executes the Silver-specific warehouse integrity tests.

## Scope boundary

SILVER provides reusable facts and dimensions. It does not yet contain dashboard-oriented aggregations, forecasting features, lags, rolling statistics, predictions, or stockout logic.

Those belong to GOLD/MARTS and the later ML milestone.
