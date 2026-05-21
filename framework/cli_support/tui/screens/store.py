"""Store tab — browse plugin registry."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Static
from textual.widget import Widget


class StoreScreen(Widget):
    """Browse the plugin registry (machine-plugins)."""

    def compose(self) -> ComposeResult:
        yield Static(
            "Plugin Store — coming soon.\n\nBrowse and install plugins from the registry."
        )
