[CmdletBinding()]
param(
    [string]$BackendHost = "127.0.0.1",
    [int]$Port = 8080,
    [int]$StartupTimeoutSeconds = 20
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonPath = Join-Path $projectRoot "venv\Scripts\python.exe"
$logsDir = Join-Path $projectRoot "logs"
$stdoutLog = Join-Path $logsDir "dashboard_backend.out.log"
$stderrLog = Join-Path $logsDir "dashboard_backend.err.log"

function Test-BackendHealth {
    param(
        [string]$ProbeHost,
        [int]$ProbePort
    )

    try {
        $response = Invoke-RestMethod -Uri "http://$ProbeHost`:$ProbePort/api/health" -Method Get -TimeoutSec 3
        return $response.status -eq "ok" -and $response.service -eq "blog-writer-blog"
    } catch {
        return $false
    }
}

if (Test-BackendHealth -ProbeHost $BackendHost -ProbePort $Port) {
    Write-Output "blog-writer-blog backend is already healthy on $BackendHost`:$Port"
    exit 0
}

if (-not (Test-Path $pythonPath)) {
    throw "Python venv not found: $pythonPath"
}

New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$existingProcess = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object {
        $_.ExecutablePath -eq $pythonPath -and
        $_.CommandLine -like "*dashboard.backend.server:app*"
    } |
    Select-Object -First 1

if (-not $existingProcess) {
    $arguments = @(
        "-m",
        "uvicorn",
        "dashboard.backend.server:app",
        "--host",
        "0.0.0.0",
        "--port",
        $Port.ToString()
    )

    Start-Process `
        -FilePath $pythonPath `
        -ArgumentList $arguments `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog | Out-Null
}

$deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
while ((Get-Date) -lt $deadline) {
    if (Test-BackendHealth -ProbeHost $BackendHost -ProbePort $Port) {
        Write-Output "blog-writer-blog backend is healthy on $BackendHost`:$Port"
        exit 0
    }

    Start-Sleep -Seconds 1
}

throw "blog-writer-blog backend did not become healthy within $StartupTimeoutSeconds seconds. Check $stdoutLog and $stderrLog"
