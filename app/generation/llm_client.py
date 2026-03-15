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
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        payload = {
            "model": self._model,
            "messages": messages,
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
            if resp.status_code == 404:
                model_error = self._extract_model_not_found(resp)
                if model_error:
                    raise RuntimeError(
                        f"Ollama is running at {self._base_url}, but the configured model "
                        f"{self._model!r} is not installed. Run `ollama pull {self._model}` "
                        "or change LLM_MODEL in .env."
                    )
                return self._chat_openai_compatible(messages, temperature)
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]
        except httpx.HTTPError as e:
            raise RuntimeError(f"Ollama request failed: {e}") from e

    def _chat_openai_compatible(
        self,
        messages: list[dict[str, str]],
        temperature: float,
    ) -> str:
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        try:
            resp = httpx.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
                timeout=120.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPError as e:
            raise RuntimeError(
                "Configured LLM endpoint did not respond as Ollama or as an OpenAI-compatible "
                f"chat API at {self._base_url}: {e}"
            ) from e

    def _extract_model_not_found(self, response: httpx.Response) -> bool:
        try:
            data = response.json()
        except ValueError:
            return False
        error = data.get("error")
        return isinstance(error, str) and "model" in error.lower() and "not found" in error.lower()


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
