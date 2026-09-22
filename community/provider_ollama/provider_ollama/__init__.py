"""provider_ollama: Pure httpx Ollama LLM provider."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class OllamaProviderPlugin:
    async def initialize(self, config=None, **kwargs):
        config = config or {}
        self._base_url = config.get("base_url", "http://localhost:11434")
        self._model = config.get("model", "llama3.2")

    async def setup(self, ctx: PluginContext):
        import httpx  # Will ImportError if httpx not installed → lazy skip

        from .provider import OllamaLLMProvider

        provider = OllamaLLMProvider(base_url=self._base_url, model=self._model)
        ctx.register("model_provider", "ollama", provider)

    async def shutdown(self, **kwargs):
        pass
