"""machine CLI — the main entry point for machine-core developer tooling."""

from __future__ import annotations

import typer
from rich.console import Console

console = Console()

app = typer.Typer(
    name="machine",
    help="machine-core CLI — build, test, and deploy AI agents.",
    no_args_is_help=True,
)


def version_callback(value: bool):
    if value:
        console.print("machine-core 0.5.0")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
):
    """machine-core CLI — build, test, and deploy AI agents."""
    pass


# Register commands
from machine_core.plugins.cli_support.commands.init_cmd import init_command
from machine_core.plugins.cli_support.commands.agent_cmd import agent_app
from machine_core.plugins.cli_support.commands.tool_cmd import tool_app
from machine_core.plugins.cli_support.commands.dev_cmd import dev_command
from machine_core.plugins.cli_support.commands.build_cmd import build_command
from machine_core.plugins.cli_support.commands.deploy_cmd import deploy_command
from machine_core.plugins.cli_support.commands.eval_cmd import eval_app
from machine_core.plugins.cli_support.commands.studio_cmd import studio_command

app.command("init")(init_command)
app.add_typer(agent_app)
app.add_typer(tool_app)
app.command("dev")(dev_command)
app.command("build")(build_command)
app.command("deploy")(deploy_command)
app.add_typer(eval_app)
app.command("studio")(studio_command)
