# ---------------------------------------------------------------------------
# Standard library imports
# ---------------------------------------------------------------------------
import asyncio
import json
import os
import warnings
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Third-party imports
# ---------------------------------------------------------------------------
import streamlit as st
from dotenv import load_dotenv
from fastmcp import Client as MCPClient
from langsmith import traceable
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from PIL import Image

# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------
from cyberthreats.utils import AuditContext, AuditState
from cyberthreats.utils.vision_providers import VisionAnalyzerBase, create_vision_analyzer

# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------
load_dotenv()

warnings.filterwarnings(
    "ignore",
    message=r"langsmith\.wrappers\._openai_agents is deprecated.*",
    category=DeprecationWarning,
)
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
# Helpers
# ---------------------------------------------------------------------------

def _extract_text(payload: Any) -> str:
    """Recursively extract a plain-text string from any MCP response payload.

    MCP tools, resources, and prompts can return strings, bytes, lists,
    dicts, or Pydantic-like objects. This function normalises all of those
    shapes into a single UTF-8 string so the rest of the code always works
    with plain text.

    Args:
        payload: Any value returned by an MCP client call.

    Returns:
        A plain-text string representation of the payload.
    """
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

@traceable(name="mcp_fetch_context")
async def _fetch_mcp_context_async(server_path: Path, limit: int) -> dict:
    """Connect to the FastMCP stdio server and return all threat-intelligence context.

    Returns a dict with keys: ``tools``, ``resources``, ``prompts``,
    ``threat_intel``, ``feed_info``, ``metadata``, and ``audit_prompt``.
    Decorated with ``@traceable`` so LangSmith captures this step automatically.
    """
    async with MCPClient(server_path) as client:
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
    }


def fetch_mcp_context(server_path: Path, limit: int) -> dict:
    """Synchronous wrapper — runs the async MCP session in a new event loop."""
    return asyncio.run(_fetch_mcp_context_async(server_path, limit))


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def prepare_context(state: AuditState) -> dict:
    """Node 1 — fetch MCP threat-intelligence context (or reuse if already set)."""
    threat_context = state.get("threat_context")
    audit_prompt = state.get("audit_prompt", "").strip()
    if not threat_context and not audit_prompt:
        threat_context = fetch_mcp_context(_SERVER_PATH, _CISA_LIMIT)
        audit_prompt = threat_context.get("audit_prompt", "")
    return {"threat_context": threat_context, "audit_prompt": audit_prompt}


def analyze_architecture(state: AuditState, runtime: Runtime[AuditContext]) -> dict:
    """Node 2 — run vision-model analysis and produce the security report."""
    image = state.get("image")
    audit_prompt = state.get("audit_prompt", "")
    if image is None:
        raise ValueError("Architecture image is required.")
    if not audit_prompt:
        raise ValueError("Audit prompt is required.")
    report = runtime.context.vision.analyze_architecture(image=image, audit_prompt=audit_prompt)
    return {"report": report}


def build_audit_graph():
    wf = StateGraph(AuditState, context_schema=AuditContext)
    wf.add_node(prepare_context)       # node name inferred: "prepare_context"
    wf.add_node(analyze_architecture)  # node name inferred: "analyze_architecture"
    wf.add_edge(START, "prepare_context")
    wf.add_edge("prepare_context", "analyze_architecture")
    wf.add_edge("analyze_architecture", END)
    return wf.compile()


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------


@st.cache_resource
def _get_resources() -> tuple:
    """Build and cache the compiled audit graph, vision provider, and label.

    Returns:
        ``(compiled_graph, vision, provider_label)`` — reused for every Streamlit run.
    """
    vision = create_vision_analyzer()
    graph = build_audit_graph()
    return graph, vision, f"{vision.provider_name} / {vision.model_name}"


@st.cache_data(ttl=int(os.environ.get("MCP_CACHE_TTL", "900")))
def _load_mcp_context() -> dict:
    """Fetch threat-intelligence context via MCP, cached for ``MCP_CACHE_TTL`` seconds."""
    return fetch_mcp_context(_SERVER_PATH, _CISA_LIMIT)


def main() -> None:
    """Render the full Streamlit application.

    Layout:
        - **Sidebar**: Live CISA KEV threat feed with a refresh button and
          an expandable MCP capabilities panel (tools, resources, prompts).
        - **Main area**: Architecture diagram uploader, analysis trigger
          button, and security report output.  Full execution traces are
          captured automatically in LangSmith via ``@traceable``.

    Run directly with::

        streamlit run src/cyberthreats/app/ui.py
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
            st.markdown(mcp_context["threat_intel"])
            st.info("Data sourced via MCP stdio server (tools/resources/prompts).")
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
                    graph, vision, _ = _get_resources()
                    result = graph.invoke(
                        {"image": image, "audit_prompt": audit_prompt},
                        config={
                            "tags": ["cyberthreats", "security-audit", "langgraph"],
                            "metadata": {"workflow": "architecture_audit"},
                        },
                        version="v2",
                        context=AuditContext(vision=vision),
                    )
                    st.markdown("### Security Analysis & Terraform Patch")
                    st.markdown(result.value.get("report", ""))
                except Exception as exc:
                    st.error(f"Analysis error: {exc}")

    st.divider()
    _, _v, provider_label = _get_resources()
    st.caption(f"Integrated with CISA KEV API · {provider_label}")


if __name__ == "__main__":
    main()

