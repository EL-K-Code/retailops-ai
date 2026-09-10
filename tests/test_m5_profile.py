"""Tests for M5 structural profiling."""

from pathlib import Path

from retailops_ai.ingestion.m5_profile import (
    CALENDAR_COLUMNS,
    SALES_COLUMNS,
    SELL_PRICES_COLUMNS,
    profile_csv,
)


def _write_csv(path: Path, header: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    content = [",".join(header), *( ",".join(row) for row in rows )]
    path.write_text("\n".join(content) + "\n", encoding="utf-8")


def test_expected_m5_schema_widths() -> None:
    assert len(CALENDAR_COLUMNS) == 14
    assert len(SELL_PRICES_COLUMNS) == 4
    assert len(SALES_COLUMNS) == 1947
    assert SALES_COLUMNS[:6] == (
        "id",
        "item_id",
        "dept_id",
        "cat_id",
        "store_id",
        "state_id",
    )
    assert SALES_COLUMNS[-1] == "d_1941"


def test_profile_csv_accepts_valid_structure(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    header = ("id", "value")
    _write_csv(path, header, [("1", "10"), ("2", "20")])

    profile = profile_csv(path, expected_columns=header, expected_rows=2)

    assert profile.valid
    assert profile.row_count == 2
    assert profile.column_count == 2
    assert profile.malformed_row_count == 0


def test_profile_csv_rejects_wrong_header_and_row_width(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    path.write_text("wrong,value\n1,10\n2\n", encoding="utf-8")

    profile = profile_csv(path, expected_columns=("id", "value"), expected_rows=2)

    assert not profile.valid
    assert not profile.schema_valid
    assert profile.malformed_row_count == 1
