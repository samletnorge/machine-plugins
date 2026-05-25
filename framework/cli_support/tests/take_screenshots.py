"""Take SVG screenshots of the TUI for verification."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from cli_support.tui.app import MachineApp


OUTPUT_DIR = Path(__file__).parent.parent / "screenshots"


async def take_screenshots():
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Mock server being down for plugins/services tabs
    with patch(
        "cli_support.tui.screens.plugins.httpx.AsyncClient"
    ) as mock_plugins_client:
        import httpx as _httpx

        mock_instance = AsyncMock()
        mock_instance.get.side_effect = _httpx.ConnectError("refused")
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_plugins_client.return_value = mock_instance

        with patch(
            "cli_support.tui.screens.services.httpx.AsyncClient"
        ) as mock_svc_client:
            mock_svc_instance = AsyncMock()
            mock_svc_instance.get.side_effect = _httpx.ConnectError("refused")
            mock_svc_instance.__aenter__ = AsyncMock(return_value=mock_svc_instance)
            mock_svc_instance.__aexit__ = AsyncMock(return_value=None)
            mock_svc_client.return_value = mock_svc_instance

            # Mock store with some plugins
            mock_plugin = MagicMock()
            mock_plugin.name = "agent_support"
            mock_plugin.tier = "framework"
            mock_plugin.runtime = "python"
            mock_plugin.version = "0.5.0"
            mock_plugin.description = "Agent support"

            mock_plugin2 = MagicMock()
            mock_plugin2.name = "tool_support"
            mock_plugin2.tier = "framework"
            mock_plugin2.runtime = "python"
            mock_plugin2.version = "0.5.0"
            mock_plugin2.description = "Tool support"

            with patch("cli_support.tui.screens.store.RegistryClient") as mock_rc:
                mock_client_inst = AsyncMock()
                mock_client_inst.list_plugins = AsyncMock(
                    return_value=[mock_plugin, mock_plugin2]
                )
                mock_client_inst.search_plugins = AsyncMock(return_value=[mock_plugin])
                mock_rc.return_value = mock_client_inst

                with patch("cli_support.tui.screens.store.PluginInstaller") as mock_pi:
                    mock_installer = MagicMock()
                    mock_installer.installed_plugins.return_value = ["agent_support"]
                    mock_installer.is_installed.side_effect = lambda n: (
                        n == "agent_support"
                    )
                    mock_pi.return_value = mock_installer

                    from textual.widgets import TabbedContent

                    app = MachineApp(server_url="http://localhost:8000")
                    async with app.run_test(size=(120, 35)) as pilot:
                        tabs = app.query_one(TabbedContent)

                        # Screenshot 1: Plugins tab (default)
                        await pilot.pause()
                        app.save_screenshot(str(OUTPUT_DIR / "01_plugins_tab.svg"))
                        print(f"Saved: {OUTPUT_DIR / '01_plugins_tab.svg'}")

                        # Screenshot 2: Store tab
                        tabs.active = "store-tab"
                        await pilot.pause()
                        await pilot.pause()
                        app.save_screenshot(str(OUTPUT_DIR / "02_store_tab.svg"))
                        print(f"Saved: {OUTPUT_DIR / '02_store_tab.svg'}")

                        # Screenshot 3: Services tab
                        tabs.active = "services-tab"
                        await pilot.pause()
                        await pilot.pause()
                        app.save_screenshot(str(OUTPUT_DIR / "03_services_tab.svg"))
                        print(f"Saved: {OUTPUT_DIR / '03_services_tab.svg'}")

                        # Screenshot 4: Config tab
                        tabs.active = "config-tab"
                        await pilot.pause()
                        await pilot.pause()
                        app.save_screenshot(str(OUTPUT_DIR / "04_config_tab.svg"))
                        print(f"Saved: {OUTPUT_DIR / '04_config_tab.svg'}")


if __name__ == "__main__":
    asyncio.run(take_screenshots())
