#!/usr/bin/env bash
set -euo pipefail

echo "== RetailOps AI: bootstrap development environment =="

if ! command -v uv >/dev/null 2>&1; then
  echo "Error: uv is not installed or not available in PATH." >&2
  echo "Install uv, then rerun this script." >&2
  exit 1
fi

echo "Resolving the Python 3.12 environment and project dependencies..."
uv sync --python 3.12

echo "Environment ready. Running validation checks..."
"$(dirname "$0")/check.sh"

echo "Bootstrap completed successfully."
