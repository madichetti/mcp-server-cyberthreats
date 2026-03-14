"""Vision analyzer backed by the OpenAI API."""
from __future__ import annotations

import os

from PIL import Image

from .base import VisionAnalyzerBase, _encode_image_b64, _max_tokens


class OpenAIVisionAnalyzer(VisionAnalyzerBase):
    """Vision analyzer backed by the OpenAI API.

    Supports both standard chat models (e.g. ``gpt-4o``) and reasoning
    models (``o1``, ``o3`` series).  The correct token-limit parameter
    (``max_tokens`` vs ``max_completion_tokens``) is chosen automatically
    based on the model name prefix.

    Required env vars:
        OPENAI_API_KEY: OpenAI secret key.

    Optional env vars:
        OPENAI_MODEL: Model name (default: ``o1``).
        MODEL_MAX_TOKENS: Response token budget (default: ``1500``).
    """

    def __init__(self) -> None:
        from langsmith.wrappers import wrap_openai
        from openai import OpenAI
        self._model = os.environ.get("OPENAI_MODEL", "o1")
        self._max_tokens = _max_tokens()
        self._client = wrap_openai(OpenAI(api_key=os.environ["OPENAI_API_KEY"]))

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    def analyze_architecture(self, image: Image.Image, audit_prompt: str) -> str:
        """Analyse the architecture diagram using the configured OpenAI model.

        Automatically selects ``max_completion_tokens`` for o1/o3 reasoning
        models and ``max_tokens`` for all other models.
        """
        b64 = _encode_image_b64(image)
        is_reasoning = self._model.startswith(("o1", "o3"))
        token_kwarg = {"max_completion_tokens" if is_reasoning else "max_tokens": self._max_tokens}
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": audit_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]}],
            **token_kwarg,
        )
        return response.choices[0].message.content
