# Configuration

machine-core configuration lives in `[tool.machine-core]` in your project's `pyproject.toml`
and in per-plugin config. The kernel resolves plugin config through a deterministic
five-step chain, so the same plugin can be configured in development with a `.env` and in
production with an override — without changing the plugin.

## Project config

`MachineConfig.from_pyproject()` reads `[tool.machine-core]`:

```toml
[tool.machine-core]
entry = "src.main:machine"
plugins = [
    "tool_support",
    "model_provider_support",
    "agent_support",
    "server_support",
    "provider_ollama",
    "agent_runtime_basic",
]
disabled_plugins = []
offline = false

[tool.machine-core.plugin_configs.provider_ollama]
base_url = "http://localhost:11434"
model = "llama3.2"
```

`MachineConfig` fields:

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `plugins` | `list[str] \| None` | `None` | Plugins to load. If set, **only** these load. |
| `disabled_plugins` | `list[str]` | `[]` | Names to skip while loading `plugins`. |
| `plugin_configs` | `dict[str, dict]` | `{}` | Per-plugin overrides (highest priority). |
| `data_dir` | `Path` | `~/.config/machine-core` | Plugin state and synced manifests. |
| `registry_url` | `str \| None` | `None` | Registry for installing missing plugins. |
| `offline` | `bool` | `False` | Never fetch from a remote registry. |

> **Tip:** `-` and `_` are treated as the same in `plugin_configs` and `disabled_plugins`.
> `provider-ollama`, `provider_ollama`, and `provider-ollama` all resolve to the same key.

### `entry`

The `machine` CLI uses `entry = "module:attribute"` to import the `Machine` instance for
`dev`, `studio`, `build`, and `deploy`. The default is `src.main:machine`.

### `plugins` and `disabled_plugins`

Only listed plugins load. This keeps runtimes explicit and reproducible — see
[Architecture](architecture.md#starting-a-machine).

```toml
plugins = ["tool_support", "agent_support", "provider_ollama", "server_support"]
disabled_plugins = ["provider_ollama"]   # skip it even though it is listed
```

## The five-step config chain

Plugin config is resolved by `PluginManager._resolve_plugin_config()`. For each key in the
plugin's `config_schema`, **the first non-`None` value wins**:

1. **Explicit override** — `MachineConfig.plugin_configs` or the `config=` passed to
   `load()`.
2. **User config file** — `<data_dir>/plugins/<name>.json`.
3. **Plugin persisted state** — from `load_plugin_data()` (self-acquired credentials such as
   OAuth tokens).
4. **Environment variable** — the key's `config_schema.env`, coerced to the declared type.
5. **Manifest default** — the key's `default`.

If nothing resolves and the key is `required`, the kernel logs a warning. The plugin never
loads its own config; machine-core assembles and pushes the dict to `initialize(config=...)`.

```
overrides ─┐
user file ─┤
persisted ─┼─▶ first non-None per key ─▶ initialize(config=...)
env var   ─┤
default   ─┘
```

### Example

Given this schema:

```json
"config_schema": {
  "base_url": { "type": "string", "default": "http://localhost:11434", "env": "OLLAMA_HOST" },
  "model":    { "type": "string", "default": "llama3.2", "env": "OLLAMA_MODEL" }
}
```

- In production you set `OLLAMA_HOST` in the environment → step 4 wins.
- Locally, with no env var, the manifest default applies → `http://localhost:11434`.
- To override for one project, add:

```toml
[tool.machine-core.plugin_configs.provider_ollama]
base_url = "http://gpu-box:11434"
```

→ step 1 wins.

### User config file

You can also drop a file at `<data_dir>/plugins/<name>.json`, where `<data_dir>` defaults to
`~/.config/machine-core`:

```json
{
  "base_url": "http://gpu-box:11434",
  "model": "qwen2.5:14b"
}
```

This is convenient for machine-local settings you do not want in the repository.

> **Note:** The user config file is `<data_dir>/plugins/<name>.json` (a file), while synced
> manifests are `<data_dir>/plugins/<name>/manifest.json` (a directory). They share the
> `plugins/` folder but never collide.

### Persisted state vs. config

`data:own` / `plugin-data/<name>.json` is for **runtime state** — tokens, cursors, counters.
It is step 3 of the chain, above env vars, because a plugin that has acquired its own
credentials (for example via a device flow) should prefer them. Do not use it for normal
configuration.

## Environment-variable coercion

Step 4 coerces the string value using the schema `type`:

| `type` | Coercion |
|--------|----------|
| `number` | `int` if no `.`, else `float`; falls back to the raw string on failure. |
| `boolean` | `value.lower() in ("true", "1", "yes")`. |
| anything else | kept as a string. |

> **Inconsistency to know about:** `ConfigSchemaEntry` documents `type` as
> `"string"`/`"number"`/`"boolean"`, but several shipped manifests use `"integer"` and
> `"json"` (for example `agent_brreg_expert` and `rag_support`). Those types are passed
> through as strings by the coercion logic, so a `"json"` value from an env var is **not**
> parsed automatically — plugins that need structured config handle it themselves (as
> `mcp_support` does).

## Secrets in config

Mark a key `"secret": true` to keep it out of logs. Resolved secret names are logged, never
values:

```json
"api_key": { "type": "string", "env": "DEEPSEEK_API_KEY", "secret": true }
```

Secrets usually arrive through the environment, via `bootstrap_secrets()`. See
[Secrets](secrets.md).

## Studio context config

Studio adds a `[tool.machine-core.studio]` section describing tenants, projects, and
environments, plus the active context. It is read by `load_context_catalog()`. See
[Studio](../guides/studio.md#context-tenants-projects-environments).

## Inspecting resolved config

Start the machine and look at the registry to confirm what loaded. From a Python shell:

```python
import asyncio
from src.main import machine

asyncio.run(machine.start())
print(machine.list_categories())
print(machine.list_category("model_provider").keys())
```

Or hit `/health` on a running dev server — it reports a count per category.

---

**Read next:** [Secrets](secrets.md) · [Config schema](../reference/config-schema.md)

**Source:** `src/machine_core/machine.py` (`MachineConfig`, `from_pyproject`),
`src/machine_core/plugin/manager.py` (`_resolve_plugin_config`, `_coerce_env_value`).
