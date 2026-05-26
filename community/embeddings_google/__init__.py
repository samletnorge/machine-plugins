"""embeddings_google: Google GenAI embedding provider."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class GoogleEmbeddingPlugin:
    async def initialize(self, **kwargs):
        pass

    async def setup(self, ctx: PluginContext):
        from google import genai  # noqa: F401 — ImportError = lazy skip

        api_key = os.environ.get("GCP_API_KEY", "")
        if not api_key:
            from loguru import logger

            logger.debug(
                "embeddings_google: GCP_API_KEY not set, skipping. "
                "Set GCP_API_KEY to enable Google embeddings."
            )
            return

        from .provider import GoogleEmbeddingProvider

        model = os.environ.get("GOOGLE_EMBED_MODEL", "text-embedding-004")
        dimensions = int(os.environ.get("EMBEDDING_DIMENSIONS", "768"))

        provider = GoogleEmbeddingProvider(
            api_key=api_key, model=model, dimensions=dimensions
        )
        ctx.register("embedding", "google", provider)

    async def shutdown(self, **kwargs):
        pass
