"""Schema validation and lightweight profiling for the M5 source files."""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

CALENDAR_COLUMNS = (
    "date",
    "wm_yr_wk",
    "weekday",
    "wday",
    "month",
    "year",
    "event_name_1",
    "event_type_1",
    "event_name_2",
    "event_type_2",
    "snap_CA",
    "snap_TX",
    "snap_WI",
)

SELL_PRICES_COLUMNS = ("store_id", "item_id", "wm_yr_wk", "sell_price")

SALES_ID_COLUMNS = ("id", "item_id", "dept_id", "cat_id", "store_id", "state_id")
SALES_DAY_COLUMNS = tuple(f"d_{day}" for day in range(1, 1942))
SALES_COLUMNS = SALES_ID_COLUMNS + SALES_DAY_COLUMNS

EXPECTED_SCHEMAS = {
    "calendar.csv": CALENDAR_COLUMNS,
    "sell_prices.csv": SELL_PRICES_COLUMNS,
    "sales_train_evaluation.csv": SALES_COLUMNS,
}

EXPECTED_ROW_COUNTS = {
    "calendar.csv": 1969,
    "sell_prices.csv": 6_841_121,
    "sales_train_evaluation.csv": 30_490,
}


@dataclass(frozen=True)
class CsvProfile:
    """Structural profile for one CSV source file."""

    file_name: str
    size_bytes: int
    row_count: int
    column_count: int
    expected_row_count: int
    expected_column_count: int
    schema_valid: bool
    row_count_valid: bool
    malformed_row_count: int

    @property
    def valid(self) -> bool:
        """Return whether the file satisfies the structural source contract."""
        return self.schema_valid and self.row_count_valid and self.malformed_row_count == 0


def profile_csv(path: Path, expected_columns: tuple[str, ...], expected_rows: int) -> CsvProfile:
    """Stream a CSV file once and validate its header, row count, and row width."""
    row_count = 0
    malformed_row_count = 0

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = tuple(next(reader))
        except StopIteration:
            header = ()

        column_count = len(header)
        expected_width = len(expected_columns)

        for row in reader:
            row_count += 1
            if len(row) != expected_width:
                malformed_row_count += 1

    return CsvProfile(
        file_name=path.name,
        size_bytes=path.stat().st_size,
        row_count=row_count,
        column_count=column_count,
        expected_row_count=expected_rows,
        expected_column_count=len(expected_columns),
        schema_valid=header == expected_columns,
        row_count_valid=row_count == expected_rows,
        malformed_row_count=malformed_row_count,
    )


def profile_m5_source(data_dir: Path) -> dict[str, CsvProfile]:
    """Profile and structurally validate all M5 files required by RetailOps AI."""
    profiles: dict[str, CsvProfile] = {}

    for file_name, expected_columns in EXPECTED_SCHEMAS.items():
        path = data_dir / file_name
        if not path.is_file():
            raise FileNotFoundError(f"Missing required M5 source file: {path}")

        profiles[file_name] = profile_csv(
            path=path,
            expected_columns=expected_columns,
            expected_rows=EXPECTED_ROW_COUNTS[file_name],
        )

    return profiles


def _serialize_profiles(profiles: dict[str, CsvProfile]) -> dict[str, object]:
    files = {name: {**asdict(profile), "valid": profile.valid} for name, profile in profiles.items()}
    return {
        "dataset": "m5-forecasting-accuracy",
        "contract_version": 1,
        "valid": all(profile.valid for profile in profiles.values()),
        "files": files,
    }


def main(argv: list[str] | None = None) -> int:
    """Profile the local M5 dataset and optionally persist a JSON report."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) not in {1, 2}:
        print(
            "Usage: python -m retailops_ai.ingestion.m5_profile <data-directory> [output-json]",
            file=sys.stderr,
        )
        return 2

    data_dir = Path(args[0])

    try:
        profiles = profile_m5_source(data_dir)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    report = _serialize_profiles(profiles)
    rendered = json.dumps(report, indent=2)
    print(rendered)

    if len(args) == 2:
        output_path = Path(args[1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(f"{rendered}\n", encoding="utf-8")
        print(f"Profile written to: {output_path}")

    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
