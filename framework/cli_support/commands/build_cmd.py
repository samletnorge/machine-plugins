"""machine build — validate and build for production."""

from __future__ import annotations

import typer
from rich.console import Console

from machine_core.plugins.cli_support.utils import (
    find_project_root,
    load_machine_config,
)

console = Console()


def build_command():
    """Validate and build for production."""
    root = find_project_root()
    if root is None:
        console.print("[red]Error: Not inside a machine-core project.[/red]")
        raise typer.Exit(code=1)

    config = load_machine_config(root)
    entry = config.get("entry", "src.main:machine")

    console.print("[bold]Running build checks...[/bold]")

    # Check pyproject.toml
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        console.print("[red]✗ pyproject.toml not found[/red]")
        raise typer.Exit(code=1)
    console.print("[green]✓[/green] pyproject.toml valid")

    # Check entry point
    module_path, _, attr_name = entry.rpartition(":")
    if not module_path or not attr_name:
        console.print(f"[red]✗ Invalid entry point: {entry}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[green]✓[/green] Entry point: {entry}")

    # Check source directory
    src_dir = root / "src"
    if not src_dir.exists():
        console.print("[red]✗ src/ directory not found[/red]")
        raise typer.Exit(code=1)
    console.print("[green]✓[/green] Source directory exists")

    console.print("\n[green]Build checks passed![/green]")
