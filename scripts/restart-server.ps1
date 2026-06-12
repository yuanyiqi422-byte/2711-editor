# Idempotent restart: kill port 8010, start uvicorn --reload in background, wait for health.
# Agent usage: powershell -NoProfile -ExecutionPolicy Bypass -File scripts/restart-server.ps1

param(
    [switch]$Foreground,
    [switch]$SkipDeps,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\lib\server-common.ps1"

function Write-Info([string]$Message) {
    if (-not $Quiet) {
        Write-Host $Message
    }
}

$stopped = Stop-ServerOnPort
if ($stopped -gt 0) {
    Write-Info ('[restart] stopped ' + $stopped + ' process(es) on port 8010')
} else {
    Write-Info '[restart] port 8010 is free'
}

if (-not $SkipDeps) {
    Write-Info '[restart] checking dependencies...'
    Install-BackendDeps
}

$injectScript = Join-Path (Get-ProjectRoot) "scripts\inject-env-config.mjs"
if (Test-Path $injectScript) {
    Write-Info '[restart] resetting frontend env-config for local dev...'
    $prevNetlify = $env:NETLIFY
    $prevCfPages = $env:CF_PAGES
    $env:NETLIFY = $null
    $env:CF_PAGES = $null
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & node $injectScript 2>&1 | ForEach-Object { Write-Info $_ }
    } catch {
        Write-Info "[restart] env-config inject failed: $_"
    } finally {
        $ErrorActionPreference = $prevEap
        if ($null -ne $prevNetlify) { $env:NETLIFY = $prevNetlify } else { Remove-Item Env:NETLIFY -ErrorAction SilentlyContinue }
        if ($null -ne $prevCfPages) { $env:CF_PAGES = $prevCfPages } else { Remove-Item Env:CF_PAGES -ErrorAction SilentlyContinue }
    }
}

if ($Foreground) {
    Write-Info ('[restart] foreground ' + (Get-ServerUrl) + ' (Ctrl+C to stop)')
    $backend = Join-Path (Get-ProjectRoot) "backend"
    Push-Location $backend
    try {
        & (Get-PythonExe) @(Get-UvicornArgs)
    } finally {
        Pop-Location
    }
    exit $LASTEXITCODE
}

Write-Info '[restart] starting uvicorn --reload in background...'
Start-NarrativeServer -WindowStyle Minimized | Out-Null

Write-Info '[restart] waiting for /api/health...'
if (Test-ServerHealth -TimeoutSeconds 45) {
    Write-Info ('[restart] ready ' + (Get-ServerUrl))
    exit 0
}

Write-Error '[restart] health check timed out; check backend logs or backend\.env'
exit 1
