"""Tests for safety scorers: toxicity, bias."""

import pytest
from unittest.mock import AsyncMock, patch
from eval_support.scorers.toxicity import ToxicityScorer
from eval_support.scorers.bias import BiasScorer


def test_toxicity_scorer_name():
    assert ToxicityScorer().name == "toxicity"


def test_bias_scorer_name():
    assert BiasScorer().name == "bias"


@pytest.mark.asyncio
async def test_toxicity_clean_content():
    scorer = ToxicityScorer()
    with patch.object(scorer, "_call_llm", new_callable=AsyncMock) as mock:
        mock.return_value = '{"score": 0.98, "reasoning": "No toxic content"}'
        result = await scorer.score(input="Hello", output="Hello! How can I help?")
    assert result.score == 0.98


@pytest.mark.asyncio
async def test_bias_neutral_content():
    scorer = BiasScorer()
    with patch.object(scorer, "_call_llm", new_callable=AsyncMock) as mock:
        mock.return_value = (
            '{"score": 0.95, "reasoning": "Neutral and balanced response"}'
        )
        result = await scorer.score(
            input="Compare X and Y", output="Both have strengths."
        )
    assert result.score == 0.95
