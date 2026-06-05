# Idempotent full-stack smoke test — lint, validate, pytest (no server required).
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke-test.ps1

param([switch]$SkipLint)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\lib\server-common.ps1"

$root = Get-ProjectRoot
Push-Location $root

try {
    Write-Host "[smoke] 2711 Editor infrastructure smoke test`n"

    # 1. Python venv
    $venvPython = Join-Path $root ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        Write-Host "[smoke] creating .venv..."
        python -m venv .venv
    }

    Write-Host "[smoke] installing backend dev deps..."
    & $venvPython -m pip install -q -r backend/requirements-dev.txt

    # 2. Node deps
    if (-not (Test-Path (Join-Path $root "node_modules"))) {
        Write-Host "[smoke] npm install..."
        npm install --no-fund --no-audit 2>&1 | Out-Null
    }

    # 3. Frontend validate
    Write-Host "[smoke] npm run validate..."
    npm run validate
    if ($LASTEXITCODE -ne 0) { throw "frontend validate failed" }

    # 4. ESLint
    if (-not $SkipLint) {
        Write-Host "[smoke] npm run lint..."
        npm run lint
        if ($LASTEXITCODE -ne 0) { throw "eslint failed" }

        Write-Host "[smoke] npm run format:check..."
        npm run format:check
        if ($LASTEXITCODE -ne 0) { throw "prettier check failed" }
    }

    # 5. Ruff
    Write-Host "[smoke] ruff check (tests)..."
    & $venvPython -m ruff check backend/tests
    if ($LASTEXITCODE -ne 0) { throw "ruff failed" }

    # 6. Pytest
    Write-Host "[smoke] pytest..."
    $env:AI_API_KEY = "test-key-for-smoke"
    $env:AI_API_BASE = "https://api.example.com"
    $env:AI_MODEL = "test-model"
    & $venvPython -m pytest backend/tests -q --tb=short
    if ($LASTEXITCODE -ne 0) { throw "pytest failed" }

    Write-Host "`n[smoke] ALL PASSED — Ready to code."
    exit 0
} catch {
    Write-Error "[smoke] FAILED: $_"
    exit 1
} finally {
    Pop-Location
}
