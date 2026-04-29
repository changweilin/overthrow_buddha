param(
    [string]$TaskName = "Drone OSINT Daily Crawl",
    [string]$DailyTime = "06:30",
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$PipelineScript = Resolve-Path (Join-Path $PSScriptRoot "run_daily_pipeline.ps1")
$PowerShell = (Get-Command powershell.exe).Source

$ArgumentParts = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$PipelineScript`""
)
if ($PythonPath) {
    $ArgumentParts += @("-PythonPath", "`"$PythonPath`"")
}

$Action = New-ScheduledTaskAction `
    -Execute $PowerShell `
    -Argument ($ArgumentParts -join " ") `
    -WorkingDirectory $RepoRoot
$Trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::ParseExact($DailyTime, "HH:mm", $null))
$Settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Daily public OSINT crawl, summary generation, and archive index build." `
    -Force | Out-Null

Write-Host "Registered scheduled task '$TaskName' at $DailyTime."
Write-Host "Pipeline: $PipelineScript"

