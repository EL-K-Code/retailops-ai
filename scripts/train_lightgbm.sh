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

required_vars=(GOOGLE_CLOUD_PROJECT BQ_LOCATION BQ_DBT_DATASET)
for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "Error: ${var_name} is required. Set it in .env or export it." >&2
    exit 1
  fi
done

echo "== RetailOps AI: LightGBM global demand model =="
echo "Training lookback: ${ML_TRAIN_LOOKBACK_DAYS:-180} days"
echo "BigQuery Storage API: ${ML_USE_BQ_STORAGE_API:-false}"
echo "Persist outputs to BigQuery: ${ML_WRITE_BIGQUERY:-false}"
echo
echo "This command reads BigQuery data and can incur query/network charges."

uv run python "${ROOT_DIR}/scripts/train_lightgbm.py" "$@"
