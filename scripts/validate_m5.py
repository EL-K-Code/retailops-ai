#!/usr/bin/env python
"""Validate the local M5 source contract."""

from __future__ import annotations

from _common import ROOT_DIR, run_python_module


def main() -> None:
    data_dir = ROOT_DIR / "data" / "raw" / "m5"
    run_python_module("retailops_ai.ingestion.m5_profile", str(data_dir))


if __name__ == "__main__":
    main()
