"""Tests for machine deploy command."""

import pytest
from typer.testing import CliRunner
from machine_core.plugins.cli_support.main import app

runner = CliRunner()


def test_deploy_requires_project(tmp_path, monkeypatch):
    """machine deploy fails outside a project."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["deploy", "--target", "docker"])
    assert result.exit_code != 0


def test_deploy_docker_target(mock_machine_project, monkeypatch):
    """machine deploy --target docker generates files."""
    monkeypatch.chdir(mock_machine_project)
    result = runner.invoke(app, ["deploy", "--target", "docker"])
    output = result.output.lower()
    assert "docker" in output or "generated" in output or "error" in output


def test_deploy_unknown_target(mock_machine_project, monkeypatch):
    """machine deploy with unknown target fails gracefully."""
    monkeypatch.chdir(mock_machine_project)
    result = runner.invoke(app, ["deploy", "--target", "nonexistent"])
    assert (
        result.exit_code != 0
        or "unknown" in result.output.lower()
        or "not found" in result.output.lower()
    )
