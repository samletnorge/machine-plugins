"""machine studio — launch the Studio web UI."""

from __future__ import annotations

import os
import subprocess
import sys

import typer
from rich.console import Console

from machine_cli.utils import (
    find_project_root,
    load_machine_config,
)

console = Console()


def studio_command(
    port: int = typer.Option(3177, "--port", "-p", help="Port to run the Studio on."),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to."),
):
    """Launch the Studio web UI for testing agents and tools."""
    root = find_project_root()
    if root is None:
        console.print("[red]Error: Not inside a machine-core project.[/red]")
        raise typer.Exit(code=1)

    config = load_machine_config(root)
    entry = config.get("entry", "src.main:machine")

    console.print(f"[green]Starting Machine Studio...[/green]")
    console.print(f"  URL: http://{host}:{port}/studio")
    console.print(f"  Entry: {entry}")

    env_vars = {
        "MACHINE_CORE_ENTRY": entry,
        "MACHINE_CORE_ROOT": str(root),
        "MACHINE_STUDIO_ENABLED": "1",
    }

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "machine_cli.commands._dev_server:app",
        "--host",
        host,
        "--port",
        str(port),
    ]

    full_env = {**os.environ, **env_vars}
    subprocess.run(cmd, cwd=str(root), env=full_env)
