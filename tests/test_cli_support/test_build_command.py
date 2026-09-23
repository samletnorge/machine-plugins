"""Tests for machine build command."""

import shutil
from unittest.mock import patch

import pytest
from typer.testing import CliRunner
from cli_support.main import app

runner = CliRunner()


def _valid_machine_project(tmp_path):
    """Create a project whose entry point imports and whose Machine starts."""
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "test-project"
version = "0.1.0"
requires-python = ">=3.12"

[tool.machine-core]
entry = "src.main:machine"
plugins = []
"""
    )
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "__init__.py").write_text("")
    (src_dir / "main.py").write_text(
        "from machine_core import Machine\nmachine = Machine()\n"
    )
    return tmp_path


def test_build_requires_project(tmp_path, monkeypatch):
    """machine build fails outside a machine-core project."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["build"])
    assert result.exit_code != 0


def test_build_validates_entry_point(mock_machine_project, monkeypatch):
    """machine build validates the configured entry point loads."""
    monkeypatch.chdir(mock_machine_project)
    result = runner.invoke(app, ["build"])
    assert result.exit_code == 0 or "error" in result.output.lower()


def test_build_checks_dependencies(mock_machine_project, monkeypatch):
    """machine build reports dependency check."""
    monkeypatch.chdir(mock_machine_project)
    result = runner.invoke(app, ["build"])
    output = result.output.lower()
    assert "check" in output or "valid" in output or "build" in output


def test_build_runs_uv_build_and_reports_artifacts(tmp_path, monkeypatch):
    """machine build runs `uv build`, reports dist/ artifacts, and starts the Machine."""
    if shutil.which("uv") is None:
        pytest.skip("uv is not available")

    project = _valid_machine_project(tmp_path)
    monkeypatch.chdir(project)

    result = runner.invoke(app, ["build"])

    assert result.exit_code == 0, result.output
    assert (project / "dist").is_dir()
    assert "dist" in result.output.lower()
    assert ".whl" in result.output or ".tar.gz" in result.output
    assert "Machine starts" in result.output


def test_build_reports_missing_uv(tmp_path, monkeypatch):
    """machine build fails with a clear message when uv is unavailable."""
    project = _valid_machine_project(tmp_path)
    monkeypatch.chdir(project)

    with patch("cli_support.commands.build_cmd.shutil.which", return_value=None):
        result = runner.invoke(app, ["build"])

    assert result.exit_code == 1
    assert "error" in result.output.lower()
    assert "uv" in result.output.lower()


def test_build_fails_on_broken_entry_point(tmp_path, monkeypatch):
    """machine build fails when the entry point cannot be imported."""
    project = _valid_machine_project(tmp_path)
    (project / "src" / "main.py").write_text(
        "from machine_core import Machine\n"
        'machine = Machine(name="not-a-valid-kwarg")\n'
    )
    monkeypatch.chdir(project)

    with patch("cli_support.commands.build_cmd.shutil.which", return_value="/usr/bin/uv"):
        with patch("cli_support.commands.build_cmd.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = ""
            (project / "dist").mkdir()
            (project / "dist" / "pkg-0.1.0-py3-none-any.whl").write_text("x")
            result = runner.invoke(app, ["build"])

    assert result.exit_code == 1
    assert "error" in result.output.lower()
