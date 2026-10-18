from typing import Any

import requests

from ai.config import settings


class OllamaClient:
    """Small HTTP client for local Ollama embeddings and generation."""

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.OLLAMA_URL).rstrip("/")

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = requests.post(
            f"{self.base_url}/api/embed",
            json={
                "model": settings.OLLAMA_EMBEDDING_MODEL,
                "input": texts,
            },
            timeout=300,
        )
        response.raise_for_status()
        data = response.json()
        return data["embeddings"]

    def chat(self, question: str, context: str) -> str:
        system = (
            "You are a finance research assistant. Answer only from supplied "
            "context when context is provided. Do not invent company-specific "
            "figures. Clearly say when the evidence is insufficient."
        )
        return self.chat_raw(
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion:\n{question}",
                },
            ]
        )

    def chat_raw(
        self,
        messages: list[dict[str, str]],
        format: str | dict[str, Any] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": settings.OLLAMA_LLM_MODEL,
            "messages": messages,
            "stream": False,
        }
        if format is not None:
            payload["format"] = format

        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=600,
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]

    def health(self) -> dict[str, Any]:
        response = requests.get(
            f"{self.base_url}/api/tags",
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
