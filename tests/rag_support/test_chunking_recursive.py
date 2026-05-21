"""Tests for recursive character text splitter."""

import pytest
from machine_core.plugins.rag_support.chunking.recursive import RecursiveChunker
from machine_core.plugins.rag_support.chunking.base import Chunker
from machine_core.plugins.rag_support.models import Chunk


def test_is_chunker_subclass():
    assert issubclass(RecursiveChunker, Chunker)


def test_short_text_single_chunk():
    chunker = RecursiveChunker(chunk_size=100, chunk_overlap=0)
    chunks = chunker.chunk("Hello world")
    assert len(chunks) == 1
    assert chunks[0].text == "Hello world"
    assert chunks[0].index == 0


def test_splits_by_paragraphs():
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    chunker = RecursiveChunker(chunk_size=20, chunk_overlap=0)
    chunks = chunker.chunk(text)
    assert len(chunks) >= 2
    assert all(isinstance(c, Chunk) for c in chunks)


def test_splits_by_sentences_when_paragraph_too_long():
    text = "First sentence. Second sentence. Third sentence. Fourth sentence."
    chunker = RecursiveChunker(chunk_size=40, chunk_overlap=0)
    chunks = chunker.chunk(text)
    assert len(chunks) >= 2


def test_chunk_overlap():
    text = "Word " * 100  # 500 chars
    chunker = RecursiveChunker(chunk_size=50, chunk_overlap=10)
    chunks = chunker.chunk(text)
    assert len(chunks) >= 2
    for i in range(len(chunks) - 1):
        assert len(chunks[i].text) > 0


def test_respects_chunk_size():
    text = "Word " * 200
    chunker = RecursiveChunker(chunk_size=50, chunk_overlap=0)
    chunks = chunker.chunk(text)
    for c in chunks:
        assert len(c.text) <= 55  # Allow small tolerance for word boundaries


def test_empty_text():
    chunker = RecursiveChunker(chunk_size=100, chunk_overlap=0)
    chunks = chunker.chunk("")
    assert len(chunks) == 0


def test_indexes_are_sequential():
    text = "A. " * 100
    chunker = RecursiveChunker(chunk_size=20, chunk_overlap=0)
    chunks = chunker.chunk(text)
    for i, chunk in enumerate(chunks):
        assert chunk.index == i


def test_custom_separators():
    text = "a|b|c|d|e|f|g|h"
    chunker = RecursiveChunker(chunk_size=5, chunk_overlap=0, separators=["|"])
    chunks = chunker.chunk(text)
    assert len(chunks) >= 2
