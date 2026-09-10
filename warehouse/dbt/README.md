# dbt warehouse

RetailOps AI uses dbt Core with the BigQuery adapter for warehouse transformations.

Current transformation flow:

```text
BigQuery RAW -> STAGING -> SILVER -> GOLD / MARTS
```

## STAGING

V1.5 implements:

- `stg_calendar`: source-conformed calendar view;
- `stg_sell_prices`: source-conformed weekly price view;
- `stg_sales`: long-format daily sales table produced from the wide M5 `d_1 ... d_1941` columns.

`stg_sales` is materialized as a BigQuery table partitioned by `date` and clustered by `store_id, item_id`.

## SILVER

V1.6 implements the reusable analytical warehouse model:

- `dim_date`;
- `dim_product`;
- `dim_store`;
- `fact_sales_daily`;
- `fact_prices_weekly`.

`fact_sales_daily` is a view over the already partitioned staging table to avoid duplicating roughly 59 million rows. `fact_prices_weekly` is a partitioned and clustered BigQuery table.

## Run

From the repository root:

```bash
./scripts/run_dbt_staging.sh
./scripts/run_dbt_silver.sh
```

The committed `profiles.yml` contains no credentials. It uses BigQuery OAuth/Application Default Credentials and environment variables.
