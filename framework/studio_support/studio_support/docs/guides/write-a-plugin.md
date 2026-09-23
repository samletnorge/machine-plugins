# Write a plugin

A plugin packages behavior for machine-core. This guide builds one end to end: a manifest, a
plugin class, a category, a config schema, and both transport options.

## Anatomy

```
my_plugin/
├── manifest.json          # metadata + capabilities + transport
├── pyproject.toml         # package config; force-includes manifest.json
└── my_plugin/
    ├── __init__.py        # the plugin class
    └── ...
```

The kernel reads manifests from `<data_dir>/plugins/<name>/manifest.json`. The CLI syncs them
there from the installed package, which is why the manifest must be **inside** the package
(for example `site-packages/my_plugin/manifest.json`).

## 1. The manifest

```json
{
  "name": "my_plugin",
  "version": "0.1.0",
  "description": "Adds a 'greeting' category and a hello tool.",
  "schema_version": "1.0.0",
  "language": "python",
  "author": "you",
  "capabilities": ["categories:define", "hooks:define", "tool:register"],
  "dependencies": ["httpx>=0.28"],
  "config_schema": {
    "greeting": {
      "type": "string",
      "default": "Hello",
      "env": "MY_PLUGIN_GREETING",
      "description": "Word to greet with"
    },
    "api_key": {
      "type": "string",
      "env": "MY_PLUGIN_API_KEY",
      "secret": true,
      "required": false
    }
  },
  "hooks_subscribed": {},
  "events_subscribed": [],
  "transport": {
    "type": "in-process",
    "entry_point": "my_plugin:MyPlugin"
  }
}
```

Field reference: [Manifest](../reference/manifest.md). Capability reference:
[Capabilities](../concepts/plugins.md#capabilities-in-practice).

## 2. The plugin class

```python
"""my_plugin — adds a greeting category and a hello tool."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from machine_core.plugin.context import PluginContext

HOOKSPECS = {"before_greet": {"firstresult": False}}


class MyPlugin:
    def __init__(self) -> None:
        self._greeting = "Hello"

    async def initialize(self, config=None, **kwargs) -> None:
        """Receive the resolved config before setup()."""
        config = config or {}
        self._greeting = config.get("greeting", "Hello")

    async def setup(self, ctx: "PluginContext") -> None:
        """Define categories and register implementations."""
        ctx.register_category("greeting")
        for name, opts in HOOKSPECS.items():
            ctx.register_hookspec(name, **opts)

        greeting = self._greeting

        async def hello(name: str) -> str:
            return f"{greeting}, {name}!"

        ctx.register("tool", "hello", {
            "name": "hello",
            "description": "Greet someone by name.",
            "handler": hello,
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        })

    async def shutdown(self, **kwargs) -> None:
        pass
```

All three methods are optional. `InProcessTransport` returns `None` for missing methods, so a
plugin that only defines `setup()` is valid.

### Lifecycle

```
initialize(config)  →  setup(ctx)  →  (running)  →  shutdown()
```

See [Architecture](../concepts/architecture.md#plugin-lifecycle) for the full kernel-driven
sequence, including auto-wiring of `hooks_subscribed` and `events_subscribed`.

## 3. Capabilities

Every `ctx` method is gated. Request exactly what you use:

| You call | Declare |
|----------|---------|
| `ctx.register_category(...)` | `categories:define` |
| `ctx.register("<category>", ...)` | `"<category>:register"` |
| `ctx.register_hookspec(...)` | `hooks:define` |
| `ctx.emit(...)` | `events:emit` |
| `ctx.load_data()` / `ctx.save_data(...)` | `data:own` |
| `ctx.subscribe_hook(...)`, `ctx.on(...)` | *(none)* |

Calling a gated method without the capability raises `CapabilityDenied`.

## 4. Config schema

Declare keys in `config_schema`; the kernel resolves each through the five-step chain and
pushes the result to `initialize(config=...)`. See
[Configuration](../concepts/configuration.md).

```json
"config_schema": {
  "base_url": { "type": "string", "default": "http://localhost", "env": "MY_BASE_URL" },
  "api_key":  { "type": "string", "env": "MY_API_KEY", "secret": true, "required": true },
  "retries":  { "type": "number", "default": 3 }
}
```

You can also use plugin data for runtime state (tokens, cursors):

```python
async def setup(self, ctx):
    state = ctx.load_data()
    state.setdefault("runs", 0)
    ctx.save_data(state)
```

## 5. Packaging

```toml
# pyproject.toml
[project]
name = "my_plugin"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["machine-core"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["my_plugin"]

[tool.hatch.build.targets.wheel.force-include]
"manifest.json" = "my_plugin/manifest.json"
```

> **Note:** `force-include` is how the manifest ends up inside the installed package, which
> the CLI's `sync_manifests` looks for (`site-packages/*/manifest.json`). Without it, the
> kernel will not discover your plugin.

Then add the plugin to your project's `[tool.machine-core].plugins` and to
`[tool.uv.sources]` if it is a git dependency.

## 6. In-process vs. JSON-RPC

### In-process (Python)

```json
"transport": { "type": "in-process", "entry_point": "my_plugin:MyPlugin" }
```

`InProcessTransport` imports the class, instantiates it with no arguments, and calls its
methods directly. Methods may be sync or async. This is the default for Python plugins.

### JSON-RPC spawn

For a plugin in another language or process:

```json
"transport": {
  "type": "json-rpc",
  "mode": "spawn",
  "binary": "my-plugin-server",
  "args": ["--stdio"]
}
```

The kernel launches `binary` + `args` with `MACHINE_CORE_PLUGIN=1`, reads a handshake line
from stdout (10s timeout), then speaks line-delimited JSON-RPC 2.0 over stdin/stdout.

### JSON-RPC connect

```json
"transport": {
  "type": "json-rpc",
  "mode": "connect",
  "address": "unix:///tmp/my-plugin.sock"
}
```

`address` accepts `unix://<path>`, `tcp://<host>:<port>`, or `<host>:<port>`.

### The wire protocol

Requests and notifications are standard JSON-RPC 2.0:

```json
{"jsonrpc": "2.0", "method": "initialize", "params": {"config": {}}, "id": 1}
{"jsonrpc": "2.0", "method": "setup", "params": {"ctx": null}, "id": 2}
{"jsonrpc": "2.0", "method": "shutdown", "params": {}, "id": 3}
```

Responses are `{"jsonrpc": "2.0", "result": ..., "id": ...}` or
`{"jsonrpc": "2.0", "error": ..., "id": ...}`. Manifest-declared hooks and events are
forwarded as calls and notifications respectively. Note that a remote plugin cannot receive
a live `PluginContext` object over the wire — design remote plugins around the JSON-RPC
method calls the kernel makes (`initialize`, `setup`, `shutdown`, hooks).

## 7. Test it

The kernel's tests show the patterns:

```python
from machine_core import Machine, MachineConfig
from machine_core.plugin.manifest import PluginManifest


async def test_plugin_loads():
    machine = Machine(config=MachineConfig(plugins=["my_plugin"], data_dir=tmp_path))
    machine.plugins.register_manifest(PluginManifest(**manifest_dict))
    await machine.plugins.load("my_plugin")
    assert machine.resolve("tool", "hello") is not None
    await machine.plugins.unload("my_plugin")
    assert machine.resolve("tool", "hello") is None
```

Use `register_manifest` to inject a manifest without needing an installed entry point; use a
temporary `data_dir` to avoid touching `~/.config/machine-core`.

## 8. Checklist

- [ ] `manifest.json` at the package root, force-included on build.
- [ ] Capabilities match exactly the gated calls you make.
- [ ] `config_schema` keys documented; secrets marked `secret: true`.
- [ ] `setup()` idempotent-safe (registering the same category from the same owner is a
      no-op).
- [ ] `shutdown()` releases resources (sessions, subprocesses, file handles).
- [ ] Manifests synced (`machine dev` does this) before testing.

---

**Read next:** [Manifest](../reference/manifest.md) · [Plugins](../concepts/plugins.md) ·
[Config schema](../reference/config-schema.md)

**Source:** `src/machine_core/plugin/manifest.py`, `src/machine_core/plugin/manager.py`,
`src/machine_core/plugin/context.py`, `src/machine_core/plugin/jsonrpc_transport.py`.
