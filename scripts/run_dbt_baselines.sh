#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DBT_DIR="${ROOT_DIR}/warehouse/dbt"

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

required_vars=(GOOGLE_CLOUD_PROJECT BQ_LOCATION BQ_RAW_DATASET BQ_DBT_DATASET)
for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "Error: ${var_name} is required. Set it in .env or export it." >&2
    exit 1
  fi
done

echo "Checking dbt/BigQuery connectivity..."
uv run dbt debug --project-dir "${DBT_DIR}" --profiles-dir "${DBT_DIR}"

echo "Building leakage-safe validation baselines..."
uv run dbt build \
  --project-dir "${DBT_DIR}" \
  --profiles-dir "${DBT_DIR}" \
  --select path:models/ml/baselines \
  --fail-fast

echo "Running baseline integrity tests..."
uv run dbt test \
  --project-dir "${DBT_DIR}" \
  --profiles-dir "${DBT_DIR}" \
  --select tag:baseline \
  --fail-fast

echo "Baseline evaluation completed. Inspect retailops_ml.ml_baseline_metrics for scores."
