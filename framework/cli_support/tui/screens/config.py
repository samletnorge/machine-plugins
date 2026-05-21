"""Config tab — plugin configuration editor."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Static
from textual.widget import Widget


class ConfigScreen(Widget):
    """Edit plugin configuration."""

    def compose(self) -> ComposeResult:
        yield Static(
            "Config — coming soon.\n\nEdit plugin configuration with auto-generated forms."
        )
