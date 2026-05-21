"""Textual pilot tests for machine-core TUI."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from textual.widgets import ListView, Static, Button, Label, Log

from machine_cli.tui.app import MachineApp


# --- Helpers ---


def mock_health_response(categories: dict | None = None):
    """Create a mock httpx response for /health."""
    if categories is None:
        categories = {"agent": 2, "tool": 3}
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"status": "healthy", "categories": categories}
    return resp


def mock_connect_error(*args, **kwargs):
    import httpx

    raise httpx.ConnectError("Connection refused")


# --- Plugins Screen Tests ---


class TestPluginsScreen:
    @pytest.mark.asyncio
    async def test_shows_server_offline_when_not_running(self):
        """Plugins tab shows offline message when server is unreachable."""
        with patch("machine_cli.tui.screens.plugins.httpx.AsyncClient") as mock_client:
            import httpx

            mock_instance = AsyncMock()
            mock_instance.get.side_effect = httpx.ConnectError("refused")
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            app = MachineApp(server_url="http://localhost:9999")
            async with app.run_test() as pilot:
                # Wait for mount
                await pilot.pause()
                details = app.query_one("#plugin-details", Static)
                text = details.content.lower()
                assert "offline" in text or "stopped" in text or "no local" in text

    @pytest.mark.asyncio
    async def test_shows_categories_when_server_running(self):
        """Plugins tab shows categories from server."""
        with patch("machine_cli.tui.screens.plugins.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(
                return_value=mock_health_response({"agent": 1, "tool": 0})
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            app = MachineApp(server_url="http://localhost:8000")
            async with app.run_test() as pilot:
                await pilot.pause()
                list_view = app.query_one("#plugin-list", ListView)
                assert len(list_view.children) > 0


# --- Store Screen Tests ---


class TestStoreScreen:
    @pytest.mark.asyncio
    async def test_loads_plugins_from_registry(self):
        """Store tab lists plugins from RegistryClient."""
        mock_plugin = MagicMock()
        mock_plugin.name = "agent_support"
        mock_plugin.tier = "framework"
        mock_plugin.runtime = "python"
        mock_plugin.version = "0.5.0"
        mock_plugin.description = "Agent support plugin"

        with patch("machine_cli.tui.screens.store.RegistryClient") as mock_rc:
            mock_client_instance = AsyncMock()
            mock_client_instance.list_plugins = AsyncMock(return_value=[mock_plugin])
            mock_rc.return_value = mock_client_instance

            with patch("machine_cli.tui.screens.store.PluginInstaller") as mock_pi:
                mock_installer = MagicMock()
                mock_installer.installed_plugins.return_value = []
                mock_pi.return_value = mock_installer

                app = MachineApp(server_url="http://localhost:8000")
                async with app.run_test() as pilot:
                    # Switch to Store tab
                    await pilot.click("#store-tab")
                    await pilot.pause()
                    store_list = app.query_one("#store-list", ListView)
                    assert len(store_list.children) >= 1

    @pytest.mark.asyncio
    async def test_install_button_disabled_initially(self):
        """Install button starts disabled."""
        with patch("machine_cli.tui.screens.store.RegistryClient") as mock_rc:
            mock_rc.return_value = AsyncMock()
            mock_rc.return_value.list_plugins = AsyncMock(return_value=[])

            with patch("machine_cli.tui.screens.store.PluginInstaller") as mock_pi:
                mock_pi.return_value = MagicMock()
                mock_pi.return_value.installed_plugins.return_value = []

                app = MachineApp(server_url="http://localhost:8000")
                async with app.run_test() as pilot:
                    await pilot.click("#store-tab")
                    await pilot.pause()
                    btn = app.query_one("#store-install-btn", Button)
                    assert btn.disabled is True


# --- Services Screen Tests ---


class TestServicesScreen:
    @pytest.mark.asyncio
    async def test_shows_stopped_when_server_down(self):
        """Services tab shows stopped status."""
        with patch("machine_cli.tui.screens.services.httpx.AsyncClient") as mock_client:
            import httpx

            mock_instance = AsyncMock()
            mock_instance.get.side_effect = httpx.ConnectError("refused")
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            app = MachineApp(server_url="http://localhost:9999")
            async with app.run_test() as pilot:
                await pilot.click("#services-tab")
                await pilot.pause()
                status = app.query_one("#server-status", Static)
                assert "stopped" in status.content.lower()

    @pytest.mark.asyncio
    async def test_start_button_enabled_when_stopped(self):
        """Start button is enabled when server is stopped."""
        with patch("machine_cli.tui.screens.services.httpx.AsyncClient") as mock_client:
            import httpx

            mock_instance = AsyncMock()
            mock_instance.get.side_effect = httpx.ConnectError("refused")
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            app = MachineApp(server_url="http://localhost:9999")
            async with app.run_test() as pilot:
                await pilot.click("#services-tab")
                await pilot.pause()
                start_btn = app.query_one("#start-dev-btn", Button)
                assert not start_btn.disabled

    @pytest.mark.asyncio
    async def test_shows_running_when_server_up(self):
        """Services tab shows running status."""
        with patch("machine_cli.tui.screens.services.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_health_response())
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            app = MachineApp(server_url="http://localhost:8000")
            async with app.run_test() as pilot:
                await pilot.click("#services-tab")
                await pilot.pause()
                status = app.query_one("#server-status", Static)
                assert "running" in status.content.lower()


# --- Config Screen Tests ---


class TestConfigScreen:
    @pytest.mark.asyncio
    async def test_shows_server_settings(self):
        """Config tab always shows server settings."""
        app = MachineApp(server_url="http://localhost:8000")
        async with app.run_test() as pilot:
            await pilot.click("#config-tab")
            await pilot.pause()
            config_list = app.query_one("#config-list", ListView)
            # Should at least have the server settings entry
            assert len(config_list.children) >= 1

    @pytest.mark.asyncio
    async def test_reads_pyproject_config(self, tmp_path, monkeypatch):
        """Config tab reads [tool.machine-core] from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.machine-core]\nplugins = ["agent_support", "tool_support"]\n'
        )
        monkeypatch.chdir(tmp_path)

        app = MachineApp(server_url="http://localhost:8000")
        async with app.run_test() as pilot:
            await pilot.click("#config-tab")
            await pilot.pause()
            config_list = app.query_one("#config-list", ListView)
            # Should have pyproject.toml entry + server settings
            assert len(config_list.children) >= 2


# --- App-level Tests ---


class TestMachineApp:
    @pytest.mark.asyncio
    async def test_app_starts_and_has_tabs(self):
        """App starts with all 4 tabs."""
        with patch("machine_cli.tui.screens.plugins.httpx.AsyncClient") as mock_client:
            import httpx

            mock_instance = AsyncMock()
            mock_instance.get.side_effect = httpx.ConnectError("refused")
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            app = MachineApp(server_url="http://localhost:9999")
            async with app.run_test() as pilot:
                await pilot.pause()
                # Check we have all 4 tabs
                assert app.query_one("#plugins-tab") is not None
                assert app.query_one("#store-tab") is not None
                assert app.query_one("#services-tab") is not None
                assert app.query_one("#config-tab") is not None

    @pytest.mark.asyncio
    async def test_quit_binding(self):
        """Pressing q quits the app."""
        with patch("machine_cli.tui.screens.plugins.httpx.AsyncClient") as mock_client:
            import httpx

            mock_instance = AsyncMock()
            mock_instance.get.side_effect = httpx.ConnectError("refused")
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            app = MachineApp(server_url="http://localhost:9999")
            async with app.run_test() as pilot:
                await pilot.press("q")
                # App should have exited
                assert app._exit
