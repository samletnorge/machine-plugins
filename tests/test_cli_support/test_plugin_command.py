"""Tests for the `machine plugin` commands (project-aware store)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from cli_support.main import app

runner = CliRunner()


def test_plugin_list_shows_declared_and_extra():
    store = MagicMock()
    store.declared_plugins.return_value = ["agent_support"]
    store.installed_plugins.return_value = ["agent_support", "memory_support"]

    with patch("cli_support.commands.plugin_cmd.PluginStore", return_value=store):
        result = runner.invoke(app, ["plugin", "list"])

    assert result.exit_code == 0
    assert "agent_support" in result.output
    assert "installed" in result.output
    assert "Installed but not declared" in result.output
    assert "memory_support" in result.output


def test_plugin_add_installs_into_project():
    store = MagicMock()
    store.install = AsyncMock(
        return_value=SimpleNamespace(
            name="auth_support", declared=True, installed=True, commands=[], output=""
        )
    )

    with patch("cli_support.commands.plugin_cmd.PluginStore", return_value=store):
        result = runner.invoke(app, ["plugin", "add", "auth_support"])

    assert result.exit_code == 0
    assert "Installed auth_support" in result.output
    store.install.assert_awaited_once()


def test_plugin_remove():
    store = MagicMock()
    store.uninstall = AsyncMock(
        return_value=SimpleNamespace(
            name="auth_support", declared=False, installed=False, commands=[], output=""
        )
    )

    with patch("cli_support.commands.plugin_cmd.PluginStore", return_value=store):
        result = runner.invoke(app, ["plugin", "remove", "auth_support"])

    assert result.exit_code == 0
    assert "Removed auth_support" in result.output
