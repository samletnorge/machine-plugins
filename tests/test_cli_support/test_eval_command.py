"""Tests for machine eval run command."""

import json

import pytest
from typer.testing import CliRunner
from cli_support.main import app

runner = CliRunner()

SCORER_AND_AGENT_MAIN = """
from machine_core import Machine
from eval_support.scorer import Scorer, EvalScore


class ConstantScorer(Scorer):
    name: str = "constant"

    async def score(self, input, output, expected=None, context=None):
        return EvalScore(scorer=self.name, score=0.75, reasoning="constant")


class EchoAgent:
    async def run(self, input, context=None):
        return f"echo: {input}"


machine = Machine()
machine.register_category("scorer")
machine.register_category("agent")
machine.register("scorer", "constant", ConstantScorer())
machine.register("agent", "echo", EchoAgent())
"""


def test_eval_requires_project(tmp_path, monkeypatch):
    """machine eval run fails outside a project."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["eval", "run", "dataset.json"])
    assert result.exit_code != 0


def test_eval_requires_dataset_file(mock_machine_project, monkeypatch):
    """machine eval run fails if dataset file doesn't exist."""
    monkeypatch.chdir(mock_machine_project)
    result = runner.invoke(app, ["eval", "run", "nonexistent.json"])
    assert result.exit_code != 0


def test_eval_accepts_dataset_file(mock_machine_project, monkeypatch):
    """machine eval run accepts a valid dataset file."""
    monkeypatch.chdir(mock_machine_project)
    dataset_file = mock_machine_project / "test_dataset.json"
    dataset_file.write_text(
        json.dumps(
            {"name": "test", "samples": [{"input": "hello", "expected": "world"}]}
        )
    )
    result = runner.invoke(app, ["eval", "run", str(dataset_file)])
    output = result.output.lower()
    assert "not found" not in output or result.exit_code == 0


def _write_dataset(project, name="dataset.json"):
    path = project / name
    path.write_text(
        json.dumps(
            {
                "name": "demo",
                "samples": [
                    {"input": "hello", "expected": "echo: hello"},
                    {"input": "world", "expected": "echo: world"},
                ],
            }
        )
    )
    return path


def test_eval_runs_experiment_and_prints_scores(mock_machine_project, monkeypatch):
    """machine eval run executes a real experiment via eval_support."""
    pytest.importorskip("eval_support")
    monkeypatch.chdir(mock_machine_project)
    (mock_machine_project / "src" / "main.py").write_text(SCORER_AND_AGENT_MAIN)
    _write_dataset(mock_machine_project)

    result = runner.invoke(app, ["eval", "run", "dataset.json"])

    assert result.exit_code == 0, result.output
    assert "Running evaluation: demo" in result.output
    assert "Agent: echo" in result.output
    assert "Aggregate scores" in result.output
    assert "constant: 0.750" in result.output


def test_eval_errors_when_no_scorers_configured(mock_machine_project, monkeypatch):
    """machine eval run gives an actionable error when no scorers are registered."""
    pytest.importorskip("eval_support")
    monkeypatch.chdir(mock_machine_project)
    (mock_machine_project / "src" / "main.py").write_text(
        "from machine_core import Machine\nmachine = Machine()\n"
    )
    _write_dataset(mock_machine_project)

    result = runner.invoke(app, ["eval", "run", "dataset.json"])

    assert result.exit_code == 1
    assert "scorer" in result.output.lower()
    assert "not found" not in result.output.lower()


def test_eval_errors_on_unknown_scorer(mock_machine_project, monkeypatch):
    """machine eval run fails clearly for an unknown --scorer."""
    pytest.importorskip("eval_support")
    monkeypatch.chdir(mock_machine_project)
    (mock_machine_project / "src" / "main.py").write_text(SCORER_AND_AGENT_MAIN)
    _write_dataset(mock_machine_project)

    result = runner.invoke(app, ["eval", "run", "dataset.json", "--scorer", "bogus"])

    assert result.exit_code == 1
    assert "bogus" in result.output
    assert "constant" in result.output
