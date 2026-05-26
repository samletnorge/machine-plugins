"""Tests for machine plugin commands."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from cli_support.main import app

runner = CliRunner()


def test_plugin_list_deduplicates_alias_names():
    with patch("cli_support.commands.plugin_cmd.PluginInstaller") as installer_cls:
        installer = MagicMock()
        installer.installed_plugins.return_value = [
            "provider_ollama",
            "provider-ollama",
            "rag_support",
            "rag-support",
            "tool_support",
        ]
        installer_cls.return_value = installer

        result = runner.invoke(app, ["plugin", "list"])

    assert result.exit_code == 0
    lines = [line.strip() for line in result.output.splitlines() if line.strip()]
    assert lines == ["provider_ollama", "rag_support", "tool_support"]
