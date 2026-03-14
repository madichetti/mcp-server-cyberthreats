<#
.SYNOPSIS
    Regenerate the project's animated SVG architecture diagrams.

.DESCRIPTION
    Wrapper around docs/generate_diagrams.py that exposes every render
    parameter as a named PowerShell argument.  Change the defaults below
    and re-run, or supply any argument on the command line.

    Requires:
      - Python  (python / python3 on PATH, or .venv activated)
      - Mermaid CLI  npm install -g @mermaid-js/mermaid-cli

.PARAMETER OutDir
    Directory where .mmd and .svg files are written.
    Default: docs/images (relative to repo root).

.PARAMETER FontSize
    CSS font-size applied to every diagram label (e.g. "20px", "18px").
    Default: 20px

.PARAMETER Background
    SVG background colour passed to mmdc (e.g. "white", "transparent",
    "#f8fafc").
    Default: white

.PARAMETER RankSpacing
    Vertical spacing between flowchart ranks in pixels.
    Default: 80

.PARAMETER NodeSpacing
    Horizontal spacing between flowchart nodes in pixels.
    Default: 60

.PARAMETER SeqWidth
    Sequence diagram actor box width in pixels.
    Default: 200

.PARAMETER SeqHeight
    Sequence diagram actor box height in pixels.
    Default: 72

.PARAMETER SeqMessageMargin
    Vertical gap between sequence diagram messages in pixels.
    Default: 55

.PARAMETER Diagrams
    Comma-separated list of diagram names to render.
    Available: solution-architecture, functional-flow-diagram, technical-architecture
    Default: all three

.PARAMETER MaxWidth
    Override canvas width (px) for every diagram.  When 0 the per-diagram
    defaults are used: solution-architecture=1400, functional-flow-diagram=1600,
    technical-architecture=1600.  Increase this if text still looks small.
    Default: 0 (per-diagram defaults)

.PARAMETER StrokeWidth
    CSS stroke-width for connecting lines and arrows (e.g. "1.5px", "2px",
    "3px").  Thicker lines make animated dashes clearly visible, especially
    in dense top-to-bottom flowcharts.
    Default: 2px

.EXAMPLE
    # Regenerate all diagrams with defaults
    .\docs\generate_diagrams.ps1

.EXAMPLE
    # Larger font and more vertical breathing room
    .\docs\generate_diagrams.ps1 -FontSize 24px -RankSpacing 100 -NodeSpacing 72

.EXAMPLE
    # Force every diagram to 2000 px wide canvas
    .\docs\generate_diagrams.ps1 -MaxWidth 2000

.EXAMPLE
    # Regenerate only the sequence diagram with a transparent background
    .\docs\generate_diagrams.ps1 -Diagrams functional-flow-diagram -Background transparent

.EXAMPLE
    # Regenerate everything with defaults
    .\docs\generate_diagrams.ps1

    # Bigger font + more breathing room
    .\docs\generate_diagrams.ps1 -FontSize 28px -StrokeWidth 4px

    # Only the sequence diagram, transparent background
    .\docs\generate_diagrams.ps1 -Diagrams functional-flow-diagram -Background transparent

    # Custom output directory
    .\docs\generate_diagrams.ps1 -OutDir exports/diagrams
#>

[CmdletBinding()]
param(
    # ── Output ──────────────────────────────────────────────────────────────
    [string] $OutDir = "",          # empty → script default (docs/images)

    # ── Typography ──────────────────────────────────────────────────────────
    [string] $FontSize = "20px",

    # ── Appearance ──────────────────────────────────────────────────────────
    [string] $Background = "white",

    # ── Flowchart spacing ───────────────────────────────────────────────────
    [int]    $RankSpacing = 80,
    [int]    $NodeSpacing = 60,

    # ── Sequence diagram sizing ─────────────────────────────────────────────
    [int]    $SeqWidth = 200,
    [int]    $SeqHeight = 72,
    [int]    $SeqMessageMargin = 55,

    # ── Diagram selection ───────────────────────────────────────────────────
    [string] $Diagrams = "solution-architecture,functional-flow-diagram,technical-architecture",

    # ── Canvas width ────────────────────────────────────────────────────────
    [int]    $MaxWidth = 0,    # 0 = use per-diagram defaults in SVG_WIDTHS

    # ── Edge / line style ───────────────────────────────────────────────────
    [string] $StrokeWidth = "2px"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Resolve repo root (parent of the docs/ folder this script lives in) ────
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ScriptPy = Join-Path $PSScriptRoot "generate_diagrams.py"

if (-not (Test-Path $ScriptPy)) {
    Write-Error "Could not find generate_diagrams.py at: $ScriptPy"
    exit 1
}

# ── Build argument list ─────────────────────────────────────────────────────
$PyArgs = @(
    $ScriptPy,
    "--font-size", $FontSize,
    "--background", $Background,
    "--rank-spacing", $RankSpacing,
    "--node-spacing", $NodeSpacing,
    "--seq-width", $SeqWidth,
    "--seq-height", $SeqHeight,
    "--seq-message-margin", $SeqMessageMargin,
    "--max-width", $MaxWidth,
    "--stroke-width", $StrokeWidth,
    "--diagrams", $Diagrams
)

if ($OutDir -ne "") {
    $PyArgs += "--out-dir", $OutDir
}

# ── Echo configuration ──────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== Diagram Render Settings ===" -ForegroundColor Cyan
Write-Host "  FontSize         : $FontSize"
Write-Host "  Background       : $Background"
Write-Host "  RankSpacing      : $RankSpacing px"
Write-Host "  NodeSpacing      : $NodeSpacing px"
Write-Host "  SeqWidth         : $SeqWidth px"
Write-Host "  SeqHeight        : $SeqHeight px"
Write-Host "  SeqMessageMargin : $SeqMessageMargin px"
Write-Host "  StrokeWidth      : $StrokeWidth"
Write-Host "  Diagrams         : $Diagrams"
if ($MaxWidth -gt 0) {
    Write-Host "  MaxWidth         : $MaxWidth px (override)"
}
else {
    Write-Host "  MaxWidth         : per-diagram defaults (solution-arch=1400, sequence=1600, tech-arch=1600)"
}
if ($OutDir -ne "") {
    Write-Host "  OutDir           : $OutDir"
}
else {
    Write-Host "  OutDir           : docs/images (default)"
}
Write-Host ""

# ── Run ─────────────────────────────────────────────────────────────────────
Push-Location $RepoRoot
try {
    python @PyArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "generate_diagrams.py exited with code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
