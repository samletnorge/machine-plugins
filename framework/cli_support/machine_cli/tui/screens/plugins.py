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
                categories = data.get("categories", {})

                for category, count in categories.items():
                    # Add category header
                    list_view.append(
                        ListItem(
                            Label(f"[{category}] ({count} items)"),
                            name=f"_cat_{category}",
                        )
                    )
                    # Fetch actual items for this category
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
                                list_view.append(
                                    ListItem(Label(f"  {item_name}"), name=item_name)
                                )
                        except Exception:
                            pass

                if not categories:
                    details = self.query_one("#plugin-details", Static)
                    details.update(
                        "No categories registered.\nPlugins are loaded but no items registered yet."
                    )

        except httpx.ConnectError:
            details = self.query_one("#plugin-details", Static)
            details.update("Server not running. Start with: machine dev")

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Show plugin details when selected."""
        name = event.item.name
        details = self.query_one("#plugin-details", Static)
        if name and name.startswith("_cat_"):
            category = name[5:]
            details.update(f"Category: {category}\nType: Plugin-defined category")
        else:
            details.update(f"Name: {name}\nStatus: Loaded")
