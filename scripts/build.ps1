#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build the cyberthreats package (sdist + wheel).

.DESCRIPTION
    Cleans previous build artefacts, runs `uv build`, and validates the
    resulting dist/ files with `twine check`.

.EXAMPLE
    .\build.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# When this script is run from scripts/, the project root is one level up.
$scriptRoot = $PSScriptRoot
$projectRoot = Split-Path -Parent $scriptRoot

Write-Host "==> Cleaning previous build artefacts..." -ForegroundColor Cyan
foreach ($dir in @("dist", "build")) {
    $path = Join-Path $projectRoot $dir
    if (Test-Path $path) {
        Remove-Item -Recurse -Force $path
        Write-Host "    Removed $dir/"
    }
}

Write-Host ""
Write-Host "==> Building sdist + wheel..." -ForegroundColor Cyan
Push-Location $projectRoot
try {
    uv build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "BUILD FAILED" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "==> Validating dist artefacts with twine check..." -ForegroundColor Cyan
$distFiles = Get-ChildItem -Path (Join-Path $projectRoot "dist" "*") -Include *.whl, *.tar.gz -File | Select-Object -ExpandProperty FullName
if (-not $distFiles) {
    Write-Host "No distribution artefacts found in dist/ to validate." -ForegroundColor Red
    exit 1
}
uv tool run twine check $distFiles
if ($LASTEXITCODE -ne 0) {
    Write-Host "TWINE CHECK FAILED" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "==> Build complete. Artefacts in dist/:" -ForegroundColor Green
Get-ChildItem (Join-Path $projectRoot "dist") |
Where-Object { $_.Extension -in ".whl", ".gz" } |
Format-Table Name, @{N = "Size (KB)"; E = { [math]::Round($_.Length / 1KB, 1) } } -AutoSize
