[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding

$webRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$venvPython = Join-Path $webRoot ".venv\Scripts\python.exe"
$env:PIP_CACHE_DIR = Join-Path $webRoot ".cache\pip"
$env:PYTHONPYCACHEPREFIX = Join-Path $webRoot ".cache\pycache"
$env:PYTHONUTF8 = "1"
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $webRoot ".runtime\playwright-browsers"
$env:PLAYWRIGHT_BROWSER_CHANNEL = "msedge"
$env:TEMP = Join-Path $webRoot ".runtime\tmp"
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Path $env:TEMP -Force | Out-Null

Set-Location $webRoot
if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Run scripts\start-gateway.ps1 once to create the local environment."
}
& $venvPython -m pytest
