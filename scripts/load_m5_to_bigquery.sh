#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v uv >/dev/null 2>&1; then
  echo "Error: uv is not installed or not available in PATH." >&2
  exit 1
fi

if [[ -f "${ROOT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env"
  set +a
fi

required_vars=(GOOGLE_CLOUD_PROJECT GCS_BUCKET BQ_LOCATION BQ_RAW_DATASET)
for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "Error: ${var_name} is required. Set it in .env or export it." >&2
    exit 1
  fi
done

PREFIX="${GCS_LANDING_PREFIX:-landing/m5/v1}"

echo "Loading immutable M5 landing files into BigQuery RAW..."
uv run python -m retailops_ai.ingestion.bigquery_raw \
  --project "${GOOGLE_CLOUD_PROJECT}" \
  --dataset "${BQ_RAW_DATASET}" \
  --location "${BQ_LOCATION}" \
  --bucket "${GCS_BUCKET}" \
  --prefix "${PREFIX}"
