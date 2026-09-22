"""provider_deepseek: DeepSeek LLM provider over the OpenAI-compatible API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class DeepSeekProviderPlugin:
    """Registers the DeepSeek model provider."""

    async def initialize(self, config=None, **kwargs):
        config = config or {}
        self._base_url = config.get("base_url", "https://api.deepseek.com")
        self._api_key = config.get("api_key") or ""
        self._model = config.get("model", "deepseek-chat")

    async def setup(self, ctx: PluginContext):
        if not self._api_key:
            logger.warning(
                "provider_deepseek: no DEEPSEEK_API_KEY configured; skipping registration"
            )
            return

        from .provider import DeepSeekLLMProvider

        provider = DeepSeekLLMProvider(
            base_url=self._base_url,
            api_key=self._api_key,
            model=self._model,
        )
        ctx.register("model_provider", "deepseek", provider)

    async def shutdown(self, **kwargs):
        pass
