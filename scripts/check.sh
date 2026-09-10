#!/usr/bin/env bash
set -euo pipefail

echo "== RetailOps AI: validation checks =="

if ! command -v uv >/dev/null 2>&1; then
  echo "Error: uv is not installed or not available in PATH." >&2
  exit 1
fi

echo "Python version:"
uv run python --version

echo "Running Ruff..."
uv run ruff check .

echo "Running pytest..."
uv run pytest -q

echo "All validation checks passed."
