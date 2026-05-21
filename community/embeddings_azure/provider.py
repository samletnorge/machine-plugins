"""Azure OpenAI embedding provider — uses REST API."""

from __future__ import annotations

import time

import httpx

from machine_core.plugins.embeddings.schemas import EmbeddingRequest, EmbeddingResult


class AzureEmbeddingProvider:
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment: str,
        api_version: str = "2024-12-01-preview",
        use_token_auth: bool = False,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.deployment = deployment
        self.api_version = api_version
        self.use_token_auth = use_token_auth

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
        return EmbeddingResult(
            vectors=vectors,
            model_ref=data.get("model", self.deployment),
            dimensions=dimensions,
            usage=data.get("usage", {}),
            duration_ms=duration,
        )
