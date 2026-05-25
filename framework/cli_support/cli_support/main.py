"""machine CLI — the main entry point for machine-core developer tooling."""

from __future__ import annotations

import typer
from rich.console import Console

console = Console()

app = typer.Typer(
    name="machine",
    help="machine-core CLI — build, test, and deploy AI agents.",
    no_args_is_help=False,
    invoke_without_command=True,
)


def version_callback(value: bool):
    if value:
        console.print("machine-core 0.5.0")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
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
    if ctx.invoked_subcommand is None:
        from .tui.app import MachineApp
        from ._server_launcher import ensure_server_running

        port = 8000
        server_url = f"http://127.0.0.1:{port}"

        # Auto-start server in background if not already running
        ensure_server_running(server_url, port, console)

        tui = MachineApp(server_url=server_url)
        tui.run()


# Register commands
from .commands.init_cmd import init_command
from .commands.agent_cmd import agent_app
from .commands.tool_cmd import tool_app
from .commands.dev_cmd import dev_command
from .commands.build_cmd import build_command
from .commands.deploy_cmd import deploy_command
from .commands.eval_cmd import eval_app
from .commands.studio_cmd import studio_command
from .commands.plugin_cmd import plugin_app

app.command("init")(init_command)
app.add_typer(agent_app)
app.add_typer(tool_app)
app.command("dev")(dev_command)
app.command("build")(build_command)
app.command("deploy")(deploy_command)
app.add_typer(eval_app)
app.command("studio")(studio_command)
app.add_typer(plugin_app, name="plugin")
