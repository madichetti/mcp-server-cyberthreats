#!/usr/bin/env pwsh
<#
.SYNOPSIS
Publish the cyberthreats package to PyPI (or TestPyPI).

.DESCRIPTION
Ensures dist/ artefacts exist, validates with twine, and uploads via `uv publish`.

.PARAMETER TestPyPI
Uploads to https://test.pypi.org/legacy/ instead of PyPI.

.PARAMETER PyPIToken
Your PyPI or TestPyPI API token.
#>
[CmdletBinding(DefaultParameterSetName = 'Publish')]
param(
    [switch]$TestPyPI,
    [string]$PyPIToken
)

# Set strict mode but initialize variables to avoid 'unassigned' warnings
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Show-Help { 
    Get-Help -Full $PSCommandPath
}

# 1. Determine which token to use
$activeToken = $null
if ($PyPIToken) {
    $activeToken = $PyPIToken
}
elseif ($env:UV_PUBLISH_TOKEN) {
    $activeToken = $env:UV_PUBLISH_TOKEN
}
elseif ($env:TWINE_PASSWORD) {
    $activeToken = $env:TWINE_PASSWORD
}

if (-not $activeToken) {
    Write-Warning "No API token found."
    Write-Host "Please provide -PyPIToken or set the UV_PUBLISH_TOKEN environment variable." -ForegroundColor Yellow
    Show-Help
    exit 1
}

# 2. Set the environment variable uv uses
$env:UV_PUBLISH_TOKEN = $activeToken

# When this script is run from scripts/, the project root is one level up.
$scriptRoot = $PSScriptRoot
$projectRoot = Split-Path -Parent $scriptRoot
$distPath = Join-Path $projectRoot 'dist'

# 3. Ensure build artefacts exist
if (-not (Test-Path $distPath)) {
    Write-Host "dist/ not found; running build.ps1..." -ForegroundColor Cyan
    & (Join-Path $scriptRoot 'build.ps1')
    $buildExit = $LASTEXITCODE
    if ($buildExit -ne 0) { exit $buildExit }
}

# 4. Validate with twine
Write-Host "Validating dist/ artefacts with twine check..." -ForegroundColor Cyan
$distFiles = Get-ChildItem -Path (Join-Path $distPath "*") -Include *.whl,*.tar.gz -File | Select-Object -ExpandProperty FullName

if (-not $distFiles) {
    Write-Error "No distribution artefacts found in dist/ directory."
    exit 1
}

# Run uv commands from the repo root so it can see pyproject.toml and other config files.
Push-Location $projectRoot
try {
    uv tool run twine check $distFiles
    $twineExit = $LASTEXITCODE
    if ($twineExit -ne 0) { 
        Write-Host "twine check failed" -ForegroundColor Red
        exit $twineExit 
    }

    # 5. Prepare and Run Publish
    $publishArgs = @()
    if ($TestPyPI) { 
        Write-Host "Targeting TestPyPI..." -ForegroundColor Cyan
        $publishArgs += '--publish-url'
        $publishArgs += 'https://test.pypi.org/legacy/' 
    }

    Write-Host "Publishing..." -ForegroundColor Cyan
    uv publish @publishArgs
    $pubExit = $LASTEXITCODE

    if ($pubExit -ne 0) { 
        Write-Host "Publish failed (exit $pubExit)" -ForegroundColor Red
        exit $pubExit 
    }

    Write-Host "Publish succeeded." -ForegroundColor Green
}
finally {
    Pop-Location
}