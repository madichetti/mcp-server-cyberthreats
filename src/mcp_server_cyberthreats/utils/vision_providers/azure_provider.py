"""Vision analyzer backed by Azure OpenAI Service."""
from __future__ import annotations

import os

from PIL import Image

from .base import VisionAnalyzerBase, _encode_image_b64, _max_tokens


class AzureOpenAIVisionAnalyzer(VisionAnalyzerBase):
    """Vision analyzer backed by Azure OpenAI Service.

    Uses the same ``openai`` SDK but targets an Azure-hosted deployment.

    Required env vars:
        AZURE_OPENAI_API_KEY: Azure OpenAI resource key.
        AZURE_OPENAI_ENDPOINT: Resource endpoint URL.

    Optional env vars:
        AZURE_OPENAI_MODEL: Deployment name (default: ``gpt-4o``).
        AZURE_OPENAI_API_VERSION: API version (default: ``2024-12-01-preview``).
        MODEL_MAX_TOKENS: Response token budget (default: ``1500``).
    """

    def __init__(self) -> None:
        from langsmith.wrappers import wrap_openai
        from openai import AzureOpenAI
        self._model = os.environ.get("AZURE_OPENAI_MODEL", "gpt-4o")
        self._max_tokens = _max_tokens()
        self._client = wrap_openai(AzureOpenAI(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        ))

    @property
    def provider_name(self) -> str:
        return "azure"

    @property
    def model_name(self) -> str:
        return self._model

    def analyze_architecture(self, image: Image.Image, audit_prompt: str) -> str:
        """Analyse the architecture diagram using the configured Azure OpenAI deployment."""
        b64 = _encode_image_b64(image)
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": audit_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]}],
            max_tokens=self._max_tokens,
        )
        return response.choices[0].message.content
