"""embeddings_sentence_transformers: SentenceTransformers embedding provider."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class EmbeddingsSentenceTransformersPlugin:
    """Provides text embeddings via sentence-transformers library."""

    def __init__(self):
        self._model = None
        self._model_name: str = "all-MiniLM-L6-v2"

    async def initialize(self, **kwargs):
        pass

    async def setup(self, ctx: PluginContext):
        config = ctx.config or {}
        self._model_name = config.get("model", self._model_name)
        ctx.register_implementation("embedding", "sentence_transformers", self)

    async def shutdown(self, **kwargs):
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
            self._model = SentenceTransformer(self._model_name)
        return self._model

    async def embed(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        """Embed a list of texts into vectors."""
        model = self._get_model()
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    async def embed_query(self, text: str, **kwargs: Any) -> list[float]:
        """Embed a single query text."""
        result = await self.embed([text], **kwargs)
        return result[0]
