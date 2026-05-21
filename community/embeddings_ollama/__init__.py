"""embeddings-ollama: Ollama embedding provider via OpenAI-compatible API."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class OllamaEmbeddingPlugin:
    async def initialize(self, **kwargs):
        pass

    async def setup(self, ctx: PluginContext):
        import httpx  # noqa: F401 — ImportError = lazy skip

        from .provider import OllamaEmbeddingProvider

        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")

        provider = OllamaEmbeddingProvider(base_url=base_url, model=model)
        ctx.register("embedding", "ollama", provider)

    async def shutdown(self, **kwargs):
        pass
