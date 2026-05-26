"""provider_groq: Groq LLM provider via pydantic-ai."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class GroqProviderPlugin:
    async def initialize(self, config=None, **kwargs):
        config = config or {}
        self._api_key = config.get("api_key")
        self._model = config.get("model", "llama-3.3-70b-versatile")

    async def setup(self, ctx: PluginContext):
        from pydantic_ai import Agent  # ImportError → lazy skip

        from .provider import GroqLLMProvider

        if not self._api_key:
            return

        provider = GroqLLMProvider(api_key=self._api_key, model=self._model)
        ctx.register("model_provider", "groq", provider)

    async def shutdown(self, **kwargs):
        pass
