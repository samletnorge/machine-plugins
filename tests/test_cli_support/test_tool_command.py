"""Tests for machine tool add command."""

import importlib.util

import pytest
from typer.testing import CliRunner
from cli_support.main import app

runner = CliRunner()


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tool_add_creates_file(mock_machine_project, monkeypatch):
    """machine tool add creates tool file."""
    monkeypatch.chdir(mock_machine_project)
    result = runner.invoke(app, ["tool", "add", "weather"])
    tool_file = mock_machine_project / "src" / "tools" / "weather.py"
    assert tool_file.exists()
    content = tool_file.read_text()
    assert "weather" in content


def test_tool_add_generates_importable_tool_definition(mock_machine_project, monkeypatch):
    """The generated tool file defines a real @tool function + ToolDefinition."""
    pytest.importorskip("tool_support")
    monkeypatch.chdir(mock_machine_project)
    result = runner.invoke(app, ["tool", "add", "weather"])
    assert result.exit_code == 0

    tool_file = mock_machine_project / "src" / "tools" / "weather.py"
    content = tool_file.read_text()
    assert "TODO" not in content

    module = _load_module(tool_file, "generated_weather")
    assert module.WEATHER_TOOL.name == "weather"
    assert module.WEATHER_TOOL.handler is not None
    assert module.weather.__tool_definition__ is module.WEATHER_TOOL

    import asyncio

    assert asyncio.run(module.weather(input="oslo")) == "weather received: oslo"


def test_tool_add_sanitizes_non_identifier_names(mock_machine_project, monkeypatch):
    """Generated tool functions stay valid Python identifiers."""
    pytest.importorskip("tool_support")
    monkeypatch.chdir(mock_machine_project)
    result = runner.invoke(app, ["tool", "add", "my-tool"])
    assert result.exit_code == 0

    tool_file = mock_machine_project / "src" / "tools" / "my_tool.py"
    assert tool_file.exists()
    content = tool_file.read_text()
    assert "TODO" not in content
    assert "async def my_tool(" in content
    compile(content, str(tool_file), "exec")
