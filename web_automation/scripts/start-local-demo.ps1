[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding

$webRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$venvPython = Join-Path $webRoot ".venv\Scripts\python.exe"
$runtimeDir = Join-Path $webRoot ".runtime"
$logDir = Join-Path $webRoot "logs"
$env:PIP_CACHE_DIR = Join-Path $webRoot ".cache\pip"
$env:PYTHONPYCACHEPREFIX = Join-Path $webRoot ".cache\pycache"
$env:PYTHONUTF8 = "1"
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $webRoot ".runtime\playwright-browsers"
$env:PLAYWRIGHT_BROWSER_CHANNEL = "msedge"
$env:TEMP = Join-Path $webRoot ".runtime\tmp"
$env:TMP = $env:TEMP
$env:WEB_AUTOMATION_ALLOW_MOCK_DEFAULT_CREDENTIALS = "1"
$env:WEB_AUTOMATION_SHOW_DEMO_CREDENTIALS = "1"
$env:MOCK_PLATFORM_USERNAME = "aiops_robot"
$env:MOCK_PLATFORM_PASSWORD = "MockOnly@123456"
$env:LEGACY_OPS_USERNAME = "legacy_reader"
$env:LEGACY_OPS_PASSWORD = "LegacyOnly@123456"

Set-Location $webRoot
New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
New-Item -ItemType Directory -Path $env:TEMP -Force | Out-Null

if (-not (Test-Path -LiteralPath $venvPython)) {
    python -m venv .venv
}
$previousErrorActionPreference = $ErrorActionPreference
try {
    # Windows PowerShell 5.1 can promote native stderr to a terminating
    # NativeCommandError when ErrorActionPreference is Stop. Import failures
    # are expected here because they trigger first-run dependency installation.
    $ErrorActionPreference = "Continue"
    & $venvPython -c "import fastapi, uvicorn, httpx, yaml, cryptography, playwright" 2>$null
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
& $venvPython scripts\generate_test_ca.py

$httpLog = Join-Path $logDir "mock-http.log"
$httpsLog = Join-Path $logDir "mock-https.log"
$httpProcess = Start-Process -FilePath $venvPython -WindowStyle Hidden -PassThru `
    -ArgumentList "-m","uvicorn","mock_platform.app:app","--host","127.0.0.1","--port","8011" `
    -RedirectStandardOutput $httpLog -RedirectStandardError (Join-Path $logDir "mock-http.err.log")
$httpsProcess = Start-Process -FilePath $venvPython -WindowStyle Hidden -PassThru `
    -ArgumentList "-m","uvicorn","mock_platform.app:app","--host","127.0.0.1","--port","8443",`
    "--ssl-certfile",".runtime/certs/mock-private-ca-server.crt",`
    "--ssl-keyfile",".runtime/certs/mock-private-ca-server.key" `
    -RedirectStandardOutput $httpsLog -RedirectStandardError (Join-Path $logDir "mock-https.err.log")
$legacyProcess = Start-Process -FilePath $venvPython -WindowStyle Hidden -PassThru `
    -ArgumentList "-m","uvicorn","legacy_ops_platform.app:app","--host","127.0.0.1","--port","8012" `
    -RedirectStandardOutput (Join-Path $logDir "legacy-ops.log") `
    -RedirectStandardError (Join-Path $logDir "legacy-ops.err.log")

try {
    Start-Sleep -Seconds 2
    & $venvPython -m uvicorn gateway.app:app --host 127.0.0.1 --port 8010
}
finally {
    foreach ($process in @($httpProcess, $httpsProcess, $legacyProcess)) {
        if ($null -ne $process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force
        }
    }
}
