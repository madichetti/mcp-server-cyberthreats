# ---------------------------------------------------------------------------
# Standard library imports
# ---------------------------------------------------------------------------
import asyncio
import json
import os
import warnings
from pathlib import Path
from typing import Any, Union

# ---------------------------------------------------------------------------
# Third-party imports
# ---------------------------------------------------------------------------
import streamlit as st
from dotenv import load_dotenv
from fastmcp import Client as MCPClient
from langsmith import traceable
from PIL import Image

# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------
from mcp_server_cyberthreats.utils.vision_providers import create_vision_analyzer

# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------
load_dotenv()

warnings.filterwarnings(
    "ignore",
    message="Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.",
    category=UserWarning,
    module=r"langchain_core\._api\.deprecation",
)
warnings.filterwarnings(
    "ignore",
    message=r"'_UnionGenericAlias' is deprecated.*",
    category=DeprecationWarning,
    module=r"google\.genai\.types",
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------
_SERVER_PATH = Path(__file__).resolve().parents[1] / "mcp" / "server.py"
_CISA_LIMIT = int(os.environ.get("CISA_THREAT_LIMIT", "8"))


# ---------------------------------------------------------------------------
# Transport selector
# ---------------------------------------------------------------------------

def _mcp_target() -> Union[str, Path]:
    """Return MCP target — HTTP URL if ``MCP_SERVER_URL`` is set, else stdio path.

    When ``MCP_SERVER_URL`` is present the Streamlit app connects to the
    already-running HTTP MCP server (``run_mcp_server_http``).
    Without it, FastMCP spawns a stdio subprocess from ``_SERVER_PATH``,
    which is the default for local development and VSCode / Claude Desktop.
    """
    url = os.environ.get("MCP_SERVER_URL", "").strip()
    return url if url else _SERVER_PATH


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_text(payload: Any) -> str:
    """Recursively extract a plain-text string from any MCP response payload."""
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, bytes):
        return payload.decode("utf-8", errors="ignore")
    if isinstance(payload, list):
        return "\n".join(t for t in (_extract_text(i) for i in payload) if t)
    if isinstance(payload, dict):
        if "text" in payload and isinstance(payload["text"], str):
            return payload["text"]
        for key in ("content", "messages"):
            if key in payload:
                return _extract_text(payload[key])
        return json.dumps(payload, indent=2)
    for attr in ("text", "content", "messages"):
        if hasattr(payload, attr):
            return _extract_text(getattr(payload, attr))
    if hasattr(payload, "model_dump"):
        return _extract_text(payload.model_dump())
    return str(payload)


# ---------------------------------------------------------------------------
# MCP context loader
# ---------------------------------------------------------------------------

@traceable(
    name="mcp_fetch_context",
    tags=["mcp-server-cyberthreats", "threat-intel"],
    metadata={"step": "context_fetch"},
)
async def _fetch_mcp_context_async(target: Union[str, Path], limit: int) -> dict:
    """Connect to the MCP server (HTTP or stdio) and return all threat-intel context.

    Returns a dict with keys: ``tools``, ``resources``, ``prompts``,
    ``threat_intel``, ``feed_info``, ``metadata``, ``audit_prompt``,
    and ``transport`` (``"http"`` or ``"stdio"``).
    Decorated with ``@traceable`` so LangSmith captures this step automatically.
    """
    async with MCPClient(target) as client:
        tools, resources, prompts = (
            await client.list_tools(),
            await client.list_resources(),
            await client.list_prompts(),
        )
        threat = await client.call_tool("get_live_cisa_threats", {"limit": limit})
        metadata = await client.call_tool("get_cisa_feed_metadata", {})
        feed_info = await client.read_resource("intel://cisa/feed-info")
        prompt = await client.get_prompt(
            "audit_prompt",
            {"threat_intel": _extract_text(threat), "architecture_context": "cloud architecture diagram"},
        )
    return {
        "tools": [getattr(t, "name", str(t)) for t in tools],
        "resources": [getattr(r, "uri", str(r)) for r in resources],
        "prompts": [getattr(p, "name", str(p)) for p in prompts],
        "threat_intel": _extract_text(threat),
        "feed_info": _extract_text(feed_info),
        "metadata": _extract_text(metadata),
        "audit_prompt": _extract_text(prompt),
        "transport": "http" if isinstance(target, str) else "stdio",
    }


def fetch_mcp_context(limit: int) -> dict:
    """Synchronous wrapper — runs the async MCP session in a new event loop."""
    return asyncio.run(_fetch_mcp_context_async(_mcp_target(), limit))


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

@traceable(
    name="run_security_audit",
    tags=["mcp-server-cyberthreats", "security-audit"],
    metadata={"workflow": "architecture_audit"},
)
def run_security_audit(image: Image.Image, audit_prompt: str, vision) -> str:
    """Single-function orchestrator — replaces LangGraph StateGraph.

    Calls the vision provider directly with the audit prompt built from
    live CISA threat intel.  ``@traceable`` sends the full span to LangSmith
    automatically when ``LANGSMITH_TRACING=true``.
    """
    return vision.analyze_architecture(image=image, audit_prompt=audit_prompt)


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

@st.cache_resource
def _get_vision() -> tuple:
    """Build and cache the vision provider. Reused for every Streamlit run."""
    vision = create_vision_analyzer()
    return vision, f"{vision.provider_name} / {vision.model_name}"


@st.cache_data(ttl=int(os.environ.get("MCP_CACHE_TTL", "900")))
def _load_mcp_context() -> dict:
    """Fetch threat-intelligence context via MCP, cached for ``MCP_CACHE_TTL`` seconds."""
    return fetch_mcp_context(_CISA_LIMIT)


def main() -> None:
    """Render the full Streamlit application.

    Layout:
        - **Sidebar**: Live CISA KEV threat feed with a refresh button and
          an expandable MCP capabilities panel (tools, resources, prompts).
          Shows whether MCP is connected via HTTP or stdio.
        - **Main area**: Architecture diagram uploader, analysis trigger
          button, and security report output.  Full execution traces are
          captured automatically in LangSmith via ``@traceable``.

    Transport:
        Set ``MCP_SERVER_URL=http://localhost:8000/mcp`` to use the HTTP
        MCP server.  Leave unset to use stdio (spawns a subprocess).

    Run with::

        uv run python -m streamlit run src/mcp_server_cyberthreats/app/ui.py
    """
    st.set_page_config(page_title="CyberThreats — Security Reviewer", layout="wide")
    st.title("🛡️ CyberThreats — Architecture Security Reviewer (MCP Powered)")

    with st.sidebar:
        st.header("🔴 Live CISA Threat Feed")
        if st.button("Refresh Threat Intel"):
            _load_mcp_context.clear()

        try:
            mcp_context = _load_mcp_context()
            audit_prompt = mcp_context["audit_prompt"]
            transport_label = mcp_context.get("transport", "stdio")
            st.markdown(mcp_context["threat_intel"])
            st.info(f"Data sourced via MCP **{transport_label}** transport.")
            with st.expander("MCP Capabilities"):
                st.markdown("**Tools**")
                st.markdown("\n".join(f"- {n}" for n in mcp_context["tools"]))
                st.markdown("**Resources**")
                st.markdown("\n".join(f"- {u}" for u in mcp_context["resources"]))
                st.markdown("**Prompts**")
                st.markdown("\n".join(f"- {n}" for n in mcp_context["prompts"]))
                st.markdown("**Feed Info**")
                st.code(mcp_context["feed_info"])
                st.markdown("**Metadata**")
                st.code(mcp_context["metadata"])
        except Exception as exc:
            audit_prompt = "Act as a Principal Cloud Security Architect and review the architecture for critical vulnerabilities."
            st.error(f"MCP error: {exc}")

    uploaded_file = st.file_uploader("Upload Architecture Diagram", type=["png", "jpg", "jpeg"])

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Target Architecture", width="stretch")

        if st.button("Analyze with MCP Intel", type="primary"):
            with st.spinner("Processing vision model and cross-referencing CISA KEV..."):
                try:
                    vision, _ = _get_vision()
                    report = run_security_audit(
                        image=image,
                        audit_prompt=audit_prompt,
                        vision=vision,
                    )
                    st.markdown("### Security Analysis & Terraform Patch")
                    st.markdown(report)
                except Exception as exc:
                    st.error(f"Analysis error: {exc}")

    st.divider()
    _, provider_label = _get_vision()
    st.caption(f"Integrated with CISA KEV API · {provider_label}")


if __name__ == "__main__":
    main()
