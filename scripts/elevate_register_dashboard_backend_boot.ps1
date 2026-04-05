[CmdletBinding()]
param(
    [string]$TaskName = "BlogWriterBlogDashboardBackendBoot"
)

$ErrorActionPreference = "Stop"

$scriptPath = (Resolve-Path (Join-Path $PSScriptRoot "register_dashboard_backend_boot.ps1")).Path
$powershellPath = (Get-Command powershell.exe).Source
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -TaskName `"$TaskName`""

Start-Process -FilePath $powershellPath -ArgumentList $arguments -Verb RunAs
Write-Output "Opened UAC prompt for boot task registration: $TaskName"
