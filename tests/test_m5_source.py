"""Tests for the M5 source contract."""

from pathlib import Path

from retailops_ai.ingestion.m5 import EXPECTED_M5_FILES, validate_m5_source_dir


def test_validate_m5_source_dir_accepts_expected_non_empty_files(tmp_path: Path) -> None:
    for filename in EXPECTED_M5_FILES:
        (tmp_path / filename).write_text("header\nvalue\n", encoding="utf-8")

    assert validate_m5_source_dir(tmp_path) == []


def test_validate_m5_source_dir_reports_missing_and_empty_files(tmp_path: Path) -> None:
    (tmp_path / "calendar.csv").write_text("date\n2020-01-01\n", encoding="utf-8")
    (tmp_path / "sell_prices.csv").touch()

    errors = validate_m5_source_dir(tmp_path)

    assert "Required file is empty: sell_prices.csv" in errors
    assert "Missing required file: sales_train_evaluation.csv" in errors
