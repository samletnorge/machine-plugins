# Hooks and events

machine-core has two extension points. They look similar — both let plugins react to what is
happening — but they answer different questions.

| | Hooks | Events |
|---|-------|--------|
| Question | "What do you think I should do?" | "Heads up, this happened." |
| Return value | Collected results (a list) | None; fire-and-forget |
| Failure mode | Subscriber errors surface to the caller | Subscriber errors are logged, never propagated |
| Ordering | By priority (`first`, `normal`, `last`) | Registration order, dispatched as tasks |
| Defined by | A plugin declares a hook spec | Any code emits a typed event |
| Use for | Extension, override, collecting answers | Notification, telemetry, side effects |

Rule of thumb: **if the caller needs an answer, use a hook. If nobody is waiting, use an
event.**

## Hooks

A hook has a **spec** and zero or more **subscribers**. A framework plugin typically declares
the spec (`hooks:define`), and other plugins subscribe.

### Declaring a spec

```python
ctx.register_hookspec("before_agent_run", firstresult=False)
ctx.register_hookspec("on_agent_handoff", firstresult=True)
```

- `firstresult=False` — every subscriber runs; all non-`None` results are collected.
- `firstresult=True` — stop at the first non-`None` result (useful for "who handles this?").

### Subscribing

```python
def on_before_run(definition=None, input=None, **kwargs):
    print("running", definition.name)

ctx.subscribe_hook("before_agent_run", on_before_run, priority="first")
```

Subscribers may be sync or async. `priority` is one of `"first"`, `"normal"` (default), or
`"last"`, sorted in that order.

### Calling

```python
results = await machine.hooks.call("before_agent_run", definition=defn, input=text)
```

`call` invokes every subscriber in priority order and returns a list of the non-`None`
results. With a first-result spec it returns as soon as one subscriber returns non-`None`.

> **Tip:** Hooks are how agent runtimes let other plugins observe and extend a run. For
> example, `agent_runtime_basic` emits `before_agent_run`, `after_agent_run`,
> `on_agent_step`, `on_agent_error`, and `before_model_invoke` / `after_model_invoke` around
> its loop.

### Built-in hook specs

| Plugin | Hook | `firstresult` |
|--------|------|---------------|
| `agent_support` | `before_agent_run`, `after_agent_run` | no |
| `agent_support` | `on_agent_handoff` | **yes** |
| `agent_support` | `on_agent_step`, `on_agent_error` | no |
| `tool_support` | `before_tool_call`, `after_tool_call`, `on_tool_error` | no |
| `model_provider_support` | `before_model_invoke`, `after_model_invoke`, `on_model_error` | no |
| `embeddings` | `before_embed`, `after_embed` | no |
| `vectorstore_support` | `before_search`, `after_search`, `before_upsert`, `after_upsert` | no |
| `structured_output` | `before_generate_object`, `after_generate_object`, `on_validation_retry` | no |
| `prompt_support` | `before_prompt_render`, `after_prompt_render` | no |
| `memory_support` | `hooks/beforeMemoryStore`, `hooks/afterMemoryStore`, `hooks/beforeFactExtraction`, `hooks/afterFactExtraction` | no |
| `workflow_support` | `hooks/collectWorkflows`, `hooks/beforeWorkflowRun`, `hooks/afterWorkflowRun` | yes for the last two |
| `server_support` | `hooks/beforeServerStart`, `hooks/afterServerStart`, `hooks/beforeRequest` (firstresult), `hooks/afterRequest` | mixed |

> **Note:** Hook names are case- and separator-sensitive. Agent/tool/model hooks use
> snake_case; memory, workflow, and server hooks use a `hooks/` prefix. Match the spec exactly
> when subscribing.

## Events

Events are typed Pydantic models deriving from `Event`. They carry `source`, a UTC
`timestamp`, and an `event_id`.

```python
from machine_core.plugin.events import Event, ItemRegistered

class DocumentIndexed(Event):
    document_id: str
    chunks: int
```

### Emitting

```python
await ctx.emit(DocumentIndexed(source="my_plugin", document_id="doc-1", chunks=12))
```

Inside a plugin, `ctx.emit` requires the `events:emit` capability. From ordinary
application code you can use `machine.bus.emit(event)`.

### Subscribing

```python
def on_registered(event: ItemRegistered) -> None:
    print(event.category, event.name)

ctx.on(ItemRegistered, on_registered)
```

`ctx.on` registers a cleanup callback automatically, so subscriptions are removed when the
plugin unloads. `machine.bus.on(EventClass, callback)` does the same without a context.

### Built-in events

`machine_core.plugin.events` defines:

| Event | Fields |
|-------|--------|
| `PluginEnabled` | `plugin_name` |
| `PluginDisabled` | `plugin_name` |
| `CategoryRegistered` | `category`, `defined_by` |
| `ItemRegistered` | `category`, `name`, `registered_by` |
| `ItemUnregistered` | `category`, `name` |

The registry emits `CategoryRegistered` and `ItemRegistered`/`ItemUnregistered`
synchronously via `bus.emit_sync`, so events fire even when registering from sync code.

### Delivery semantics

- `await bus.emit(event)` dispatches each subscriber as a separate asyncio task. Subscriber
  exceptions are logged and never reach the emitter.
- `bus.emit_sync(event)` is used by the registry. If an event loop is running it schedules
  tasks; otherwise it calls sync subscribers directly (async subscribers are closed without
  awaiting, since there is no loop).

This means events are **best-effort notifications**. Do not put required control flow in an
event handler; use a hook if the caller must wait for a result.

## Manifest-declared subscriptions

A plugin can also declare subscriptions in its manifest. The kernel auto-wires them after
`setup()`:

```json
{
  "hooks_subscribed": { "before_agent_run": { "priority": "first" } },
  "events_subscribed": ["ItemRegistered"]
}
```

- For **in-process** plugins this creates proxy callbacks that call the plugin's method
  `before_agent_run(**kwargs)` / receive events.
- For **out-of-process** plugins the proxies forward across the transport: hooks via
  `transport.call(hook_name, kwargs)`, events via
  `transport.notify(event_name, payload)`.

Both proxies are recorded with the plugin's context and removed on unload.

## A worked example

Suppose you want to log every tool call:

```python
class AuditPlugin:
    async def setup(self, ctx):
        ctx.subscribe_hook("before_tool_call", self._on_before, priority="last")

    def _on_before(self, tool_name=None, **kwargs):
        print(f"[audit] {tool_name}")
```

And separately, announce indexing with an event no one must wait for:

```python
async def ingest(doc):
    await vector_store.upsert(...)
    await bus.emit(DocumentIndexed(source="ingest", document_id=doc.id, chunks=n))
```

---

**Read next:** [Configuration](configuration.md) · [Secrets](secrets.md)

**Source:** `src/machine_core/plugin/hooks.py`, `src/machine_core/plugin/events.py`,
`framework/*/*/hooks.py`, `framework/*/manifest.json`.
