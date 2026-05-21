"""Tests for machine agent add command."""

import pytest
from typer.testing import CliRunner
from machine_core.plugins.cli_support.main import app

runner = CliRunner()


def test_agent_add_creates_file(mock_machine_project, monkeypatch):
    """machine agent add creates agent file."""
    monkeypatch.chdir(mock_machine_project)
    result = runner.invoke(app, ["agent", "add", "greeter"])
    agent_file = mock_machine_project / "src" / "agents" / "greeter.py"
    assert agent_file.exists()
    content = agent_file.read_text()
    assert "greeter" in content
