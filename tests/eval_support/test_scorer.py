"""Tests for the Scorer ABC and EvalScore model."""

import pytest
from machine_core.plugins.eval_support.scorer import EvalScore, Scorer


def test_eval_score_valid():
    score = EvalScore(
        scorer="test", score=0.85, reasoning="Good answer", metadata={"tokens": 42}
    )
    assert score.scorer == "test"
    assert score.score == 0.85
    assert score.reasoning == "Good answer"
    assert score.metadata == {"tokens": 42}


def test_eval_score_defaults():
    score = EvalScore(scorer="test", score=0.5)
    assert score.reasoning is None
    assert score.metadata is None


def test_eval_score_clamps_below_zero():
    score = EvalScore(scorer="test", score=-0.5)
    assert score.score == 0.0


def test_eval_score_clamps_above_one():
    score = EvalScore(scorer="test", score=1.5)
    assert score.score == 1.0


def test_scorer_is_abstract():
    with pytest.raises(TypeError):
        Scorer()


class DummyScorer(Scorer):
    name: str = "dummy"

    async def score(
        self,
        input: str,
        output: str,
        expected: str | None = None,
        context: dict | None = None,
    ) -> EvalScore:
        return EvalScore(scorer=self.name, score=1.0, reasoning="always perfect")


@pytest.mark.asyncio
async def test_dummy_scorer():
    scorer = DummyScorer()
    result = await scorer.score(input="hello", output="world")
    assert result.score == 1.0
    assert result.scorer == "dummy"
