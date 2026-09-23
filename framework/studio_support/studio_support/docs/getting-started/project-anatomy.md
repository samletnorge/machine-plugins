# Project anatomy

A machine-core project is intentionally thin. This page walks through every file
`machine init` generates and explains what the kernel does with each one.

## Layout

```
my-project/
├── pyproject.toml          # dependencies, [tool.uv.sources], [tool.machine-core]
├── .gitignore
├── .env                    # (you create this) secrets for bootstrap_secrets()
└── src/
    ├── __init__.py
    ├── main.py             # entry point: src.main:machine
    ├── agents/
    │   ├── __init__.py
    │   └── example.py      # a @tool and an agent definition
    └── tools/              # (you create this) your own tools
```

`machine dev` also writes and removes `_machine_dev_server.py` in the project root; it is
listed in `.gitignore` and should never be committed.

## `pyproject.toml`

The generated `pyproject.toml` has four important parts.

### 1. Dependencies

```toml
[project]
name = "my-project"
requires-python = ">=3.12"
dependencies = [
    "machine-core[secrets]",
    "server_support",
    "tool_support",
    # ... the rest of the plugin list
]
```

`machine-core[secrets]` installs the optional Infisical SDK. Everything else is a plugin.

### 2. `[tool.uv.sources]`

Every plugin name is mapped to the git source it should resolve from. This must live at the
project root; `uv` only honours sources there.

```toml
[tool.uv.sources]
machine-core = { git = "git+ssh://git@github.com/samletnorge/machine-core.git" }
tool_support = { git = "git+ssh://git@github.com/samletnorge/machine-plugins.git", subdirectory = "framework/tool_support" }
provider_ollama = { git = "git+ssh://git@github.com/samletnorge/machine-plugins.git", subdirectory = "community/provider_ollama" }
```

See [Registry](../reference/registry.md) for the full catalog.

### 3. `[tool.machine-core]`

This is the section the kernel and CLI read. `MachineConfig.from_pyproject()` parses it.

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

| Key | Meaning |
|-----|---------|
| `entry` | Entry point the CLI imports, as `module:attribute` (default `src.main:machine`). |
| `plugins` | Explicit list of plugins to load. **If set, only these load.** If omitted/empty, the machine starts empty. |
| `disabled_plugins` | Plugin names to skip (`-`/`_` aliases are normalized). |
| `plugin_configs` | Per-plugin config overrides, highest priority in config resolution. |
| `registry_url` | Registry URL used when installing missing plugins. |
| `offline` | If `true`, never fetch from a remote registry. |

See [Configuration](../concepts/configuration.md) and
[Config schema](../reference/config-schema.md).

### 4. `[tool.machine-core.studio]`

Studio reads tenants, projects, and environments from here. The scaffold generates one of
each:

```toml
[tool.machine-core.studio]
active_tenant = "tenant-default"
active_project = "project-my-project"
active_environment = "env-dev"

[[tool.machine-core.studio.tenants]]
id = "tenant-default"
slug = "default"
name = "Default"

[[tool.machine-core.studio.projects]]
id = "project-my-project"
tenant_id = "tenant-default"
slug = "my-project"
name = "my-project"
entry = "src.main:machine"

[[tool.machine-core.studio.environments]]
id = "env-dev"
project_id = "project-my-project"
name = "dev"
connection_kind = "local"
connection_ref = "src.main:machine"
status = "healthy"
```

See [Studio](../guides/studio.md#context-tenants-projects-environments).

## `src/main.py`

The canonical entry point:

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

Three things matter here:

1. **`bootstrap_secrets()` runs first**, before any component resolves configuration. It is
   the only module that mutates `os.environ`. See [Secrets](../concepts/secrets.md).
2. **`Machine(config=...)` starts empty.** Nothing happens until `machine.start()` is called —
   either by `server_support.create_app()` in its lifespan, or by your own code.
3. **`@machine.when_ready` defers registration.** The callback runs *after* declared plugins
   load, so the `tool`, `agent`, and `memory` categories already exist.

## Why `when_ready`?

Categories are defined by plugins. If your project tried to `machine.register("tool", ...)`
at import time, the category might not exist yet and you would get a `CategoryNotFound`
error. `when_ready` guarantees ordering:

```
machine.start()
  ├─ discover manifests
  ├─ load category-defining plugins (categories:define)
  ├─ load implementing plugins
  └─ run when_ready callbacks   ← your registrations happen here
```

The callback may be sync or async; the kernel awaits it if needed.

```python
@machine.when_ready
def _sync_register():        # also fine
    machine.register("tool", "ping", object())
```

## The registration pattern

```python
machine.register(category, name, implementation)
```

- `category` must already exist, or you get `CategoryNotFound`.
- The kernel may run a category validator; failing it raises `ValidationError`.
- The owner defaults to `"core"`; plugins register with their own name via `PluginContext`.

Read items back with:

```python
machine.resolve("agent", "assistant")      # the instance, or None
machine.list_category("tool")              # {name: impl}
machine.list_categories()                  # ["tool", "agent", "memory", ...]
machine.get_owner("tool", "word_count")    # "core" for project registrations
```

## `_machine_dev_server.py` (generated)

During `machine dev`, the CLI writes a temporary file that looks like:

```python
"""Auto-generated dev server for machine dev. Do not edit."""
import os, sys
sys.path.insert(0, os.environ.get("MACHINE_CORE_ROOT", "."))
import importlib
module = importlib.import_module("src.main")
machine = getattr(module, "machine")
from server_support.app import create_app
app = create_app(machine)
```

It is removed when the dev server stops. Do not edit or commit it.

## Adding files

The CLI has scaffolds for common additions:

```bash
machine agent add researcher    # src/agents/researcher.py
machine tool add search         # src/tools/search.py
```

> **Note:** In the current `cli_support`, these scaffolds write a TODO stub, not a
> ready-to-run `@tool`/agent. Treat them as a starting placeholder and fill in the body. See
> [`machine agent add`](../reference/cli.md#machine-agent-add) in the CLI reference.

---

**Read next:** [Architecture](../concepts/architecture.md) · [Plugins](../concepts/plugins.md)

**Source:** `framework/cli_support/cli_support/scaffolds/project/`,
`framework/cli_support/cli_support/commands/dev_cmd.py`,
`src/machine_core/machine.py`.
