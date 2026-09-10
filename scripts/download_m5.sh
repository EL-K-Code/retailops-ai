#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_DIR="${ROOT_DIR}/data/raw/m5"
COMPETITION="m5-forecasting-accuracy"
ARCHIVE="${DEST_DIR}/${COMPETITION}.zip"

if ! command -v uv >/dev/null 2>&1; then
  echo "Error: uv is not installed or not available in PATH." >&2
  exit 1
fi

mkdir -p "${DEST_DIR}"

echo "Downloading M5 from Kaggle..."
echo "Kaggle authentication and competition-rule acceptance are required."
uvx kaggle competitions download -c "${COMPETITION}" -p "${DEST_DIR}" --force

if [[ ! -f "${ARCHIVE}" ]]; then
  echo "Error: expected archive was not created at ${ARCHIVE}." >&2
  exit 1
fi

echo "Extracting source files..."
uv run python -m zipfile -e "${ARCHIVE}" "${DEST_DIR}"

echo "Validating source contract..."
"${ROOT_DIR}/scripts/validate_m5.sh"

echo "M5 source acquisition completed successfully."
