<#
.SYNOPSIS
Runs the Streamlit UI for the MCP Cyberthreats project using the local virtual environment.

.DESCRIPTION
This script:
  - Resolves the repo root relative to this script.
  - Activates the `.venv` virtual environment (if present).
  - Runs Streamlit against the default UI entrypoint.

.PARAMETER ScriptPath
Path to the Streamlit app python file, relative to the repository root.

.PARAMETER Host
Host binding for Streamlit (default: localhost).

.PARAMETER Port
Port for Streamlit (default: 8501).
#>

param(
    [string]$ScriptPath = "src/mcp_server_cyberthreats/app/ui.py",
    [string]$Host = 'localhost',
    [int]$Port = 8501
)

# Ensure we run from repo root
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

# Activate the virtual environment if it exists
$venvActivate = Join-Path $repoRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    . $venvActivate
} else {
    Write-Warning "Virtual environment activation script not found at: $venvActivate"
    Write-Warning "Ensure you have created the venv (e.g. python -m venv .venv) and installed dependencies."
}

# Resolve and validate the script path
try {
    $fullScriptPath = Resolve-Path -Path (Join-Path $repoRoot $ScriptPath) -ErrorAction Stop
} catch {
    Write-Error "Unable to resolve Streamlit script path: $ScriptPath"
    exit 1
}

# Run Streamlit
Write-Host "Launching Streamlit app: $fullScriptPath`n"
streamlit run $fullScriptPath --server.address $Host --server.port $Port
