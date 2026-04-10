[CmdletBinding()]
param(
    [string]$TaskName = "BlogWriterBlogDashboardBackendBoot"
)

$ErrorActionPreference = "Stop"

schtasks.exe /Delete /TN $TaskName /F | Out-Null
Write-Output "Unregistered boot task: $TaskName"
