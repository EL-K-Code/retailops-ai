# dbt GOLD / marts layer

V1.7 introduces business-consumption marts on top of the reusable SILVER warehouse model.

## Purpose

SILVER provides reusable facts and dimensions.

GOLD answers concrete consumption questions and exposes stable datasets for analytics and the later ML milestone.

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

The mart joins daily unit sales with:

- product category and department;
- store state;
- calendar week and weekend flag;
- both M5 event slots;
- the state-specific SNAP indicator;
- the weekly M5 sell price when available.

The source contains two possible event slots per date. GOLD preserves both instead of collapsing them into a single event and silently losing information.

The mart also exposes:

```text
price_available
estimated_sales_value = units_sold x sell_price
```

`estimated_sales_value` is deliberately named as an estimate. It is derived from observed unit sales and the M5 weekly sell price; it is not claimed to be transaction-level realized revenue. When no price is available, the value remains null rather than being forced to zero.

Because this is the main analytics and ML-ready consumption contract, it is materialized as a BigQuery table partitioned by `date` and clustered by `store_id, item_id`. The physical copy is intentional here: unlike the SILVER view, GOLD adds several joins and derived business fields that would otherwise be recomputed by every downstream consumer.

## `mart_store_daily_sales`

Grain:

```text
store x date
```

Metrics include:

- total units sold;
- number of items with positive unit sales;
- average available sell price;
- estimated sales value;
- price coverage rate.

## `mart_product_daily_sales`

Grain:

```text
item x date
```

Metrics include:

- total units sold across stores;
- number of stores with positive unit sales;
- average available sell price;
- estimated sales value;
- price coverage rate.

## Data quality

GOLD tests validate the properties introduced by this layer:

- `mart_demand_daily` keeps the expected 59,181,090-row demand grain;
- required business keys and attributes are populated;
- units remain non-negative;
- SNAP is always 0 or 1 for the represented states;
- available prices are positive;
- `price_available` agrees with `sell_price`;
- derived estimated sales value agrees with `units_sold x sell_price`;
- store-day and item-day aggregate grains are unique;
- unit and estimated-value totals reconcile across the detailed, store, and product marts;
- price coverage rates stay between 0 and 1.

## Dataset

With:

```text
BQ_DBT_DATASET=retailops
```

the default dbt schema naming creates:

```text
retailops_gold
```

for GOLD models.

## Run

STAGING and SILVER must already exist and pass their tests.

Then run:

```bash
chmod +x scripts/run_dbt_gold.sh
./scripts/run_dbt_gold.sh
```

The command can process a large detailed mart and therefore may consume BigQuery query bytes and storage. Check the active Google Cloud billing/free-tier context before executing it.

## Scope boundary

GOLD is still descriptive and consumption-oriented. It does **not** create forecasting labels, lags, rolling statistics, model predictions, simulated inventory, stockout risk, or other ML features.

Those transformations begin in V2.
