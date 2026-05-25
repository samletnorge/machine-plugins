"""Config tab — view and edit machine-core configuration."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, ListView, ListItem, Label, Button, TextArea
from textual.widget import Widget


PLUGIN_DIR = Path.home() / ".config" / "machine-core" / "plugins"


class ConfigScreen(Widget):
    """View machine-core configuration from pyproject.toml and plugin manifests."""

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="config-list-pane"):
                yield Label("Configuration", classes="pane-title")
                yield ListView(id="config-list")
                yield Button("Refresh", id="refresh-config-btn", variant="primary")
            with Vertical(id="config-edit-pane"):
                yield Label("Details", classes="pane-title")
                yield Static("Select an item to view", id="config-content")

    async def on_mount(self) -> None:
        """Load config sources."""
        await self._load_config()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh-config-btn":
            await self._load_config()

    async def _load_config(self) -> None:
        """Populate config items from multiple sources."""
        list_view = self.query_one("#config-list", ListView)
        list_view.clear()

        self._config_items: dict[str, str] = {}

        # 1. Current project pyproject.toml [tool.machine-core]
        pyproject_path = Path.cwd() / "pyproject.toml"
        if pyproject_path.exists():
            try:
                data = tomllib.loads(pyproject_path.read_text())
                machine_config = data.get("tool", {}).get("machine-core", {})
                if machine_config:
                    formatted = json.dumps(machine_config, indent=2)
                    self._config_items["pyproject.toml"] = (
                        f"[tool.machine-core] from {pyproject_path}\n\n{formatted}"
                    )
                    list_view.append(
                        ListItem(Label("📄 pyproject.toml"), name="pyproject.toml")
                    )
            except Exception:
                pass

        # 2. Plugin manifests from install dir
        if PLUGIN_DIR.exists():
            for manifest_path in sorted(PLUGIN_DIR.glob("*/manifest.json")):
                try:
                    manifest = json.loads(manifest_path.read_text())
                    name = manifest.get("name", manifest_path.parent.name)
                    formatted = json.dumps(manifest, indent=2)
                    key = f"manifest:{name}"
                    self._config_items[key] = (
                        f"Plugin: {name}\nPath: {manifest_path}\n\n{formatted}"
                    )
                    list_view.append(ListItem(Label(f"  📦 {name}"), name=key))
                except (json.JSONDecodeError, OSError):
                    pass

        # 3. Global config file (if exists)
        global_config = Path.home() / ".config" / "machine-core" / "config.json"
        if global_config.exists():
            try:
                data = json.loads(global_config.read_text())
                formatted = json.dumps(data, indent=2)
                self._config_items["global"] = (
                    f"Global config: {global_config}\n\n{formatted}"
                )
                list_view.append(ListItem(Label("⚙️  Global config"), name="global"))
            except Exception:
                pass

        # 4. Server URL setting
        server_url = getattr(self.app, "server_url", "http://localhost:8000")
        self._config_items["server"] = (
            f"Server URL: {server_url}\n\n"
            f"Plugin directory: {PLUGIN_DIR}\n"
            f"Plugins installed: {len(list(PLUGIN_DIR.glob('*/manifest.json'))) if PLUGIN_DIR.exists() else 0}"
        )
        list_view.append(ListItem(Label("🌐 Server settings"), name="server"))

        if not self._config_items:
            content = self.query_one("#config-content", Static)
            content.update(
                "No configuration found.\n\n"
                "Create a project with: machine init <name>\n"
                "Or install plugins with: machine plugin install --all-framework"
            )

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Show selected config content."""
        name = event.item.name
        content = self.query_one("#config-content", Static)
        if hasattr(self, "_config_items") and name in self._config_items:
            content.update(self._config_items[name])
        else:
            content.update(f"No data for: {name}")
