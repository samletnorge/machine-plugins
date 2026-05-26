"""embeddings_sentence_transformers: SentenceTransformers embedding provider."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from embeddings.schemas import EmbeddingRequest, EmbeddingResult

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

    async def invoke(self, request: Any) -> Any:
        if isinstance(request, EmbeddingRequest):
            return await self.embed(request)
        raise TypeError(f"Unsupported request type: {type(request)}")

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        """Embed text input into vectors."""
        start = time.monotonic()
        model = self._get_model()
        texts = request.input if isinstance(request.input, list) else [request.input]
        embeddings = model.encode(texts, convert_to_numpy=True)
        vectors = embeddings.tolist()
        dimensions = len(vectors[0]) if vectors else 0
        return EmbeddingResult(
            vectors=vectors,
            model_ref=request.model_ref or self._model_name,
            dimensions=dimensions,
            usage={"input_count": len(texts)},
            duration_ms=(time.monotonic() - start) * 1000,
        )
