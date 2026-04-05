[CmdletBinding()]
param(
    [string]$TaskName = "BlogWriterBlogDashboardBackend",
    [string]$StartupEntryName = "BlogWriterBlogDashboardBackend.cmd"
)

$ErrorActionPreference = "Stop"
$startupDir = Join-Path $env:APPDATA "Microsoft\\Windows\\Start Menu\\Programs\\Startup"
$startupEntryPath = Join-Path $startupDir $StartupEntryName

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Output "Unregistered scheduled task: $TaskName"
} else {
    Write-Output "Scheduled task not found: $TaskName"
}

if (Test-Path $startupEntryPath) {
    Remove-Item -LiteralPath $startupEntryPath -Force
    Write-Output "Removed startup entry: $startupEntryPath"
} else {
    Write-Output "Startup entry not found: $startupEntryPath"
}
