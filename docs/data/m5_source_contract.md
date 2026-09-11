# M5 source contract — V1

RetailOps AI treats the downloaded M5 CSV files as immutable source data. Before cloud ingestion, the files must satisfy a structural contract.

## Required files

| File | Expected rows | Expected columns | Grain |
| --- | ---: | ---: | --- |
| `calendar.csv` | 1,969 | 14 | one row per M5 day |
| `sell_prices.csv` | 6,841,121 | 4 | store × item × Walmart week |
| `sales_train_evaluation.csv` | 30,490 | 1,947 | one item-store time series |

## Expected headers

### `calendar.csv`

```text
date, wm_yr_wk, weekday, wday, month, year, d,
event_name_1, event_type_1, event_name_2, event_type_2,
snap_CA, snap_TX, snap_WI
```

### `sell_prices.csv`

```text
store_id, item_id, wm_yr_wk, sell_price
```

### `sales_train_evaluation.csv`

The first six columns are:

```text
id, item_id, dept_id, cat_id, store_id, state_id
```

They are followed by 1,941 daily sales columns:

```text
d_1, d_2, ..., d_1941
```

## Why validate before ingestion?

A file being present does not mean it is safe to ingest. A truncated download, an unexpected competition file, a changed header, or malformed rows could otherwise enter the warehouse and fail much later during transformation.

V1.2 therefore checks the boundary between the external source and RetailOps AI before GCS or BigQuery are introduced.

## Run the profiler

```bash
python scripts/profile_m5.py
```

The command streams the CSV files rather than loading the full dataset into memory. It validates:

- exact header order;
- row count;
- column count;
- malformed row widths;
- file size metadata.

A machine-readable report is written locally to:

```text
data/reports/m5_profile.json
```

The report is intentionally Git-ignored because it describes a local dataset copy.

## Scope boundary

This milestone validates source structure only. Data-type normalization, long-format conversion, business rules, null handling, and warehouse transformations are deliberately deferred to the following ingestion/dbt milestones.
