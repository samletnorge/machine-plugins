"""Task 11 — machine studio command tests."""

from typer.testing import CliRunner
from machine_core.plugins.cli_support.main import app

runner = CliRunner()


def test_studio_help():
    result = runner.invoke(app, ["studio", "--help"])
    assert result.exit_code == 0
    assert "studio" in result.output.lower()


def test_studio_no_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["studio"])
    assert result.exit_code == 1
    assert "Not inside" in result.output
