"""machine-core TUI application."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane, Static


class MachineApp(App):
    """The machine-core terminal UI."""

    TITLE = "machine"
    CSS_PATH = "styles/app.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("?", "help", "Help"),
    ]

    def __init__(self, server_url: str = "http://localhost:8000") -> None:
        super().__init__()
        self.server_url = server_url

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Plugins", id="plugins-tab"):
                from .screens.plugins import PluginsScreen

                yield PluginsScreen()
            with TabPane("Store", id="store-tab"):
                from .screens.store import StoreScreen

                yield StoreScreen()
            with TabPane("Services", id="services-tab"):
                from .screens.services import ServicesScreen

                yield ServicesScreen()
            with TabPane("Config", id="config-tab"):
                from .screens.config import ConfigScreen

                yield ConfigScreen()
        yield Footer()
