#!/usr/bin/env python
"""Upload validated M5 source files to the immutable GCS landing zone."""

from __future__ import annotations

import os

from _common import ROOT_DIR, load_env, require_env, run_python_module, run_python_script


def main() -> None:
    load_env()
    values = require_env(("GCS_BUCKET",))
    data_dir = ROOT_DIR / "data" / "raw" / "m5"
    prefix = os.getenv("GCS_LANDING_PREFIX", "landing/m5/v1")

    print("Validating the M5 source contract before cloud upload...")
    run_python_script("profile_m5.py")

    args = [
        "--data-dir",
        str(data_dir),
        "--bucket",
        values["GCS_BUCKET"],
        "--prefix",
        prefix,
    ]
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if project:
        args.extend(["--project", project])

    print("Uploading M5 source files to immutable GCS landing...")
    run_python_module("retailops_ai.ingestion.gcs_landing", *args)


if __name__ == "__main__":
    main()
