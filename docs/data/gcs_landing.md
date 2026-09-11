# GCS immutable landing zone

V1.3 introduces Google Cloud Storage as the durable landing layer for the original M5 source files.

## Purpose

The landing zone preserves the source files before warehouse transformation. This gives RetailOps AI a replayable and auditable boundary between the external dataset and BigQuery.

The object layout is:

```text
gs://<bucket>/landing/m5/v1/
├── calendar.csv
├── sell_prices.csv
└── sales_train_evaluation.csv
```

The files are uploaded unchanged. No business transformation is performed in GCS.

## Immutability and idempotence

Each local file is hashed with SHA-256 before upload.

For an object that already exists:

- the same stored `source_sha256` means the upload is skipped;
- a different or missing `source_sha256` causes the run to fail;
- existing objects are never silently overwritten.

For a new object, the uploader uses the GCS generation precondition `if_generation_match=0`. This means the server accepts the upload only if no live object already exists at that path.

Each uploaded object receives metadata:

```text
source_dataset
source_file
source_sha256
source_contract_version
```

This is enough to trace the source artifact without changing its bytes.

## Authentication

RetailOps AI uses Google Application Default Credentials (ADC), not a service-account key committed to the repository.

For local development:

```bash
gcloud auth application-default login
```

The application can then create a Cloud Storage client without embedding credentials in code.

## Local configuration

Copy the template once:

```bash
cp .env.example .env
```

Set at least:

```text
GOOGLE_CLOUD_PROJECT=your-project-id
GCS_BUCKET=your-globally-unique-bucket-name
GCS_LOCATION=us-central1
GCS_LANDING_PREFIX=landing/m5/v1
```

The `.env` file is ignored by Git.

## Bucket creation

Bucket creation is intentionally not automated at this milestone. It is a cloud-side operation and can incur charges.

For the portfolio environment, the recommended configuration is a Standard bucket in `us-central1` with uniform bucket-level access:

```bash
gcloud storage buckets create "gs://${GCS_BUCKET}" \
  --project="${GOOGLE_CLOUD_PROJECT}" \
  --location="${GCS_LOCATION}" \
  --default-storage-class=STANDARD \
  --uniform-bucket-level-access
```

Bucket names are globally unique. Choose a name that belongs to your project rather than copying the example literally.

## Upload

After the bucket exists and ADC is configured:

```bash
python scripts/upload_m5_to_gcs.py
```

The script re-runs the M5 structural profiler before any cloud upload, then uploads or safely skips each source file.

A second successful run should report `SKIPPED` for all three objects. That second run is the practical idempotence test.

## Scope boundary

V1.3 ends at immutable object storage. BigQuery tables, schema loading, SQL transformations, dbt models, partitioning, and clustering belong to the next milestones.
