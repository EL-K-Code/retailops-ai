# dbt STAGING layer

V1.5 introduces dbt Core as the transformation layer between BigQuery RAW and the future SILVER/GOLD warehouse models.

## Why dbt starts here

Python ingestion owns transport and source-boundary validation. BigQuery RAW preserves the original M5 structure. dbt now owns warehouse transformations, lineage, model documentation, and data tests.

## Models

### `stg_calendar`

A lightweight view over `raw_calendar`. The source column `d` is renamed to `day_key`. No business aggregation is performed.

### `stg_sell_prices`

A lightweight view over `raw_sell_prices`, keeping the source grain:

```text
store_id x item_id x wm_yr_wk
```

### `stg_sales`

The M5 source stores daily demand in 1,941 columns:

```text
d_1, d_2, ..., d_1941
```

`stg_sales` uses BigQuery `UNPIVOT` to convert those columns to rows and joins the M5 calendar only to map `day_key` to `date`.

The resulting grain is:

```text
item-store-series x date
```

Expected row count:

```text
30,490 x 1,941 = 59,181,090
```

The model is materialized as a BigQuery table and configured with:

```text
partition: date
cluster: store_id, item_id
```

This avoids repeatedly executing the large unpivot and prepares efficient date- and SKU/store-based access for later models.

## Tests

The staging build checks:

- RAW identifiers and calendar keys are present;
- calendar `date` and `day_key` are unique;
- price keys and values are non-null;
- sell prices are positive;
- `stg_sales` contains exactly 59,181,090 rows;
- required sales fields are non-null;
- units sold are non-negative.

## Dataset naming

The dbt target dataset defaults to `retailops`. The staging folder uses dbt's custom-schema naming, so the models are created in `retailops_staging`.

Configure the base name through:

```text
BQ_DBT_DATASET=retailops
```

## Authentication

The BigQuery profile uses `method: oauth`. No key file is committed. Local execution uses existing Google credentials/Application Default Credentials.

## Run

```bash
python scripts/run_dbt_staging.py
```

`dbt debug` runs first. The script stops immediately if connectivity or credentials are invalid.

## Scope boundary

V1.5 does not yet create business dimensions, facts, or marts. Those belong to the SILVER and GOLD milestones.
