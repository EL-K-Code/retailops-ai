$ErrorActionPreference = "Stop"

Write-Host "== RetailOps AI: validation checks =="

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is not installed or not available in PATH."
}

Write-Host "Python version:"
uv run python --version

Write-Host "Running Ruff..."
uv run ruff check .

Write-Host "Running pytest..."
uv run pytest -q

Write-Host "All validation checks passed."
