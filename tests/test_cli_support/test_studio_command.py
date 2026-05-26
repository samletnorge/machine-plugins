"""Task 11 — machine studio command tests."""

from unittest.mock import patch

from typer.testing import CliRunner

from cli_support.main import app

runner = CliRunner()


def test_studio_help():
    result = runner.invoke(app, ["studio", "--help"])
    assert result.exit_code == 0
    assert "studio" in result.output.lower()


def test_studio_no_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch.dict("sys.modules", {"studio_support": None}):
        result = runner.invoke(app, ["studio"])
    assert result.exit_code == 1
    assert "studio_support" in result.output
