# Architecture

machine-core is a language-agnostic plugin kernel. It owns a generic registry, a plugin
lifecycle, hooks, events, config resolution, and plugin transports. It deliberately does
**not** implement agents, tools, model providers, workflows, RAG, HTTP APIs, or Studio —
those are plugins.

## Kernel vs. plugins

| Concern | Lives in | Notes |
|---------|----------|-------|
| Registry, lifecycle, hooks, events, config, transports, secrets | `machine-core` (`src/machine_core/`) | Generic; domain-free. |
| Categories, contracts, hook specs, shared support | `machine-plugins` → `framework/` | Define the vocabulary. |
| Concrete providers, runtimes, integrations | `machine-plugins` → `community/` | Implement the vocabulary. |
| Out-of-tree plugins | satellite repos | Referenced by git URL and listed in `registry.json`. |

The kernel source tree:

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

## The generic registry

`Machine` stores implementations by `category -> name -> implementation` and tracks the
owner of each category and item.

```python
from machine_core import Machine

machine = Machine()
machine.register_category("tool")
machine.register("tool", "calculator", object())

machine.resolve("tool", "calculator")   # <object>
machine.list_category("tool")           # {"calculator": <object>}
machine.list_categories()               # ["tool"]
```

| Method | Behavior |
|--------|----------|
| `register_category(category, validator=None, defined_by="core", *, operations=None)` | Create a category. Re-registering from the **same** owner is idempotent; a different owner raises `CategoryExists`. `validator` gates `register`; `operations` describe HTTP-callable operations. Emits `CategoryRegistered`. |
| `register(category, name, impl, owner="core")` | Add an implementation. Unknown category raises `CategoryNotFound`; a failing validator raises `ValidationError`. Emits `ItemRegistered`. |
| `resolve(category, name)` | Return an implementation, or `None`. |
| `list_category(category)` | A copy of the `name -> impl` mapping. |
| `list_categories()` | All category names. |
| `get_owner(category, name)` | The owning plugin for an item. |
| `get_operations(category)` | The category's declared operations. |
| `unregister(category, name)` | Remove an item. Emits `ItemUnregistered`. |

`Machine` also owns `machine.hooks` (`HookSystem`), `machine.bus` (`DataBus`),
`machine.plugins` (`PluginManager`), and plugin data persistence
(`load_plugin_data` / `save_plugin_data`, stored under `<data_dir>/plugin-data/`).

## Starting a Machine

```python
from machine_core import Machine, MachineConfig

machine = Machine(config=MachineConfig.from_pyproject())
await machine.start()
```

`start()` does three things:

1. `plugins.discover()` scans `importlib.metadata` entry points in the
   `machine_core.plugins` group for manifests.
2. If `config.plugins` is set, `_load_declared_plugins()` loads **only** those plugins,
   reading manifests from `<data_dir>/plugins/<name>/manifest.json`. Category-defining
   plugins (those with `categories:define`) sort first.
3. `_run_ready_callbacks()` awaits every callback registered with `when_ready`.

```python
@machine.when_ready
async def _register():
    machine.register("tool", "word_count", WORD_COUNT_TOOL)
```

`shutdown()` unloads every loaded plugin.

> **Note:** A `Machine` starts **empty**. If `[tool.machine-core].plugins` is missing or
> empty, nothing loads. There is no auto-discovery of builtin plugins in the current
> architecture.

## `MachineConfig`

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

`MachineConfig.from_pyproject(path=None)` reads `[tool.machine-core]` from `pyproject.toml`
and normalizes `-`/`_` aliases for `plugin_configs` and `disabled_plugins`. `data_dir`
defaults to `~/.config/machine-core/` and contains:

- `plugins/<name>/manifest.json` — synced manifests,
- `plugins/<name>.json` — optional user config,
- `plugin-data/<name>.json` — persisted plugin runtime state.

## Plugin lifecycle

Plugins are described by `manifest.json` and driven by `PluginManager.load()`:

1. **Manifest** — looked up among discovered manifests.
2. **Transport** — created from `manifest.transport` (`in-process` or `json-rpc`).
3. **Config** — resolved through the five-step chain (see [Configuration](configuration.md)).
4. **`initialize(config=...)`** — called on the plugin via the transport.
5. **`PluginContext`** — constructed with the plugin's declared capabilities.
6. **`setup(ctx=...)`** — the plugin defines categories, registers implementations, and
   subscribes to hooks/events.
7. **Auto-wire** — every `hooks_subscribed` entry becomes a proxy subscriber; every
   `events_subscribed` entry becomes a proxy event handler. Both are recorded for cleanup.
8. **Emit `PluginEnabled`.**

Unload reverses this: `context.cleanup()` removes everything registered through the context,
then `shutdown({})` is called, then the transport closes, then `PluginDisabled` is emitted.

A minimal in-process plugin:

```python
class ToolSupportPlugin:
    async def initialize(self, **kwargs):
        pass

    async def setup(self, ctx):
        ctx.register_category(
            "tool",
            operations={"execute": {"method": "POST", "on": "item"}},
        )

    async def shutdown(self, **kwargs):
        pass
```

## Capabilities

`PluginContext` is capability-gated. The manifest is the contract; calling a gated method
without the capability raises `CapabilityDenied`.

| `PluginContext` method | Required capability |
|------------------------|--------------------|
| `register(category, name, impl)` | `{category}:register` |
| `register_category(category, ...)` | `categories:define` |
| `register_hookspec(hook_name, ...)` | `hooks:define` |
| `subscribe_hook(hook_name, callback, priority)` | *(not gated)* |
| `emit(event)` | `events:emit` |
| `on(event_type, callback)` | *(not gated)* |
| `load_data()` / `save_data(data)` | `data:own` |

`data:own` state is for **runtime state** (tokens, cursors, counters) — never for
configuration. Config flows through `initialize(config=...)`.

## Transports

The plugin boundary is language-agnostic. `PluginManager._create_transport()` builds one of:

- **`in-process`** — `InProcessTransport` imports the class named by
  `transport.entry_point` (e.g. `tool_support:ToolSupportPlugin`), instantiates it, and
  calls its methods directly. Methods may be sync or async. Missing methods return `None`,
  which is why `setup` is optional.
- **`json-rpc` / `spawn`** — launches `transport.binary` (+ `args`) as a subprocess with
  `MACHINE_CORE_PLUGIN=1`, reads a handshake line from stdout (10s timeout), then speaks
  line-delimited JSON-RPC 2.0 over stdin/stdout.
- **`json-rpc` / `connect`** — connects to an already-running process via
  `unix://<path>`, `tcp://<host>:<port>`, or plain `<host>:<port>` and speaks the same
  protocol.

`JsonRpcTransport` tracks request IDs, resolves responses into futures, and fails all
pending requests when the connection drops. For spawned plugins it terminates (then kills)
the subprocess on close.

## Errors

All plugin errors derive from `PluginError`:

| Error | Raised when |
|-------|-------------|
| `CapabilityDenied` | A plugin uses an API it did not declare a capability for. |
| `PluginNotFound` | A name is not in the discovered manifests, or a plugin is not loaded. |
| `TransportError` | Transport communication fails. |
| `CategoryExists` | A different owner tries to redefine an existing category. |
| `CategoryNotFound` | Registering into (or resolving) a missing category. |
| `ValidationError` | An implementation fails a category validator. |

---

**Read next:** [Plugins](plugins.md) · [Configuration](configuration.md) ·
[Plugin authoring](../guides/write-a-plugin.md)

**Source:** `src/machine_core/machine.py`, `src/machine_core/plugin/manager.py`,
`src/machine_core/plugin/context.py`, `src/machine_core/plugin/transport.py`,
`src/machine_core/plugin/jsonrpc_transport.py`, `src/machine_core/plugin/errors.py`.
