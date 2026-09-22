"""Azure OpenAI embedding provider — uses REST API."""

from __future__ import annotations

import time
from typing import Any, Callable

import httpx

from embeddings.schemas import EmbeddingRequest, EmbeddingResult


class AzureEmbeddingProvider:
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment: str,
        api_version: str = "2024-12-01-preview",
        use_token_auth: bool = False,
        hook_caller: Callable[..., Any] | None = None,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.deployment = deployment
        self.api_version = api_version
        self.use_token_auth = use_token_auth
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

    def _headers(self) -> dict[str, str]:
        if self.use_token_auth:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {"api-key": self.api_key}

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        start = time.monotonic()
        texts = [request.input] if isinstance(request.input, str) else request.input
        await self._fire("before_embed", request=request)
        url = (
            f"{self.endpoint}/openai/deployments/{self.deployment}"
            f"/embeddings?api-version={self.api_version}"
        )
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                url,
                headers=self._headers(),
                json={"input": texts},
            )
            resp.raise_for_status()
            data = resp.json()
        duration = (time.monotonic() - start) * 1000
        vectors = [item["embedding"] for item in data["data"]]
        dimensions = len(vectors[0]) if vectors else 0
        result = EmbeddingResult(
            vectors=vectors,
            model_ref=data.get("model", self.deployment),
            dimensions=dimensions,
            usage=data.get("usage", {}),
            duration_ms=duration,
        )
        await self._fire("after_embed", request=request, result=result)
        return result
