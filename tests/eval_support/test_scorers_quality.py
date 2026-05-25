"""Tests for quality scorers: completeness, content_similarity, summarization."""

import pytest
from unittest.mock import AsyncMock, patch
from eval_support.scorers.completeness import CompletenessScorer
from eval_support.scorers.content_similarity import (
    ContentSimilarityScorer,
)
from eval_support.scorers.summarization import SummarizationScorer


def test_completeness_name():
    assert CompletenessScorer().name == "completeness"


def test_content_similarity_name():
    assert ContentSimilarityScorer().name == "content_similarity"


def test_summarization_name():
    assert SummarizationScorer().name == "summarization"


@pytest.mark.asyncio
async def test_completeness_full_answer():
    scorer = CompletenessScorer()
    with patch.object(scorer, "_call_llm", new_callable=AsyncMock) as mock:
        mock.return_value = '{"score": 0.9, "reasoning": "Covers all aspects"}'
        result = await scorer.score(
            input="Explain X, Y, Z", output="X is... Y is... Z is..."
        )
    assert result.score == 0.9


@pytest.mark.asyncio
async def test_content_similarity_high():
    scorer = ContentSimilarityScorer()
    with patch.object(scorer, "_call_llm", new_callable=AsyncMock) as mock:
        mock.return_value = '{"score": 0.92, "reasoning": "Nearly identical meaning"}'
        result = await scorer.score(
            input="Q", output="Python is great", expected="Python is excellent"
        )
    assert result.score == 0.92


@pytest.mark.asyncio
async def test_summarization_quality():
    scorer = SummarizationScorer()
    with patch.object(scorer, "_call_llm", new_callable=AsyncMock) as mock:
        mock.return_value = (
            '{"score": 0.85, "reasoning": "Good summary, captures key points"}'
        )
        result = await scorer.score(
            input="Summarize this article",
            output="The article discusses...",
            context={"documents": ["Long article text..."]},
        )
    assert result.score == 0.85
