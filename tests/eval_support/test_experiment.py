"""Tests for ExperimentRunner."""

import pytest
from eval_support.experiment import (
    ExperimentRunner,
    ExperimentResult,
    SampleResult,
)
from eval_support.dataset import Dataset, EvalSample
from eval_support.scorer import Scorer, EvalScore


class ConstantScorer(Scorer):
    name: str = "constant"
    value: float = 0.8

    async def score(
        self,
        input: str,
        output: str,
        expected: str | None = None,
        context: dict | None = None,
    ) -> EvalScore:
        return EvalScore(scorer=self.name, score=self.value, reasoning="constant")


class FakeAgent:
    async def run(self, input: str) -> str:
        return f"answer to: {input}"


@pytest.mark.asyncio
async def test_experiment_runner_basic():
    dataset = Dataset(
        name="test",
        samples=[
            EvalSample(input="Q1", expected_output="A1"),
            EvalSample(input="Q2", expected_output="A2"),
        ],
    )
    scorer = ConstantScorer()
    agent = FakeAgent()
    runner = ExperimentRunner(agent_fn=agent.run, scorers=[scorer])
    result = await runner.run(dataset)
    assert isinstance(result, ExperimentResult)
    assert result.dataset_name == "test"
    assert len(result.sample_results) == 2
    assert result.aggregate_scores["constant"] == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_experiment_runner_multiple_scorers():
    dataset = Dataset(
        name="multi", samples=[EvalSample(input="Q1", expected_output="A1")]
    )
    scorer_a = ConstantScorer(name="scorer_a", value=0.9)
    scorer_b = ConstantScorer(name="scorer_b", value=0.6)
    agent = FakeAgent()
    runner = ExperimentRunner(agent_fn=agent.run, scorers=[scorer_a, scorer_b])
    result = await runner.run(dataset)
    assert result.aggregate_scores["scorer_a"] == pytest.approx(0.9)
    assert result.aggregate_scores["scorer_b"] == pytest.approx(0.6)


@pytest.mark.asyncio
async def test_experiment_result_summary():
    dataset = Dataset(
        name="summary",
        samples=[
            EvalSample(input="Q1"),
            EvalSample(input="Q2"),
            EvalSample(input="Q3"),
        ],
    )
    scorer = ConstantScorer(value=0.7)
    agent = FakeAgent()
    runner = ExperimentRunner(agent_fn=agent.run, scorers=[scorer])
    result = await runner.run(dataset)
    summary = result.summary()
    assert "constant" in summary
    assert "0.7" in summary


@pytest.mark.asyncio
async def test_experiment_runner_handles_agent_error():
    dataset = Dataset(name="error_test", samples=[EvalSample(input="Q1")])

    async def failing_agent(input: str) -> str:
        raise RuntimeError("agent crashed")

    scorer = ConstantScorer()
    runner = ExperimentRunner(agent_fn=failing_agent, scorers=[scorer])
    result = await runner.run(dataset)
    assert len(result.sample_results) == 1
    assert result.sample_results[0].error is not None
    assert result.aggregate_scores["constant"] == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_experiment_ab_compare():
    dataset = Dataset(name="ab", samples=[EvalSample(input="Q1")])
    scorer = ConstantScorer(name="quality", value=0.8)

    async def agent_a(input: str) -> str:
        return "A"

    async def agent_b(input: str) -> str:
        return "B"

    result_a, result_b = await ExperimentRunner.ab_compare(
        agent_a=agent_a,
        agent_b=agent_b,
        dataset=dataset,
        scorers=[scorer],
    )
    assert result_a.dataset_name == "ab"
    assert result_b.dataset_name == "ab"
