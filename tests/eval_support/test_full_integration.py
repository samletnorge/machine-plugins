"""Integration tests verifying the full eval_support plugin works end-to-end."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from eval_support import EvalSupportPlugin
from eval_support.scorer import EvalScore, Scorer
from eval_support.dataset import Dataset, EvalSample
from eval_support.experiment import (
    ExperimentRunner,
    ExperimentResult,
)


@pytest.mark.asyncio
async def test_plugin_registers_all_scorers():
    plugin = EvalSupportPlugin()
    ctx = MagicMock()
    registered_categories = {}
    registered_items = {}

    def mock_register_category(name, operations=None):
        registered_categories[name] = operations

    def mock_register(category, name, impl):
        registered_items.setdefault(category, {})[name] = impl

    ctx.register_category = mock_register_category
    ctx.register = mock_register

    await plugin.setup(ctx)

    assert "scorer" in registered_categories
    assert "dataset" in registered_categories

    scorer_names = set(registered_items.get("scorer", {}).keys())
    expected = {
        "relevancy",
        "faithfulness",
        "hallucination",
        "toxicity",
        "bias",
        "completeness",
        "content_similarity",
        "summarization",
        "tone",
        "prompt_alignment",
        "tool_call_accuracy",
        "context_precision",
        "context_recall",
    }
    assert scorer_names == expected


def test_all_types_importable():
    from eval_support.scorer import EvalScore, Scorer
    from eval_support.llm_judge import LLMJudgeScorer
    from eval_support.dataset import Dataset, EvalSample
    from eval_support.experiment import (
        ExperimentRunner,
        ExperimentResult,
        SampleResult,
    )
    from eval_support.scorers import parse_json_score

    assert issubclass(LLMJudgeScorer, Scorer)
