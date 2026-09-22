"""LLM-based reranker."""

from __future__ import annotations
from typing import Any
from loguru import logger
from vectorstore_support.schemas import SearchResult
from rag_support.models import RankedResult
from rag_support.rerankers.base import BaseReranker


class LLMReranker(BaseReranker):
    def __init__(self, llm: Any = None) -> None:
        self.llm = llm

    async def rerank(
        self, query: str, results: list[SearchResult]
    ) -> list[RankedResult]:
        if not results:
            return []
        ranked: list[RankedResult] = []
        for result in results:
            try:
                prompt = (
                    "Rate the relevance of the following document to the query "
                    "on a scale of 0.0 to 1.0. Return ONLY a number.\n\n"
                    f"Query: {query}\n\nDocument: {(result.text or '')[:1000]}"
                )
                response = await self.llm.generate(prompt)
                score = float(response.strip())
                score = max(0.0, min(1.0, score))
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning(f"LLM rerank failed for {result.id}: {e}")
                score = result.score
            ranked.append(
                RankedResult(
                    id=result.id,
                    text=result.text or "",
                    original_score=result.score,
                    rerank_score=score,
                    metadata=result.metadata,
                )
            )
        ranked.sort(key=lambda r: r.rerank_score, reverse=True)
        return ranked
