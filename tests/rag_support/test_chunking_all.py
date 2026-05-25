"""Tests for all chunking strategies."""

import pytest
from rag_support.chunking.base import Chunker
from rag_support.models import Chunk
from rag_support.chunking.sentence import SentenceChunker
from rag_support.chunking.token import TokenChunker
from rag_support.chunking.markdown import MarkdownChunker
from rag_support.chunking.html import HTMLChunker
from rag_support.chunking.json_chunker import JSONChunker
from rag_support.chunking.code import CodeChunker
from rag_support.chunking.semantic import SemanticChunker


# --- SentenceChunker ---
class TestSentenceChunker:
    def test_is_chunker(self):
        assert issubclass(SentenceChunker, Chunker)

    def test_splits_sentences(self):
        text = "First sentence. Second sentence! Third sentence? Fourth."
        chunker = SentenceChunker(max_sentences=2)
        chunks = chunker.chunk(text)
        assert len(chunks) >= 2

    def test_single_sentence(self):
        chunker = SentenceChunker(max_sentences=5)
        chunks = chunker.chunk("Just one sentence.")
        assert len(chunks) == 1

    def test_empty_text(self):
        assert SentenceChunker().chunk("") == []


# --- TokenChunker ---
class TestTokenChunker:
    def test_is_chunker(self):
        assert issubclass(TokenChunker, Chunker)

    def test_splits_by_token_count(self):
        text = " ".join(f"word{i}" for i in range(100))
        chunker = TokenChunker(max_tokens=20, token_overlap=0)
        chunks = chunker.chunk(text)
        assert len(chunks) >= 4

    def test_empty_text(self):
        assert TokenChunker().chunk("") == []


# --- MarkdownChunker ---
class TestMarkdownChunker:
    def test_is_chunker(self):
        assert issubclass(MarkdownChunker, Chunker)

    def test_splits_by_headers(self):
        text = "# Title\nContent 1\n## Section\nContent 2\n## Section 2\nContent 3"
        chunks = MarkdownChunker().chunk(text)
        assert len(chunks) >= 2

    def test_preserves_header_in_metadata(self):
        text = "# My Title\nSome content here."
        chunks = MarkdownChunker().chunk(text)
        assert len(chunks) >= 1
        assert "header" in chunks[0].metadata or chunks[0].text.startswith("# My Title")

    def test_empty_text(self):
        assert MarkdownChunker().chunk("") == []


# --- HTMLChunker ---
class TestHTMLChunker:
    def test_is_chunker(self):
        assert issubclass(HTMLChunker, Chunker)

    def test_splits_by_tags(self):
        html = "<div><p>Para 1</p><p>Para 2</p></div><div><p>Para 3</p></div>"
        chunks = HTMLChunker().chunk(html)
        assert len(chunks) >= 2

    def test_empty_text(self):
        assert HTMLChunker().chunk("") == []


# --- JSONChunker ---
class TestJSONChunker:
    def test_is_chunker(self):
        assert issubclass(JSONChunker, Chunker)

    def test_splits_dict_keys(self):
        import json

        data = json.dumps({"a": "value1", "b": "value2", "c": "value3"})
        chunks = JSONChunker().chunk(data)
        assert len(chunks) >= 1

    def test_splits_array(self):
        import json

        data = json.dumps([{"id": i, "text": f"item {i}"} for i in range(10)])
        chunks = JSONChunker(max_items=3).chunk(data)
        assert len(chunks) >= 2

    def test_empty_text(self):
        assert JSONChunker().chunk("") == []

    def test_invalid_json(self):
        chunks = JSONChunker().chunk("not json at all")
        assert len(chunks) == 1


# --- CodeChunker ---
class TestCodeChunker:
    def test_is_chunker(self):
        assert issubclass(CodeChunker, Chunker)

    def test_splits_python_functions(self):
        code = """
def foo():
    return 1

def bar():
    return 2

class MyClass:
    def method(self):
        pass
"""
        chunks = CodeChunker(language="python").chunk(code)
        assert len(chunks) >= 2

    def test_empty_text(self):
        assert CodeChunker().chunk("") == []


# --- SemanticChunker ---
class TestSemanticChunker:
    def test_is_chunker(self):
        assert issubclass(SemanticChunker, Chunker)

    def test_requires_embedder(self):
        import asyncio

        class MockEmbedder:
            async def embed_batch(self, texts, **kw):
                return [[float(i)] for i, _ in enumerate(texts)]

        text = "Sentence one. Totally different topic. Back to first topic."
        chunker = SemanticChunker(embedder=MockEmbedder(), similarity_threshold=0.5)
        chunks = chunker.chunk(text)
        assert len(chunks) >= 1

    def test_empty_text(self):
        assert SemanticChunker(embedder=None).chunk("") == []
