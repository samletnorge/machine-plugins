# Troubleshooting

Common problems and how to diagnose them. Most issues come down to one of three things:
a plugin was not listed, a manifest was not synced, or a required config value is missing.

## Diagnostic checklist

```bash
# 1. Is there a project root?
grep -A5 '\[tool.machine-core\]' pyproject.toml

# 2. Did manifests sync?
ls ~/.config/machine-core/plugins/

# 3. What loaded?
curl -s http://127.0.0.1:8008/health

# 4. What does the server think?
#    Open http://127.0.0.1:8008/docs or /openapi.json
```

---

## Installation and CLI

### `machine: command not found`

`~/.local/bin` is not on `PATH`.

```bash
export PATH="$HOME/.local/bin:$PATH"
# persist it in your shell profile
```

### `uv: command not found`

Re-run the installer (it installs `uv`), or install `uv` from
<https://docs.astral.sh/uv/>.

### Install fails at a git step

The CLI and plugins are fetched over SSH from the private `samletnorge` repos. Confirm access:

```bash
ssh -T git@github.com
```

Set up an SSH key if needed. Without repository access, the git-based install cannot succeed.

### `machine dev` says "No .venv found"

Run `uv sync` in the project root first.

### `machine init` refuses to run

The target directory already exists and is not empty. Choose a new path or empty it.

### `machine studio` says studio_support is not installed

Add `studio_support` to the project and `uv sync`:

```toml
[tool.machine-core]
plugins = [..., "studio_support"]
```

---

## Plugin loading

### Warning: `Plugin 'X' not found. Run 'machine plugin install X'.`

The plugin is listed in `[tool.machine-core].plugins` but no manifest was found in
`~/.config/machine-core/plugins/`.

1. Is it installed? `machine plugin list` / `machine plugin install X`.
2. Is it synced? Run `machine dev` or `machine studio` (they sync manifests).
3. Check the name spelling (`-` and `_` are equivalent).

### Warning: `required config key 'api_key' has no value`

The key is `required` and nothing resolved. Add the value at one of these levels:

1. `[tool.machine-core.plugin_configs.<plugin>]`,
2. `~/.config/machine-core/plugins/<plugin>.json`,
3. the env var named in the schema (e.g. `DEEPSEEK_API_KEY`),
4. a manifest default.

See [Config schema](reference/config-schema.md).

### `CapabilityDenied: Plugin 'X' lacks capability '...'`

The plugin called a gated `PluginContext` method without declaring the capability in its
manifest. Add it:

```json
"capabilities": ["categories:define", "tool:register"]
```

### `CategoryNotFound: Category 'X' not registered`

You registered an item before its category existed. Register project items inside
`@machine.when_ready`, and ensure a category-defining plugin is in `plugins`:

```python
@machine.when_ready
async def _register():
    machine.register("tool", "my_tool", td)
```

### `CategoryExists: Category 'X' already owned by 'Y'`

Two different owners tried to define the same category. Only one plugin may own a category.
Rename your category or remove the conflicting plugin. Re-registering from the **same** owner
is a no-op.

### A plugin loads but its category is empty

Load order within a tier is not guaranteed. If your plugin depends on another registration,
resolve it **lazily** on first use (as `rag_support` and `tool_filter_rag` do) instead of in
`setup()`.

### Plugin loads twice / stale code

`uv sync`, then restart. Manifest sync is based on file content, but the Python code comes
from the venv; reinstall with `uv sync --reinstall-package <name>` if needed.

---

## Runtime and HTTP

### `/health` shows an expected category missing

The plugin did not load. Re-check the warning logs from `machine dev`. Common causes: not
listed in `plugins`, missing dependency (`ImportError` is logged at debug), or a manifest not
synced.

### `POST /api/agent/{name}/run` does not behave as expected

The operation route passes the body as keyword args and falls back to a single positional
argument. A method `run(self, input, context=None)` receives the whole body as `input`. Send a
JSON string for a plain string, or a JSON object for a Pydantic-annotated first parameter.
See [HTTP API](guides/http-api.md#how-an-operation-is-invoked).

### `POST /api/tool/{name}/execute` returns 404

A bare `ToolDefinition` has no `execute` method. Use Studio's tool tester
(`/_studio/tools/{name}`), an agent runtime, or wrap the tool in an object with an `execute`
method. See [Tools](guides/tools.md).

### Gateway returns `503 No model provider available`

No `model_provider` is registered, or the selected provider lacks `generate`.

1. Add a provider plugin (`provider_ollama`, `provider_deepseek`, ...).
2. Confirm with `curl -s http://127.0.0.1:8008/api/model_provider`.
3. Use a valid `provider/model` string.

### Gateway returns `429 Rate limit exceeded`

The default cap is 60 requests/minute per client. Customize the router:

```python
from server_support.gateway import GatewayConfig, create_gateway_router
app.include_router(create_gateway_router(GatewayConfig(rate_limit_rpm=600), machine=machine))
```

### Gateway returns `401 Invalid API key`

`api_keys` is configured. Send `Authorization: Bearer <key>`.

### SSE stream is buffered behind a proxy

SSE needs unbuffered responses. `server_support` sets
`X-Accel-Buffering: no`; if a proxy still buffers, disable buffering there.

### Sensitive values appear as `"***"`

This is intentional. The serializer redacts keys matching `api_key`, `secret`, `password`,
`access_token`, `authorization`, `credential`, and similar markers.

---

## Studio

### `/_studio/` is blank or 404

Studio sub-apps mount under `/_studio`. Confirm you are using the host app
(`create_studio_host_app`) and the port from the command output (`3177` by default).

### Chat lists no agents

Studio prefers agents whose `run` has at most one required parameter, and it **skips** agent
runtimes (owners starting with `agent_runtime_`). Register a thin wrapper agent (like the
scaffold's `ExampleAgent`) with `async def run(self, input, context=None)`.

### A tool does not execute in Studio

The tester tries `execute()`, then `handler(**body)`, then `filter(...)`. If none exist, it
returns 400. Verify the tool object exposes one of those.

---

## Secrets

### Infisical warnings in the logs

The integration is soft. Typical messages:

- `Infisical Machine Identity not configured; using the plain environment` — expected when
  `INFISICAL_CLIENT_ID`/`INFISICAL_CLIENT_SECRET` are unset.
- `Infisical bootstrap timed out after 10s; continuing with the plain environment` — network
  or auth issue; the plain environment is used.
- `Infisical returned N masked secret(s); skipped (no read-value permission): ...` — the
  Machine Identity lacks read-value permission; grant it or set the values locally.

Secret **values** are never logged.

### `.env` values are ignored

Existing environment variables always win over `.env`. Unset the variable, or set the value
in the environment. Also confirm `MACHINE_CORE_ROOT` points at the project if you rely on
`$MACHINE_CORE_ROOT/.env`.

---

## Data and state

### Threads disappear after restart

The default memory storage is in-memory. Set a SQLite path:

```toml
[tool.machine-core.plugin_configs.memory_support]
sqlite_path = "./data/memory.db"
```

### Where is my data?

- `~/.config/machine-core/plugins/` — synced manifests and user config,
- `~/.config/machine-core/plugin-data/` — plugin runtime state,
- `~/.machine/cache/registry.json` — registry cache.

Override the base with `MachineConfig(data_dir=...)` (useful in containers and tests).

---

## Still stuck?

- Re-read the [Architecture](concepts/architecture.md) and
  [Plugin lifecycle](concepts/plugins.md) pages.
- Check the kernel source: `src/machine_core/`.
- Reproduce with a minimal machine:

```python
import asyncio
from machine_core import Machine, MachineConfig

async def main():
    machine = Machine(config=MachineConfig(plugins=["tool_support"]))
    await machine.start()
    print(machine.list_categories())

asyncio.run(main())
```
