"""machine tool — manage tools."""

from __future__ import annotations

from pathlib import Path

import typer
from jinja2 import Environment, PackageLoader, select_autoescape
from rich.console import Console

from machine_core.plugins.cli_support.utils import find_project_root

console = Console()

env = Environment(
    loader=PackageLoader("machine_core.plugins.cli_support", "scaffolds"),
    autoescape=select_autoescape(),
    keep_trailing_newline=True,
)

tool_app = typer.Typer(name="tool", help="Manage tools.")


@tool_app.command("add")
def tool_add(
    name: str = typer.Argument(..., help="Name of the tool to create."),
):
    """Scaffold a new tool."""
    root = find_project_root()
    if root is None:
        console.print("[red]Error: Not inside a machine-core project.[/red]")
        raise typer.Exit(code=1)

    tools_dir = root / "src" / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)

    tool_file = tools_dir / f"{name}.py"
    if tool_file.exists():
        console.print(f"[red]Tool {name} already exists at {tool_file}[/red]")
        raise typer.Exit(code=1)

    template = env.get_template("tool.py.j2")
    tool_file.write_text(template.render(tool_name=name))

    console.print(f"[green]✓[/green] Created tool [bold]{name}[/bold] at {tool_file}")
