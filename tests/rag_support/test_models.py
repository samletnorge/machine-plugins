"""Tests for RAG data models and ABCs."""

import pytest
from machine_core.plugins.rag_support.models import (
    Chunk,
    RankedResult,
    DocumentMetadata,
    IngestDocument,
)
from machine_core.plugins.rag_support.chunking.base import Chunker
from machine_core.plugins.rag_support.extractors.base import MetadataExtractor
from machine_core.plugins.rag_support.rerankers.base import BaseReranker


def test_chunk_has_required_fields():
    chunk = Chunk(text="Hello world", index=0, metadata={"source": "test.md"})
    assert chunk.text == "Hello world"
    assert chunk.index == 0
    assert chunk.metadata["source"] == "test.md"


def test_chunk_defaults():
    chunk = Chunk(text="Hello", index=0)
    assert chunk.metadata == {}
    assert chunk.start_char is None
    assert chunk.end_char is None


def test_chunk_with_offsets():
    chunk = Chunk(text="Hello", index=0, start_char=0, end_char=5)
    assert chunk.start_char == 0
    assert chunk.end_char == 5


def test_ranked_result():
    result = RankedResult(
        id="doc1",
        text="Hello world",
        original_score=0.8,
        rerank_score=0.95,
        metadata={},
    )
    assert result.rerank_score > result.original_score


def test_document_metadata():
    meta = DocumentMetadata(
        title="Test Doc",
        summary="A test",
        keywords=["test", "doc"],
        questions=["What is this?"],
        source="test.md",
    )
    assert meta.title == "Test Doc"
    assert len(meta.keywords) == 2


def test_ingest_document():
    doc = IngestDocument(id="doc1", text="Hello world", metadata={"source": "test"})
    assert doc.id == "doc1"
    assert doc.metadata["source"] == "test"


def test_chunker_is_abstract():
    with pytest.raises(TypeError):
        Chunker()


def test_metadata_extractor_is_abstract():
    with pytest.raises(TypeError):
        MetadataExtractor()


def test_base_reranker_is_abstract():
    with pytest.raises(TypeError):
        BaseReranker()
