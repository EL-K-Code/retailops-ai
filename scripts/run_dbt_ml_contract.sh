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

echo "Building the leakage-aware ML dataset contract..."
uv run dbt build \
  --project-dir "${DBT_DIR}" \
  --profiles-dir "${DBT_DIR}" \
  --select ml_demand_split \
  --fail-fast

echo "Validating temporal split counts and boundaries..."
uv run dbt test \
  --project-dir "${DBT_DIR}" \
  --profiles-dir "${DBT_DIR}" \
  --select ml_split_boundaries ml_split_row_counts \
  --fail-fast

echo "ML dataset contract validation completed successfully."
