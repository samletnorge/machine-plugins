"""embeddings-ollama: Ollama embedding provider via OpenAI-compatible API."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class OllamaEmbeddingPlugin:
    async def initialize(self, config=None, **kwargs):
        config = config or {}
        self._base_url = config.get("base_url", "http://localhost:11434")
        self._model = config.get("model", "qwen3-embedding:8b")

    async def setup(self, ctx: PluginContext):
        import httpx  # noqa: F401 — ImportError = lazy skip

        from .provider import OllamaEmbeddingProvider

        provider = OllamaEmbeddingProvider(base_url=self._base_url, model=self._model)
        ctx.register("embedding", "ollama", provider)

    async def shutdown(self, **kwargs):
        pass
