"""provider-azure-openai: Azure OpenAI LLM provider via pydantic-ai."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class AzureOpenAIProviderPlugin:
    async def initialize(self, config=None, **kwargs):
        config = config or {}
        self._endpoint = config.get("endpoint")
        self._api_key = config.get("api_key")
        self._deployment = config.get("deployment", "gpt-4o")
        self._api_version = config.get("api_version", "2024-12-01-preview")
        self._use_token_auth = config.get("use_token_auth", False)

    async def setup(self, ctx: PluginContext):
        from pydantic_ai import Agent  # ImportError → lazy skip

        from .provider import AzureOpenAILLMProvider

        if not self._endpoint:
            return  # Not configured, skip silently

        provider = AzureOpenAILLMProvider(
            endpoint=self._endpoint,
            api_key=self._api_key,
            deployment=self._deployment,
            api_version=self._api_version,
            use_token_auth=self._use_token_auth,
        )
        ctx.register("model_provider", "azure-openai", provider)

    async def shutdown(self, **kwargs):
        pass
