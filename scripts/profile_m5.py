#!/usr/bin/env python
"""Profile the local M5 dataset and persist the JSON report."""

from __future__ import annotations

from _common import ROOT_DIR, run_python_module


def main() -> None:
    data_dir = ROOT_DIR / "data" / "raw" / "m5"
    report_path = ROOT_DIR / "data" / "reports" / "m5_profile.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    run_python_module(
        "retailops_ai.ingestion.m5_profile",
        str(data_dir),
        str(report_path),
    )


if __name__ == "__main__":
    main()
