"""Shared orchestration helpers for repository scripts."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DBT_DIR = ROOT_DIR / "warehouse" / "dbt"


def load_env(path: Path | None = None) -> None:
    """Load the repository .env file into the current process if it exists."""
    env_path = path or ROOT_DIR / ".env"
    if not env_path.exists():
        return

    lines = env_path.read_text(encoding="utf-8").splitlines()
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").lstrip()

        key, separator, value = line.partition("=")
        if not separator:
            raise RuntimeError(f"Invalid .env entry at {env_path}:{line_number}")

        key = key.strip()
        value = value.strip()
        if not key:
            raise RuntimeError(f"Empty .env key at {env_path}:{line_number}")

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        os.environ[key] = value


def require_command(command: str) -> str:
    """Return the executable path or fail with a readable message."""
    executable = shutil.which(command)
    if executable is None:
        raise SystemExit(f"Error: {command} is not installed or not available in PATH.")
    return executable


def require_env(names: Sequence[str]) -> dict[str, str]:
    """Return required environment values or fail before starting cloud work."""
    values: dict[str, str] = {}
    missing: list[str] = []
    for name in names:
        value = os.getenv(name)
        if value:
            values[name] = value
        else:
            missing.append(name)

    if missing:
        joined = ", ".join(missing)
        raise SystemExit(f"Error: missing required environment variable(s): {joined}.")
    return values


def run(command: Sequence[str], *, cwd: Path = ROOT_DIR) -> None:
    """Run one subprocess and fail immediately on a non-zero exit code."""
    rendered = shlex.join(str(part) for part in command)
    print(f"$ {rendered}", flush=True)
    subprocess.run([str(part) for part in command], cwd=cwd, check=True)


def run_uv(*args: str) -> None:
    """Run a command inside the uv-managed project environment."""
    require_command("uv")
    run(["uv", "run", *args])


def run_python_script(script_name: str, *args: str) -> None:
    """Run another repository Python script in the uv environment."""
    run_uv("python", str(ROOT_DIR / "scripts" / script_name), *args)


def run_python_module(module: str, *args: str) -> None:
    """Run a project module in the uv environment."""
    run_uv("python", "-m", module, *args)


def prepare_dbt_environment() -> None:
    """Load local configuration and validate the dbt/GCP prerequisites."""
    load_env()
    require_command("uv")
    require_env(("GOOGLE_CLOUD_PROJECT", "BQ_LOCATION", "BQ_RAW_DATASET", "BQ_DBT_DATASET"))


def run_dbt(command: str, *args: str) -> None:
    """Run dbt against the repository project/profile directories."""
    run_uv(
        "dbt",
        command,
        "--project-dir",
        str(DBT_DIR),
        "--profiles-dir",
        str(DBT_DIR),
        *args,
    )
