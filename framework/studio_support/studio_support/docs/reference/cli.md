# CLI reference

The `machine` CLI is provided by the `cli_support` framework plugin. It is a Typer app with
commands for scaffolding, development, building, deploying, evaluating, Studio, and plugin
management.

```bash
machine [COMMAND] [OPTIONS]
```

Run with no subcommand to launch the interactive TUI and auto-start the dev server on port
`8008` if it is not already running.

| Command | Purpose |
|---------|---------|
| `machine` | Interactive TUI; auto-starts the dev server on `8008`. |
| `machine --version`, `-v` | Print `machine-core <version>` and exit. |
| [`machine init`](#machine-init) | Scaffold a new project. |
| [`machine agent add`](#machine-agent-add) | Scaffold an agent file. |
| [`machine tool add`](#machine-tool-add) | Scaffold a tool file. |
| [`machine dev`](#machine-dev) | Run the dev server with hot reload. |
| [`machine build`](#machine-build) | Validate the project for production. |
| [`machine deploy`](#machine-deploy) | Deploy via a deployer plugin. |
| [`machine eval run`](#machine-eval-run) | Run an evaluation dataset. |
| [`machine studio`](#machine-studio) | Launch the Studio web UI. |
| [`machine plugin ...`](#machine-plugin) | Manage plugins. |

## `machine --version`

```bash
machine --version
# machine-core 0.11.0
```

The version is read from installed `machine-core` metadata, falling back to `0.11.0`.

## `machine init`

```bash
machine init <path> [--name/-n <project_name>]
```

Scaffolds a project into `<path>`. Refuses to write into a non-empty directory. The project
name defaults to the directory name.

Creates:

```
<path>/
├── pyproject.toml
├── .gitignore
└── src/
    ├── __init__.py
    ├── main.py
    └── agents/
        ├── __init__.py
        └── example.py
```

After scaffolding it prints:

```
  cd <path>
  uv sync
  machine dev
```

## `machine agent add`

```bash
machine agent add <name>
```

Creates `src/agents/<name>.py` from the agent scaffold. Fails if the file already exists.

> **Note:** The current template is a TODO stub, not a runnable agent. See
> `scaffolds/agent.py.j2`.

## `machine tool add`

```bash
machine tool add <name>
```

Creates `src/tools/<name>.py` from the tool scaffold (creating `src/tools/` if needed). Fails
if the file already exists.

> **Note:** The current template is a TODO stub, not a runnable `@tool`. See
> `scaffolds/tool.py.j2`.

## `machine dev`

```bash
machine dev [--port/-p <port>] [--host <host>]
```

| Option | Default | Meaning |
|--------|---------|---------|
| `--port/-p` | `8008` | Port to bind. |
| `--host` | `127.0.0.1` | Host to bind. |

What it does:

1. Finds the project root (walking up for `pyproject.toml` with `[tool.machine-core]`).
2. Reads `entry` (default `src.main:machine`).
3. Syncs plugin manifests from site-packages to `~/.config/machine-core/plugins/`.
4. Ensures `server_support`, `agent_support`, and `tool_support` are importable, installing
   them from git subdirectories if missing.
5. Writes a temporary `_machine_dev_server.py` and runs `uvicorn --reload` with the project's
   `.venv/bin/python`, setting `MACHINE_CORE_ENTRY` and `MACHINE_CORE_ROOT`.
6. Removes the temporary file when it exits.

Errors if no project root or no `.venv` is found.

## `machine build`

```bash
machine build
```

Validates the project: `pyproject.toml` exists, `entry` is a valid `module:attr`, and `src/`
exists. Prints a checklist and exits non-zero on failure.

> **Note:** This command validates only; it does not produce build artifacts.

## `machine deploy`

```bash
machine deploy --target/-t <target> [--port/-p <port>] [--env/-e KEY=VALUE ...]
```

| Option | Default | Meaning |
|--------|---------|---------|
| `--target/-t` | required | `docker`, `dokploy`, `vercel`, or `cloudflare`. |
| `--port/-p` | `8008` | Port to expose. |
| `--env/-e` | — | Repeatable `KEY=VALUE` environment variable. |

Resolves a deployer from `machine.resolve("deployer", target)`, falling back to the built-in
map (`docker`, `vercel`, `cloudflare`). Runs `deployer.deploy(None, config)` and prints the
result URL on success.

> **Note:** `dokploy` is advertised but is neither registered by `deployer_support` nor in
> the fallback map, so `--target dokploy` is not usable out of the box. See
> [Deployers](../guides/deployers.md#built-in-deployers).

## `machine eval run`

```bash
machine eval run <dataset.json>
```

Reads a JSON dataset with `name` and `samples`, resolves relative paths against the current
directory, and prints a summary.

> **Note:** This command is a stub — it validates and counts samples but does not execute
> scorers. See [Evals](../guides/evals.md).

## `machine studio`

```bash
machine studio [--port/-p <port>] [--host <host>]
```

| Option | Default | Meaning |
|--------|---------|---------|
| `--port/-p` | `3177` | Port to bind. |
| `--host` | `127.0.0.1` | Host to bind. |

Requires `studio_support`. Finds the project root, syncs manifests, writes a temporary
`_machine_studio_server.py`, and runs it with `MACHINE_STUDIO_ENABLED=1`,
`MACHINE_CORE_ENTRY`, `MACHINE_CORE_ROOT`, and a `PYTHONPATH` that includes the project and
its parent. If there is no `.venv`, it warns and uses the CLI interpreter.

URL: `http://<host>:<port>/_studio/`.

## `machine plugin`

```bash
machine plugin list
machine plugin install <name> [-f/--force]
machine plugin install --all-framework [-f/--force]
machine plugin remove <name>
machine plugin search <query>
```

| Subcommand | Behavior |
|------------|----------|
| `list` | List locally installed plugins (canonicalized to `_`). |
| `install <name>` | Install one plugin from the registry into `~/.config/machine-core/plugins/`. |
| `install --all-framework` | Install every plugin with `tier = "framework"`. |
| `remove <name>` | Remove an installed plugin (and its `-`/`_` alias). |
| `search <query>` | Search the registry by name/description. |

These require `machine-core` to be importable in the CLI environment (they use
`PluginInstaller` and `RegistryClient`).

See [Registry](registry.md) for the registry format and how install works.

## Exit codes

Commands that fail (no project, unknown target, missing file, deploy failure) call
`typer.Exit(code=1)`. Scripts can rely on a non-zero exit for failure.

## Environment variables the CLI sets

| Variable | Set by | Value |
|----------|--------|-------|
| `MACHINE_CORE_ENTRY` | `dev`, `studio` | The configured `entry`. |
| `MACHINE_CORE_ROOT` | `dev`, `studio` | The project root. |
| `MACHINE_STUDIO_ENABLED` | `studio` | `1`. |
| `PYTHONPATH` | `studio` | Project root, its parent, and any existing value. |

---

**Read next:** [Registry](registry.md) · [Studio guide](../guides/studio.md)

**Source:** `framework/cli_support/cli_support/main.py` and `.../commands/`.
