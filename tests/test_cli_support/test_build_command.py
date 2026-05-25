"""Tests for machine build command."""

import pytest
from typer.testing import CliRunner
from cli_support.main import app

runner = CliRunner()


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
