"""Ollama embedding provider — uses /v1/embeddings (OpenAI-compatible)."""

from __future__ import annotations

import time
from typing import Any, Callable

import httpx

from embeddings.schemas import EmbeddingRequest, EmbeddingResult


class OllamaEmbeddingProvider:
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen3-embedding:8b",
        hook_caller: Callable[..., Any] | None = None,
    ):
        self.base_url = base_url
        self.model = model
        self._hook_caller = hook_caller

    async def _fire(self, hook_name: str, **kwargs: Any) -> None:
        if self._hook_caller is None:
            return
        try:
            result = self._hook_caller(hook_name, **kwargs)
            if hasattr(result, "__await__"):
                await result
        except Exception:  # noqa: BLE001 - hooks must not break embedding
            pass

    async def invoke(self, request):
        if isinstance(request, EmbeddingRequest):
            return await self.embed(request)
        raise TypeError(f"Unsupported request type: {type(request)}")

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        start = time.monotonic()
        texts = [request.input] if isinstance(request.input, str) else request.input
        await self._fire("before_embed", request=request)
        async with httpx.AsyncClient(base_url=self.base_url, timeout=300.0) as client:
            resp = await client.post(
                "/v1/embeddings",
                json={"model": request.model_ref or self.model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()
        duration = (time.monotonic() - start) * 1000
        vectors = [item["embedding"] for item in data["data"]]
        dimensions = len(vectors[0]) if vectors else 0
        result = EmbeddingResult(
            vectors=vectors,
            model_ref=data.get("model", self.model),
            dimensions=dimensions,
            usage=data.get("usage", {}),
            duration_ms=duration,
        )
        await self._fire("after_embed", request=request, result=result)
        return result
