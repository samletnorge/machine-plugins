"""Plugins tab — shows installed plugins with status."""

from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, ListView, ListItem, Label, Button
from textual.widget import Widget

import httpx


PLUGIN_DIR = Path.home() / ".config" / "machine-core" / "plugins"


class PluginsScreen(Widget):
    """Displays installed plugins with details panel."""

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="plugin-list-pane"):
                yield Label("Installed Plugins", classes="pane-title")
                yield ListView(id="plugin-list")
                yield Button("Refresh", id="refresh-plugins-btn", variant="primary")
            with Vertical(id="plugin-detail-pane"):
                yield Label("Details", classes="pane-title")
                yield Static("Select a plugin to view details", id="plugin-details")

    async def on_mount(self) -> None:
        """Load plugins on mount."""
        await self._load_plugins()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh-plugins-btn":
            await self._load_plugins()

    async def _load_plugins(self) -> None:
        """Load plugins from multiple sources: server, local manifests, pip."""
        list_view = self.query_one("#plugin-list", ListView)
        details = self.query_one("#plugin-details", Static)
        list_view.clear()

        plugins_found: list[dict] = []

        # Source 1: Try server /health for running categories
        server_online = False
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                resp = await client.get(f"{self.app.server_url}/health")
                data = resp.json()
                categories = data.get("categories", {})
                server_online = True

                for category, count in categories.items():
                    plugins_found.append(
                        {
                            "name": category,
                            "source": "server",
                            "status": "running",
                            "items": count,
                        }
                    )
                    # Fetch items if any
                    if count > 0:
                        try:
                            items_resp = await client.get(
                                f"{self.app.server_url}/api/{category}"
                            )
                            items = items_resp.json()
                            for item in items:
                                item_name = (
                                    item
                                    if isinstance(item, str)
                                    else item.get("name", str(item))
                                )
                                plugins_found.append(
                                    {
                                        "name": f"  {item_name}",
                                        "source": "server",
                                        "status": "loaded",
                                        "category": category,
                                    }
                                )
                        except Exception:
                            pass
        except (httpx.ConnectError, httpx.ReadTimeout):
            pass

        # Source 2: Local manifests in ~/.config/machine-core/plugins/
        if PLUGIN_DIR.exists():
            for manifest_path in sorted(PLUGIN_DIR.glob("*/manifest.json")):
                try:
                    manifest = json.loads(manifest_path.read_text())
                    name = manifest.get("name", manifest_path.parent.name)
                    # Skip if already found via server
                    if not any(p["name"] == name for p in plugins_found):
                        plugins_found.append(
                            {
                                "name": name,
                                "source": "local",
                                "status": "installed",
                                "version": manifest.get("version", "?"),
                                "path": str(manifest_path.parent),
                            }
                        )
                except (json.JSONDecodeError, OSError):
                    pass

        # Source 3: pip-installed machine-core-* packages
        for dist in importlib.metadata.distributions():
            dist_name = dist.metadata["Name"] or ""
            if dist_name.startswith("machine-core-") and dist_name != "machine-core":
                short = dist_name.removeprefix("machine-core-").replace("-", "_")
                if not any(p["name"] == short for p in plugins_found):
                    plugins_found.append(
                        {
                            "name": short,
                            "source": "pip",
                            "status": "installed",
                            "version": dist.metadata["Version"] or "?",
                        }
                    )

        # Populate the list
        if not plugins_found:
            if server_online:
                details.update(
                    "Server is running but no plugins are registered.\n"
                    "Install plugins with: machine plugin install --all-framework"
                )
            else:
                details.update(
                    "Server: [red]offline[/red]\n"
                    "No local plugins found.\n\n"
                    "Start server: machine dev\n"
                    "Install plugins: machine plugin install --all-framework"
                )
            return

        status_icon = {"running": "●", "loaded": "  •", "installed": "○"}
        status_color = {"running": "green", "loaded": "cyan", "installed": "yellow"}

        for p in plugins_found:
            icon = status_icon.get(p["status"], "?")
            color = status_color.get(p["status"], "white")
            display = f"[{color}]{icon}[/{color}] {p['name']}"
            list_view.append(ListItem(Label(display), name=p["name"]))

        # Store for detail lookup
        self._plugins = {p["name"]: p for p in plugins_found}

        # Summary at top
        server_status = (
            "[green]online[/green]" if server_online else "[red]offline[/red]"
        )
        details.update(
            f"Server: {server_status}\n"
            f"Plugins: {len(plugins_found)} found\n\n"
            f"● running  ○ installed (not loaded)\n"
            f"Select a plugin to see details."
        )

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Show plugin details when selected."""
        name = event.item.name
        details = self.query_one("#plugin-details", Static)
        if hasattr(self, "_plugins") and name in self._plugins:
            p = self._plugins[name]
            lines = [f"Name: {name}"]
            lines.append(f"Source: {p['source']}")
            lines.append(f"Status: {p['status']}")
            if "version" in p:
                lines.append(f"Version: {p['version']}")
            if "path" in p:
                lines.append(f"Path: {p['path']}")
            if "items" in p:
                lines.append(f"Items registered: {p['items']}")
            if "category" in p:
                lines.append(f"Category: {p['category']}")
            details.update("\n".join(lines))
        else:
            details.update(f"Name: {name}\nStatus: unknown")
