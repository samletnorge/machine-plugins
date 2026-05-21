"""Tests for core LLM scorers: relevancy, faithfulness, hallucination."""

import pytest
from unittest.mock import AsyncMock, patch
from machine_core.plugins.eval_support.scorers.relevancy import RelevancyScorer
from machine_core.plugins.eval_support.scorers.faithfulness import FaithfulnessScorer
from machine_core.plugins.eval_support.scorers.hallucination import HallucinationScorer


def test_relevancy_scorer_name():
    assert RelevancyScorer().name == "relevancy"


@pytest.mark.asyncio
async def test_relevancy_scorer_high_score():
    scorer = RelevancyScorer()
    with patch.object(scorer, "_call_llm", new_callable=AsyncMock) as mock:
        mock.return_value = (
            '{"score": 0.95, "reasoning": "Directly answers the question"}'
        )
        result = await scorer.score(
            input="What is Python?", output="Python is a programming language."
        )
    assert result.score == 0.95
    assert result.scorer == "relevancy"


@pytest.mark.asyncio
async def test_relevancy_scorer_low_score():
    scorer = RelevancyScorer()
    with patch.object(scorer, "_call_llm", new_callable=AsyncMock) as mock:
        mock.return_value = (
            '{"score": 0.1, "reasoning": "Answer is about cooking, not Python"}'
        )
        result = await scorer.score(input="What is Python?", output="I like pasta.")
    assert result.score == 0.1


def test_faithfulness_scorer_name():
    assert FaithfulnessScorer().name == "faithfulness"


@pytest.mark.asyncio
async def test_faithfulness_with_context():
    scorer = FaithfulnessScorer()
    with patch.object(scorer, "_call_llm", new_callable=AsyncMock) as mock:
        mock.side_effect = [
            '{"claims": ["Python was created by Guido van Rossum", "Python is interpreted"]}',
            '{"score": 1.0, "reasoning": "All claims are in the context"}',
        ]
        result = await scorer.score(
            input="Tell me about Python",
            output="Python was created by Guido van Rossum. It is interpreted.",
            context={
                "documents": [
                    "Python is an interpreted language created by Guido van Rossum in 1991."
                ]
            },
        )
    assert result.score == 1.0
    assert result.scorer == "faithfulness"


def test_hallucination_scorer_name():
    assert HallucinationScorer().name == "hallucination"


@pytest.mark.asyncio
async def test_hallucination_no_fabrication():
    scorer = HallucinationScorer()
    with patch.object(scorer, "_call_llm", new_callable=AsyncMock) as mock:
        mock.return_value = (
            '{"score": 0.95, "reasoning": "No fabricated facts detected"}'
        )
        result = await scorer.score(
            input="What is 2+2?",
            output="2+2 is 4.",
            context={"documents": ["Basic arithmetic: 2+2=4"]},
        )
    assert result.score == 0.95
