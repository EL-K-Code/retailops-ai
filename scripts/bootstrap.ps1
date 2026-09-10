$ErrorActionPreference = "Stop"

Write-Host "== RetailOps AI: bootstrap development environment =="

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is not installed or not available in PATH. Install uv before running this script."
}

Write-Host "Resolving the Python 3.12 environment and project dependencies..."
uv sync --python 3.12

Write-Host "Environment ready. Running validation checks..."
& "$PSScriptRoot\check.ps1"

Write-Host "Bootstrap completed successfully."
