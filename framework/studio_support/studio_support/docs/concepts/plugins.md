# Plugins

Plugins are how machine-core gets its behavior. This page explains the manifest, the plugin
class, capabilities, config, and how plugins collaborate through the registry.

## What a plugin is

A plugin is a package with:

1. a `manifest.json` at its root (force-included inside the installed package),
2. a plugin class exposing `initialize()`, `setup(ctx)`, and `shutdown()`,
3. whatever categories, items, hooks, or events it wants to contribute.

The kernel discovers manifests, resolves each plugin's config, then drives the lifecycle.

## `manifest.json`

```json
{
  "name": "tool_support",
  "version": "0.5.0",
  "description": "Defines the 'tool' category with ToolDefinition schema and @tool decorator",
  "schema_version": "1.0.0",
  "language": "python",
  "capabilities": ["categories:define", "hooks:define", "events:emit", "tool:register"],
  "dependencies": ["pyyaml>=6.0"],
  "config_schema": {
    "api_key": { "type": "string", "env": "MY_API_KEY", "secret": true }
  },
  "hooks_subscribed": { "before_agent_run": { "priority": "first" } },
  "events_subscribed": ["ItemRegistered"],
  "transport": { "type": "in-process", "entry_point": "tool_support:ToolSupportPlugin" }
}
```

| Field | Type | Notes |
|-------|------|-------|
| `schema_version` | `str` | Default `"1.0.0"`. |
| `name` | `str` | Plugin name; also the config/sync key. |
| `version` | `str` | Plugin version. |
| `description` | `str?` | Human-readable. |
| `language` | `str` | Default `"python"`; informs the language-agnostic boundary. |
| `author` | `str?` | — |
| `capabilities` | `list[str]` | Enforced by `PluginContext`. |
| `dependencies` | `list[str]` | **PyPI package names**, not plugin names. |
| `config_schema` | `dict[str, ConfigSchemaEntry]` | Declares config keys. |
| `hooks_subscribed` | `dict[str, dict]` | Hook name → options (`priority`). |
| `events_subscribed` | `list[str]` | Event class names, resolved from `machine_core.plugin.events`. |
| `transport` | `TransportConfig` | How the kernel talks to the plugin. |

See the full field reference in [Manifest](../reference/manifest.md).

## The plugin class

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext


class MyPlugin:
    async def initialize(self, config=None, **kwargs):
        """Store config. Called before setup()."""
        self._config = config or {}

    async def setup(self, ctx: "PluginContext"):
        """Define categories, register items, subscribe to hooks/events."""
        ctx.register_category("my_category")
        ctx.register("my_category", "thing", Thing())

    async def shutdown(self, **kwargs):
        """Release resources."""
        pass
```

All three methods are optional from the kernel's point of view — `InProcessTransport`
returns `None` for methods that do not exist, so a plugin can implement only what it needs.

### `initialize(config=...)`

Called once, before `setup()`, with the fully-resolved config dict. This is where you read
configuration. Plugins never load their own config; the kernel assembles and pushes it.

### `setup(ctx=...)`

Called with the capability-gated `PluginContext`. This is where the plugin does its work:

```python
ctx.register_category(name, validator=None, operations=None)
ctx.register(category, name, impl)
ctx.register_hookspec(hook_name, firstresult=False)
ctx.subscribe_hook(hook_name, callback, priority="normal")
await ctx.emit(event)
ctx.on(EventClass, callback)
ctx.load_data() / ctx.save_data(data)
```

### `shutdown()`

Called on unload, after `context.cleanup()` has already removed everything the plugin
registered through the context.

## Categories: define vs. register

This is the central convention of the ecosystem.

- **Framework plugins define categories** and their contracts. `tool_support` defines the
  `tool` category, `agent_support` defines `agent`, and so on. They declare
  `categories:define` and `{category}:register` capabilities.
- **Community plugins register implementations.** `provider_ollama` registers
  `model_provider/ollama`; `agent_runtime_basic` registers `agent/basic`. They declare only
  the category registration capability they need (e.g. `model_provider:register`).

Why the split? It lets a framework plugin own the *contract* while many plugins implement
it, and it lets category-defining plugins load first so implementers find their categories.

```python
# framework: define the category and one operation
ctx.register_category(
    "tool",
    operations={"execute": {"method": "POST", "on": "item"}},
)

# community: register an implementation
ctx.register("tool", "echo", ToolDefinition(name="echo", ..., handler=echo))
```

Categories can attach a validator. `register()` runs it and raises `ValidationError` if the
implementation does not satisfy the contract:

```python
ctx.register_category("model_provider", validator=lambda impl: hasattr(impl, "generate"))
```

## Operations: HTTP routes for free

A category's `operations` map describes item methods that the HTTP server should expose:

```python
ctx.register_category(
    "memory",
    operations={
        "create_thread": {"method": "POST", "on": "item", "path": "threads"},
        "list_threads":  {"method": "GET",  "on": "item", "path": "threads"},
        "get_thread":    {"method": "GET",  "on": "item", "path": "threads/{thread_id}"},
    },
)
```

With `server_support` loaded, this becomes
`POST /api/memory/{name}/threads`, `GET /api/memory/{name}/threads`, and so on. Operations
whose name contains `stream` are served as Server-Sent Events. See
[HTTP API](../guides/http-api.md).

## Capabilities in practice

The capability list in the manifest is the plugin's permission slip. Declaring too little
causes `CapabilityDenied` at runtime; declaring too much weakens the sandbox. Common
capabilities:

| Capability | Enables |
|------------|---------|
| `categories:define` | `ctx.register_category(...)` |
| `hooks:define` | `ctx.register_hookspec(...)` |
| `events:emit` | `ctx.emit(...)` |
| `data:own` | `ctx.load_data()` / `ctx.save_data(...)` |
| `tool:register`, `agent:register`, `model_provider:register`, ... | `ctx.register("<category>", ...)` |

> **Note:** `subscribe_hook` and `on` are not gated, but their registrations are still
> auto-removed on `cleanup()`. `emit` *is* gated by `events:emit`.

## Config

A plugin declares config keys in `config_schema`. Each key resolves through a five-step chain
(overrides → user config file → persisted state → env var → default). This is covered in
depth in [Configuration](configuration.md) and [Config schema](../reference/config-schema.md).

```json
"config_schema": {
  "base_url": { "type": "string", "default": "http://localhost:11434", "env": "OLLAMA_HOST" },
  "api_key":  { "type": "string", "env": "MY_KEY", "secret": true, "required": true }
}
```

`secret: true` keys are never logged — only their names appear in debug logs.

## Plugin data (runtime state)

Plugins capture their own runtime state — OAuth tokens, sync cursors, counters — through
`ctx.load_data()` / `ctx.save_data(data)`, or `machine.load_plugin_data(name)` /
`save_plugin_data(name, data)`. This is stored at
`<data_dir>/plugin-data/<name>.json` and is **not** configuration.

```python
data = ctx.load_data()
data["cursor"] = new_cursor
ctx.save_data(data)
```

## Transports

A plugin runs either:

- **in-process** — the default for Python plugins; `entry_point` names the class,
- **out-of-process** over JSON-RPC — spawned (`binary` + `args`) or connected
  (`address`).

The manifest declares which. See [Architecture](architecture.md#transports) and
[Write a plugin](../guides/write-a-plugin.md#out-of-process-json-rpc).

## How plugins find each other

Plugins collaborate only through the registry and the shared schemas:

```python
# provider_ollama registers itself
ctx.register("model_provider", "ollama", OllamaProvider(...))

# agent_runtime_basic, later, resolves it
provider = ctx._machine.resolve("model_provider", "ollama")
```

This is why load order matters and why implementations that depend on other registrations
often resolve *lazily* on first use (see `rag_support` and `tool_filter_rag`).

---

**Read next:** [Hooks and events](hooks-and-events.md) ·
[Write a plugin](../guides/write-a-plugin.md) · [Manifest](../reference/manifest.md)

**Source:** `src/machine_core/plugin/manifest.py`, `src/machine_core/plugin/manager.py`,
`src/machine_core/plugin/context.py`, `framework/*/manifest.json`.
