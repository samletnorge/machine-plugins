"""RAG-based tool filtering."""

from __future__ import annotations

from typing import Any

from embeddings.schemas import EmbeddingRequest, EmbeddingResult
from tool_support.schemas import ToolDefinition
from vectorstore_support.schemas import (
    SearchRequest,
    SearchResult,
    UpsertRequest,
)

TOOLS_TABLE = "tools"


class ToolFilterManager:
    def __init__(self, embedder: Any, store: Any) -> None:
        self._embedder = embedder
        self._store = store

    async def index_tools(self, tools: list[ToolDefinition]) -> None:
        if not tools:
            return
        descriptions = [f"{t.name}: {t.description}" for t in tools]
        embed_result: EmbeddingResult = await self._embedder.embed(
            EmbeddingRequest(input=descriptions)
        )
        records = [
            UpsertRequest(
                id=tool.name,
                vector=vector,
                text=f"{tool.name}: {tool.description}",
                metadata={"name": tool.name, "description": tool.description},
                table=TOOLS_TABLE,
            )
            for tool, vector in zip(tools, embed_result.vectors)
        ]
        await self._store.upsert(records)

    async def filter(self, prompt: str, top_k: int = 10) -> list[SearchResult]:
        if not prompt.strip():
            return []
        embed_result: EmbeddingResult = await self._embedder.embed(
            EmbeddingRequest(input=prompt)
        )
        return await self._store.search(
            SearchRequest(
                query_vector=embed_result.vectors[0],
                top_k=top_k,
                table=TOOLS_TABLE,
            )
        )
