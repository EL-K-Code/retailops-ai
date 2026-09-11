#!/usr/bin/env python
"""Download, extract, and validate the M5 source dataset."""

from __future__ import annotations

from zipfile import ZipFile

from _common import ROOT_DIR, require_command, run, run_python_script

COMPETITION = "m5-forecasting-accuracy"


def main() -> None:
    require_command("uv")
    require_command("uvx")

    destination = ROOT_DIR / "data" / "raw" / "m5"
    archive = destination / f"{COMPETITION}.zip"
    destination.mkdir(parents=True, exist_ok=True)

    print("Downloading M5 from Kaggle...")
    print("Kaggle authentication and competition-rule acceptance are required.")
    run(
        [
            "uvx",
            "kaggle",
            "competitions",
            "download",
            "-c",
            COMPETITION,
            "-p",
            str(destination),
            "--force",
        ]
    )

    if not archive.is_file():
        raise SystemExit(f"Error: expected archive was not created at {archive}.")

    print("Extracting source files...")
    with ZipFile(archive) as zip_file:
        zip_file.extractall(destination)

    print("Validating source contract...")
    run_python_script("validate_m5.py")

    print("M5 source acquisition completed successfully.")


if __name__ == "__main__":
    main()
