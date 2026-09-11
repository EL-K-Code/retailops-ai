#!/usr/bin/env python
"""Bootstrap the RetailOps AI development environment."""

from __future__ import annotations

from _common import ROOT_DIR, require_command, run


def main() -> None:
    require_command("uv")

    print("== RetailOps AI: bootstrap development environment ==")
    print("Resolving the Python 3.12 environment and project dependencies...")
    run(["uv", "sync", "--python", "3.12"])

    print("Environment ready. Running validation checks...")
    run(["uv", "run", "python", str(ROOT_DIR / "scripts" / "check.py")])

    print("Bootstrap completed successfully.")


if __name__ == "__main__":
    main()
