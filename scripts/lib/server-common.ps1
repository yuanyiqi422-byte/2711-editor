# Shared helpers for 2711 Editor dev server (port 8010). Internal env NARRATIVE_ENGINE_ROOT unchanged.

function Get-ProjectRoot {
    if ($env:NARRATIVE_ENGINE_ROOT) {
        return $env:NARRATIVE_ENGINE_ROOT
    }
    # scripts/lib -> scripts -> project root
    return (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function Get-ServerPort {
    return 8010
}

function Get-ServerUrl {
    return "http://127.0.0.1:$(Get-ServerPort)"
}

function Stop-NarrativeUvicornProcesses {
    $killed = @()
    $port = Get-ServerPort
    $patterns = @("uvicorn", "main:app", ":$port")

    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | ForEach-Object {
        $cmd = $_.CommandLine
        if (-not $cmd) { return }
        $isTarget = $false
        foreach ($pat in $patterns) {
            if ($cmd -like "*$pat*") { $isTarget = $true; break }
        }
        if (-not $isTarget) { return }
        if ($_.ProcessId -notin $killed) {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            $killed += $_.ProcessId
        }
    }
    return $killed
}

function Stop-ServerOnPort {
    param([int]$Port = (Get-ServerPort))

    $killedTotal = 0
    for ($round = 0; $round -lt 5; $round++) {
        $killed = @()
        $zombies = Stop-NarrativeUvicornProcesses
        foreach ($procId in $zombies) {
            if ($procId -notin $killed) { $killed += $procId }
        }

        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        foreach ($conn in $connections) {
            $processId = $conn.OwningProcess
            if ($processId -and $processId -notin $killed) {
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                $killed += $processId
            }
        }

        $killedTotal += $killed.Count
        if ($killed.Count -gt 0) {
            Start-Sleep -Milliseconds 800
        }

        $still = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if (-not $still) {
            break
        }
    }
    return $killedTotal
}

function Get-UvicornArgs {
    return @(
        "-m", "uvicorn", "main:app",
        "--host", "127.0.0.1",
        "--port", "$(Get-ServerPort)",
        "--reload",
        "--reload-dir", ".",
        "--reload-include", ".env"
    )
}

function Start-NarrativeServer {
    param(
        [ValidateSet("Minimized", "Normal", "Hidden")]
        [string]$WindowStyle = "Minimized",
        [switch]$PassThru
    )

    $root = Get-ProjectRoot
    $backend = Join-Path $root "backend"
    if (-not (Test-Path (Join-Path $backend ".env"))) {
        throw "backend\.env missing; copy .env.example and set AI_API_KEY"
    }

    $proc = Start-Process -FilePath (Get-PythonExe) `
        -ArgumentList (Get-UvicornArgs) `
        -WorkingDirectory $backend `
        -WindowStyle $WindowStyle `
        -PassThru

    if ($PassThru) {
        return $proc
    }
}

function Test-ServerHealth {
    param(
        [int]$TimeoutSeconds = 30
    )

    $url = "$(Get-ServerUrl)/api/health"
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
            if ($resp.StatusCode -eq 200) {
                return $true
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    return $false
}

function Get-PythonExe {
    $root = Get-ProjectRoot
    $venvPy = Join-Path $root ".venv\Scripts\python.exe"
    if (Test-Path $venvPy) { return $venvPy }
    return "python"
}

function Install-BackendDeps {
    $backend = Join-Path (Get-ProjectRoot) "backend"
    $py = Get-PythonExe
    Push-Location $backend
    try {
        $prev = $ErrorActionPreference
        $ErrorActionPreference = "SilentlyContinue"
        & $py -m pip install -r requirements.txt -q 2>&1 | Out-Null
        $ErrorActionPreference = $prev
    } finally {
        Pop-Location
    }
}
