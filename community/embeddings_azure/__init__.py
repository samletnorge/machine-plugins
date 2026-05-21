"""embeddings-azure: Azure OpenAI embedding provider."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class AzureEmbeddingPlugin:
    async def initialize(self, **kwargs):
        pass

    async def setup(self, ctx: PluginContext):
        import httpx  # noqa: F401 — ImportError = lazy skip

        from .provider import AzureEmbeddingProvider

        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        api_key = os.environ.get("AZURE_OPENAI_API_KEY", "")
        deployment = os.environ.get("AZURE_OPENAI_EMBED_DEPLOYMENT", "")
        api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        use_token_auth = os.environ.get("AZURE_USE_TOKEN_AUTH", "").lower() in (
            "1",
            "true",
            "yes",
        )

        provider = AzureEmbeddingProvider(
            endpoint=endpoint,
            api_key=api_key,
            deployment=deployment,
            api_version=api_version,
            use_token_auth=use_token_auth,
        )
        ctx.register("embedding", "azure", provider)

    async def shutdown(self, **kwargs):
        pass
