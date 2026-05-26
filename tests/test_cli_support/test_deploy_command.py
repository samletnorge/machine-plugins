"""Tests for machine deploy command."""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from cli_support.main import app

runner = CliRunner()


def test_deploy_requires_project(tmp_path, monkeypatch):
    """machine deploy fails outside a project."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["deploy", "--target", "docker"])
    assert result.exit_code != 0


def test_deploy_docker_target(mock_machine_project, monkeypatch):
    """machine deploy fails cleanly when deployer_support is unavailable."""
    monkeypatch.chdir(mock_machine_project)
    with patch("cli_support.commands.deploy_cmd.DeployConfig", None):
        result = runner.invoke(app, ["deploy", "--target", "docker"])
    assert result.exit_code == 1
    assert "deployer_support" in result.output


def test_deploy_unknown_target(mock_machine_project, monkeypatch):
    """machine deploy with unknown target fails gracefully."""
    monkeypatch.chdir(mock_machine_project)
    with patch("cli_support.commands.deploy_cmd.DeployConfig", None):
        result = runner.invoke(app, ["deploy", "--target", "nonexistent"])
    assert result.exit_code == 1
    assert "deployer_support" in result.output
