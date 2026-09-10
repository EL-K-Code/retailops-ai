"""Source contract validation for the M5 retail dataset."""

from __future__ import annotations

import sys
from pathlib import Path

EXPECTED_M5_FILES = (
    "calendar.csv",
    "sell_prices.csv",
    "sales_train_evaluation.csv",
)


def validate_m5_source_dir(data_dir: Path) -> list[str]:
    """Return validation errors for the expected M5 source files."""
    errors: list[str] = []

    if not data_dir.exists():
        return [f"Data directory does not exist: {data_dir}"]

    if not data_dir.is_dir():
        return [f"Expected a directory, got: {data_dir}"]

    for filename in EXPECTED_M5_FILES:
        path = data_dir / filename
        if not path.exists():
            errors.append(f"Missing required file: {filename}")
            continue
        if not path.is_file():
            errors.append(f"Expected a file: {filename}")
            continue
        if path.stat().st_size == 0:
            errors.append(f"Required file is empty: {filename}")

    return errors


def main(argv: list[str] | None = None) -> int:
    """Validate the M5 source directory from the command line."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("Usage: python -m retailops_ai.ingestion.m5 <data-directory>", file=sys.stderr)
        return 2

    data_dir = Path(args[0])
    errors = validate_m5_source_dir(data_dir)

    if errors:
        print("M5 source validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"M5 source validation passed: {data_dir}")
    for filename in EXPECTED_M5_FILES:
        print(f"- {filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
