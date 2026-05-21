"""Config tab — view and edit plugin configurations."""

from __future__ import annotations

import json
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, ListView, ListItem, Label
from textual.widget import Widget


CONFIG_DIR = Path.home() / ".config" / "machine-core" / "plugins"


class ConfigScreen(Widget):
    """View and edit plugin configurations."""

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="config-list-pane"):
                yield Label("Plugin Configs", classes="pane-title")
                yield ListView(id="config-list")
            with Vertical(id="config-edit-pane"):
                yield Label("Configuration", classes="pane-title")
                yield Static("Select a plugin to edit its config", id="config-content")

    async def on_mount(self) -> None:
        """Load config files on mount."""
        list_view = self.query_one("#config-list", ListView)
        if CONFIG_DIR.exists():
            for config_file in sorted(CONFIG_DIR.glob("*.json")):
                name = config_file.stem
                list_view.append(ListItem(Label(f"  {name}"), name=name))

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Show config file contents."""
        name = event.item.name
        config_path = CONFIG_DIR / f"{name}.json"
        content = self.query_one("#config-content", Static)
        if config_path.exists():
            data = json.loads(config_path.read_text())
            formatted = json.dumps(data, indent=2)
            content.update(f"File: {config_path}\n\n{formatted}")
        else:
            content.update(f"No config file for {name}")
