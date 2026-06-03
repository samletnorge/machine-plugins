# cli_support

Framework plugin package for the `machine` CLI and local developer tooling.

## Provides

- the Typer-based `machine` CLI entrypoint
- project loading and config helpers
- dev-server launch helpers
- manifest synchronization utilities used to keep plugin metadata aligned with the active environment
- TUI startup behavior when no explicit subcommand is provided

## Key Files

- `manifest.json`
- `cli_support/main.py`
- `cli_support/_server_launcher.py`
- `cli_support/manifest_sync.py`
- `cli_support/utils.py`

## Role

This package is the command-line surface for working with Machine projects, plugins, Studio, and local development workflows.
