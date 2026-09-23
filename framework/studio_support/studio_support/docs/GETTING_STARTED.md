# Getting Started with machine-core

This guide walks through the real, current flow: install the `machine` CLI, scaffold a
project, declare plugins, run the dev server or Studio, and understand the auto-generated
HTTP API and secret loading.

`machine-core` is a small, language-agnostic plugin kernel. It starts **empty**: a project's
behavior comes entirely from the plugins it declares and the items its own entry point
registers after those plugins load.

See also:

- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — registry, plugin lifecycle, capabilities, transports
- [`../README.md`](../README.md) — kernel overview

## 1. Requirements

- Python `>= 3.12`
- [`uv`](https://docs.astral.sh/uv/)
- Git SSH access to the private `samletnorge` GitHub repositories (plugins are installed
  from git `subdirectory` sources)

## 2. Install the `machine` CLI

The CLI lives in the `cli_support` framework plugin and is installed as an isolated tool:

```bash
curl -fsSL https://gist.githubusercontent.com/valiantlynx/c3eaf552adf9aecff7c0366a25ff1e99/raw/install.sh | bash
```

The installer (`scripts/install.sh`):

1. ensures `uv` is available (installing it via `astral.sh` if needed),
2. warns if GitHub SSH access is not confirmed,
3. runs `uv tool install` against `machine-plugins#subdirectory=framework/cli_support`
   (falling back to a dedicated venv at `$MACHINE_HOME`/`~/.machine` with a shim if that fails),
4. makes sure `~/.local/bin` is on `PATH`.

After it finishes, `machine --help` should work. The installer prints the quick start:

```bash
machine init my-project
cd my-project
uv sync
machine dev
```

## 3. Scaffold a project

```bash
machine init my-project
cd my-project
```

`machine init <dir>` refuses to write into a non-empty directory and scaffolds:

```
my-project/
├── pyproject.toml          # [tool.machine-core] + [tool.uv.sources]
├── .gitignore
└── src/
    ├── __init__.py
    ├── main.py             # entry point: src.main:machine
    └── agents/
        ├── __init__.py
        └── example.py
```

Then resolve dependencies:

```bash
uv sync
```

`uv sync` reads the generated `pyproject.toml`, which lists the framework and community
plugin packages and pins each one to a git **subdirectory** source. `uv` resolves the
transitive bare dependencies each plugin declares.

## 4. Declaring plugins

Plugin selection is explicit. `MachineConfig.from_pyproject()` reads the
`[tool.machine-core]` section of `pyproject.toml`:

```toml
[tool.machine-core]
entry = "src.main:machine"
plugins = [
    "tool_support",
    "model_provider_support",
    "agent_support",
    "prompt_support",
    "structured_output",
    "embeddings",
    "memory_support",
    "vectorstore_support",
    "server_support",
    "provider_ollama",
    "provider_deepseek",
    "embeddings_ollama",
    "embeddings_sentence_transformers",
    "vectorstore_lancedb",
    "eval_support",
    "tool_openapi",
    "tool_filter_rag",
    "rag_support",
    "agent_runtime_basic",
    "agent_runtime_pydantic",
]
```

Recognized `[tool.machine-core]` keys (see `MachineConfig` in `src/machine_core/machine.py`):

| Key | Meaning |
|-----|---------|
| `entry` | Entry point the CLI imports, as `module:attribute` (default `src.main:machine`). |
| `plugins` | Explicit list of plugins to load. **If set, only these load.** If omitted/empty, the machine starts with no plugins. |
| `disabled_plugins` | Plugin names to skip (aliases with `-`/`_` are normalized). |
| `plugin_configs` | Per-plugin config overrides, highest priority in config resolution. |
| `registry_url` | Registry URL used when installing missing plugins. |
| `offline` | If `true`, never fetch from a remote registry. |

`uv` sources must live at the project root. The generated `[tool.uv.sources]` maps every
plugin name to a git subdirectory, for example:

```toml
[tool.uv.sources]
machine-core = { git = "git+ssh://git@github.com/samletnorge/machine-core.git" }
tool_support = { git = "git+ssh://git@github.com/samletnorge/machine-plugins.git", subdirectory = "framework/tool_support" }
provider_ollama = { git = "git+ssh://git@github.com/samletnorge/machine-plugins.git", subdirectory = "community/provider_ollama" }
vectorstore_lancedb = { git = "git+ssh://git@github.com/samletnorge/machine-plugin-vectorstore-lancedb.git" }
eval_support = { git = "git+ssh://git@github.com/samletnorge/machine-plugin-eval-support.git" }
```

## 5. The project entry point

The scaffold's `src/main.py` shows the canonical pattern:

```python
"""Main entry point for my-project."""
from machine_core import Machine, MachineConfig, bootstrap_secrets

# Attach local .env and Infisical secrets to the environment before config loads.
bootstrap_secrets()

config = MachineConfig.from_pyproject()
machine = Machine(config=config)


@machine.when_ready
async def _register_project_items() -> None:
    """Register this project's own tools, agents, and memory once plugins load."""
    from memory_support.in_memory_storage import InMemoryStorage
    from memory_support.manager import MemoryManager

    from .agents.example import WORD_COUNT_TOOL, ExampleAgent

    machine.register("tool", WORD_COUNT_TOOL.name, WORD_COUNT_TOOL)
    machine.register("agent", "assistant", ExampleAgent(machine))
    machine.register("memory", "default", MemoryManager(storage=InMemoryStorage()))
```

Key points:

- `bootstrap_secrets()` runs **first**, before any component resolves config.
- `Machine(config=...)` starts empty; plugins load during `machine.start()`.
- `@machine.when_ready` registers a sync-or-async callback that runs **after** declared
  plugins load, so the categories (`tool`, `agent`, `memory`, …) already exist.

## 6. Run the dev server

```bash
machine dev                 # http://127.0.0.1:8008
machine dev --port 9000 --host 0.0.0.0
```

`machine dev`:

1. walks up from the current directory to find the project (`pyproject.toml` with `[tool.machine-core]`),
2. reads the `entry` point,
3. **syncs plugin manifests** from the project's `site-packages` into
   `~/.config/machine-core/plugins/<name>/manifest.json` (this is what the kernel reads),
4. ensures `server_support`, `agent_support`, and `tool_support` are importable, installing
   them from git subdirectories if missing,
5. writes a temporary `_machine_dev_server.py` that imports the entry machine, calls
   `server_support.app.create_app(machine)`, and runs `uvicorn --reload` against the
   project's `.venv` Python.

> `uv sync` must have been run first — `machine dev` requires the project's `.venv`.

## 7. Run Studio

```bash
machine studio              # http://127.0.0.1:3177/_studio/
machine studio --port 4000
```

`machine studio` requires the `studio_support` plugin, finds the project root, syncs
manifests, and launches a host app via `studio_support.app.create_studio_host_app(machine)`
with `MACHINE_STUDIO_ENABLED=1`.

Running `machine` with no subcommand launches the interactive TUI and auto-starts the dev
server in the background on port `8008` if it is not already running.

## 8. The auto-generated HTTP API

`server_support` builds a FastAPI app from a live `Machine` instance and mounts a router at
`/api`. Routes are derived from the registry at app startup (and re-generated after
`machine.start()` loads plugins):

| Method | Path | Source | Description |
|--------|------|--------|-------------|
| `GET` | `/api/{category}` | every category | List items: `[{ "name", "owner", ...serialized }]` |
| `GET` | `/api/{category}/{name}` | every item | Fetch one item by name (404 if absent) |
| `{op.method}` | `/api/{category}/{name}/{op.path}` | category `operations` | Invoke a method on the resolved item |
| `GET` | `/health` | built-in | `{ "status": "healthy", "categories": { ...: count } }` |

Category operations are declared when a plugin defines its category. For example,
`tool_support` registers:

```python
ctx.register_category("tool", operations={"execute": {"method": "POST", "on": "item"}})
```

which yields `POST /api/tool/{name}/execute`. Operation routes resolve the item, call the
named method (async or sync), coerce JSON bodies into annotated Pydantic types, and
JSON-serialize the result with sensitive keys (`api_key`, `secret`, `password`, …)
redacted. Operations whose name contains `stream` are served as Server-Sent Events (SSE).

FastAPI's standard OpenAPI/Swagger endpoints remain available alongside these routes.

## 9. Secrets

`machine_core.bootstrap_secrets()` is the only module that mutates the process environment.
Call it once at startup, before any component resolves configuration.

Two sources, in order:

1. **Local `.env`** — read from `$MACHINE_CORE_ROOT/.env` (if `MACHINE_CORE_ROOT` is set),
   falling back to `./.env`. Existing environment variables **always win**; the parser never
   overrides them.
2. **Infisical** — enabled when `INFISICAL_CLIENT_ID` and `INFISICAL_CLIENT_SECRET` are set.
   Secrets fetched from Infisical **overwrite** the same keys, so production values win over
   the local fallback.

| Env var | Default | Purpose |
|---------|---------|---------|
| `INFISICAL_CLIENT_ID` | — | Machine Identity client ID (enables Infisical). |
| `INFISICAL_CLIENT_SECRET` | — | Machine Identity client secret. |
| `INFISICAL_HOST` | `https://infisical.valiantlynx.com` | Infisical host. |
| `INFISICAL_PROJECT_ID` | `""` | Project to read secrets from. |
| `INFISICAL_ENVIRONMENT` | `dev` | Environment slug. |
| `INFISICAL_TIMEOUT_SECONDS` | `10` | Bootstrap timeout. |

The integration is **soft**: a missing Machine Identity, an unreachable Infisical, or an
unimportable SDK logs a warning and leaves the plain environment intact. It never raises.
Secret values are never logged — only counts and names. Install the optional SDK with
`machine-core[secrets]` (the scaffold already does this).

## 10. Tests

- `machine-core` kernel tests: 124
- `machine-plugins` ecosystem tests: 1029

See each repository for how to run them.
