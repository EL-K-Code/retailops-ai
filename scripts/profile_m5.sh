#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${ROOT_DIR}/data/raw/m5"
REPORT_PATH="${ROOT_DIR}/data/reports/m5_profile.json"

uv run python -m retailops_ai.ingestion.m5_profile "${DATA_DIR}" "${REPORT_PATH}"
