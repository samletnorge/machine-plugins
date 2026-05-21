"""Ollama LLM provider — pure httpx, no pydantic-ai dependency.

This is the reference implementation showing how ANY provider can
implement the machine_core.types.Provider protocol directly.
"""

from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator

import httpx

from machine_core.plugins.model_provider_support.schemas import (
    ModelRequest,
    ModelResponse,
)


class OllamaLLMProvider:
    """Pure httpx Ollama provider implementing Provider protocol."""

    def __init__(
        self, base_url: str = "http://localhost:11434", model: str = "llama3.2"
    ) -> None:
        self.base_url = base_url
        self.model = model

    async def invoke(self, request: Any) -> Any:
        """Provider protocol — delegates to generate()."""
        if isinstance(request, ModelRequest):
            return await self.generate(request)
        raise TypeError(f"Unsupported request type: {type(request)}")

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate a response from Ollama's /api/chat endpoint."""
        start = time.monotonic()
        async with httpx.AsyncClient(base_url=self.base_url, timeout=120.0) as client:
            payload: dict[str, Any] = {
                "model": request.model or self.model,
                "messages": self._to_messages(request.input),
                "stream": False,
                **request.parameters,
            }
            resp = await client.post("/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        duration = (time.monotonic() - start) * 1000
        return ModelResponse(
            provider="ollama",
            model=data.get("model", request.model or self.model),
            output=data["message"]["content"],
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
            duration_ms=duration,
        )

    async def stream(self, request: ModelRequest) -> AsyncIterator[str]:
        """Stream responses from Ollama's /api/chat endpoint."""
        async with httpx.AsyncClient(base_url=self.base_url, timeout=120.0) as client:
            payload: dict[str, Any] = {
                "model": request.model or self.model,
                "messages": self._to_messages(request.input),
                "stream": True,
                **request.parameters,
            }
            async with client.stream("POST", "/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    if content := chunk.get("message", {}).get("content"):
                        yield content

    def get_pydantic_model(self, model_name: str | None = None) -> Any:
        """Return a pydantic-ai OpenAIChatModel pointing at Ollama's OpenAI-compat endpoint."""
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            base_url=f"{self.base_url}/v1",
            api_key="ollama",
        )
        provider = OpenAIProvider(openai_client=client)
        return OpenAIChatModel(model_name=model_name or self.model, provider=provider)

    @staticmethod
    def _to_messages(input: Any) -> list[dict[str, Any]]:
        """Convert input to Ollama message format."""
        if isinstance(input, str):
            return [{"role": "user", "content": input}]
        if isinstance(input, list):
            return input
        return [{"role": "user", "content": str(input)}]
