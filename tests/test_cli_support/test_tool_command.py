"""Tests for machine tool add command."""

import pytest
from typer.testing import CliRunner
from cli_support.main import app

runner = CliRunner()


def test_tool_add_creates_file(mock_machine_project, monkeypatch):
    """machine tool add creates tool file."""
    monkeypatch.chdir(mock_machine_project)
    result = runner.invoke(app, ["tool", "add", "weather"])
    tool_file = mock_machine_project / "src" / "tools" / "weather.py"
    assert tool_file.exists()
    content = tool_file.read_text()
    assert "weather" in content
