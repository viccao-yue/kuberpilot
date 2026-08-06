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
    python -m venv .venv
}

$previousErrorActionPreference = $ErrorActionPreference
try {
    # Windows PowerShell 5.1 can promote native stderr to a terminating
    # NativeCommandError when ErrorActionPreference is Stop. Import failures
    # are expected here because they trigger first-run dependency installation.
    $ErrorActionPreference = "Continue"
    & $venvPython -c "import apscheduler, fastapi, uvicorn, httpx, yaml, playwright" 2>$null
    $dependencyCheckExitCode = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $previousErrorActionPreference
}
if ($dependencyCheckExitCode -ne 0) {
    try {
        $ErrorActionPreference = "Continue"
        & $venvPython -m pip install -r requirements.txt --timeout 120 --retries 10
        $dependencyInstallExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($dependencyInstallExitCode -ne 0) {
        throw "Web Automation dependency installation failed with exit code $dependencyInstallExitCode."
    }
}
& $venvPython -m uvicorn gateway.app:app --host 127.0.0.1 --port 8010 --reload
