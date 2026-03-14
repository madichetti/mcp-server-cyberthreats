"""LangGraph state and runtime-context models for the audit workflow."""
from dataclasses import dataclass
from typing import Any, TypedDict

from PIL import Image

from mcp_server_cyberthreats.utils.vision_providers import VisionAnalyzerBase


@dataclass
class AuditContext:
    """Runtime context for the audit graph — holds non-serializable dependencies.

    Passed via ``context=AuditContext(...)`` at ``graph.invoke()`` time so the
    vision provider is never stored inside the serializable state, keeping state
    checkpointer-safe per LangGraph standards.
    """

    vision: VisionAnalyzerBase


class AuditState(TypedDict, total=False):
    """Shared mutable state passed between LangGraph workflow nodes.

    All fields are optional (``total=False``) so each node returns only
    the keys it updates.  Execution tracing is handled automatically by
    LangSmith when ``LANGSMITH_TRACING=true``.

    Attributes:
        image: The uploaded architecture diagram as a PIL Image.
        audit_prompt: The security-audit prompt built from live CISA threat intel.
        report: The final Markdown security report produced by the vision model.
        threat_context: Raw context dict returned by ``fetch_mcp_context``.
    """

    image: Image.Image
    audit_prompt: str
    report: str
    threat_context: dict[str, Any]
