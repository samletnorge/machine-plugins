"""Grok (xAI) LLM provider — pydantic-ai wrapper."""

from __future__ import annotations

import time
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from machine_core.plugins.model_provider_support.schemas import (
    ModelRequest,
    ModelResponse,
)


class GrokLLMProvider:
    def __init__(self, api_key: str, model: str = "grok-3") -> None:
        self._model = OpenAIChatModel(
            model_name=model,
            provider=OpenAIProvider(api_key=api_key, base_url="https://api.x.ai/v1"),
        )
        self._agent = Agent(model=self._model)
        self._provider_name = "grok"
        self._model_name = model

    async def invoke(self, request: Any) -> Any:
        if isinstance(request, ModelRequest):
            return await self.generate(request)
        raise TypeError(f"Unsupported request type: {type(request)}")

    async def generate(self, request: ModelRequest) -> ModelResponse:
        start = time.monotonic()
        prompt = request.input if isinstance(request.input, str) else str(request.input)
        result = await self._agent.run(prompt)
        duration = (time.monotonic() - start) * 1000

        usage_data = {}
        try:
            usage = result.usage()
            usage_data = {
                "prompt_tokens": getattr(usage, "request_tokens", 0),
                "completion_tokens": getattr(usage, "response_tokens", 0),
                "total_tokens": getattr(usage, "total_tokens", 0),
            }
        except Exception:
            pass

        return ModelResponse(
            provider=self._provider_name,
            model=self._model_name,
            output=result.data,
            usage=usage_data,
            duration_ms=duration,
        )
