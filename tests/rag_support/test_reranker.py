"""Tests for rerankers."""

import pytest
from rag_support.rerankers.base import BaseReranker
from rag_support.rerankers.llm import LLMReranker
from rag_support.rerankers.cross_encoder import (
    CrossEncoderReranker,
)
from vectorstore_support.schemas import SearchResult
from rag_support.models import RankedResult


def test_base_is_abstract():
    with pytest.raises(TypeError):
        BaseReranker()


class MockLLM:
    async def generate(self, prompt: str) -> str:
        return "0.95"


class MockCrossEncoder:
    def predict(self, pairs: list[tuple[str, str]]) -> list[float]:
        return [1.0 - i * 0.1 for i in range(len(pairs))]


@pytest.fixture
def sample_results():
    return [
        SearchResult(id="1", text="Relevant doc", score=0.8),
        SearchResult(id="2", text="Less relevant", score=0.6),
        SearchResult(id="3", text="Least relevant", score=0.4),
    ]


async def test_llm_reranker(sample_results):
    reranker = LLMReranker(llm=MockLLM())
    ranked = await reranker.rerank("test query", sample_results)
    assert len(ranked) == 3
    assert all(isinstance(r, RankedResult) for r in ranked)
    assert all(r.rerank_score >= 0 for r in ranked)


async def test_cross_encoder_reranker(sample_results):
    reranker = CrossEncoderReranker(model=MockCrossEncoder())
    ranked = await reranker.rerank("test query", sample_results)
    assert len(ranked) == 3
    assert ranked[0].rerank_score >= ranked[1].rerank_score


async def test_reranker_empty_results():
    reranker = LLMReranker(llm=MockLLM())
    ranked = await reranker.rerank("query", [])
    assert ranked == []
