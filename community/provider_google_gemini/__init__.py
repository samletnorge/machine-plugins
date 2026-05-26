"""provider_google_gemini: Google Gemini LLM provider via pydantic-ai."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class GoogleGeminiProviderPlugin:
    async def initialize(self, config=None, **kwargs):
        config = config or {}
        self._api_key = config.get("api_key")
        self._model = config.get("model", "gemini-2.0-flash")

    async def setup(self, ctx: PluginContext):
        from pydantic_ai import Agent  # ImportError → lazy skip

        from .provider import GoogleGeminiLLMProvider

        if not self._api_key:
            return

        provider = GoogleGeminiLLMProvider(api_key=self._api_key, model=self._model)
        ctx.register("model_provider", "google-gemini", provider)

    async def shutdown(self, **kwargs):
        pass
