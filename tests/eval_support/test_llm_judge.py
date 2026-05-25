"""Tests for the LLM-based judge scorer base class."""

import pytest
from unittest.mock import AsyncMock, patch
from eval_support.llm_judge import LLMJudgeScorer
from eval_support.scorer import EvalScore


class MockJudge(LLMJudgeScorer):
    name: str = "mock_judge"

    def build_prompt(
        self, input: str, output: str, expected: str | None, context: dict | None
    ) -> str:
        return f"Rate this answer:\nQ: {input}\nA: {output}"

    def parse_result(self, llm_output: str) -> EvalScore:
        lines = llm_output.strip().split("\n")
        score_val = float(lines[0].split(":")[1].strip())
        reason = lines[1].split(":", 1)[1].strip() if len(lines) > 1 else None
        return EvalScore(scorer=self.name, score=score_val, reasoning=reason)


@pytest.mark.asyncio
async def test_llm_judge_scorer_calls_model():
    judge = MockJudge(model="openai:gpt-4o-mini")
    with patch.object(judge, "_call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "SCORE: 0.9\nREASON: very relevant"
        result = await judge.score(
            input="What is Python?", output="A programming language"
        )
    assert result.score == 0.9
    assert result.reasoning == "very relevant"
    mock_llm.assert_called_once()


@pytest.mark.asyncio
async def test_llm_judge_scorer_handles_parse_error():
    judge = MockJudge(model="openai:gpt-4o-mini")
    with patch.object(judge, "_call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "GARBAGE OUTPUT"
        result = await judge.score(input="Q", output="A")
    assert result.score == 0.0
    assert "parse" in result.reasoning.lower() or "error" in result.reasoning.lower()


def test_llm_judge_is_abstract():
    with pytest.raises(TypeError):
        LLMJudgeScorer(name="bad", model="openai:gpt-4o-mini")
