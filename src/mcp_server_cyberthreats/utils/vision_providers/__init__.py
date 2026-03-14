"""Vision providers package for the CyberThreats security reviewer.

Re-exports the public API so callers use the same import path regardless
of the internal file layout::

    from mcp_server_cyberthreats.utils.vision_providers import VisionAnalyzerBase, create_vision_analyzer

Sub-modules:
    base               — ``VisionAnalyzerBase`` abstract class and shared helpers
    openai_provider    — ``OpenAIVisionAnalyzer``
    azure_provider     — ``AzureOpenAIVisionAnalyzer``
    anthropic_provider — ``AnthropicVisionAnalyzer``
    google_provider    — ``GoogleVisionAnalyzer``
    factory            — ``create_vision_analyzer`` factory and provider registry
"""
from .base import VisionAnalyzerBase
from .factory import create_vision_analyzer
from .openai_provider import OpenAIVisionAnalyzer
from .azure_provider import AzureOpenAIVisionAnalyzer
from .anthropic_provider import AnthropicVisionAnalyzer
from .google_provider import GoogleVisionAnalyzer

__all__ = [
    "VisionAnalyzerBase",
    "create_vision_analyzer",
    "OpenAIVisionAnalyzer",
    "AzureOpenAIVisionAnalyzer",
    "AnthropicVisionAnalyzer",
    "GoogleVisionAnalyzer",
]
