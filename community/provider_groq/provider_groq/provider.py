"""Groq LLM provider — pydantic-ai wrapper."""

from __future__ import annotations

import time
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from model_provider_support.compat import agent_run_output, agent_run_usage
from model_provider_support.schemas import (
    ModelRequest,
    ModelResponse,
)


class GroqLLMProvider:
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile") -> None:
        self._model = OpenAIChatModel(
            model_name=model,
            provider=OpenAIProvider(
                api_key=api_key, base_url="https://api.groq.com/openai/v1"
            ),
        )
        self._agent = Agent(model=self._model)
        self._provider_name = "groq"
        self._model_name = model

    def get_pydantic_model(self, model_name: str | None = None) -> Any:
        return self._model

    async def invoke(self, request: Any) -> Any:
        if isinstance(request, ModelRequest):
            return await self.generate(request)
        raise TypeError(f"Unsupported request type: {type(request)}")

    async def generate(self, request: ModelRequest) -> ModelResponse:
        start = time.monotonic()
        prompt = request.input if isinstance(request.input, str) else str(request.input)
        result = await self._agent.run(prompt)

        return ModelResponse(
            provider=self._provider_name,
            model=self._model_name,
            output=agent_run_output(result),
            usage=agent_run_usage(result),
            duration_ms=(time.monotonic() - start) * 1000,
        )
