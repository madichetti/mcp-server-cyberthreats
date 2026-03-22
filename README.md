
<p align="center">
  <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.14%2B-blue.svg" alt="Python 3.14+"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License"/></a>
  <a href="https://github.com/madichetti/mcp-server-cyberthreats/actions"><img src="https://img.shields.io/github/actions/workflow/status/madichetti/mcp-server-cyberthreats/ci.yml?branch=main" alt="Build Status"/></a>
</p>

# 🛡️ MCP Server CyberThreats — AI Cloud Architecture Security Auditor

> AI-powered cloud architecture security auditor backed by live CISA threat intelligence.

Upload a cloud architecture diagram (PNG/JPG) and receive a structured Markdown security report — complete with Terraform remediation snippets — cross-referenced against current [CISA Known Exploited Vulnerabilities](https://www.cisa.gov/known-exploited-vulnerabilities-catalog).

---

## Table of Contents

- [Executive Summary](#-executive-summary)
- [Features](#-features)
- [How It Works](#-how-it-works)
- [Quick Start](#-quick-start)
  - [Prerequisites](#prerequisites)
  - [Install](#install)
  - [Configure](#configure)
  - [Run](#run)
- [MCP Server](#-mcp-server)
  - [Primitives](#primitives)
  - [Transport Modes](#transport-modes)
  - [Claude Desktop](#claude-desktop)
  - [VS Code Copilot](#vs-code-copilot-agent-mode)
- [Architecture](#-architecture)
  - [Solution Overview](#solution-overview)
  - [Audit Workflow](#audit-workflow)
  - [Component Detail](#component-detail)
- [Observability](#-observability)
- [Project Structure](#-project-structure)

---

## 📋 Executive Summary

CyberThreats is an AI-driven security auditing tool that transforms cloud architecture diagrams into actionable security reports in seconds. Upload a PNG or JPG diagram and the tool automatically cross-references your architecture against the [CISA Known Exploited Vulnerabilities (KEV)](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) catalog, identifying critical risks and generating production-ready Terraform remediation code.

The system is built on three integrated layers:

- **FastMCP server** — a lightweight threat-intelligence provider that streams live CISA KEV data. Supports both **stdio** (for VSCode and Claude Desktop) and **HTTP** (for the Streamlit app) transports. Carries no LLM dependency; the MCP host supplies all reasoning.
- **`@traceable` orchestrator** — a simple Python function that fetches MCP context, passes the enriched prompt to the vision LLM, and returns a Markdown report. LangSmith captures full execution traces automatically.
- **Streamlit front-end** — a browser-based UI; supports four pluggable vision LLM providers (OpenAI, Azure OpenAI, Anthropic, Google Gemini), switchable via `.env`.

This makes CyberThreats useful in two distinct modes: as a standalone web application for one-off audits, and as an MCP tool registered in any compliant AI assistant for on-demand threat-intel retrieval inside agentic workflows.

---

## ✨ Features

- 🔍 Vision-model analysis of cloud architecture diagrams (PNG/JPG)
- 🔗 Live CISA KEV threat intelligence via FastMCP (stdio **and** HTTP transport)
- 🧠 Pluggable LLM providers: OpenAI, Azure OpenAI, Anthropic, Google Gemini
- 📝 Markdown security report with Terraform remediation suggestions
- 📊 Executive summary + developer-focused findings in one output
- 📡 LangSmith observability via `@traceable` — zero boilerplate
- ⚡ MCP server connectable from Claude Desktop, VS Code Copilot, and more

---

## ⚙️ How It Works

```
Upload diagram
     │
     ▼
┌─────────────────────────────────────────────────┐
│  run_security_audit()  (@traceable)             │
│                                                 │
│  Step 1: fetch_mcp_context()                    │
│    └─ MCP server (HTTP or stdio)                │
│       → CISA KEV feed → enriched audit_prompt   │
│                                                 │
│  Step 2: vision.analyze_architecture()          │
│    └─ Vision LLM (provider from LLM_PROVIDER)   │
│       → Markdown report + Terraform patches     │
└─────────────────────────────────────────────────┘
     │
     ▼
Security report in Streamlit UI
```

1. **Fetch threat intel** — the MCP server queries the CISA KEV feed and returns cloud-relevant CVEs (via HTTP or stdio depending on `MCP_SERVER_URL`).
2. **Build audit prompt** — live CVE data is embedded into the prompt template returned by the `audit_prompt` MCP prompt.
3. **Vision analysis** — the diagram + enriched prompt are sent to the configured vision LLM.
4. **Report** — a structured Markdown report with risk prioritization and Terraform remediation is returned and rendered in Streamlit.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.14+
- [`uv`](https://docs.astral.sh/uv/) package manager
- API key for at least one [supported LLM provider](#configure)

### Install

```bash
git clone https://github.com/madichetti/mcp-server-cyberthreats
cd mcp-server-cyberthreats
uv sync
```

### Configure

Copy `.env.example` to `.env` and fill in the values for your chosen provider:

```bash
cp .env.example .env
```

Set `LLM_PROVIDER` to one of `openai` | `azure` | `anthropic` | `google`, then provide the matching API key(s).

#### Provider environment variables

<details>
<summary><strong>OpenAI</strong> (default)</summary>

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=o1           # optional, default: o1
```

</details>

<details>
<summary><strong>Azure OpenAI</strong></summary>

```env
LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_MODEL=gpt-4o                  # optional, default: gpt-4o
AZURE_OPENAI_API_VERSION=2024-12-01-preview  # optional
```

</details>

<details>
<summary><strong>Anthropic</strong></summary>

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6   # optional
```

</details>

<details>
<summary><strong>Google Gemini</strong></summary>

```env
LLM_PROVIDER=google
GOOGLE_API_KEY=AIza...
GOOGLE_MODEL=gemini-2.0-flash   # optional
```

</details>

#### All configuration variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `LLM_PROVIDER` | ✅ | `openai` | `openai` \| `azure` \| `anthropic` \| `google` |
| `OPENAI_API_KEY` | if openai | — | OpenAI secret key |
| `OPENAI_MODEL` | — | `o1` | OpenAI model name |
| `AZURE_OPENAI_API_KEY` | if azure | — | Azure OpenAI key |
| `AZURE_OPENAI_ENDPOINT` | if azure | — | `https://<resource>.openai.azure.com/` |
| `AZURE_OPENAI_MODEL` | — | `gpt-4o` | Azure deployment name |
| `AZURE_OPENAI_API_VERSION` | — | `2024-12-01-preview` | API version |
| `ANTHROPIC_API_KEY` | if anthropic | — | Anthropic API key |
| `ANTHROPIC_MODEL` | — | `claude-sonnet-4-6` | Anthropic model |
| `GOOGLE_API_KEY` | if google | — | Google AI API key |
| `GOOGLE_MODEL` | — | `gemini-2.0-flash` | Gemini model |
| `MODEL_MAX_TOKENS` | — | `1500` | Token budget for the report |
| `CISA_THREAT_LIMIT` | — | `8` | Max CVEs fetched per refresh |
| `CISA_FEED_TIMEOUT` | — | `10` | CISA KEV HTTP request timeout (seconds) |
| `MCP_CACHE_TTL` | — | `900` | Threat intel cache TTL (seconds) |
| `MCP_SERVER_URL` | — | — | HTTP MCP endpoint (e.g. `http://localhost:8000/mcp`). Leave unset to use stdio. |
| `MCP_HTTP_HOST` | — | `localhost` | Bind host for the HTTP MCP server |
| `MCP_HTTP_PORT` | — | `8000` | Bind port for the HTTP MCP server |
| `LANGSMITH_TRACING` | — | `false` | Enable LangSmith tracing |
| `LANGSMITH_API_KEY` | — | — | LangSmith API key |
| `LANGSMITH_PROJECT` | — | `cyberthreats` | LangSmith project name |

### Run

#### stdio mode (default — no extra server needed)

```bash
uv run python -m streamlit run src/mcp_server_cyberthreats/app/ui.py
```

The Streamlit app spawns the MCP server as a stdio subprocess automatically.
Open [http://localhost:8501](http://localhost:8501) in your browser.

#### HTTP mode (MCP server runs separately)

Start the MCP HTTP server in one terminal:

```bash
uv run mcp-server-cyberthreats-http
# Binds to http://localhost:8000/mcp by default
```

Then start the Streamlit app with `MCP_SERVER_URL` pointing at it:

```bash
# Windows PowerShell
$env:MCP_SERVER_URL="http://localhost:8000/mcp"
uv run python -m streamlit run src/mcp_server_cyberthreats/app/ui.py

# macOS / Linux
MCP_SERVER_URL=http://localhost:8000/mcp uv run python -m streamlit run src/mcp_server_cyberthreats/app/ui.py
```

The sidebar shows which transport is active (`stdio` or `http`).

**Usage:**

1. The **sidebar** shows live CISA KEV threat intel. Click **Refresh Threat Intel** to reload.
2. **Upload** a PNG or JPG cloud architecture diagram.
3. Click **Analyze with MCP Intel** — the orchestrator runs and the report appears below.

---

## 🏗️ Build & Publish (PowerShell)

The repo includes two convenience scripts in `scripts/`:

### Build (create dist/ artifacts)

```powershell
.\scripts\build.ps1
```

This cleans previous build artefacts, runs `uv build` to produce an sdist + wheel, and validates the output with `twine check`.

### Publish (PyPI / TestPyPI)

Provide a PyPI API token either via `-PyPIToken <token>` or via the environment variables `UV_PUBLISH_TOKEN` / `TWINE_PASSWORD`.

```powershell
# Publish to PyPI
.\scripts\publish.ps1 -PyPIToken <token>

# Publish to TestPyPI
.\scripts\publish.ps1 -TestPyPI -PyPIToken <token>
```

---

## 🏷️ Release tags & build artifacts

This repo includes a GitHub Actions workflow that **builds and stores release artifacts whenever you push a `v*` tag** (e.g. `v1.0.0`). The workflow produces the same `dist/` wheel + sdist files as `scripts/build.ps1` and attaches them to a GitHub Release.

### 1) Create a tag

```powershell
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

### 2) What happens next

- GitHub Actions runs `release-build.yml` (triggered by `refs/tags/v*`).
- The build output is uploaded as a workflow artifact and attached to a Release.
- You can download the artifacts from the workflow run or from the GitHub Release page.

> If you want to run builds on every `main` commit instead, update `.github/workflows/release-build.yml` to trigger on `push: branches: [main]`.

---

## 📁 Example Input & Output

A sample diagram and the generated security report are included in the `examples/` folder:

![Sample architecture diagram](examples/azure1.png)

---

## 🖧 MCP Server

The threat-intelligence backend is a [FastMCP](https://github.com/jlowin/fastmcp) server. It exposes live CISA KEV data as MCP primitives and supports **two transport modes**:

| Transport | Entry point | Used by |
|---|---|---|
| **stdio** | `mcp-server-cyberthreats-mcp` | VSCode Copilot, Claude Desktop, Claude Code |
| **HTTP** | `mcp-server-cyberthreats-http` | Streamlit app (when `MCP_SERVER_URL` is set) |

### Primitives

| Type | Name / URI | Description |
|---|---|---|
| Tool | `get_live_cisa_threats(limit)` | Cloud-relevant KEV entries as Markdown |
| Tool | `get_cisa_feed_metadata()` | Feed URL, fetch timestamp, keyword list |
| Resource | `intel://cisa/cloud-keywords` | Keyword filter list |
| Resource | `intel://cisa/feed-info` | Feed source description |
| Prompt | `audit_prompt` | Full audit prompt template |

### Transport Modes

#### stdio (VSCode / Claude Desktop / Claude Code)

The MCP server is launched as a subprocess. No network port is opened. Ideal for local AI assistant integrations.

```bash
# Run directly (for testing)
uv run mcp-server-cyberthreats-mcp
```

#### HTTP (Streamlit app)

The server binds to `MCP_HTTP_HOST:MCP_HTTP_PORT` and exposes the MCP endpoint at `/mcp`. Allows the Streamlit app to connect without spawning a new subprocess per session.

```bash
uv run mcp-server-cyberthreats-http
# → listening on http://localhost:8000/mcp
```

> **Note:** The MCP server has **no LLM dependency**. It fetches and filters CISA KEV data and returns it as plain text to the calling AI client. LLM provider keys belong to the Streamlit app (or Claude Desktop / VS Code) — not the server.

### Server environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `CISA_THREAT_LIMIT` | — | `8` | Maximum CVEs returned by `get_live_cisa_threats` |
| `CISA_FEED_TIMEOUT` | — | `10` | HTTP timeout for CISA feed requests (seconds) |
| `MCP_HTTP_HOST` | — | `localhost` | Bind host (HTTP transport only) |
| `MCP_HTTP_PORT` | — | `8000` | Bind port (HTTP transport only) |

---

### Claude Desktop

Config file location:
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Replace `/path/to/mcp-server-cyberthreats` with the absolute path to the repo root.

```json
{
  "mcpServers": {
    "mcp-server-cyberthreats": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/mcp-server-cyberthreats", "mcp-server-cyberthreats-mcp"],
      "env": {
        "CISA_THREAT_LIMIT": "8"
      }
    }
  }
}
```

> The MCP server provides threat-intel data only. Claude supplies the LLM reasoning — no API keys are required in this config.

---

### VS Code Copilot (Agent mode)

Create `.vscode/mcp.json` in the repo root:

```json
{
  "servers": {
    "mcp-server-cyberthreats": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--project", "${workspaceFolder}", "mcp-server-cyberthreats-mcp"],
      "env": {
        "CISA_THREAT_LIMIT": "8"
      }
    }
  }
}
```

Open **Copilot Chat → Agent mode** and the `mcp-server-cyberthreats` server appears in the tools list.

---

### Claude Code (stdio)

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "mcp-server-cyberthreats": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--project", "/path/to/mcp-server-cyberthreats", "mcp-server-cyberthreats-mcp"]
    }
  }
}
```

---

## 🏗️ Architecture

> Regenerate diagrams: `uv run python docs/generate_diagrams.py` (requires [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli))

---

### Solution Overview

![Solution Architecture](docs/images/solution-architecture.svg)

The solution is split across two modules that communicate over an MCP channel (stdio or HTTP):

- **`app/ui.py`** — the Streamlit front-end. `main()` drives the UI; `_load_mcp_context()` (cached 900 s via `@st.cache_data`) connects to the MCP server and pulls live CISA KEV data; `_get_vision()` (`@st.cache_resource`) constructs the selected vision provider once per session.
- **`run_security_audit()`** — a single `@traceable` orchestrator function that replaces the previous LangGraph graph. Calls the vision provider with the enriched audit prompt and returns the Markdown report. LangSmith captures the full span automatically.
- **`mcp/server.py`** — a FastMCP server (`CloudThreatIntel`) backed by `CisaKevThreatIntelService`. Supports stdio (for AI assistants) and HTTP (`streamable-http`, for the Streamlit app) transports. Exposes two tools, two resources, and one prompt (see [MCP Primitives](#primitives)).
- **Vision providers** — OpenAI, Azure OpenAI, Anthropic, and Google Gemini are all supported; the active provider is selected at startup from `LLM_PROVIDER`.
- **LangSmith** — optional; both `_fetch_mcp_context_async` and `run_security_audit` are decorated with `@traceable` so full traces appear in LangSmith when `LANGSMITH_TRACING=true`.

---

### Audit Workflow

![Functional Flow](docs/images/functional-flow-diagram.svg)

End-to-end sequence for a single audit run:

1. **App load / cache cold-start** — if the threat-intel cache is empty, `_load_mcp_context()` connects to the MCP server (HTTP if `MCP_SERVER_URL` is set, else stdio subprocess), calls `get_live_cisa_threats` and `get_cisa_feed_metadata`, and stores the result for up to 900 seconds. The sidebar immediately shows the live CVE list and active transport mode.
2. **User uploads diagram** — a PNG or JPG cloud architecture image is accepted via the Streamlit file-uploader.
3. **Analyse click** — `run_security_audit()` is called with the image and the cached `audit_prompt`. It passes both directly to the vision LLM and streams back the Markdown report.
4. **Report display** — the structured report (risk findings + Terraform remediation snippets) is rendered directly in the Streamlit UI.

---

### Component Detail

![Technical Architecture](docs/images/technical-architecture.svg)

| Layer | Key symbols |
|---|---|
| **Streamlit app** | `main()`, `_get_vision()` (@st.cache_resource), `_load_mcp_context()` (@st.cache_data TTL 900 s) |
| **Orchestrator** | `run_security_audit()` (@traceable) — single function, no state graph |
| **MCP context loader** | `fetch_mcp_context()` (asyncio.run) → `_fetch_mcp_context_async()` (@traceable) → `MCPClient` (HTTP or stdio via `_mcp_target()`) |
| **Vision providers** | `create_vision_analyzer()` factory resolves `LLM_PROVIDER` to one of `OpenAIVisionAnalyzer`, `AzureOpenAIVisionAnalyzer`, `AnthropicVisionAnalyzer`, or `GoogleVisionAnalyzer` — all extend `VisionAnalyzerBase` |
| **MCP server** | `run_mcp_server()` (stdio) / `run_mcp_server_http()` (HTTP) / `create_mcp_server()` launch `FastMCP("CloudThreatIntel")` backed by `CisaKevThreatIntelService`; exposes tools `get_live_cisa_threats` & `get_cisa_feed_metadata`, resources `intel://cisa/cloud-keywords` & `intel://cisa/feed-info`, and prompt `audit_prompt` |
| **Observability** | `run_security_audit` and `_fetch_mcp_context_async` wrapped with LangSmith `@traceable`; OpenAI / Azure clients wrapped with `wrap_openai()` |

---

## 📊 Observability

When `LANGSMITH_TRACING=true`, every audit run produces a full trace in [LangSmith](https://smith.langchain.com/) with two spans:

| Span | Decorator | What it captures |
|---|---|---|
| `mcp_fetch_context` | `@traceable` | MCP transport used, CISA KEV payload, tool/resource/prompt list |
| `run_security_audit` | `@traceable` | Audit prompt, image metadata, vision LLM response |

Both spans are tagged with `mcp-server-cyberthreats` and grouped under `LANGSMITH_PROJECT`.

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=ls__...
LANGSMITH_PROJECT=cyberthreats
```

---

## 📁 Project Structure

```
mcp-server-cyberthreats/
├── src/mcp_server_cyberthreats/
│   ├── app/
│   │   └── ui.py                  # Streamlit app + @traceable orchestrator
│   ├── mcp/
│   │   └── server.py              # FastMCP server — stdio + HTTP transports
│   └── utils/
│       └── vision_providers/
│           ├── base.py            # Abstract base class
│           ├── openai_provider.py
│           ├── azure_provider.py
│           ├── anthropic_provider.py
│           ├── google_provider.py
│           └── factory.py         # create_vision_analyzer() factory
├── examples/                      # Sample diagram and report
├── docs/                          # Architecture diagrams + generation scripts
├── scripts/
│   ├── build.ps1                  # Build sdist + wheel
│   └── publish.ps1                # Publish to PyPI / TestPyPI
├── pyproject.toml
├── uv.toml
└── .env.example
```

---

## 📄 License

[MIT](LICENSE)
