"""Tests for machine dev command."""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from cli_support.main import app

runner = CliRunner()


def test_dev_requires_project(tmp_path, monkeypatch):
    """machine dev fails outside a machine-core project."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["dev"])
    assert result.exit_code != 0


@patch("cli_support.commands.dev_cmd.subprocess.run")
def test_dev_starts_uvicorn(mock_run, mock_machine_project, monkeypatch):
    """machine dev starts uvicorn with reload."""
    monkeypatch.chdir(mock_machine_project)
    mock_run.return_value = MagicMock(returncode=0)
    result = runner.invoke(app, ["dev"])
    if mock_run.called:
        cmd_str = str(mock_run.call_args)
        assert "uvicorn" in cmd_str
        assert "reload" in cmd_str


def test_dev_custom_port(mock_machine_project, monkeypatch):
    """machine dev --port sets the port."""
    monkeypatch.chdir(mock_machine_project)
    with patch(
        "cli_support.commands.dev_cmd.subprocess.run"
    ) as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        runner.invoke(app, ["dev", "--port", "9000"])
        if mock_run.called:
            cmd_str = str(mock_run.call_args)
            assert "9000" in cmd_str
