"""Tests for machine agent add command."""

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


def test_agent_add_creates_file(mock_machine_project, monkeypatch):
    """machine agent add creates agent file."""
    monkeypatch.chdir(mock_machine_project)
    result = runner.invoke(app, ["agent", "add", "greeter"])
    agent_file = mock_machine_project / "src" / "agents" / "greeter.py"
    assert agent_file.exists()
    content = agent_file.read_text()
    assert "greeter" in content


def test_agent_add_generates_runnable_agent(mock_machine_project, monkeypatch):
    """The generated agent file defines an AgentDefinition and a runnable class."""
    pytest.importorskip("agent_support")
    monkeypatch.chdir(mock_machine_project)
    result = runner.invoke(app, ["agent", "add", "greeter"])
    assert result.exit_code == 0

    agent_file = mock_machine_project / "src" / "agents" / "greeter.py"
    content = agent_file.read_text()
    assert "TODO" not in content

    module = _load_module(agent_file, "generated_greeter")
    assert module.GREETER_DEFINITION.name == "greeter"
    assert module.GREETER_DEFINITION.tool_refs == []
    assert callable(module.GreeterAgent.run)

    import inspect

    assert inspect.iscoroutinefunction(module.GreeterAgent.run)


def test_agent_add_sanitizes_non_identifier_names(mock_machine_project, monkeypatch):
    """Generated agent classes/functions stay valid Python identifiers."""
    pytest.importorskip("agent_support")
    monkeypatch.chdir(mock_machine_project)
    result = runner.invoke(app, ["agent", "add", "my-agent"])
    assert result.exit_code == 0

    agent_file = mock_machine_project / "src" / "agents" / "my_agent.py"
    assert agent_file.exists()
    content = agent_file.read_text()
    assert "TODO" not in content
    assert "class MyAgent" in content
    compile(content, str(agent_file), "exec")
