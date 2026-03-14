"""Provider registry and factory for vision analyzers."""
from __future__ import annotations

import os

from .base import VisionAnalyzerBase
from .openai_provider import OpenAIVisionAnalyzer
from .azure_provider import AzureOpenAIVisionAnalyzer
from .anthropic_provider import AnthropicVisionAnalyzer
from .google_provider import GoogleVisionAnalyzer

_PROVIDERS: dict[str, type[VisionAnalyzerBase]] = {
    "openai":    OpenAIVisionAnalyzer,
    "azure":     AzureOpenAIVisionAnalyzer,
    "anthropic": AnthropicVisionAnalyzer,
    "google":    GoogleVisionAnalyzer,
}


def create_vision_analyzer() -> VisionAnalyzerBase:
    """Instantiate the correct provider from the ``LLM_PROVIDER`` env var.

    Returns:
        A fully initialised ``VisionAnalyzerBase`` subclass.

    Raises:
        ValueError: If ``LLM_PROVIDER`` is not one of the supported values.
    """
    provider = os.environ.get("LLM_PROVIDER", "openai").lower().strip()
    cls = _PROVIDERS.get(provider)
    if cls is None:
        raise ValueError(
            f"Unsupported LLM_PROVIDER '{provider}'. Choose from: {', '.join(_PROVIDERS)}"
        )
    return cls()
