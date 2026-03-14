"""Vision analyzer backed by Google Gemini."""
from __future__ import annotations

import os

from google import genai
from google.genai import types
from PIL import Image

from .base import VisionAnalyzerBase, _max_tokens


class GoogleVisionAnalyzer(VisionAnalyzerBase):
    """Vision analyzer backed by Google Gemini.

    Required env vars:
        GOOGLE_API_KEY: Google AI Studio or Vertex API key.

    Optional env vars:
        GOOGLE_MODEL: Model name (default: ``gemini-2.0-flash``).
        MODEL_MAX_TOKENS: Response token budget (default: ``1500``).
    """

    def __init__(self) -> None:
        self._model = os.environ.get("GOOGLE_MODEL", "gemini-2.0-flash")
        self._max_tokens = _max_tokens()
        self._client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

    @property
    def provider_name(self) -> str:
        return "google"

    @property
    def model_name(self) -> str:
        return self._model

    def analyze_architecture(self, image: Image.Image, audit_prompt: str) -> str:
        """Analyse the architecture diagram using the configured Gemini model."""
        response = self._client.models.generate_content(
            model=self._model,
            contents=[audit_prompt, image],
            config=types.GenerateContentConfig(max_output_tokens=self._max_tokens),
        )
        return response.text
