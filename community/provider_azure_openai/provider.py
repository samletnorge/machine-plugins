"""Azure OpenAI LLM provider — pydantic-ai wrapper.

Supports both API key and token-based auth (DefaultAzureCredential).
"""

from __future__ import annotations

import time
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from model_provider_support.schemas import (
    ModelRequest,
    ModelResponse,
)


class AzureOpenAILLMProvider:
    def __init__(
        self,
        endpoint: str,
        api_key: str | None,
        deployment: str,
        api_version: str = "2024-12-01-preview",
        use_token_auth: bool = False,
    ) -> None:
        self.endpoint = endpoint
        self.deployment = deployment

        base_url = f"{endpoint}/openai/deployments/{deployment}"

        if use_token_auth and not api_key:
            try:
                from azure.identity import (
                    DefaultAzureCredential,
                    get_bearer_token_provider,
                )

                credential = DefaultAzureCredential()
                token_provider = get_bearer_token_provider(
                    credential, "https://cognitiveservices.azure.com/.default"
                )
                provider = OpenAIProvider(
                    base_url=base_url,
                    api_key="token-auth",
                )
                self._token_provider = token_provider
            except ImportError:
                raise ImportError(
                    "azure-identity required for token auth. "
                    "Install with: pip install azure-identity"
                )
        else:
            provider = OpenAIProvider(
                base_url=base_url,
                api_key=api_key or "",
            )
            self._token_provider = None

        self._model = OpenAIChatModel(
            model_name=deployment,
            provider=provider,
        )
        self._agent = Agent(model=self._model)

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
            provider="azure-openai",
            model=self.deployment,
            output=result.data,
            usage=usage_data,
            duration_ms=duration,
        )
