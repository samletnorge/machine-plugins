"""Services tab — server and studio status/control."""

from __future__ import annotations

import subprocess
import sys

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, Button, Label, Log
from textual.widget import Widget

import httpx


class ServicesScreen(Widget):
    """Shows server/studio status with start/stop controls."""

    _server_process: subprocess.Popen | None = None

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

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        log = self.query_one("#service-logs", Log)

        if event.button.id == "start-dev-btn":
            log.write_line("Starting dev server...")
            try:
                self._server_process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "machine_cli.commands._dev_server:app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "8000",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                log.write_line(f"Server started (PID: {self._server_process.pid})")
                # Wait briefly then check status
                import asyncio

                await asyncio.sleep(1.5)
                await self._check_status()
            except Exception as e:
                log.write_line(f"Failed to start: {e}")

        elif event.button.id == "stop-server-btn":
            log.write_line("Stopping server...")
            if self._server_process and self._server_process.poll() is None:
                self._server_process.terminate()
                self._server_process.wait(timeout=5)
                self._server_process = None
                log.write_line("Server stopped.")
            else:
                # Try to kill by port
                try:
                    subprocess.run(
                        ["fuser", "-k", "8000/tcp"],
                        capture_output=True,
                    )
                    log.write_line("Server stopped (killed by port).")
                except Exception:
                    log.write_line("Could not stop server.")
            await self._check_status()
