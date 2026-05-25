"""Services tab — server and studio status/control."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Button, Label, Log
from textual.widget import Widget

import httpx

# Shared log file path — must match _server_launcher.py
SERVER_LOG_FILE = (
    __import__("pathlib").Path.home() / ".config" / "machine-core" / "server.log"
)


class ServicesScreen(Widget):
    """Shows server/studio status with start/stop controls."""

    _server_process: subprocess.Popen | None = None
    _log_task: asyncio.Task | None = None
    _tail_task: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Services", classes="pane-title")
            yield Static("Checking server status...", id="server-status")
            with Horizontal(id="service-buttons"):
                yield Button("Start Server", id="start-dev-btn", variant="success")
                yield Button(
                    "Stop Server", id="stop-server-btn", variant="error", disabled=True
                )
                yield Button("Refresh", id="refresh-status-btn", variant="primary")
            yield Label("Server Logs", classes="pane-title")
            yield Log(id="service-logs", max_lines=500)

    async def on_mount(self) -> None:
        """Check server status on mount."""
        await self._check_status()

    async def _check_status(self) -> None:
        status = self.query_one("#server-status", Static)
        start_btn = self.query_one("#start-dev-btn", Button)
        stop_btn = self.query_one("#stop-server-btn", Button)

        try:
            async with httpx.AsyncClient(timeout=2) as client:
                resp = await client.get(f"{self.app.server_url}/health")
                data = resp.json()
                categories = data.get("categories", {})
                cat_list = (
                    ", ".join(f"{k}({v})" for k, v in categories.items())
                    if categories
                    else "none"
                )
                status.update(
                    f"Server: [green]● running[/green] at {self.app.server_url}\n"
                    f"Categories: {cat_list}"
                )
                stop_btn.disabled = False
                start_btn.disabled = True

                # If server is running but we didn't start it, tail the log file
                if self._server_process is None and self._tail_task is None:
                    self._start_log_tail()

        except (httpx.ConnectError, httpx.ReadTimeout):
            status.update(
                f"Server: [red]● stopped[/red]\nExpected at: {self.app.server_url}"
            )
            stop_btn.disabled = True
            start_btn.disabled = False
            # Stop tailing if server went down
            self._stop_log_tail()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        log = self.query_one("#service-logs", Log)

        if event.button.id == "start-dev-btn":
            await self._start_server(log)
        elif event.button.id == "stop-server-btn":
            await self._stop_server(log)
        elif event.button.id == "refresh-status-btn":
            await self._check_status()

    async def _start_server(self, log: Log) -> None:
        """Start the dev server as a subprocess."""
        log.write_line("Starting dev server...")

        # Stop any existing tail task
        self._stop_log_tail()

        try:
            SERVER_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            log_fh = open(SERVER_LOG_FILE, "w")

            self._server_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "cli_support.commands._dev_server:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                    "--log-level",
                    "info",
                ],
                stdout=log_fh,
                stderr=subprocess.STDOUT,
            )
            log.write_line(f"Server process started (PID: {self._server_process.pid})")

            # Start tailing the log file
            self._start_log_tail()

            # Wait for server to become healthy
            for _ in range(10):
                await asyncio.sleep(0.5)
                try:
                    async with httpx.AsyncClient(timeout=1) as client:
                        resp = await client.get(f"{self.app.server_url}/health")
                        if resp.status_code == 200:
                            log.write_line("[green]Server is healthy![/green]")
                            break
                except (httpx.ConnectError, httpx.ReadTimeout):
                    continue
            else:
                log.write_line(
                    "[yellow]Server started but health check not responding yet.[/yellow]"
                )

            await self._check_status()

        except FileNotFoundError:
            log.write_line(
                "[red]Error: uvicorn not found. Install with: pip install uvicorn[/red]"
            )
        except Exception as e:
            log.write_line(f"[red]Failed to start: {e}[/red]")

    async def _stop_server(self, log: Log) -> None:
        """Stop the server."""
        log.write_line("Stopping server...")

        # Cancel log tasks
        if self._log_task and not self._log_task.done():
            self._log_task.cancel()
            self._log_task = None
        self._stop_log_tail()

        if self._server_process and self._server_process.poll() is None:
            self._server_process.terminate()
            try:
                self._server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._server_process.kill()
            self._server_process = None
            log.write_line("Server stopped.")
        else:
            # Try to kill by port
            try:
                result = subprocess.run(
                    ["lsof", "-ti", ":8000"],
                    capture_output=True,
                    text=True,
                )
                if result.stdout.strip():
                    pids = result.stdout.strip().split("\n")
                    for pid in pids:
                        subprocess.run(["kill", pid.strip()], capture_output=True)
                    log.write_line(
                        f"Killed process(es) on port 8000: {', '.join(pids)}"
                    )
                else:
                    log.write_line("No process found on port 8000.")
            except FileNotFoundError:
                # lsof not available, try fuser
                try:
                    subprocess.run(["fuser", "-k", "8000/tcp"], capture_output=True)
                    log.write_line("Server stopped (killed by port).")
                except Exception:
                    log.write_line(
                        "[red]Could not stop server. Try: kill $(lsof -ti:8000)[/red]"
                    )

        await asyncio.sleep(0.5)
        await self._check_status()

    async def _read_logs(self, log: Log) -> None:
        """Read stdout from server process in background."""
        if not self._server_process or not self._server_process.stdout:
            return
        try:
            loop = asyncio.get_event_loop()
            while self._server_process and self._server_process.poll() is None:
                line = await loop.run_in_executor(
                    None, self._server_process.stdout.readline
                )
                if line:
                    log.write_line(line.rstrip())
                else:
                    break
        except (asyncio.CancelledError, OSError):
            pass

    def _start_log_tail(self) -> None:
        """Start tailing the server log file."""
        log = self.query_one("#service-logs", Log)
        self._tail_task = asyncio.create_task(self._tail_log_file(log))

    def _stop_log_tail(self) -> None:
        """Stop the log file tail task."""
        if self._tail_task and not self._tail_task.done():
            self._tail_task.cancel()
            self._tail_task = None

    async def _tail_log_file(self, log: Log) -> None:
        """Tail SERVER_LOG_FILE, streaming new lines to the Log widget."""
        try:
            # Wait for log file to appear (server may have just started)
            for _ in range(20):  # up to 6 seconds
                if SERVER_LOG_FILE.exists() and SERVER_LOG_FILE.stat().st_size > 0:
                    break
                await asyncio.sleep(0.3)

            if not SERVER_LOG_FILE.exists() or SERVER_LOG_FILE.stat().st_size == 0:
                log.write_line(
                    "[dim]No server logs available yet. "
                    "Logs will appear after the server is (re)started with the current version.[/dim]"
                )
                # Still keep polling for the file to appear
                while True:
                    await asyncio.sleep(1.0)
                    if SERVER_LOG_FILE.exists() and SERVER_LOG_FILE.stat().st_size > 0:
                        break
                # Fall through to read it

            # Read existing content (last 50 lines)
            lines = SERVER_LOG_FILE.read_text().splitlines()
            for line in lines[-50:]:
                log.write_line(line)

            # Then follow new lines
            with open(SERVER_LOG_FILE, "r") as f:
                # Seek to end
                f.seek(0, os.SEEK_END)
                while True:
                    line = f.readline()
                    if line:
                        log.write_line(line.rstrip())
                    else:
                        await asyncio.sleep(0.3)
        except (asyncio.CancelledError, OSError):
            pass
