# BigQuery RAW layer

V1.4 introduces BigQuery as the first warehouse layer after the immutable GCS landing zone.

## Data flow

```text
GCS landing/m5/v1/
    |
    +-- calendar.csv -----------------> retailops_raw.raw_calendar
    +-- sell_prices.csv --------------> retailops_raw.raw_sell_prices
    +-- sales_train_evaluation.csv ---> retailops_raw.raw_sales
```

The RAW layer remains intentionally close to the source. No business joins, feature engineering,
long-format conversion, or analytical aggregations are performed here.

## Explicit schemas

RetailOps AI does not use schema autodetection for these source tables.

`raw_calendar` uses typed calendar fields such as `DATE`, `INTEGER`, and `STRING`.

`raw_sell_prices` preserves store, item, Walmart week, and price. `sell_price` uses BigQuery
`NUMERIC` to avoid unnecessary floating-point approximation for source prices.

`raw_sales` keeps the original wide M5 representation:

```text
id, item_id, dept_id, cat_id, store_id, state_id, d_1, ..., d_1941
```

The long-format transformation is deliberately deferred to dbt staging.

## Idempotent rebuild strategy

The immutable source of truth is GCS. BigQuery RAW is reconstructible.

Each load therefore uses:

```text
WRITE_TRUNCATE
```

rather than `WRITE_APPEND`.

A rerun replaces the destination table instead of duplicating source rows. BigQuery applies the
write disposition atomically when an individual load job completes successfully.

After every load, RetailOps AI validates the resulting table row count against the M5 source
contract:

| Table | Expected rows |
| --- | ---: |
| `raw_calendar` | 1,969 |
| `raw_sell_prices` | 6,841,121 |
| `raw_sales` | 30,490 |

A mismatch fails the command.

## Location

Use the same single region for the portfolio GCS bucket and BigQuery dataset:

```text
us-central1
```

This keeps the storage and warehouse layers colocated.

BigQuery dataset locations cannot be changed in place. The loader therefore checks the existing
dataset location and fails if it differs from `BQ_LOCATION`.

## Authentication

The loader uses Google Application Default Credentials, the same local authentication mechanism as
the GCS uploader:

```bash
gcloud auth application-default login
```

No credential files belong in Git.

## Configuration

```bash
cp .env.example .env
```

Set:

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GCS_BUCKET=your-bucket
GCS_LANDING_PREFIX=landing/m5/v1
BQ_LOCATION=us-central1
BQ_RAW_DATASET=retailops_raw
```

## Run

After the GCS landing files exist:

```bash
chmod +x scripts/load_m5_to_bigquery.sh
./scripts/load_m5_to_bigquery.sh
```

A successful run should finish with the three validated table counts.

## Scope boundary

V1.4 only creates the RAW warehouse layer.

The following are intentionally deferred to dbt:

- sales unpivoting from `d_1 ... d_1941`;
- normalized dimensions and facts;
- joins between sales, prices, and calendar;
- business tests;
- analytics marts;
- ML-ready feature datasets.
