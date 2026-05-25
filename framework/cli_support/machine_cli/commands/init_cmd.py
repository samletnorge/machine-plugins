"""machine init — scaffold a new machine-core project."""

from __future__ import annotations

from pathlib import Path

import typer
from jinja2 import Environment, PackageLoader, select_autoescape
from rich.console import Console

console = Console()

env = Environment(
    loader=PackageLoader("cli_support", "scaffolds"),
    autoescape=select_autoescape(),
    keep_trailing_newline=True,
)


def init_command(
    path: str = typer.Argument(..., help="Directory to create the project in."),
    name: str = typer.Option(
        None, "--name", "-n", help="Project name (defaults to directory name)."
    ),
):
    """Scaffold a new machine-core project."""
    target = Path(path).resolve()

    if target.exists() and any(target.iterdir()):
        console.print(f"[red]Error: {target} already exists and is not empty.[/red]")
        raise typer.Exit(code=1)

    project_name = name or target.name

    target.mkdir(parents=True, exist_ok=True)
    (target / "src").mkdir(exist_ok=True)
    (target / "src" / "agents").mkdir(exist_ok=True)

    context = {"project_name": project_name}

    templates = {
        "project/pyproject.toml.j2": target / "pyproject.toml",
        "project/src/__init__.py.j2": target / "src" / "__init__.py",
        "project/src/main.py.j2": target / "src" / "main.py",
        "project/src/agents/example.py.j2": target / "src" / "agents" / "example.py",
    }

    for template_name, output_path in templates.items():
        template = env.get_template(template_name)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(template.render(**context))

    (target / "src" / "agents" / "__init__.py").write_text("")

    console.print(
        f"[green]✓[/green] Created project [bold]{project_name}[/bold] at {target}"
    )
    console.print(f"\n  cd {target}")
    console.print("  uv sync")
    console.print("  machine dev")
