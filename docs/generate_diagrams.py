"""Export the project's Mermaid diagrams to animated SVG files.

Rendering highlights
--------------------
- **Animated SVG output** — CSS ``@keyframes`` give flowing edge-dash and
  node-pulse effects, making the architecture diagrams come alive in any
  SVG-capable viewer (browser, GitHub README, VS Code preview).
- **shadcn colour palette** — each node type is colour-coded using Tailwind
  semantic tokens (blue UI layer, indigo orchestration, violet gateway,
  purple providers, emerald MCP server, amber external services).
- **20 px Inter font** — large, crisp, readable at any scale without zooming.
- **Drop-shadow depth** injected into every SVG ``<style>`` block after render.
- Per-diagram spacing tuned to the diagram direction.

Prerequisites
-------------
Install the Mermaid CLI once (requires Node.js >= 18)::

    npm install -g @mermaid-js/mermaid-cli

Then run from the repo root::

    python docs/generate_diagrams.py

Output
------
::

    docs/images/
        solution-architecture.mmd / .svg
        functional-flow-diagram.mmd  / .svg
        technical-architecture.mmd   / .svg
"""

# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# ---------------------------------------------------------------------------
# Mermaid configuration  (shadcn colour tokens + Inter font stack)
# ---------------------------------------------------------------------------

MERMAID_CONFIG: dict = {
    "theme": "base",
    "themeVariables": {
        # ── default node fills / borders
        "primaryColor":          "#dbeafe",   # blue-100
        "primaryTextColor":      "#1e3a8a",   # blue-900
        "primaryBorderColor":    "#3b82f6",   # blue-400
        "secondaryColor":        "#ede9fe",   # violet-100
        "secondaryTextColor":    "#4c1d95",   # violet-900
        "secondaryBorderColor":  "#8b5cf6",   # violet-400
        "tertiaryColor":         "#d1fae5",   # emerald-100
        "tertiaryTextColor":     "#064e3b",   # emerald-900
        "tertiaryBorderColor":   "#34d399",   # emerald-400
        # ── edges
        "lineColor":             "#64748b",   # slate-500
        "edgeLabelBackground":   "#f8fafc",   # slate-50
        # ── page
        "background":            "#ffffff",
        "mainBkg":               "#dbeafe",
        "nodeBorder":            "#3b82f6",
        # ── subgraphs
        "clusterBkg":            "#f8fafc",   # slate-50
        "clusterBorder":         "#cbd5e1",   # slate-300
        "titleColor":            "#0f172a",   # slate-900
        # ── typography  (20 px for readability at normal zoom)
        "fontFamily": "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
        "fontSize":   "20px",
        # ── sequence: actors
        "actorBkg":              "#dbeafe",
        "actorBorder":           "#2563eb",
        "actorTextColor":        "#1e3a8a",
        "actorLineColor":        "#94a3b8",   # slate-400
        # ── sequence: signals / messages
        "signalColor":           "#2563eb",
        "signalTextColor":       "#0f172a",
        # ── sequence: activation boxes
        "activationBorderColor": "#2563eb",
        "activationBkgColor":    "#eff6ff",
        # ── sequence: notes
        "noteBorderColor":       "#7c3aed",
        "noteBkgColor":          "#ede9fe",
        "noteTextColor":         "#4c1d95",
        # ── sequence: misc
        "loopTextColor":         "#0f172a",
        "labelBoxBkgColor":      "#f1f5f9",
        "labelBoxBorderColor":   "#94a3b8",
        "labelTextColor":        "#0f172a",
        "sequenceNumberColor":   "#ffffff",
    },
    "flowchart": {
        "htmlLabels":  True,
        "curve":       "basis",
        "rankSpacing": 80,
        "nodeSpacing": 60,
        "padding":     36,
        "useMaxWidth": False,
    },
    "sequence": {
        "diagramMarginX": 55,
        "diagramMarginY": 35,
        "actorMargin":    90,
        "width":          200,
        "height":         72,
        "boxTextMargin":  6,
        "noteMargin":     12,
        "messageMargin":  55,
        "useMaxWidth":    False,
    },
}


# ---------------------------------------------------------------------------
# CSS appended into the SVG <style> block after rendering.
# Only used for properties where CSS has no specificity conflicts:
#   - drop-shadow filters (not set by Mermaid at all)
#   - node / actor opacity pulse (animation property not set by Mermaid)
#   - sequence messageLine dashes  (.messageLine0/1 have equal-specificity in Mermaid)
# Flowchart edge flow animation is handled differently: the `edge-animation-fast`
# class is injected directly onto the elements (see inject_svg_styles below),
# which leverages Mermaid v11's own pre-scoped animation CSS at #my-svg specificity.
# ---------------------------------------------------------------------------

INJECT_CSS = """\

  /* ── Drop shadows ── */
  .node rect, .node polygon, .node circle, .node ellipse {
    filter: drop-shadow(0 2px 8px rgba(37, 99, 235, 0.22))
            drop-shadow(0 1px 3px rgba(37, 99, 235, 0.08));
  }
  .cluster rect {
    filter: drop-shadow(0 3px 10px rgba(0, 0, 0, 0.08));
  }
  .actor {
    filter: drop-shadow(0 2px 8px rgba(37, 99, 235, 0.28));
  }
  .note rect {
    filter: drop-shadow(0 2px 8px rgba(124, 58, 237, 0.22));
  }

  /* ── Sequence: forward message arrows ── */
  .messageLine0 {
    stroke-dasharray: 10 4 !important;
    animation: msgFlow 1.6s linear infinite;
  }
  @keyframes msgFlow {
    from { stroke-dashoffset: 42; }
    to   { stroke-dashoffset: 0;  }
  }

  /* ── Sequence: return / dashed arrows ── */
  .messageLine1 {
    stroke-dasharray: 8 4 !important;
    animation: retFlow 2.2s linear infinite;
  }
  @keyframes retFlow {
    from { stroke-dashoffset: 36; }
    to   { stroke-dashoffset: 0;  }
  }

  /* ── Sequence: actor lifeline flow ── */
  .actor-line {
    stroke-dasharray: 6 3 !important;
    animation: lifeFlow 2s linear infinite;
  }
  @keyframes lifeFlow {
    from { stroke-dashoffset: 18; }
    to   { stroke-dashoffset: 0;  }
  }

  /* ── Node subtle pulse ── */
  .node rect, .node polygon, .node circle {
    animation: nodePulse 3.5s ease-in-out infinite;
  }
  @keyframes nodePulse {
    0%, 100% { opacity: 1;    }
    50%      { opacity: 0.88; }
  }

  /* ── Actor subtle pulse ── */
  .actor {
    animation: actorPulse 3.5s ease-in-out infinite;
  }
  @keyframes actorPulse {
    0%, 100% { opacity: 1;    }
    50%      { opacity: 0.85; }
  }

  /* ── Sequence: lift message labels above connector lines ── */
  /* White halo painted behind each character so lines don't bleed through */
  .messageText {
    paint-order: stroke fill;
    stroke: #ffffff !important;
    stroke-width: 6px !important;
    stroke-linejoin: round !important;
  }
  /* Note text same treatment */
  .noteText {
    paint-order: stroke fill;
    stroke: #ede9fe !important;
    stroke-width: 5px !important;
    stroke-linejoin: round !important;
  }
"""


# ---------------------------------------------------------------------------
# Per-diagram SVG canvas widths
# mmdc uses --width to constrain the diagram layout so that the configured
# font-size renders at its stated pixel value when the SVG is displayed at
# approximately the same width in any viewer.
# ---------------------------------------------------------------------------

SVG_WIDTHS: dict[str, int] = {
    "solution-architecture":   1400,   # LR graph, compacted layout
    "functional-flow-diagram": 1600,   # sequence, 7 participants
    "technical-architecture":  1600,   # TB graph, medium
}


# ---------------------------------------------------------------------------
# Diagram sources
# Colour classes follow shadcn / Tailwind semantic tokens:
#   actor     slate-900   👤 User
#   ui        blue-700    Streamlit UI + cache helpers
#   orch      indigo-600  LangGraph workflow nodes
#   mcpload   sky-700     MCP async/sync loader functions
#   provider  purple-500  Vision LLM provider classes
#   server    emerald-700 FastMCP server + service class
#   primitive teal-600    MCP primitives (tools/resources/prompts)
#   external  amber-700   External APIs (CISA)
#   llmapi    red-600     LLM API endpoints
#   optional  amber-900   Optional integrations (LangSmith)
# ---------------------------------------------------------------------------

DIAGRAMS: dict[str, str] = {
    "solution-architecture": """\
---
config:
  theme: base
  flowchart:
    rankSpacing: 60
    nodeSpacing: 40
---
flowchart LR
 subgraph app["app/ui.py"]
        UI["main()\\nStreamlit UI"]
        Cache["_load_mcp_context\\ncache_data"]
        Res["_get_resources\\ncache_resource"]
        Graph["build_audit_graph\\nLangGraph"]
        N1["prepare_context"]
        N2["analyze_architecture"]
        OAI["OpenAI"]
        AZ["Azure OpenAI"]
        ANT["Anthropic"]
        GGL["Google Gemini"]
  end
 subgraph mcp["mcp/server.py"]
        SRV["FastMCP\\nCloudThreatIntel"]
        SVC["CisaKevThreat\\nIntelService"]
  end
    SRV --> SVC
    U(["👤 Security\\nEngineer"]) -- upload + analyze --> UI
    UI --> Cache & Res
    Cache -->|MCPClient stdio| SRV
    Res --> Graph --> N1 --> N2
    N2 --> OAI & AZ & ANT & GGL
    SVC --> CISA[("CISA\\nKEV API")]
    Cache -. traceable .-> LS{{"LangSmith\\noptional"}}
    Graph -. traces .-> LS

     UI:::ui
     Cache:::ui
     Res:::ui
     Graph:::orch
     N1:::orch
     N2:::orch
     OAI:::provider
     AZ:::provider
     ANT:::provider
     GGL:::provider
     SRV:::server
     SVC:::server
     U:::actor
     CISA:::external
     LS:::optional
    classDef actor    fill:#0f172a,stroke:#334155,color:#f8fafc,stroke-width:1.5px
    classDef ui       fill:#1d4ed8,stroke:#1e40af,color:#eff6ff,stroke-width:1.5px
    classDef orch     fill:#4f46e5,stroke:#4338ca,color:#eef2ff,stroke-width:1.5px
    classDef provider fill:#a855f7,stroke:#9333ea,color:#faf5ff,stroke-width:1.5px
    classDef server   fill:#059669,stroke:#047857,color:#ecfdf5,stroke-width:1.5px
    classDef external fill:#b45309,stroke:#92400e,color:#fffbeb,stroke-width:1.5px
    classDef optional fill:#713f12,stroke:#92400e,color:#fef9c3,stroke-width:1.5px,stroke-dasharray:4 2
""",

    "functional-flow-diagram": """\
sequenceDiagram
    actor U as 👤 Security Engineer
    participant UI as main()
    participant Cache as _load_mcp_context
    participant SRV as FastMCP Server
    participant CISA as CISA KEV API
    participant Graph as LangGraph
    participant LLM as Vision LLM

    U->>UI: Open application
    UI->>Cache: _load_mcp_context()
    Note over Cache: st.cache_data TTL=900s
    Cache->>SRV: MCPClient stdio
    Note over SRV: create_mcp_server run stdio
    SRV->>CISA: GET vulnerabilities.json
    CISA-->>SRV: KEV JSON feed
    Note over SRV: filter cloud CVEs
    SRV-->>Cache: list primitives
    SRV-->>Cache: get_live_cisa_threats
    SRV-->>Cache: get_prompt audit_prompt
    Cache-->>UI: mcp_context dict
    UI-->>U: Sidebar: CISA threats

    U->>UI: Upload diagram PNG/JPG
    U->>UI: Click Analyze
    UI->>Graph: graph.invoke
    Note over Graph: prepare_context node
    Graph->>Graph: analyze_architecture node
    Graph->>LLM: image + audit_prompt
    Note over LLM: OpenAI/Azure/Anthropic/Google
    LLM-->>Graph: Markdown report
    Graph-->>UI: result report
    UI-->>U: Security report
""",

    "technical-architecture": """\
%%{init: {"theme": "base"}}%%
graph TB
    classDef entry    fill:#0f172a,stroke:#334155,color:#f8fafc,stroke-width:1.5px
    classDef ui       fill:#1d4ed8,stroke:#1e40af,color:#eff6ff,stroke-width:1.5px
    classDef orch     fill:#4f46e5,stroke:#4338ca,color:#eef2ff,stroke-width:1.5px
    classDef mcpload  fill:#0369a1,stroke:#075985,color:#f0f9ff,stroke-width:1.5px
    classDef provider fill:#a855f7,stroke:#9333ea,color:#faf5ff,stroke-width:1.5px
    classDef server   fill:#059669,stroke:#047857,color:#ecfdf5,stroke-width:1.5px
    classDef primitive fill:#0d9488,stroke:#0f766e,color:#f0fdfa,stroke-width:1.5px
    classDef external fill:#b45309,stroke:#92400e,color:#fffbeb,stroke-width:1.5px
    classDef llmapi   fill:#dc2626,stroke:#b91c1c,color:#fef2f2,stroke-width:1.5px
    classDef optional fill:#713f12,stroke:#92400e,color:#fef9c3,stroke-width:1.5px,stroke-dasharray:4 2

    ENTRY["streamlit run\\napp/ui.py"] --> Main

    subgraph app["src/cyberthreats/app/ui.py"]
        Main["main()\\nStreamlit UI"]
        GetRes["_get_resources\\ncache_resource"]

        subgraph langgraph["LangGraph Workflow"]
            N1["prepare_context"]
            N2["analyze_architecture"]
            N1 --> N2
        end

        subgraph mcploader["MCP Context Loader"]
            LoadCtx["_load_mcp_context\\ncache_data"]
            FetchSync["fetch_mcp_context\\nasyncio.run"]
            FetchAsync["fetch_context_async\\n@traceable"]
            MCPCli["MCPClient\\nfastmcp.Client"]
            LoadCtx --> FetchSync --> FetchAsync --> MCPCli
        end

        subgraph providers["vision_providers"]
            OAI["OpenAI\\nVisionAnalyzer"]
            AZ["AzureOpenAI\\nVisionAnalyzer"]
            ANT["Anthropic\\nVisionAnalyzer"]
            GGL["Google\\nVisionAnalyzer"]
        end

        Main --> LoadCtx
        Main --> GetRes
        GetRes --> langgraph
        GetRes --> providers
        N2 --> providers
    end

    subgraph mcp["src/cyberthreats/mcp/server.py"]
        RunSrv["run_mcp_server\\ncreate_mcp_server"]
        SVC["CisaKevThreat\\nIntelService"]
        T1["get_live_cisa\\n_threats"]
        T2["get_cisa_feed\\n_metadata"]
        R1["cloud-keywords\\nresource"]
        R2["feed-info\\nresource"]
        P1["audit_prompt\\nprompt"]
        RunSrv --> SVC
        RunSrv -.-> T1 & T2 & R1 & R2 & P1
    end

    MCPCli -->|stdio subprocess| RunSrv
    SVC -->|HTTP GET| CISA[("CISA KEV\\nJSON Feed")]

    OAI -->|API| OpenAIAPI["OpenAI API"]
    AZ  -->|API| AzureAPI["Azure OpenAI API"]
    ANT -->|API| AnthropicAPI["Anthropic API"]
    GGL -->|API| GoogleAPI["Google AI API"]

    FetchAsync -. traceable .-> LS[/"LangSmith\\noptional"/]

    class ENTRY entry
    class Main,LoadCtx,GetRes ui
    class FetchSync,FetchAsync,MCPCli mcpload
    class N1,N2 orch
    class OAI,AZ,ANT,GGL provider
    class RunSrv,SVC server
    class T1,T2,R1,R2,P1 primitive
    class CISA external
    class OpenAIAPI,AzureAPI,AnthropicAPI,GoogleAPI llmapi
    class LS optional
""",
}


# ---------------------------------------------------------------------------
# SVG post-processing: inject drop-shadows + flow animations
# ---------------------------------------------------------------------------

import uuid as _uuid


def inject_svg_styles(svg_path: Path, *, stroke_width: str = "2px") -> None:
    """Post-process svg_path: inject animation CSS, animated dots, font-size
    override, and pin display dimensions.

    Steps:
    1. Add edge-animation-fast class to every flowchart-link path element.
    2. Inject dynamic CSS (stroke-width, animation speed, shadows, sequence).
    3. Inject an animated dot (<circle> + <animateMotion>) on each edge path.
    4. Override font-size in all <text>/<tspan> elements to match configured size.
    5. Pin SVG width/height to natural viewBox pixel dimensions.

    Args:
        svg_path: Path to the rendered SVG file to modify in place.
        stroke_width: CSS stroke-width for edges and sequence lines (default: "2px").
    """
    content = svg_path.read_text(encoding="utf-8")

    # 1. Add edge-animation-fast class to every flowchart-link element.
    content = re.sub(
        r'(class="([^"]*)\bflowchart-link\b([^"]*)")',
        lambda m: f'class="{m.group(2)}flowchart-link{m.group(3)} edge-animation-fast"',
        content,
    )

    # 2. Build dynamic CSS: stroke-width + animation speed override.
    dynamic_css = (
        f"\n  /* -- Dynamic: stroke-width + animation speed -- */"
        f"\n  #my-svg .edge-animation-fast {{"
        f"\n    stroke-width: {stroke_width} !important;"
        f"\n    animation-duration: 4s !important;"
        f"\n  }}"
        f"\n  .messageLine0, .messageLine1, .actor-line {{"
        f"\n    stroke-width: {stroke_width} !important;"
        f"\n  }}\n"
    )
    full_css = dynamic_css + INJECT_CSS
    if "</style>" in content:
        content = content.replace("</style>", full_css + "\n  </style>", 1)
    else:
        content = re.sub(
            r"(<svg[^>]*>)",
            r"\1\n<style>" + full_css + "</style>",
            content,
            count=1,
        )

    # 3. Animate a dot along each flowchart edge using <animateMotion>.
    #    Only for flowchart diagrams (has flowchart-link paths).
    def _add_dot(m: re.Match) -> str:
        path_tag = m.group(0)
        # Ensure the path has an id so <mpath> can reference it.
        id_match = re.search(r'\bid="([^"]+)"', path_tag)
        if id_match:
            path_id = id_match.group(1)
            path_tag2 = path_tag
        else:
            path_id = f"ep-{_uuid.uuid4().hex[:8]}"
            path_tag2 = path_tag.replace("<path ", f'<path id="{path_id}" ', 1)
        dot = (
            f'<circle r="6" fill="#fbbf24" stroke="#b45309" stroke-width="1.5" opacity="0.9">'
            f'<animateMotion dur="2.5s" repeatCount="indefinite" rotate="auto">'
            f'<mpath href="#{path_id}"/>'
            f'</animateMotion>'
            f'</circle>'
        )
        return path_tag2 + dot

    content = re.sub(
        r'<path [^>]*class="[^"]*\bflowchart-link\b[^"]*"[^>]*/>',
        _add_dot,
        content,
    )

    # 3b. Animate a dot along each sequence diagram message line.
    #     Sequence lines are <line> elements (no path d-attr), so we build the
    #     animateMotion path directly from x1/y1/x2/y2 coordinates.
    def _add_dot_to_line(m: re.Match) -> str:
        line_tag = m.group(0)
        x1m = re.search(r'\bx1="([^"]+)"', line_tag)
        y1m = re.search(r'\by1="([^"]+)"', line_tag)
        x2m = re.search(r'\bx2="([^"]+)"', line_tag)
        y2m = re.search(r'\by2="([^"]+)"', line_tag)
        if not (x1m and y1m and x2m and y2m):
            return line_tag
        dot = (
            f'<circle r="6" fill="#fbbf24" stroke="#b45309" stroke-width="1.5" opacity="0.9">'
            f'<animateMotion dur="2.5s" repeatCount="indefinite" rotate="auto"'
            f' path="M {x1m.group(1)} {y1m.group(1)} L {x2m.group(1)} {y2m.group(1)}"/>'
            f'</circle>'
        )
        return line_tag + dot

    content = re.sub(
        r'<line\b[^>]*\bclass="messageLine[01]"[^>]*/?>', 
        _add_dot_to_line,
        content,
    )

    # 3c. Shift messageText labels upward so they clear the connector line.
    #     Mermaid places the <text> with dy="1em" at the line's y-coord; we
    #     subtract 10px from the y attribute to give a consistent gap.
    def _shift_msg_text(m: re.Match) -> str:
        tag = m.group(0)
        y_m = re.search(r'\by="([0-9.]+)"', tag)
        if not y_m:
            return tag
        new_y = float(y_m.group(1)) - 10
        return tag[:y_m.start(1)] + f"{new_y:.1f}" + tag[y_m.end(1):]

    content = re.sub(
        r'<text\b[^>]*\bclass="messageText"[^>]*>',
        _shift_msg_text,
        content,
    )

    # 4. Override font-size in all <text>/<tspan> elements to match root CSS.
    fs_match = re.search(r'#my-svg\{[^}]*font-size:([0-9.]+px)', content)
    if fs_match:
        root_fs = fs_match.group(1)
        content = re.sub(
            r'(style="[^"]*?)font-size\s*:\s*[0-9.]+px',
            lambda mm: re.sub(r'font-size\s*:\s*[0-9.]+px', f'font-size: {root_fs}', mm.group(0)),
            content,
        )
        content = re.sub(
            r'(font-size\s*=\s*")[0-9.]+px(")',
            lambda mm: mm.group(1) + root_fs + mm.group(2),
            content,
        )

    # 5. Pin width / height to natural viewBox dimensions.
    vb_match = re.search(r'viewBox="([^"]+)"', content)
    if vb_match:
        parts = vb_match.group(1).split()
        if len(parts) == 4:
            nat_w = int(float(parts[2]))
            nat_h = int(float(parts[3]))
            content = re.sub(r'(<svg[^>]+)width="[^"]*"', fr'\1width="{nat_w}"', content, count=1)
            if 'height="' in content:
                content = re.sub(r'(<svg[^>]+)height="[^"]*"', fr'\1height="{nat_h}"', content, count=1)
            else:
                content = re.sub(r'(<svg[^>]+)(viewBox=)', fr'\1height="{nat_h}" \2', content, count=1)

    svg_path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_diagrams(
    out_dir: Path,
    *,
    background: str = "white",
    diagram_filter: list[str] | None = None,
    max_width: int = 0,
    stroke_width: str = "2px",
) -> None:
    """Write .mmd source files and render each to animated SVG via mmdc.

    Uses the configured Mermaid theme/font settings and then post-processes
    each SVG to inject drop-shadow depth and CSS flow-animation keyframes.

    Args:
        out_dir: Directory where .mmd and .svg files are written.
        background: SVG background colour passed to mmdc (default: white).
        diagram_filter: Optional list of diagram stem names to render.
            When None all diagrams in DIAGRAMS are rendered.
        max_width: Canvas width passed to mmdc via --width.  When 0
            (default) the per-diagram value from SVG_WIDTHS is used.
        stroke_width: CSS stroke-width for flowchart edges and sequence lines
            (default: "2px").
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    mmdc = shutil.which("mmdc")
    if mmdc is None:
        print(
            "ERROR: Mermaid CLI (mmdc) not found.\n"
            "Install it with:  npm install -g @mermaid-js/mermaid-cli",
            file=sys.stderr,
        )
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        config_path = tmp_path / "mermaid-config.json"
        config_path.write_text(json.dumps(MERMAID_CONFIG, indent=2), encoding="utf-8")

        for stem, source in DIAGRAMS.items():
            if diagram_filter and stem not in diagram_filter:
                print(f"  skipped {stem}  (not in --diagrams filter)")
                continue

            mmd_path = out_dir / f"{stem}.mmd"
            svg_path = out_dir / f"{stem}.svg"

            mmd_path.write_text(source, encoding="utf-8")
            print(f"  wrote   {mmd_path.relative_to(out_dir.parent)}")

            width = max_width if max_width > 0 else SVG_WIDTHS.get(stem, 1400)
            result = subprocess.run(
                [
                    mmdc,
                    "--input",           str(mmd_path),
                    "--output",          str(svg_path),
                    "--backgroundColor", background,
                    "--configFile",      str(config_path),
                    "--width",           str(width),
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"  ERROR  {stem}:\n{result.stderr}", file=sys.stderr)
                continue

            inject_svg_styles(svg_path, stroke_width=stroke_width)
            size_kb = svg_path.stat().st_size // 1024
            print(f"  rendered {svg_path.relative_to(out_dir.parent)}  ({size_kb} KB, animated SVG)")


if __name__ == "__main__":
    _all_diagrams = ",".join(DIAGRAMS.keys())

    parser = argparse.ArgumentParser(
        description="Render Mermaid architecture diagrams as animated SVGs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        metavar="PATH",
        help="Output directory for .mmd/.svg files (default: docs/images)",
    )
    parser.add_argument(
        "--font-size",
        default="20px",
        metavar="SIZE",
        help="CSS font-size for all diagram text",
    )
    parser.add_argument(
        "--background",
        default="white",
        metavar="COLOR",
        help="SVG background colour passed to mmdc",
    )
    parser.add_argument(
        "--rank-spacing",
        type=int,
        default=80,
        metavar="PX",
        help="Flowchart vertical rank spacing in pixels",
    )
    parser.add_argument(
        "--node-spacing",
        type=int,
        default=60,
        metavar="PX",
        help="Flowchart horizontal node spacing in pixels",
    )
    parser.add_argument(
        "--seq-width",
        type=int,
        default=200,
        metavar="PX",
        help="Sequence diagram actor box width",
    )
    parser.add_argument(
        "--seq-height",
        type=int,
        default=72,
        metavar="PX",
        help="Sequence diagram actor box height",
    )
    parser.add_argument(
        "--seq-message-margin",
        type=int,
        default=55,
        metavar="PX",
        help="Sequence diagram vertical message margin",
    )
    parser.add_argument(
        "--max-width",
        type=int,
        default=0,
        metavar="PX",
        help="Override canvas width for all diagrams (0 = use per-diagram defaults: "
             "solution-architecture=1400, functional-flow-diagram=1600, technical-architecture=1600)",
    )
    parser.add_argument(
        "--stroke-width",
        default="2px",
        metavar="WIDTH",
        help="CSS stroke-width for connecting lines / arrows (e.g. \"1.5px\", \"2px\", \"3px\")",
    )
    parser.add_argument(
        "--diagrams",
        default=_all_diagrams,
        metavar="NAMES",
        help="Comma-separated diagram names to render",
    )
    args = parser.parse_args()

    # Apply CLI overrides to the shared config dict before rendering.
    MERMAID_CONFIG["themeVariables"]["fontSize"] = args.font_size
    MERMAID_CONFIG["flowchart"]["rankSpacing"]   = args.rank_spacing
    MERMAID_CONFIG["flowchart"]["nodeSpacing"]   = args.node_spacing
    MERMAID_CONFIG["sequence"]["width"]          = args.seq_width
    MERMAID_CONFIG["sequence"]["height"]         = args.seq_height
    MERMAID_CONFIG["sequence"]["messageMargin"]  = args.seq_message_margin

    repo_root  = Path(__file__).resolve().parent.parent
    images_dir = Path(args.out_dir) if args.out_dir else repo_root / "docs" / "images"
    diagram_filter = [d.strip() for d in args.diagrams.split(",") if d.strip()]

    print(f"Rendering diagrams into {images_dir} …")
    render_diagrams(
        images_dir,
        background=args.background,
        diagram_filter=diagram_filter,
        max_width=args.max_width,
        stroke_width=args.stroke_width,
    )
    print("Done.")
