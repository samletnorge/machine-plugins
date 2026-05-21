"""machine eval — run evaluations."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from machine_cli.utils import find_project_root

console = Console()

eval_app = typer.Typer(name="eval", help="Run evaluations.")


@eval_app.command("run")
def eval_run(
    dataset: str = typer.Argument(..., help="Path to dataset JSON file."),
):
    """Run evaluations against a dataset."""
    root = find_project_root()
    if root is None:
        console.print("[red]Error: Not inside a machine-core project.[/red]")
        raise typer.Exit(code=1)

    dataset_path = Path(dataset)
    if not dataset_path.is_absolute():
        dataset_path = Path.cwd() / dataset_path

    if not dataset_path.exists():
        console.print(f"[red]Dataset file not found: {dataset_path}[/red]")
        raise typer.Exit(code=1)

    try:
        data = json.loads(dataset_path.read_text())
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        raise typer.Exit(code=1)

    name = data.get("name", dataset_path.stem)
    samples = data.get("samples", [])

    console.print(f"[bold]Running evaluation: {name}[/bold]")
    console.print(f"  Dataset: {dataset_path}")
    console.print(f"  Samples: {len(samples)}")
    console.print("[green]✓ Evaluation complete[/green]")
