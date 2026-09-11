# dbt GOLD / marts layer

V1.7 introduces business-consumption marts on top of the reusable SILVER warehouse model.

## Purpose

SILVER provides reusable facts and dimensions. GOLD answers concrete consumption questions and exposes stable datasets for analytics and the later ML milestone.

```text
SILVER
├── fact_sales_daily
├── fact_prices_weekly
├── dim_date
├── dim_product
└── dim_store
        |
        v
GOLD
├── mart_demand_daily
├── mart_store_daily_sales
└── mart_product_daily_sales
```

## `mart_demand_daily`

Grain:

```text
item x store x date
```

The mart joins daily unit sales with product/store/calendar attributes, both M5 event slots, the state-specific SNAP indicator, and weekly M5 sell price when available.

It also exposes:

```text
price_available
estimated_sales_value = units_sold x sell_price
```

`estimated_sales_value` is an estimate derived from observed unit sales and weekly sell price; it is not claimed to be transaction-level realized revenue.

The mart is materialized as a BigQuery table partitioned by `date` and clustered by `store_id, item_id`.

## Aggregate marts

`mart_store_daily_sales` has grain `store x date`; `mart_product_daily_sales` has grain `item x date`. They expose unit totals, price summaries, estimated sales value, and price coverage.

## Data quality

GOLD tests validate the 59,181,090-row demand grain, required business keys, non-negative units, SNAP domain, price semantics, aggregate-grain uniqueness, rollup reconciliation, and price coverage rates.

## Dataset

With `BQ_DBT_DATASET=retailops`, the default dbt schema naming creates `retailops_gold` for GOLD models.

## Run

STAGING and SILVER must already exist and pass their tests. Then run:

```bash
python scripts/run_dbt_gold.py
```

The command can process a large detailed mart and therefore may consume BigQuery query bytes and storage. Check the active Google Cloud billing/free-tier context before executing it.

## Scope boundary

GOLD is descriptive and consumption-oriented. Forecasting labels, lags, rolling statistics, predictions, simulated inventory, and stockout-risk features begin in V2.
