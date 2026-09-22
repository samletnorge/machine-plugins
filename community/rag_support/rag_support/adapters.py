"""Adapters that bridge machine-core provider interfaces to RAG component interfaces."""

from __future__ import annotations

from typing import Any


class EmbedderAdapter:
    """Wraps a machine-core embedding provider into the interface SemanticChunker expects.

    SemanticChunker calls: embedder.embed_batch(texts: list[str]) -> list[list[float]]
    Machine-core providers: provider.embed(EmbeddingRequest) -> EmbeddingResult
    """

    def __init__(self, provider: Any, model: str | None = None) -> None:
        self._provider = provider
        self._model = model

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        from embeddings.schemas import EmbeddingRequest

        request = EmbeddingRequest(input=texts, model_ref=self._model)
        result = await self._provider.embed(request)
        return result.vectors

    async def embed(self, text: str) -> list[float]:
        """Embed a single text, returning the vector directly."""
        vectors = await self.embed_batch([text])
        return vectors[0]


class LLMAdapter:
    """Wraps a machine-core model provider into the interface RAG components expect.

    RAG components call: llm.generate(prompt: str) -> str
    Machine-core providers: provider.generate(ModelRequest) -> ModelResponse
    """

    def __init__(self, provider: Any, model: str | None = None) -> None:
        self._provider = provider
        self._model = model

    async def generate(self, prompt: str) -> str:
        from model_provider_support.schemas import ModelRequest

        request = ModelRequest(
            provider=self._provider.__class__.__name__,
            model=self._model or "default",
            input=[{"role": "user", "content": prompt}],
            stream=False,
        )
        response = await self._provider.generate(request)
        return response.output or ""
