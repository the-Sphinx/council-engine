"""
LLM client abstraction. OllamaClient + OpenAIClient, behind LLMClient ABC.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMClient(ABC):
    @abstractmethod
    def chat(
        self,
        system: str,
        user: str,
        temperature: float = 0.0,
    ) -> str:
        """Send a chat request and return the response text."""
        ...


class OllamaClient(LLMClient):
    def __init__(self, base_url: str, model: str):
        self._base_url = base_url.rstrip("/")
        self._model = model

    def chat(self, system: str, user: str, temperature: float = 0.0) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": temperature},
            "format": "json",
        }
        try:
            resp = httpx.post(
                f"{self._base_url}/api/chat",
                json=payload,
                timeout=120.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]
        except httpx.HTTPError as e:
            raise RuntimeError(f"Ollama request failed: {e}") from e


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str | None = None):
        self._api_key = api_key
        self._model = model
        self._base_url = (base_url or "https://api.openai.com/v1").rstrip("/")

    def chat(self, system: str, user: str, temperature: float = 0.0) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        resp = httpx.post(
            f"{self._base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=120.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def get_llm_client(settings: Settings) -> LLMClient:
    if settings.LLM_PROVIDER == "openai":
        import os
        api_key = os.environ.get("OPENAI_API_KEY", "")
        return OpenAIClient(api_key=api_key, model=settings.LLM_MODEL)
    # Default: ollama
    return OllamaClient(base_url=settings.LLM_BASE_URL, model=settings.LLM_MODEL)
