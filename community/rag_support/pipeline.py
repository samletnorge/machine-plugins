"""RAG pipeline: ingest (chunk -> extract -> embed -> store) and retrieve (embed -> search -> rerank -> return).

Uses vectorstore_support schemas for vector store communication.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from rag_support.chunking.base import Chunker
from rag_support.extractors.base import MetadataExtractor
from rag_support.models import IngestDocument, RankedResult
from rag_support.rerankers.base import BaseReranker
from vectorstore_support.schemas import (
    SearchRequest,
    SearchResult,
    UpsertRequest,
)


class RAGPipeline:
    """End-to-end RAG pipeline.

    Args:
        chunker: Strategy for splitting documents into chunks.
        extractors: Metadata extractors to run on each chunk.
        vector_store: Vector store instance (from vectorstore_lancedb or similar).
        embedder: Object with async embed(text) -> list[float] and embed_batch(texts) -> list[list[float]].
        reranker: Optional reranker for result reranking.
        table: Vector store table name (default: "rag_documents").
    """

    def __init__(
        self,
        chunker: Chunker,
        extractors: list[MetadataExtractor],
        vector_store: Any,
        embedder: Any,
        reranker: BaseReranker | None = None,
        table: str = "rag_documents",
    ) -> None:
        self.chunker = chunker
        self.extractors = extractors
        self.vector_store = vector_store
        self.embedder = embedder
        self.reranker = reranker
        self.table = table

    async def ingest(self, documents: list[IngestDocument]) -> int:
        """Ingest documents: chunk -> extract metadata -> embed -> store.

        Returns:
            Number of vector documents stored.
        """
        if not documents:
            return 0

        all_upserts: list[UpsertRequest] = []

        for doc in documents:
            chunks = self.chunker.chunk(doc.text)
            if not chunks:
                continue

            texts = [c.text for c in chunks]
            embeddings = await self.embedder.embed_batch(texts)

            for chunk, embedding in zip(chunks, embeddings):
                merged_metadata = {**doc.metadata}
                merged_metadata["source_id"] = doc.id
                merged_metadata["chunk_index"] = chunk.index

                for extractor in self.extractors:
                    try:
                        extracted = await extractor.extract(chunk.text)
                        merged_metadata.update(extracted)
                    except Exception as e:
                        logger.warning(
                            f"Extractor {type(extractor).__name__} failed: {e}"
                        )

                chunk_id = f"{doc.id}::{chunk.index}"
                all_upserts.append(
                    UpsertRequest(
                        id=chunk_id,
                        vector=embedding,
                        text=chunk.text,
                        metadata=merged_metadata,
                        table=self.table,
                    )
                )

        if all_upserts:
            await self.vector_store.upsert(all_upserts)
            logger.info(
                f"Ingested {len(all_upserts)} chunks from {len(documents)} documents"
            )

        return len(all_upserts)

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filter: dict | None = None,
        rerank: bool = False,
    ) -> list[SearchResult] | list[RankedResult]:
        """Retrieve relevant chunks for a query.

        Args:
            query: The search query.
            top_k: Number of results.
            filter: Optional metadata filter.
            rerank: Whether to rerank results.

        Returns:
            List of SearchResult or RankedResult.
        """
        embedding = await self.embedder.embed(query)
        if not embedding:
            return []

        request = SearchRequest(
            query_vector=embedding,
            top_k=top_k,
            filter=filter,
            table=self.table,
        )
        results = await self.vector_store.search(request)

        if rerank and self.reranker is not None:
            return await self.reranker.rerank(query, results)

        return results
