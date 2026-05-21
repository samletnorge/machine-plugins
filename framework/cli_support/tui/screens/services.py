"""Services tab — control running services."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Static
from textual.widget import Widget


class ServicesScreen(Widget):
    """View and control machine-core services."""

    def compose(self) -> ComposeResult:
        yield Static(
            "Services — coming soon.\n\nStart, stop, and monitor machine-core services."
        )
