"""Google GenAI embedding provider — uses google-genai SDK."""

from __future__ import annotations

import time

from google import genai

from embeddings.schemas import EmbeddingRequest, EmbeddingResult


class GoogleEmbeddingProvider:
    def __init__(
        self, api_key: str, model: str = "text-embedding-004", dimensions: int = 768
    ):
        self._client = genai.Client(api_key=api_key)
        self.model = model
        self.dimensions = dimensions

    async def invoke(self, request):
        if isinstance(request, EmbeddingRequest):
            return await self.embed(request)
        raise TypeError(f"Unsupported request type: {type(request)}")

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        start = time.monotonic()
        texts = [request.input] if isinstance(request.input, str) else request.input
        model = request.model_ref or self.model
        response = self._client.models.embed_content(
            model=model,
            contents=texts,
            config={"output_dimensionality": self.dimensions},
        )
        duration = (time.monotonic() - start) * 1000
        vectors = [list(e.values) for e in response.embeddings]
        dimensions = len(vectors[0]) if vectors else 0
        return EmbeddingResult(
            vectors=vectors,
            model_ref=model,
            dimensions=dimensions,
            usage={},
            duration_ms=duration,
        )
