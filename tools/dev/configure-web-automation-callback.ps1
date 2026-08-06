[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent (Split-Path -Parent $scriptDir)
$backendDir = Join-Path $root 'backend'
$webRoot = Join-Path $root 'web_automation'
$envFile = Join-Path $webRoot '.env'
$backendVenvPython = Join-Path $backendDir '.venv\Scripts\python.exe'
$python = if (Test-Path -LiteralPath $backendVenvPython) { $backendVenvPython } else { 'python' }

$values = [ordered]@{}
if (Test-Path -LiteralPath $envFile) {
    foreach ($line in [System.IO.File]::ReadAllLines($envFile, [System.Text.Encoding]::UTF8)) {
        if ($line -match '^([^#=]+)=(.*)$') {
            $values[$Matches[1].Trim()] = $Matches[2]
        }
    }
}

$token = $values['WEB_AUTOMATION_CALLBACK_TOKEN']
if (-not $token -or $token -eq 'replace-with-a-local-or-secret-managed-token') {
    $bytes = New-Object byte[] 32
    $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $random.GetBytes($bytes) } finally { $random.Dispose() }
    $token = -join ($bytes | ForEach-Object { $_.ToString('x2') })
}

$values['WEB_AUTOMATION_CALLBACK_ENABLED'] = '1'
$values['WEB_AUTOMATION_CALLBACK_URL'] = 'http://127.0.0.1:8000/api/alerts/webhooks/web-automation/'
$values['WEB_AUTOMATION_CALLBACK_TOKEN'] = $token
$values['WEB_AUTOMATION_CALLBACK_TIMEOUT_SECONDS'] = '5'
$values['WEB_AUTOMATION_CALLBACK_RETRY_DELAYS_SECONDS'] = '10,30,90'

$lines = foreach ($entry in $values.GetEnumerator()) { "$($entry.Key)=$($entry.Value)" }
[System.IO.File]::WriteAllLines(
    $envFile,
    $lines,
    (New-Object System.Text.UTF8Encoding($false))
)

$previousToken = $env:WEB_AUTOMATION_CALLBACK_TOKEN
try {
    $env:WEB_AUTOMATION_CALLBACK_TOKEN = $token
    Push-Location $backendDir
    & $python manage.py setup_web_automation_demo
    if ($LASTEXITCODE -ne 0) {
        throw "Callback integration setup failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
    $env:WEB_AUTOMATION_CALLBACK_TOKEN = $previousToken
}

Write-Host 'Web Automation callback configured in the project-local .env file.'
