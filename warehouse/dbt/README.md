# dbt warehouse

RetailOps AI uses dbt Core with the BigQuery adapter for warehouse transformations.

Current transformation flow:

```text
BigQuery RAW -> STAGING -> SILVER -> GOLD / MARTS
```

V1.5 implements the STAGING layer:

- `stg_calendar`: source-conformed calendar view;
- `stg_sell_prices`: source-conformed weekly price view;
- `stg_sales`: long-format daily sales table produced from the wide M5 `d_1 ... d_1941` columns.

`stg_sales` is materialized as a BigQuery table partitioned by `date` and clustered by
`store_id, item_id`. The source tables remain unchanged.

## Run

From the repository root:

```bash
./scripts/run_dbt_staging.sh
```

The script loads `.env`, checks the required variables, runs `dbt debug`, validates the RAW
sources, and then builds/tests the staging models.

The committed `profiles.yml` contains no credentials. It uses BigQuery OAuth/Application Default
Credentials and environment variables.
