"""Tests for the machine CLI entry point."""

import pytest
from typer.testing import CliRunner
from cli_support.main import app


runner = CliRunner()


def test_cli_help():
    """CLI shows help text."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "machine" in result.output.lower() or "Machine" in result.output


def test_cli_version():
    """CLI shows version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "machine-core" in result.output or "0." in result.output


def test_cli_unknown_command():
    """CLI errors on unknown command."""
    result = runner.invoke(app, ["nonexistent"])
    assert result.exit_code != 0
