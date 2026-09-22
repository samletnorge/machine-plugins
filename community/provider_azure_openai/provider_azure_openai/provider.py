"""Azure OpenAI LLM provider — pydantic-ai wrapper.

Uses the Azure-aware OpenAI client so ``api_version`` and the Azure endpoint are
honoured, with either API-key or Entra ID (token) authentication.
"""

from __future__ import annotations

import time
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from model_provider_support.compat import agent_run_output, agent_run_usage
from model_provider_support.schemas import ModelRequest, ModelResponse

_AZURE_SCOPE = "https://cognitiveservices.azure.com/.default"


class AzureOpenAILLMProvider:
    def __init__(
        self,
        endpoint: str,
        api_key: str | None,
        deployment: str,
        api_version: str = "2024-12-01-preview",
        use_token_auth: bool = False,
    ) -> None:
        from openai import AsyncAzureOpenAI

        self.endpoint = endpoint
        self.deployment = deployment
        self.api_version = api_version

        client_kwargs: dict[str, Any] = {
            "azure_endpoint": endpoint,
            "api_version": api_version,
        }
        if use_token_auth and not api_key:
            try:
                from azure.identity import (
                    DefaultAzureCredential,
                    get_bearer_token_provider,
                )
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise ImportError(
                    "azure-identity required for token auth. "
                    "Install with: pip install azure-identity"
                ) from exc
            credential = DefaultAzureCredential()
            client_kwargs["azure_ad_token_provider"] = get_bearer_token_provider(
                credential, _AZURE_SCOPE
            )
        else:
            client_kwargs["api_key"] = api_key or ""

        client = AsyncAzureOpenAI(**client_kwargs)
        self._provider = OpenAIProvider(openai_client=client)
        self._model = OpenAIChatModel(
            model_name=deployment, provider=self._provider
        )
        self._agent = Agent(model=self._model)

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
            provider="azure-openai",
            model=self.deployment,
            output=agent_run_output(result),
            usage=agent_run_usage(result),
            duration_ms=(time.monotonic() - start) * 1000,
        )
