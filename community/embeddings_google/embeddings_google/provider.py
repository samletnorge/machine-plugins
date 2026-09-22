"""Google GenAI embedding provider — uses google-genai SDK."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable

from google import genai

from embeddings.schemas import EmbeddingRequest, EmbeddingResult


class GoogleEmbeddingProvider:
    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-004",
        dimensions: int = 768,
        hook_caller: Callable[..., Any] | None = None,
    ):
        self._client = genai.Client(api_key=api_key)
        self.model = model
        self.dimensions = dimensions
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
        model = request.model_ref or self.model
        await self._fire("before_embed", request=request)
        # google-genai is synchronous; run it off the event loop.
        response = await asyncio.to_thread(
            self._client.models.embed_content,
            model=model,
            contents=texts,
            config={"output_dimensionality": self.dimensions},
        )
        duration = (time.monotonic() - start) * 1000
        vectors = [list(e.values) for e in response.embeddings]
        dimensions = len(vectors[0]) if vectors else 0
        result = EmbeddingResult(
            vectors=vectors,
            model_ref=model,
            dimensions=dimensions,
            usage={},
            duration_ms=duration,
        )
        await self._fire("after_embed", request=request, result=result)
        return result
