"""machine dev — start development server with hot reload."""

from __future__ import annotations

import os
import subprocess
import sys

import typer
from rich.console import Console

from cli_support.utils import (
    find_project_root,
    load_machine_config,
)

console = Console()


def dev_command(
    port: int = typer.Option(
        8000, "--port", "-p", help="Port to run the dev server on."
    ),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to."),
):
    """Start development server with hot reload."""
    root = find_project_root()
    if root is None:
        console.print("[red]Error: Not inside a machine-core project.[/red]")
        raise typer.Exit(code=1)

    config = load_machine_config(root)
    entry = config.get("entry", "src.main:machine")

    console.print(f"[green]Starting dev server...[/green]")
    console.print(f"  URL: http://{host}:{port}")
    console.print(f"  Entry: {entry}")

    # Ensure server_support is installed (required for machine dev)
    try:
        import machine_server  # noqa: F401
    except ImportError:
        console.print("[yellow]Installing server-support plugin...[/yellow]")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "uv",
                "pip",
                "install",
                "git+ssh://git@github.com/samletnorge/machine-plugins.git#subdirectory=framework/server_support",
            ],
            check=True,
            capture_output=True,
        )

    # Ensure agent_support is installed
    try:
        import machine_agent  # noqa: F401
    except ImportError:
        console.print("[yellow]Installing agent-support plugin...[/yellow]")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "uv",
                "pip",
                "install",
                "git+ssh://git@github.com/samletnorge/machine-plugins.git#subdirectory=framework/agent_support",
            ],
            check=True,
            capture_output=True,
        )

    # Ensure tool_support is installed
    try:
        import machine_tool  # noqa: F401
    except ImportError:
        console.print("[yellow]Installing tool-support plugin...[/yellow]")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "uv",
                "pip",
                "install",
                "git+ssh://git@github.com/samletnorge/machine-plugins.git#subdirectory=framework/tool_support",
            ],
            check=True,
            capture_output=True,
        )

    env_vars = {
        "MACHINE_CORE_ENTRY": entry,
        "MACHINE_CORE_ROOT": str(root),
    }

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "cli_support.commands._dev_server:app",
        "--reload",
        "--host",
        host,
        "--port",
        str(port),
    ]

    # Only add --reload-dir if src/ exists
    src_dir = root / "src"
    if src_dir.is_dir():
        cmd.extend(["--reload-dir", str(src_dir)])

    full_env = {**os.environ, **env_vars}
    subprocess.run(cmd, cwd=str(root), env=full_env)
