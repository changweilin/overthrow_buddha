param(
    [string]$PythonPath = "",
    [switch]$NoDelay
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$LogDir = Join-Path $RepoRoot "crawler_project\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$PipelineLog = Join-Path $LogDir ("daily-pipeline-" + (Get-Date -Format "yyyyMMdd") + ".log")

function Resolve-Python {
    param([string]$RequestedPython)
    if ($RequestedPython -and (Test-Path $RequestedPython)) {
        return (Resolve-Path $RequestedPython).Path
    }
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        return "py"
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return $python.Source
    }
    throw "Python was not found. Pass -PythonPath with a full python.exe path."
}

$Python = Resolve-Python -RequestedPython $PythonPath
Set-Location $RepoRoot

function Invoke-Step {
    param([string]$Name, [string[]]$Args)
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$stamp] START $Name" | Tee-Object -FilePath $PipelineLog -Append
    if ($Python -eq "py") {
        & py @Args 2>&1 | Tee-Object -FilePath $PipelineLog -Append
    } else {
        & $Python @Args 2>&1 | Tee-Object -FilePath $PipelineLog -Append
    }
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$stamp] END $Name" | Tee-Object -FilePath $PipelineLog -Append
}

$CrawlerArgs = @("crawler_project\run_crawler.py")
if ($NoDelay) {
    $CrawlerArgs += "--no-delay"
}

Invoke-Step -Name "crawler" -Args $CrawlerArgs
Invoke-Step -Name "summaries" -Args @("analysis_project\generate_summaries.py")
Invoke-Step -Name "index" -Args @("analysis_project\build_index.py")

