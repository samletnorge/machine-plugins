"""Tests for RAG scorers: context_precision, context_recall."""

import pytest
from unittest.mock import AsyncMock, patch
from machine_core.plugins.eval_support.scorers.context_precision import (
    ContextPrecisionScorer,
)
from machine_core.plugins.eval_support.scorers.context_recall import ContextRecallScorer


def test_context_precision_name():
    assert ContextPrecisionScorer().name == "context_precision"


def test_context_recall_name():
    assert ContextRecallScorer().name == "context_recall"


@pytest.mark.asyncio
async def test_context_precision_all_relevant():
    scorer = ContextPrecisionScorer()
    with patch.object(scorer, "_call_llm", new_callable=AsyncMock) as mock:
        mock.return_value = (
            '{"score": 1.0, "reasoning": "All retrieved contexts are relevant"}'
        )
        result = await scorer.score(
            input="What is Python?",
            output="Python is a language",
            context={
                "documents": [
                    "Python is a programming language",
                    "Python was created by Guido",
                ]
            },
        )
    assert result.score == 1.0


@pytest.mark.asyncio
async def test_context_recall_complete():
    scorer = ContextRecallScorer()
    with patch.object(scorer, "_call_llm", new_callable=AsyncMock) as mock:
        mock.return_value = (
            '{"score": 0.8, "reasoning": "Most relevant info was retrieved"}'
        )
        result = await scorer.score(
            input="What is Python?",
            output="Python is a language",
            expected="Python is a programming language created by Guido van Rossum",
            context={"documents": ["Python is a programming language"]},
        )
    assert result.score == 0.8
