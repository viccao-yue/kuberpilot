[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,
    [string]$Cluster = "host",
    [string]$Username = "admin",
    [string]$CredentialId = "kubercon-readonly"
)

$ErrorActionPreference = "Stop"
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function ConvertTo-DotEnvValue {
    param([AllowEmptyString()][string]$Value)

    $escaped = $Value.Replace("\", "\\").Replace("'", "\'")
    return "'$escaped'"
}

$webRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$envFile = Join-Path $webRoot ".env"
$runtimePlatformDir = Join-Path $webRoot ".runtime\platforms"
$definitionDir = Join-Path $webRoot "platforms\definitions"

$parsedUrl = $null
if (-not [Uri]::TryCreate($BaseUrl, [UriKind]::Absolute, [ref]$parsedUrl)) {
    throw "BaseUrl must be an absolute HTTP or HTTPS URL."
}
if ($parsedUrl.Scheme -notin @("http", "https")) {
    throw "BaseUrl must use HTTP or HTTPS."
}
if ($Cluster -notmatch '^[a-z0-9][a-z0-9.-]{0,62}$') {
    throw "Cluster contains unsupported characters."
}
if ($CredentialId -notmatch '^[a-z][a-z0-9_-]{1,63}$') {
    throw "CredentialId contains unsupported characters."
}

$securePassword = Read-Host "KuberCon password" -AsSecureString
$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
}
if ([string]::IsNullOrWhiteSpace($Username) -or [string]::IsNullOrEmpty($password)) {
    throw "Username and password must not be empty."
}

New-Item -ItemType Directory -Path $runtimePlatformDir -Force | Out-Null
Get-ChildItem -LiteralPath $definitionDir -Filter "*.yaml" | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $runtimePlatformDir -Force
}

$origin = "{0}://{1}" -f $parsedUrl.Scheme, $parsedUrl.Authority
$loginUrl = "$origin/login"
$platformYaml = @"
platform: kubercon
display_name: KuberCon Kubernetes platform
base_url: $loginUrl
enabled: true
timeout_seconds: 15
expected_login_path: /login
adapter: kubercon
adapter_options:
  cluster: $Cluster
  include_builtin: true
credential_id: $CredentialId
alarm_collection_interval_seconds: 60
allowed_resolved_cidrs:
  - 10.0.0.0/8
  - 172.16.0.0/12
  - 192.168.0.0/16
"@
[IO.File]::WriteAllText(
    (Join-Path $runtimePlatformDir "kubercon.yaml"),
    $platformYaml,
    $utf8NoBom
)

$values = [ordered]@{}
if (Test-Path -LiteralPath $envFile) {
    foreach ($line in Get-Content -LiteralPath $envFile -Encoding UTF8) {
        if ($line -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            $values[$Matches[1]] = $Matches[2]
        }
    }
}
$credentialPrefix = ($CredentialId -replace '[^A-Za-z0-9]+', '_').Trim('_').ToUpperInvariant()
$values["WEB_AUTOMATION_PLATFORM_DIR"] = ".runtime/platforms"
$values["CREDENTIAL_${credentialPrefix}_USERNAME"] = ConvertTo-DotEnvValue $Username
$values["CREDENTIAL_${credentialPrefix}_PASSWORD"] = ConvertTo-DotEnvValue $password
$lines = foreach ($entry in $values.GetEnumerator()) {
    "{0}={1}" -f $entry.Key, $entry.Value
}
[IO.File]::WriteAllLines($envFile, $lines, $utf8NoBom)
$password = $null

Write-Output "Local KuberCon configuration saved under web_automation/.runtime and .env."
Write-Output "No credential value was printed."
