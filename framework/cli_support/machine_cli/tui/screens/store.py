"""Store tab — browse and install plugins from registry."""

from __future__ import annotations

import asyncio
import subprocess
import sys

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, ListView, ListItem, Label, Input, Button
from textual.widget import Widget

try:
    from machine_core.plugin.registry import RegistryClient
    from machine_core.plugin.installer import PluginInstaller
except ImportError:
    RegistryClient = None  # type: ignore[assignment, misc]
    PluginInstaller = None  # type: ignore[assignment, misc]


class StoreScreen(Widget):
    """Browse plugins from the registry and install them."""

    _selected_plugin = None

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Input(placeholder="Search plugins...", id="store-search")
            with Horizontal():
                with Vertical(id="store-list-pane"):
                    yield Label("Available Plugins", classes="pane-title")
                    yield ListView(id="store-list")
                with Vertical(id="store-detail-pane"):
                    yield Label("Details", classes="pane-title")
                    yield Static("Select a plugin to view details", id="store-details")
                    yield Button(
                        "Install",
                        id="store-install-btn",
                        variant="success",
                        disabled=True,
                    )

    async def on_mount(self) -> None:
        """Load plugins from registry on mount."""
        if RegistryClient is None:
            details = self.query_one("#store-details", Static)
            details.update(
                "machine-core not installed.\n"
                "Cannot browse registry.\n\n"
                "Install: pip install git+ssh://git@github.com/samletnorge/machine-core.git"
            )
            return
        self._client = RegistryClient()
        self._installer = PluginInstaller() if PluginInstaller else None
        await self._load_plugins()

    async def _load_plugins(self, query: str = "") -> None:
        """Populate list from registry."""
        list_view = self.query_one("#store-list", ListView)
        details = self.query_one("#store-details", Static)
        list_view.clear()

        try:
            if query:
                plugins = await self._client.search_plugins(query)
            else:
                plugins = await self._client.list_plugins()
        except Exception as e:
            details.update(f"Failed to load registry:\n{e}")
            return

        if not plugins:
            details.update("No plugins found.")
            return

        # Check which are installed
        installed_names = set()
        if self._installer:
            installed_names = set(self._installer.installed_plugins())

        for plugin in plugins:
            installed = (
                plugin.name in installed_names
                or plugin.name.replace("-", "_") in installed_names
            )
            icon = "[green]✓[/green]" if installed else " "
            tier_badge = f"[dim]{plugin.tier}[/dim]"
            item = ListItem(
                Label(f"{icon} {plugin.name} {tier_badge}"),
                name=plugin.name,
            )
            list_view.append(item)

        details.update(
            f"{len(plugins)} plugins available\n"
            f"[green]✓[/green] = already installed\n\n"
            f"Select a plugin to see details and install."
        )

        # Store for later
        self._all_plugins = {p.name: p for p in plugins}

    async def on_input_changed(self, event: Input.Changed) -> None:
        """Filter list on search input."""
        if event.input.id == "store-search":
            await self._load_plugins(event.value)

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Show plugin details."""
        name = event.item.name
        if not hasattr(self, "_client"):
            return

        try:
            plugin = await self._client.get_plugin(name)
        except Exception:
            plugin = (
                self._all_plugins.get(name) if hasattr(self, "_all_plugins") else None
            )

        if plugin:
            details = self.query_one("#store-details", Static)
            installed = False
            if self._installer:
                installed = self._installer.is_installed(
                    plugin.name
                ) or self._installer.is_installed(plugin.name.replace("-", "_"))

            status_str = (
                "[green]Installed[/green]"
                if installed
                else "[yellow]Not installed[/yellow]"
            )
            info = (
                f"Name: {plugin.name}\n"
                f"Tier: {plugin.tier}\n"
                f"Runtime: {plugin.runtime}\n"
                f"Version: {plugin.version}\n"
                f"Status: {status_str}\n"
            )
            if plugin.description:
                info += f"\n{plugin.description}"

            details.update(info)
            self._selected_plugin = plugin
            install_btn = self.query_one("#store-install-btn", Button)
            if installed:
                install_btn.label = "Reinstall"
                install_btn.disabled = False
            else:
                install_btn.label = "Install"
                install_btn.disabled = False

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle install button."""
        if event.button.id == "store-install-btn" and self._selected_plugin:
            plugin = self._selected_plugin
            details = self.query_one("#store-details", Static)
            install_btn = self.query_one("#store-install-btn", Button)
            install_btn.disabled = True
            details.update(f"Installing {plugin.name}...\nThis may take a moment.")

            try:
                if self._installer:
                    path = await self._installer.install(plugin.name, force=True)
                    details.update(
                        f"[green]✓ Installed {plugin.name}[/green]\n"
                        f"Path: {path}\n\n"
                        f"Restart server to load: machine dev"
                    )
                else:
                    # Fallback: use uv pip install
                    source = getattr(plugin, "source", None)
                    if source and hasattr(source, "get"):
                        git_url = f"git+ssh://git@github.com/samletnorge/machine-plugins.git#subdirectory={source.get('path', '')}"
                    else:
                        git_url = f"git+ssh://git@github.com/samletnorge/machine-plugins.git#subdirectory=framework/{plugin.name}"

                    proc = await asyncio.create_subprocess_exec(
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        git_url,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT,
                    )
                    output, _ = await proc.communicate()
                    if proc.returncode == 0:
                        details.update(
                            f"[green]✓ Installed {plugin.name}[/green]\n\n"
                            f"Restart server to load."
                        )
                    else:
                        details.update(
                            f"[red]✗ Install failed[/red]\n\n{output.decode()[:500]}"
                        )
            except Exception as e:
                details.update(f"[red]✗ Install failed:[/red]\n{e}")
            finally:
                install_btn.disabled = False
