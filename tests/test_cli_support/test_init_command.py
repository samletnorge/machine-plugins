"""Tests for machine init command."""

import pytest
from typer.testing import CliRunner
from cli_support.main import app
from pathlib import Path

runner = CliRunner()


def test_init_creates_project(tmp_path):
    """machine init creates project structure."""
    result = runner.invoke(app, ["init", str(tmp_path / "myproject")])
    assert result.exit_code == 0
    project = tmp_path / "myproject"
    assert (project / "pyproject.toml").exists()
    assert (project / "src" / "__init__.py").exists()
    assert (project / "src" / "main.py").exists()
    assert (project / "src" / "agents").is_dir()


def test_init_pyproject_has_machine_core_dep(tmp_path):
    """Generated pyproject.toml lists machine-core as a dependency."""
    runner.invoke(app, ["init", str(tmp_path / "proj")])
    content = (tmp_path / "proj" / "pyproject.toml").read_text()
    assert "machine-core" in content


def test_init_main_has_machine_instance(tmp_path):
    """Generated main.py creates a Machine instance."""
    runner.invoke(app, ["init", str(tmp_path / "proj")])
    content = (tmp_path / "proj" / "src" / "main.py").read_text()
    assert "Machine" in content
    assert "machine" in content


def test_init_creates_example_agent(tmp_path):
    """Generated project includes an example agent."""
    runner.invoke(app, ["init", str(tmp_path / "proj")])
    agents_dir = tmp_path / "proj" / "src" / "agents"
    assert agents_dir.is_dir()
    agent_files = list(agents_dir.glob("*.py"))
    assert len(agent_files) >= 1


def test_init_refuses_existing_nonempty_dir(tmp_path):
    """machine init refuses to overwrite existing non-empty directory."""
    target = tmp_path / "existing"
    target.mkdir()
    (target / "file.txt").write_text("content")
    result = runner.invoke(app, ["init", str(target)])
    assert (
        result.exit_code != 0
        or "already exists" in result.output.lower()
        or "not empty" in result.output.lower()
    )


def test_init_with_name_flag(tmp_path):
    """machine init --name sets project name in pyproject.toml."""
    runner.invoke(app, ["init", str(tmp_path / "proj"), "--name", "my-ai-app"])
    content = (tmp_path / "proj" / "pyproject.toml").read_text()
    assert "my-ai-app" in content
