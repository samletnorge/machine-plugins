"""Tests for alignment scorers: tone, prompt_alignment, tool_call_accuracy."""

import pytest
from unittest.mock import AsyncMock, patch
from machine_core.plugins.eval_support.scorers.tone import ToneScorer
from machine_core.plugins.eval_support.scorers.prompt_alignment import (
    PromptAlignmentScorer,
)
from machine_core.plugins.eval_support.scorers.tool_call_accuracy import (
    ToolCallAccuracyScorer,
)


def test_tone_name():
    assert ToneScorer().name == "tone"


def test_prompt_alignment_name():
    assert PromptAlignmentScorer().name == "prompt_alignment"


def test_tool_call_accuracy_name():
    assert ToolCallAccuracyScorer().name == "tool_call_accuracy"


@pytest.mark.asyncio
async def test_tone_matches_desired():
    scorer = ToneScorer()
    with patch.object(scorer, "_call_llm", new_callable=AsyncMock) as mock:
        mock.return_value = '{"score": 0.9, "reasoning": "Professional and friendly"}'
        result = await scorer.score(
            input="Help me",
            output="I'd be happy to help!",
            context={"desired_tone": "professional, friendly"},
        )
    assert result.score == 0.9


@pytest.mark.asyncio
async def test_prompt_alignment_follows_instructions():
    scorer = PromptAlignmentScorer()
    with patch.object(scorer, "_call_llm", new_callable=AsyncMock) as mock:
        mock.return_value = '{"score": 0.95, "reasoning": "Follows all instructions"}'
        result = await scorer.score(
            input="List 3 items in bullet points",
            output="- Item 1\n- Item 2\n- Item 3",
        )
    assert result.score == 0.95


@pytest.mark.asyncio
async def test_tool_call_accuracy_correct_tools():
    scorer = ToolCallAccuracyScorer()
    with patch.object(scorer, "_call_llm", new_callable=AsyncMock) as mock:
        mock.return_value = (
            '{"score": 1.0, "reasoning": "Correct tool with correct args"}'
        )
        result = await scorer.score(
            input="Search for gas stations near me",
            output="Called search_stations(lat=59.9, lon=10.7)",
            expected="search_stations(lat=59.9, lon=10.7)",
            context={
                "tool_calls": [
                    {"name": "search_stations", "args": {"lat": 59.9, "lon": 10.7}}
                ]
            },
        )
    assert result.score == 1.0
