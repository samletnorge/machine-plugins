"""Vertex AI Claude LLM provider — pydantic-ai wrapper."""

from __future__ import annotations

import time
from typing import Any

from anthropic import AsyncAnthropicVertex
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

from model_provider_support.compat import agent_run_output, agent_run_usage
from model_provider_support.schemas import (
    ModelRequest,
    ModelResponse,
)


class VertexClaudeLLMProvider:
    def __init__(
        self, project: str, location: str, model: str = "claude-sonnet-4-20250514"
    ) -> None:
        self._model = AnthropicModel(
            model_name=model,
            provider=AnthropicProvider(
                anthropic_client=AsyncAnthropicVertex(
                    project_id=project, region=location
                ),
            ),
        )
        self._agent = Agent(model=self._model)
        self._provider_name = "vertex-claude"
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
