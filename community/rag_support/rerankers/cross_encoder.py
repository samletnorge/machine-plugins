"""Cross-encoder reranker."""

from __future__ import annotations
import asyncio
from typing import Any
from vectorstore_support.schemas import SearchResult
from rag_support.models import RankedResult
from rag_support.rerankers.base import BaseReranker


class CrossEncoderReranker(BaseReranker):
    def __init__(self, model: Any = None) -> None:
        self.model = model

    async def rerank(
        self, query: str, results: list[SearchResult]
    ) -> list[RankedResult]:
        if not results or self.model is None:
            return [
                RankedResult(
                    id=r.id,
                    text=r.text or "",
                    original_score=r.score,
                    rerank_score=r.score,
                    metadata=r.metadata,
                )
                for r in results
            ]
        pairs = [(query, r.text or "") for r in results]
        scores = await asyncio.to_thread(self.model.predict, pairs)
        ranked = [
            RankedResult(
                id=r.id,
                text=r.text or "",
                original_score=r.score,
                rerank_score=float(s),
                metadata=r.metadata,
            )
            for r, s in zip(results, scores)
        ]
        ranked.sort(key=lambda r: r.rerank_score, reverse=True)
        return ranked
