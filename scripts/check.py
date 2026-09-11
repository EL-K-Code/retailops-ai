#!/usr/bin/env python
"""Run local static and unit-test validation."""

from __future__ import annotations

from _common import require_command, run


def main() -> None:
    require_command("uv")

    print("== RetailOps AI: validation checks ==")
    print("Python version:")
    run(["uv", "run", "python", "--version"])

    print("Running Ruff...")
    run(["uv", "run", "ruff", "check", "."])

    print("Running pytest...")
    run(["uv", "run", "pytest", "-q"])

    print("All validation checks passed.")


if __name__ == "__main__":
    main()
