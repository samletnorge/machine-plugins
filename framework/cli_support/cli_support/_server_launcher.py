"""Auto-start the dev server in background before TUI launches."""

from __future__ import annotations

import os
import subprocess
import sys
import time

import httpx
from rich.console import Console

from .utils import find_project_root, load_machine_config


def is_server_running(server_url: str) -> bool:
    """Check if server is already running."""
    try:
        resp = httpx.get(f"{server_url}/health", timeout=1.5)
        return resp.status_code == 200
    except httpx.HTTPError:
        return False


def ensure_server_running(server_url: str, port: int, console: Console) -> None:
    """Start the dev server in background if it's not already running."""
    if is_server_running(server_url):
        return

    root = find_project_root()
    if root is None:
        # Not in a project — can't start server, TUI will show offline
        return

    config = load_machine_config(root)
    entry = config.get("entry", "src.main:machine")

    # Check that server_support is available
    try:
        import server_support  # noqa: F401
    except ImportError:
        console.print(
            "[yellow]server-support not installed, skipping auto-start.[/yellow]"
        )
        return

    console.print("[dim]Starting server in background...[/dim]")

    env_vars = {
        **os.environ,
        "MACHINE_CORE_ENTRY": entry,
        "MACHINE_CORE_ROOT": str(root),
    }

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "cli_support.commands._dev_server:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--log-level",
        "warning",
    ]

    # Start as detached background process
    proc = subprocess.Popen(
        cmd,
        cwd=str(root),
        env=env_vars,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,  # Detach from terminal — survives TUI exit
    )

    # Wait for it to become healthy (up to 5 seconds)
    for i in range(10):
        time.sleep(0.5)
        if is_server_running(server_url):
            console.print(
                f"[green]Server running[/green] (PID {proc.pid}) at {server_url}"
            )
            return

    # Process might have died
    if proc.poll() is not None:
        console.print(
            "[yellow]Server failed to start. TUI will show offline status.[/yellow]"
        )
    else:
        console.print(
            f"[yellow]Server started (PID {proc.pid}) but not yet healthy.[/yellow]"
        )
