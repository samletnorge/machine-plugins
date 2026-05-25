"""machine agent — manage agents."""

from __future__ import annotations

from pathlib import Path

import typer
from jinja2 import Environment, PackageLoader, select_autoescape
from rich.console import Console

from cli_support.utils import find_project_root

console = Console()

env = Environment(
    loader=PackageLoader("cli_support", "scaffolds"),
    autoescape=select_autoescape(),
    keep_trailing_newline=True,
)

agent_app = typer.Typer(name="agent", help="Manage agents.")


@agent_app.command("add")
def agent_add(
    name: str = typer.Argument(..., help="Name of the agent to create."),
):
    """Scaffold a new agent."""
    root = find_project_root()
    if root is None:
        console.print("[red]Error: Not inside a machine-core project.[/red]")
        raise typer.Exit(code=1)

    agents_dir = root / "src" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    agent_file = agents_dir / f"{name}.py"
    if agent_file.exists():
        console.print(f"[red]Agent {name} already exists at {agent_file}[/red]")
        raise typer.Exit(code=1)

    template = env.get_template("agent.py.j2")
    agent_file.write_text(template.render(agent_name=name))

    console.print(f"[green]✓[/green] Created agent [bold]{name}[/bold] at {agent_file}")
