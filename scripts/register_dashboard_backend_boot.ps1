[CmdletBinding()]
param(
    [string]$TaskName = "BlogWriterBlogDashboardBackendBoot"
)

$ErrorActionPreference = "Stop"

$scriptPath = (Resolve-Path (Join-Path $PSScriptRoot "start_dashboard_backend.ps1")).Path
$powershellPath = (Get-Command powershell.exe).Source

$taskCommand = "`"$powershellPath`" -NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

schtasks.exe /Create `
    /TN $TaskName `
    /TR $taskCommand `
    /SC ONSTART `
    /RU SYSTEM `
    /RL HIGHEST `
    /F | Out-Null

Write-Output "Registered boot task: $TaskName"
