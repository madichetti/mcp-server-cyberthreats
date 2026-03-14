#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Publish the cyberthreats package to PyPI (or TestPyPI).

.DESCRIPTION
    Ensures dist/ artefacts exist (runs build.ps1 if not), re-validates with
    twine check, then uploads via `uv publish`.

    Pass -TestPyPI to publish to test.pypi.org instead of the live index.

.PARAMETER TestPyPI
    When set, uploads to https://test.pypi.org/legacy/ instead of PyPI.

.EXAMPLE
    # Publish to PyPI
    .\publish.ps1

.EXAMPLE
    # Publish to TestPyPI first for a dry-run
    .\publish.ps1 -TestPyPI
#>

param(
    [switch]$TestPyPI
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$distDir     = Join-Path $projectRoot "dist"

# ── Ensure artefacts exist ──────────────────────────────────────────────────
$artefacts = @(Get-ChildItem $distDir -Filter "*.whl" -ErrorAction SilentlyContinue) +
             @(Get-ChildItem $distDir -Filter "*.tar.gz" -ErrorAction SilentlyContinue)

if ($artefacts.Count -lt 2) {
    Write-Host "==> No dist artefacts found — running build first..." -ForegroundColor Yellow
    & (Join-Path $projectRoot "build.ps1")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

# ── Re-validate ─────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "==> Validating dist artefacts..." -ForegroundColor Cyan
uv tool run twine check (Join-Path $distDir "*")
if ($LASTEXITCODE -ne 0) {
    Write-Host "TWINE CHECK FAILED — aborting publish." -ForegroundColor Red
    exit $LASTEXITCODE
}

# ── Publish ──────────────────────────────────────────────────────────────────
Write-Host ""
if ($TestPyPI) {
    Write-Host "==> Publishing to TestPyPI..." -ForegroundColor Cyan
    uv publish --publish-url https://test.pypi.org/legacy/
} else {
    Write-Host "==> Publishing to PyPI..." -ForegroundColor Cyan
    uv publish
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "PUBLISH FAILED" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "==> Published successfully!" -ForegroundColor Green
if ($TestPyPI) {
    Write-Host "    https://test.pypi.org/project/cyberthreats/" -ForegroundColor Gray
} else {
    Write-Host "    https://pypi.org/project/cyberthreats/" -ForegroundColor Gray
}
