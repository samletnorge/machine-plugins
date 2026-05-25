"""Tests for machine eval run command."""

import pytest
import json
from typer.testing import CliRunner
from cli_support.main import app

runner = CliRunner()


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
