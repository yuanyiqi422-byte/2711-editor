# Lightweight fallback watcher: ensures server is up, restarts on backend/.env changes
# when you are NOT already running uvicorn --reload (e.g. production-like run).
# Normal dev: just use start.bat or restart-server.ps1 — uvicorn --reload handles .py and .env.

param(
    [int]$DebounceMs = 800
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\lib\server-common.ps1"

$root = Get-ProjectRoot
$backend = Join-Path $root "backend"

if (-not (Test-ServerHealth -TimeoutSeconds 2)) {
    Write-Host '[dev-watch] server not running, starting...'
    & "$PSScriptRoot\restart-server.ps1"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host ('[dev-watch] watching ' + $backend + ' (.py / .env -> restart-server.ps1)')
Write-Host '[dev-watch] skip if start.bat --reload is already running'

$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $backend
$watcher.Filter = "*.*"
$watcher.IncludeSubdirectories = $false
$watcher.EnableRaisingEvents = $true

$script:pending = $false
$script:timer = $null

$onChange = {
    $ext = [System.IO.Path]::GetExtension($Event.SourceEventArgs.Name).ToLowerInvariant()
    if ($ext -notin @(".py", ".env")) { return }

    if ($script:timer) {
        $script:timer.Stop()
        $script:timer.Dispose()
    }

    $script:timer = New-Object System.Timers.Timer
    $script:timer.Interval = $DebounceMs
    $script:timer.AutoReset = $false
    Register-ObjectEvent -InputObject $script:timer -EventName Elapsed -Action {
        Write-Host '[dev-watch] change detected, restarting...'
        & "$using:PSScriptRoot\restart-server.ps1" -Quiet
    } | Out-Null
    $script:timer.Start()
}

Register-ObjectEvent -InputObject $watcher -EventName Changed -Action $onChange | Out-Null
Register-ObjectEvent -InputObject $watcher -EventName Created -Action $onChange | Out-Null
Register-ObjectEvent -InputObject $watcher -EventName Renamed -Action $onChange | Out-Null

try {
    while ($true) { Start-Sleep -Seconds 1 }
} finally {
    $watcher.EnableRaisingEvents = $false
    $watcher.Dispose()
}
