"""Services tab — server and studio status/control."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, Button, Label, Log
from textual.widget import Widget

import httpx


class ServicesScreen(Widget):
    """Shows server/studio status with start/stop controls."""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Services", classes="pane-title")
            yield Static("Checking server status...", id="server-status")
            yield Button("Start Dev Server", id="start-dev-btn", variant="success")
            yield Button(
                "Stop Server", id="stop-server-btn", variant="error", disabled=True
            )
            yield Label("Logs", classes="pane-title")
            yield Log(id="service-logs", max_lines=200)

    async def on_mount(self) -> None:
        """Check server status on mount."""
        await self._check_status()

    async def _check_status(self) -> None:
        status = self.query_one("#server-status", Static)
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                resp = await client.get(f"{self.app.server_url}/health")
                data = resp.json()
                categories = data.get("categories", {})
                status.update(
                    f"Server: [green]running[/green] at {self.app.server_url}\n"
                    f"Categories: {len(categories)} loaded"
                )
                self.query_one("#stop-server-btn").disabled = False
                self.query_one("#start-dev-btn").disabled = True
        except (httpx.ConnectError, httpx.ReadTimeout):
            status.update("Server: [red]stopped[/red]")
            self.query_one("#stop-server-btn").disabled = True
            self.query_one("#start-dev-btn").disabled = False
