# machine-core Architecture

`machine-core` is a language-agnostic plugin kernel. It owns a generic registry, a plugin
lifecycle, hooks, events, config resolution, and plugin transports. It deliberately does
**not** implement agents, tools, model providers, workflows, RAG, HTTP APIs, or Studio —
those are plugins.

See also:

- [`GETTING_STARTED.md`](./GETTING_STARTED.md) — install, scaffold, run, HTTP API, secrets
- [`../README.md`](../README.md) — kernel overview

## 1. Kernel vs. plugins

| Concern | Lives in | Notes |
|---------|----------|-------|
| Registry, lifecycle, hooks, events, config, transports, secrets | `machine-core` (`src/machine_core/`) | Generic; domain-free. |
| Categories, contracts, hook specs, shared support | `machine-plugins` → `framework/` | Define vocabulary. |
| Concrete providers, runtimes, integrations, domain behavior | `machine-plugins` → `community/` | Implement the vocabulary. |
| Out-of-tree plugins | satellite repos | Referenced by git URL and listed in `registry.json`. |

The kernel is intentionally small:

```
src/machine_core/
├── machine.py                    # Machine registry + MachineConfig
├── secrets.py                    # bootstrap_secrets() / .env / Infisical
├── stream.py, dynamic.py, types.py
└── plugin/
    ├── manager.py                # PluginManager: discovery, lifecycle, config, transports
    ├── context.py                # PluginContext: capability-gated plugin API
    ├── manifest.py               # PluginManifest, ConfigSchemaEntry, TransportConfig
    ├── host.py                   # PluginHost: manifest + transport + context
    ├── hooks.py                  # HookSystem: hookspecs, prioritized subscribers
    ├── events.py                 # DataBus + Event classes
    ├── transport.py              # PluginTransport + InProcessTransport
    ├── jsonrpc_transport.py      # JsonRpcTransport (line-delimited JSON-RPC 2.0)
    ├── installer.py / registry.py# optional registry-backed plugin install
    └── errors.py
```

## 2. The generic registry (`Machine`)

`Machine` stores implementations by `category -> name -> implementation` and tracks the
owner of each category and item.

### Registry API

| Method | Behavior |
|--------|----------|
| `register_category(category, validator=None, defined_by="core", *, operations=None)` | Create a category. Re-registering from the **same** owner is idempotent; a different owner raises `CategoryExists`. `validator` gates `register`; `operations` describe HTTP-callable category operations. Emits `CategoryRegistered`. |
| `register(category, name, impl, owner="core")` | Add an implementation. Unknown category raises `CategoryNotFound`; a failing validator raises `ValidationError`. Emits `ItemRegistered`. |
| `resolve(category, name)` | Return an implementation (or `None`). |
| `list_category(category)` | Return a copy of a category's `name -> impl` mapping. |
| `list_categories()` | Return all category names. |
| `get_owner(category, name)` | Return the owning plugin for an item. |
| `get_operations(category)` | Return the category's declared operations. |
| `unregister(category, name)` | Remove an item. Emits `ItemUnregistered`. |

`Machine` also owns `machine.hooks` (`HookSystem`), `machine.bus` (`DataBus`),
`machine.plugins` (`PluginManager`), and plugin data persistence
(`load_plugin_data` / `save_plugin_data`, stored under `<data_dir>/plugin-data/`).

### Starting and readiness

```python
machine = Machine(config=MachineConfig.from_pyproject())
await machine.start()
```

- `Machine` starts **empty**.
- `start()` discovers manifests and, if `config.plugins` is set, loads **only** those
  declared plugins. If `plugins` is empty, nothing is loaded.
- Category-defining plugins (those with the `categories:define` capability) are sorted
  first so later plugins can register into categories that already exist.
- After plugins load, callbacks registered with `when_ready` run (sync or async). Use them
  to register the application's own items once categories exist:

  ```python
  @machine.when_ready
  async def _register():
      machine.register("tool", "word_count", WORD_COUNT_TOOL)
  ```

- `shutdown()` unloads every loaded plugin.

### Configuration (`MachineConfig`)

```python
@dataclass
class MachineConfig:
    plugins: list[str] | None = None
    disabled_plugins: list[str] = []
    plugin_configs: dict[str, dict[str, Any]] = {}
    data_dir: Path = ~/.config/machine-core
    registry_url: str | None = None
    offline: bool = False
```

`MachineConfig.from_pyproject(path=None)` reads `[tool.machine-core]` from
`pyproject.toml` and normalizes `-`/`_` aliases for `plugin_configs` and
`disabled_plugins`. `data_dir` defaults to `~/.config/machine-core/` and contains
`plugins/` (synced manifests) and `plugin-data/` (persisted runtime state).

## 3. Plugin lifecycle

Plugins are described by a `manifest.json` and driven by `PluginManager`. The load sequence
in `PluginManager.load()`:

1. **Manifest** — looked up among discovered manifests.
2. **Transport** — created from `manifest.transport` (`in-process` or `json-rpc`).
3. **Config** — resolved through the 5-step chain (below), with explicit overrides on top.
4. **`initialize(config=...)`** — called on the plugin via the transport.
5. **`PluginContext`** — constructed with the plugin's declared capabilities.
6. **`setup(ctx=...)`** — called so the plugin can define categories, register
   implementations, and subscribe to hooks/events. (`InProcessTransport` returns `None`
   for missing methods, so `setup` is optional.)
7. **Auto-wire** — every `hooks_subscribed` entry becomes a proxy subscriber; every
   `events_subscribed` entry becomes a proxy event handler. Both are recorded for cleanup.
8. **Emit `PluginEnabled`.**

Unload reverses this: `context.cleanup()` removes everything registered through the
context, then `shutdown({})` is called, then the transport is closed, then `PluginDisabled`
is emitted.

A minimal in-process plugin (from `tool_support`):

```python
class ToolSupportPlugin:
    async def initialize(self, **kwargs):
        pass

    async def setup(self, ctx):
        ctx.register_category("tool", operations={"execute": {"method": "POST", "on": "item"}})
        for hook_name, opts in HOOKSPECS.items():
            ctx.register_hookspec(hook_name, **opts)

    async def shutdown(self, **kwargs):
        pass
```

## 4. Plugin manifest (`PluginManifest`)

| Field | Type | Notes |
|-------|------|-------|
| `schema_version` | `str` | Default `"1.0.0"`. |
| `name` | `str` | Plugin name. |
| `version` | `str` | Plugin version. |
| `description` | `str?` | Human-readable. |
| `language` | `str` | Default `"python"`; informs the language-agnostic boundary. |
| `author` | `str?` | — |
| `capabilities` | `list[str]` | Capability declarations enforced by `PluginContext`. |
| `dependencies` | `list[str]` | **PyPI package names**, not plugin names. |
| `config_schema` | `dict[str, ConfigSchemaEntry]` | Declares config keys. |
| `hooks_subscribed` | `dict[str, dict]` | Hook name → options (`priority`). |
| `events_subscribed` | `list[str]` | Event class names. |
| `transport` | `TransportConfig` | How the kernel talks to the plugin. |

**`ConfigSchemaEntry`**: `type` (`"string"`/`"number"`/`"boolean"`), `default`, `env`
(ecosystem env var), `secret` (never logged), `required`, `description`.

**`TransportConfig`**: `type`, `entry_point`, `mode`, `binary`, `args`, `address`.

Every plugin ships a `manifest.json` at its plugin root; the build force-includes it inside
the installed Python package (e.g. `site-packages/tool_support/manifest.json`). The CLI
syncs these into `~/.config/machine-core/plugins/<name>/manifest.json`, which is where the
kernel reads declared plugins from.

## 5. Capabilities

`PluginContext` is capability-gated. The manifest is the contract; calling a gated method
without the capability raises `CapabilityDenied`.

| `PluginContext` method | Required capability | Behavior |
|------------------------|--------------------|----------|
| `register(category, name, impl)` | `{category}:register` | Registers an item, owner-tracked and auto-removed on cleanup. |
| `register_category(category, validator=None, operations=None)` | `categories:define` | Defines a category owned by the plugin. |
| `register_hookspec(hook_name, **kwargs)` | `hooks:define` | Declares a hook (e.g. `firstresult=True`). |
| `subscribe_hook(hook_name, callback, priority="normal")` | *(not gated)* | Subscribes to a hook; auto-removed on cleanup. |
| `emit(event)` | `events:emit` | Emits a typed event. |
| `on(event_type, callback)` | *(not gated)* | Subscribes to an event type; auto-removed on cleanup. |
| `load_data()` / `save_data(data)` | `data:own` | Plugin-owned runtime state. |

Capability names seen in framework/community manifests include `categories:define`,
`hooks:define`, `events:emit`, and category registration capabilities such as
`tool:register`, `agent:register`, and `model_provider:register`.

`data:own` state is for **runtime state** (tokens, cursors, counters) — never for
configuration; config flows through `initialize(config=...)`.

## 6. Config resolution

`PluginManager._resolve_plugin_config()` fills each `config_schema` key. **First non-`None`
value wins** per key:

1. **Explicit overrides** — `MachineConfig.plugin_configs` or the `config=` passed to `load()`.
2. **User config file** — `<data_dir>/plugins/<name>.json`.
3. **Plugin persisted state** — from `load_plugin_data()` (self-acquired credentials).
4. **Environment variable** — the key's `config_schema.env`, coerced to the declared type.
5. **Manifest default** — the key's `default`.

If nothing resolves and the key is `required`, a warning is logged. The plugin never loads
its own config; machine-core assembles and pushes the dict. Secret keys are logged by name
only.

## 7. Hooks vs. events

Both are extension points, but they serve different purposes.

### Hooks (`HookSystem`) — query/collect

- A hook has a **spec** (`register_spec(name, firstresult=False)`), usually declared by a
  framework plugin via `hooks:define`.
- Subscribers are ordered by `priority`: `"first"` < `"normal"` < `"last"`.
- `await machine.hooks.call(name, **kwargs)` invokes every subscriber in order, collecting
  non-`None` results. With `firstresult=True`, it stops at the first non-`None` result.
- Use hooks when a caller wants answers or wants to allow extension/override.

### Events (`DataBus`) — fire-and-forget

- Events are typed Pydantic models deriving from `Event` (`source`, `timestamp`,
  `event_id`). Built-ins: `PluginEnabled`, `PluginDisabled`, `CategoryRegistered`,
  `ItemRegistered`, `ItemUnregistered`.
- `await machine.bus.emit(event)` dispatches callbacks as tasks; subscriber exceptions are
  logged, never propagated.
- `bus.emit_sync(event)` supports synchronous emitters (used by the registry): it schedules
  tasks if a loop is running, otherwise calls sync subscribers directly.
- Use events for notification without expectation of a return value.

Manifest-declared hook and event subscriptions are also forwarded across the transport to
out-of-process plugins: hook proxies call `transport.call(hook_name, kwargs)` and event
proxies call `transport.notify(event_name, payload)` (see below).

## 8. Transports

The plugin boundary is language-agnostic. `PluginManager._create_transport()` builds one of:

- **`in-process`** — `InProcessTransport` imports the class named by
  `transport.entry_point` (e.g. `tool_support:ToolSupportPlugin`), instantiates it, and
  calls its methods directly (`call`/`notify`/`close`). Methods may be sync or async.
- **`json-rpc` / `spawn`** — launches `transport.binary` (+ `args`) as a subprocess with
  `MACHINE_CORE_PLUGIN=1`, reads a handshake line from stdout (10s timeout), then speaks
  line-delimited JSON-RPC 2.0 over stdin/stdout.
- **`json-rpc` / `connect`** — connects to an already-running process via
  `unix://<path>` or `tcp://<host>:<port>` and speaks the same JSON-RPC 2.0 protocol.

`JsonRpcTransport` tracks request IDs, resolves responses into futures, and fails all
pending requests when the connection drops. For spawned plugins it terminates (then kills)
the subprocess on close. This is what lets non-Python plugins participate.

## 9. Secrets

`machine_core.secrets.bootstrap_secrets()` attaches secrets to the process environment. It
is the only place that mutates `os.environ`, and application entry points call it once at
startup before config resolution. It loads `$MACHINE_CORE_ROOT/.env` (or `./.env`) without
overriding existing variables, then — if `INFISICAL_CLIENT_ID` and
`INFISICAL_CLIENT_SECRET` are set — fetches from Infisical and overwrites matching keys.
The integration is soft: failures log warnings and never raise, and secret values are never
logged. See [`GETTING_STARTED.md`](./GETTING_STARTED.md#9-secrets) for the env var table.

## 10. Topology of the ecosystem

- `machine-core` — this repository; the kernel.
- `machine-plugins` — a root **uv workspace** with:
  - `framework/*` — category-defining and support plugins,
  - `community/*` — concrete implementations and integrations,
  - `registry.json` — catalog of framework, community, and `external` (git) plugins,
  - satellite repos referenced from `registry.json`: `machine-plugin-eval-support` and
    `machine-plugin-vectorstore-lancedb`.
- Consumer projects — a `pyproject.toml` with `[tool.machine-core]`, a plugin list, and a
  small entry point. Plugins are referenced by git `subdirectory` sources.

See the [`machine-plugins` README](https://github.com/samletnorge/machine-plugins) for the
full catalog.
