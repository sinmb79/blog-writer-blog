[CmdletBinding()]
param(
    [string]$TaskName = "BlogWriterBlogDashboardBackend",
    [string]$StartupEntryName = "BlogWriterBlogDashboardBackend.cmd",
    [switch]$RunNow
)

$ErrorActionPreference = "Stop"

$scriptPath = (Resolve-Path (Join-Path $PSScriptRoot "start_dashboard_backend.ps1")).Path
$powershellPath = (Get-Command powershell.exe).Source
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$startupDir = Join-Path $env:APPDATA "Microsoft\\Windows\\Start Menu\\Programs\\Startup"
$startupEntryPath = Join-Path $startupDir $StartupEntryName

$action = New-ScheduledTaskAction `
    -Execute $powershellPath `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $currentUser
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Highest

try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -ErrorAction Stop `
        -Force | Out-Null

    Write-Output "Registered scheduled task: $TaskName"
} catch {
    $launcher = @(
        "@echo off",
        "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
    )

    New-Item -ItemType Directory -Force -Path $startupDir | Out-Null
    Set-Content -Path $startupEntryPath -Value $launcher -Encoding ASCII
    Write-Warning "Scheduled Task registration failed. Falling back to Startup folder entry."
    Write-Output "Registered startup entry: $startupEntryPath"
}

if ($RunNow) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Start-ScheduledTask -TaskName $TaskName
        Write-Output "Started scheduled task: $TaskName"
    } else {
        & $scriptPath
    }
}
