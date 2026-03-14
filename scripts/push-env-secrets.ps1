#!/usr/bin/env pwsh
<##
.SYNOPSIS
    Push .env variables into GitHub repository secrets via GitHub CLI.

.DESCRIPTION
    Reads the project root .env file and creates/updates GitHub Actions secrets.
    By default, each variable is created as a secret named "ENV_<KEY>".

    Requires: GitHub CLI (gh) installed and authenticated (gh auth login).

.EXAMPLE
    .\push-env-secrets.ps1

.EXAMPLE
    .\push-env-secrets.ps1 -Prefix "MYAPP_"

.PARAMETER Prefix
    Prefix to prefix each secret name with. Defaults to "ENV_".

.PARAMETER Repo
    Optional repo slug (owner/repo). If omitted, the current repo is inferred via gh.

.PARAMETER FilePath
    Path to the .env file to import. Defaults to the repository root .env.

.PARAMETER DryRun
    If set, prints the secrets that would be created/updated without calling gh.

.PARAMETER EncodeFileAsSecret
    If set, encodes the entire .env file as base64 and pushes it as a single secret.

.PARAMETER FileSecretName
    Secret name to use when writing the encoded .env file. Defaults to "ENV_FILE_BASE64".
#>

[CmdletBinding()]
param(
    [string]$Prefix = 'ENV_',
    [string]$Repo,
    [string]$FilePath,
    [switch]$DryRun,
    [switch]$EncodeFileAsSecret,
    [string]$FileSecretName = 'ENV_FILE_BASE64'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-ErrorAndExit([string]$msg) {
    Write-Host $msg -ForegroundColor Red
    exit 1
}

# Determine the repo slug if not provided
if (-not $Repo) {
    $repoInfo = gh repo view --json nameWithOwner -q .nameWithOwner 2>&1
    if ($LASTEXITCODE -ne 0 -or -not $repoInfo) {
        Write-ErrorAndExit "Failed to infer repository. Ensure you're in a git repo and gh is authenticated.\n$repoInfo"
    }
    $Repo = $repoInfo.Trim()
}

# Determine .env file path
if (-not $FilePath) {
    $scriptRoot = $PSScriptRoot
    $projectRoot = Split-Path -Parent $scriptRoot
    $FilePath = Join-Path $projectRoot '.env'
}

if (-not (Test-Path $FilePath)) {
    Write-ErrorAndExit "Could not find .env at '$FilePath'."
}

Write-Host "Using repo: $Repo" -ForegroundColor Cyan
Write-Host "Reading env file: $FilePath" -ForegroundColor Cyan

if ($EncodeFileAsSecret) {
    $bytes = [System.IO.File]::ReadAllBytes($FilePath)
    $b64 = [System.Convert]::ToBase64String($bytes)
    $entries = @([pscustomobject]@{ Name = $FileSecretName; Value = $b64 })
}
else {
    $lines = Get-Content -Path $FilePath -ErrorAction Stop
    $entries = @()

    foreach ($line in $lines) {
        $trim = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($trim) -or $trim.StartsWith('#')) {
            continue
        }

        # Allow both KEY=VALUE and export KEY=VALUE
        if ($trim -like 'export *') {
            $trim = $trim.Substring(6).TrimStart()
        }

        $split = $trim -split '=', 2
        if ($split.Count -ne 2) {
            Write-Host "Skipping invalid line: $line" -ForegroundColor Yellow
            continue
        }

        $key = $split[0].Trim()
        $value = $split[1]

        if (-not $key) {
            Write-Host "Skipping line with empty key: $line" -ForegroundColor Yellow
            continue
        }

        $secretName = "$Prefix$key"
        $entries += [pscustomobject]@{ Name = $secretName; Value = $value }
    }
}

if (-not $entries) {
    Write-Host "No valid env variables found to push." -ForegroundColor Yellow
    exit 0
}

foreach ($entry in $entries) {
    $name = $entry.Name
    $value = $entry.Value

    if ($DryRun) {
        Write-Host "[DryRun] Would set secret $name" -ForegroundColor Yellow
        continue
    }

    Write-Host "Setting secret: $name" -ForegroundColor Cyan
    $processInfo = @{ }
    try {
        gh secret set $name --repo $Repo --body $value | Out-Null
    }
    catch {
        Write-Host "Failed to set secret ${name}: $($_)" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Done. $($entries.Count) secrets set." -ForegroundColor Green
