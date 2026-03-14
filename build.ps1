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

$projectRoot = $PSScriptRoot

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
uv build
if ($LASTEXITCODE -ne 0) {
    Write-Host "BUILD FAILED" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "==> Validating dist artefacts with twine check..." -ForegroundColor Cyan
uv tool run twine check (Join-Path $projectRoot "dist" "*")
if ($LASTEXITCODE -ne 0) {
    Write-Host "TWINE CHECK FAILED" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "==> Build complete. Artefacts in dist/:" -ForegroundColor Green
Get-ChildItem (Join-Path $projectRoot "dist") |
    Where-Object { $_.Extension -in ".whl", ".gz" } |
    Format-Table Name, @{N="Size (KB)"; E={[math]::Round($_.Length / 1KB, 1)}} -AutoSize
