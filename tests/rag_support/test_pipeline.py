"""Tests for the RAG pipeline."""

import pytest
from rag_support.pipeline import RAGPipeline
from rag_support.models import IngestDocument
from rag_support.chunking.recursive import RecursiveChunker
from vectorstore_support.schemas import SearchResult, UpsertRequest


class MockEmbedder:
    async def embed(self, text: str) -> list[float]:
        h = hash(text) % 1000
        return [h / 1000.0, (1000 - h) / 1000.0]

    async def embed_batch(self, texts: list[str], **kw) -> list[list[float]]:
        return [await self.embed(t) for t in texts]


class InMemoryVectorStore:
    """Minimal mock that matches vectorstore_lancedb interface."""

    def __init__(self):
        self.records: list[dict] = []

    async def upsert(self, records: list[UpsertRequest]) -> None:
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

    async def search(self, request) -> list[SearchResult]:
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


@pytest.fixture
def pipeline():
    return RAGPipeline(
        chunker=RecursiveChunker(chunk_size=100, chunk_overlap=0),
        extractors=[],
        vector_store=InMemoryVectorStore(),
        embedder=MockEmbedder(),
    )


async def test_ingest_stores_chunks(pipeline):
    docs = [
        IngestDocument(
            id="doc1", text="Hello world. " * 20, metadata={"source": "test"}
        )
    ]
    count = await pipeline.ingest(docs)
    assert count > 0
    assert len(pipeline.vector_store.records) > 0


async def test_retrieve_returns_results(pipeline):
    docs = [IngestDocument(id="doc1", text="Python is a programming language. " * 10)]
    await pipeline.ingest(docs)
    results = await pipeline.retrieve("What is Python?", top_k=3)
    assert len(results) > 0


async def test_ingest_empty():
    p = RAGPipeline(
        chunker=RecursiveChunker(),
        extractors=[],
        vector_store=InMemoryVectorStore(),
        embedder=MockEmbedder(),
    )
    count = await p.ingest([])
    assert count == 0


async def test_retrieve_empty_store():
    p = RAGPipeline(
        chunker=RecursiveChunker(),
        extractors=[],
        vector_store=InMemoryVectorStore(),
        embedder=MockEmbedder(),
    )
    results = await p.retrieve("anything")
    assert results == []


class AsyncAwareChunker:
    """Chunker with an async path that must be preferred by the pipeline."""

    def __init__(self):
        self.used_async = False

    def chunk(self, text: str, **kwargs):
        raise AssertionError("sync chunk() should not be called in async ingest")

    async def chunk_async(self, text: str, **kwargs):
        from rag_support.models import Chunk

        self.used_async = True
        return [Chunk(text=text, index=0)]


async def test_ingest_prefers_chunk_async():
    chunker = AsyncAwareChunker()
    p = RAGPipeline(
        chunker=chunker,
        extractors=[],
        vector_store=InMemoryVectorStore(),
        embedder=MockEmbedder(),
    )
    count = await p.ingest([IngestDocument(id="d1", text="Hello async world")])
    assert count == 1
    assert chunker.used_async is True
