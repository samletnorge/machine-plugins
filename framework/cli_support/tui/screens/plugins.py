"""Plugins tab — shows installed plugins with status."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, ListView, ListItem, Label
from textual.widget import Widget

import httpx


class PluginsScreen(Widget):
    """Displays installed plugins with details panel."""

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="plugin-list-pane"):
                yield Label("Installed Plugins", classes="pane-title")
                yield ListView(id="plugin-list")
            with Vertical(id="plugin-detail-pane"):
                yield Label("Details", classes="pane-title")
                yield Static("Select a plugin to view details", id="plugin-details")

    async def on_mount(self) -> None:
        """Load plugins from server on mount."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.app.server_url}/health")
                data = resp.json()
                list_view = self.query_one("#plugin-list", ListView)
                for category, info in data.get("categories", {}).items():
                    for item_name in info.get("items", []):
                        list_view.append(
                            ListItem(Label(f"  {item_name}"), name=item_name)
                        )
        except httpx.ConnectError:
            details = self.query_one("#plugin-details", Static)
            details.update("Server not running. Start with: machine dev")

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Show plugin details when selected."""
        name = event.item.name
        details = self.query_one("#plugin-details", Static)
        details.update(f"Name: {name}\nStatus: Loaded")
