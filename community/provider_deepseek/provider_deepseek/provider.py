"""DeepSeek LLM provider — pure httpx over the OpenAI-compatible API.

DeepSeek implements the OpenAI `/chat/completions` contract, so this provider
parses the standard `choices[0].message` shape (including OpenAI-style
`tool_calls`) and needs no vendor SDK. `get_pydantic_model` bridges to
pydantic-ai for agent runtimes that want a native model object.
"""

from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator

import httpx

from model_provider_support.schemas import ModelRequest, ModelResponse


class DeepSeekLLMProvider:
    """Provider implementation for the DeepSeek API."""

    def __init__(
        self,
        base_url: str = "https://api.deepseek.com",
        api_key: str = "",
        model: str = "deepseek-chat",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def invoke(self, request: Any) -> Any:
        if isinstance(request, ModelRequest):
            return await self.generate(request)
        raise TypeError(f"Unsupported request type: {type(request)}")

    async def generate(self, request: ModelRequest) -> ModelResponse:
        start = time.monotonic()
        payload: dict[str, Any] = {
            "model": request.model or self.model,
            "messages": self._to_messages(request.input),
            "stream": False,
            **request.parameters,
        }
        async with httpx.AsyncClient(base_url=self.base_url, timeout=120.0) as client:
            resp = await client.post(
                "/chat/completions", json=payload, headers=self._headers()
            )
            resp.raise_for_status()
            data = resp.json()

        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message", {})
        usage = data.get("usage", {})
        return ModelResponse(
            provider="deepseek",
            model=data.get("model", request.model or self.model),
            output=message.get("content"),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            },
            duration_ms=(time.monotonic() - start) * 1000,
            tool_calls=message.get("tool_calls"),
        )

    async def stream(self, request: ModelRequest) -> AsyncIterator[str]:
        payload: dict[str, Any] = {
            "model": request.model or self.model,
            "messages": self._to_messages(request.input),
            "stream": True,
            **request.parameters,
        }
        async with httpx.AsyncClient(base_url=self.base_url, timeout=120.0) as client:
            async with client.stream(
                "POST", "/chat/completions", json=payload, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    delta = (chunk.get("choices") or [{}])[0].get("delta", {})
                    if content := delta.get("content"):
                        yield content

    def get_pydantic_model(self, model_name: str | None = None) -> Any:
        from openai import AsyncOpenAI
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)
        provider = OpenAIProvider(openai_client=client)
        return OpenAIChatModel(model_name=model_name or self.model, provider=provider)

    @staticmethod
    def _to_messages(input: Any) -> list[dict[str, Any]]:
        if isinstance(input, str):
            return [{"role": "user", "content": input}]
        if isinstance(input, list):
            return input
        return [{"role": "user", "content": str(input)}]
