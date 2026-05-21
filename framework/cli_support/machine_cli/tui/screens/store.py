"""Store tab — browse and install plugins from registry."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, ListView, ListItem, Label, Input, Button
from textual.widget import Widget

try:
    from machine_core.plugin.registry import RegistryClient
except ImportError:
    RegistryClient = None  # type: ignore[assignment, misc]


class StoreScreen(Widget):
    """Browse plugins from the registry."""

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
            details.update("machine-core not installed. Cannot browse registry.")
            return
        self._client = RegistryClient()
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
            details.update(f"Failed to load registry: {e}")
            return

        for plugin in plugins:
            item = ListItem(Label(f"  {plugin.name} [{plugin.tier}]"), name=plugin.name)
            list_view.append(item)

    async def on_input_changed(self, event: Input.Changed) -> None:
        """Filter list on search input."""
        if event.input.id == "store-search":
            await self._load_plugins(event.value)

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Show plugin details."""
        name = event.item.name
        plugin = await self._client.get_plugin(name)
        if plugin:
            details = self.query_one("#store-details", Static)
            info = (
                f"Name: {plugin.name}\n"
                f"Tier: {plugin.tier}\n"
                f"Runtime: {plugin.runtime}\n"
                f"Version: {plugin.version}\n\n"
                f"{plugin.description}"
            )
            details.update(info)
            self.query_one("#store-install-btn").disabled = False
            self._selected_plugin = plugin

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle install button."""
        if event.button.id == "store-install-btn" and hasattr(self, "_selected_plugin"):
            plugin = self._selected_plugin
            details = self.query_one("#store-details", Static)
            details.update(f"Installing {plugin.name}...")
