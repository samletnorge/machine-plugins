"""Ollama embedding provider — uses /v1/embeddings (OpenAI-compatible)."""

from __future__ import annotations

import time

import httpx

from embeddings.schemas import EmbeddingRequest, EmbeddingResult


class OllamaEmbeddingProvider:
    def __init__(
        self, base_url: str = "http://localhost:11434", model: str = "qwen3-embedding:8b"
    ):
        self.base_url = base_url
        self.model = model

    async def invoke(self, request):
        if isinstance(request, EmbeddingRequest):
            return await self.embed(request)
        raise TypeError(f"Unsupported request type: {type(request)}")

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        start = time.monotonic()
        texts = [request.input] if isinstance(request.input, str) else request.input
        async with httpx.AsyncClient(base_url=self.base_url, timeout=60.0) as client:
            resp = await client.post(
                "/v1/embeddings",
                json={"model": request.model_ref or self.model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()
        duration = (time.monotonic() - start) * 1000
        vectors = [item["embedding"] for item in data["data"]]
        dimensions = len(vectors[0]) if vectors else 0
        return EmbeddingResult(
            vectors=vectors,
            model_ref=data.get("model", self.model),
            dimensions=dimensions,
            usage=data.get("usage", {}),
            duration_ms=duration,
        )
