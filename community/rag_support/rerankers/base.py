"""Abstract base class for rerankers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from vectorstore_support.schemas import SearchResult
from rag_support.models import RankedResult


class BaseReranker(ABC):
    """Abstract base for reranking strategies."""

    @abstractmethod
    async def rerank(
        self, query: str, results: list[SearchResult]
    ) -> list[RankedResult]:
        """Rerank results by relevance to query.

        Args:
            query: The original search query.
            results: Initial retrieval results (from vectorstore_support schema).

        Returns:
            Reranked results sorted by rerank_score descending.
        """
        ...
