"""Tests for RAG pipeline with reranker integration."""

import pytest
from machine_core.plugins.rag_support.pipeline import RAGPipeline
from machine_core.plugins.rag_support.models import IngestDocument, RankedResult
from machine_core.plugins.rag_support.chunking.recursive import RecursiveChunker
from machine_core.plugins.rag_support.rerankers.llm import LLMReranker
from machine_core.plugins.vectorstore_support.schemas import SearchResult, UpsertRequest


class MockEmbedder:
    async def embed(self, text):
        return [hash(text) % 100 / 100.0, 0.5]

    async def embed_batch(self, texts, **kw):
        return [await self.embed(t) for t in texts]


class InMemoryStore:
    def __init__(self):
        self.records = []

    async def upsert(self, records):
        for r in records:
            self.records = [rec for rec in self.records if rec["id"] != r.id]
            self.records.append(
                {
                    "id": r.id,
                    "vector": r.vector,
                    "text": r.text or "",
                    "metadata": r.metadata,
                }
            )

    async def search(self, request):
        results = []
        for rec in self.records:
            score = sum(a * b for a, b in zip(request.query_vector, rec["vector"]))
            results.append(
                SearchResult(
                    id=rec["id"],
                    text=rec["text"],
                    score=score,
                    metadata=rec["metadata"],
                )
            )
        results.sort(key=lambda r: r.score, reverse=True)
        return results[: request.top_k]


class MockLLM:
    async def generate(self, prompt):
        return "0.85"


async def test_retrieve_with_reranker():
    pipeline = RAGPipeline(
        chunker=RecursiveChunker(chunk_size=50),
        extractors=[],
        vector_store=InMemoryStore(),
        embedder=MockEmbedder(),
        reranker=LLMReranker(llm=MockLLM()),
    )
    await pipeline.ingest([IngestDocument(id="d1", text="Hello world. " * 20)])
    results = await pipeline.retrieve("hello", top_k=3, rerank=True)
    assert len(results) > 0
    assert all(isinstance(r, RankedResult) for r in results)


async def test_retrieve_without_reranker():
    pipeline = RAGPipeline(
        chunker=RecursiveChunker(chunk_size=50),
        extractors=[],
        vector_store=InMemoryStore(),
        embedder=MockEmbedder(),
    )
    await pipeline.ingest([IngestDocument(id="d1", text="Hello world. " * 20)])
    results = await pipeline.retrieve("hello", top_k=3)
    assert len(results) > 0
    assert all(isinstance(r, SearchResult) for r in results)
