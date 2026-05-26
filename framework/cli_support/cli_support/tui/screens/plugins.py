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
        except httpx.HTTPError:
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

        # Populate the list with section headers
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

        # Split into active (running/loaded) vs available (installed but not active)
        active = [p for p in plugins_found if p["status"] in ("running", "loaded")]
        available = [p for p in plugins_found if p["status"] == "installed"]

        # Section: Active in this project
        if active:
            list_view.append(
                ListItem(
                    Label("[bold green]━━ Active in this project ━━[/bold green]"),
                    name="_header_active",
                )
            )
            for p in active:
                if p["status"] == "running":
                    display = f"  [green]●[/green] {p['name']} [dim]({p.get('items', 0)} items)[/dim]"
                else:
                    display = f"    [cyan]•[/cyan] {p['name']}"
                list_view.append(ListItem(Label(display), name=p["name"]))

        # Section: Available on this machine
        if available:
            list_view.append(
                ListItem(
                    Label("[bold yellow]━━ Available on this machine ━━[/bold yellow]"),
                    name="_header_available",
                )
            )
            for p in available:
                version = (
                    f" [dim]v{p.get('version', '?')}[/dim]" if "version" in p else ""
                )
                source_tag = f" [dim]({p['source']})[/dim]"
                display = f"  [yellow]○[/yellow] {p['name']}{version}{source_tag}"
                list_view.append(ListItem(Label(display), name=p["name"]))

        # Store for detail lookup
        self._plugins = {p["name"]: p for p in plugins_found}

        # Summary in details pane
        server_status = (
            "[green]online[/green]" if server_online else "[red]offline[/red]"
        )
        details.update(
            f"Server: {server_status}\n"
            f"Active: {len(active)} plugins loaded in this project\n"
            f"Available: {len(available)} installed but not active\n\n"
            f"To activate a plugin, add it to\n"
            f"[tool.machine-core].plugins in pyproject.toml\n"
            f"then restart: machine dev"
        )

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Show plugin details when selected."""
        name = event.item.name
        details = self.query_one("#plugin-details", Static)

        # Ignore section headers
        if name and name.startswith("_header_"):
            return

        if hasattr(self, "_plugins") and name in self._plugins:
            p = self._plugins[name]
            lines = [f"[bold]{name}[/bold]", ""]

            if p["status"] in ("running", "loaded"):
                lines.append("Status: [green]Active in this project[/green]")
                if "items" in p:
                    lines.append(f"Registered items: {p['items']}")
                if "category" in p:
                    lines.append(f"Category: {p['category']}")
            else:
                lines.append("Status: [yellow]Installed but not active[/yellow]")
                lines.append("")
                lines.append("To activate, add to pyproject.toml:")
                lines.append(f'  plugins = ["...', '{name}", ...]')

            if "version" in p:
                lines.append(f"\nVersion: {p['version']}")
            if "source" in p:
                lines.append(f"Source: {p['source']}")
            if "path" in p:
                lines.append(f"Path: {p['path']}")

            details.update("\n".join(lines))
        else:
            details.update(f"Name: {name}\nStatus: unknown")
