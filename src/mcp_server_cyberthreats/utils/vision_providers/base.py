"""Abstract base class and shared helpers for vision-model providers."""
from __future__ import annotations

import base64
import os
from abc import ABC, abstractmethod
from io import BytesIO

from PIL import Image


def _encode_image_b64(image: Image.Image) -> str:
    """Encode a PIL Image to a Base64-encoded PNG string."""
    buf = BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _max_tokens() -> int:
    """Read the token limit from ``MODEL_MAX_TOKENS``, defaulting to 1500."""
    return int(os.environ.get("MODEL_MAX_TOKENS", "1500"))


class VisionAnalyzerBase(ABC):
    """Abstract base class for all vision-model providers.

    Concrete subclasses wrap a specific LLM provider SDK and expose a
    uniform ``analyze_architecture`` method so the orchestrator is
    decoupled from provider-specific API details.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Short lowercase identifier for the provider (e.g. ``'openai'``)."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The model identifier as accepted by the provider's API."""
        ...

    @abstractmethod
    def analyze_architecture(self, image: Image.Image, audit_prompt: str) -> str:
        """Run vision analysis and return the model's Markdown response.

        Args:
            image: The PIL image of the architecture diagram to audit.
            audit_prompt: The security-audit prompt from the MCP server.

        Returns:
            A Markdown-formatted security analysis with Terraform remediation.
        """
        ...
