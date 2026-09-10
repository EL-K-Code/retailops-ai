#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${ROOT_DIR}/data/raw/m5"

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

if [[ -z "${GCS_BUCKET:-}" ]]; then
  echo "Error: GCS_BUCKET is required. Set it in .env or export it in your shell." >&2
  exit 1
fi

PREFIX="${GCS_LANDING_PREFIX:-landing/m5/v1}"

echo "Validating the M5 source contract before cloud upload..."
"${ROOT_DIR}/scripts/profile_m5.sh"

ARGS=(
  --data-dir "${DATA_DIR}"
  --bucket "${GCS_BUCKET}"
  --prefix "${PREFIX}"
)

if [[ -n "${GOOGLE_CLOUD_PROJECT:-}" ]]; then
  ARGS+=(--project "${GOOGLE_CLOUD_PROJECT}")
fi

echo "Uploading M5 source files to immutable GCS landing..."
uv run python -m retailops_ai.ingestion.gcs_landing "${ARGS[@]}"
