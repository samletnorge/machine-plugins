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
        self._encode_batch_size: int = 256

    async def initialize(self, config=None, **kwargs):
        config = config or {}
        self._model_name = config.get("model", self._model_name)
        self._encode_batch_size = int(
            config.get("encode_batch_size", self._encode_batch_size)
        )

    async def setup(self, ctx: PluginContext):
        ctx.register("embedding", "sentence_transformers", self)

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
        embeddings = model.encode(
            texts,
            batch_size=self._encode_batch_size,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        vectors = embeddings.tolist()
        dimensions = len(vectors[0]) if vectors else 0
        return EmbeddingResult(
            vectors=vectors,
            model_ref=request.model_ref or self._model_name,
            dimensions=dimensions,
            usage={
                "input_count": len(texts),
                "encode_batch_size": self._encode_batch_size,
            },
            duration_ms=(time.monotonic() - start) * 1000,
        )
