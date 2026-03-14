"""Vision analyzer backed by Anthropic Claude."""
from __future__ import annotations

import os

import anthropic
from PIL import Image

from .base import VisionAnalyzerBase, _encode_image_b64, _max_tokens


class AnthropicVisionAnalyzer(VisionAnalyzerBase):
    """Vision analyzer backed by Anthropic Claude.

    Required env vars:
        ANTHROPIC_API_KEY: Anthropic API key.

    Optional env vars:
        ANTHROPIC_MODEL: Model name (default: ``claude-3-7-sonnet-20250219``).
        MODEL_MAX_TOKENS: Response token budget (default: ``1500``).
    """

    def __init__(self) -> None:
        self._model = os.environ.get("ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219")
        self._max_tokens = _max_tokens()
        self._client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    def analyze_architecture(self, image: Image.Image, audit_prompt: str) -> str:
        """Analyse the architecture diagram using the configured Claude model."""
        b64 = _encode_image_b64(image)
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                {"type": "text", "text": audit_prompt},
            ]}],
        )
        return response.content[0].text
