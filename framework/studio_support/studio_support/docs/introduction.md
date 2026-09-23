# Introduction

machine-core is a **plugin kernel** for building AI agent runtimes. It is deliberately
small: it knows how to register things, load plugins, resolve configuration, dispatch hooks
and events, and talk to plugins over a language-agnostic boundary. Everything that makes an
application *useful* — agents, tools, model providers, memory, retrieval, workflows, HTTP
APIs, the Studio UI — is a plugin.

That is the whole idea. You compose a runtime by listing plugins; the kernel wires them
together.

## Why it exists

Most agent frameworks make you pick a stack up front. machine-core inverts that:

- **The kernel is tiny and stable.** `Machine`, a registry, a plugin manager, hooks, events,
  and transports. No agents, no providers, no vector stores baked in.
- **Behavior is composable.** Want a different model provider? Swap a plugin. Want RAG?
  Add `rag_support` plus an embedder and a vector store. The registry is the integration
  point.
- **The boundary is language-agnostic.** Python plugins run in-process. Plugins in any
  language can run out-of-process over line-delimited JSON-RPC. The manifest declares the
  `language` and the transport.

The result is a system where a project stays small — a `pyproject.toml`, a plugin list, and
a handful of lines in `src/main.py` — while the capabilities underneath are whatever you
declared.

## The mental model: kernel + plugins

Think of machine-core as an operating system kernel and plugins as drivers and user-space
services.

```
                       ┌──────────────────────────────────────────────┐
                       │                  Machine                     │
                       │  registry: category -> name -> implementation│
   @machine.when_ready │  hooks: HookSystem   events: DataBus         │
   ───────────────────▶│  plugins: PluginManager   data: plugin-data  │
                       └───────────────┬──────────────────────────────┘
                                       │ loads
                 ┌─────────────────────┼─────────────────────┐
                 ▼                     ▼                     ▼
        framework plugins       community plugins      your project code
   (define categories,      (implement categories:   (register a few
    contracts, hooks)        providers, runtimes)     agents/tools locally)
```

Three ideas carry the whole design:

1. **The registry.** A `Machine` stores implementations under
   `category -> name -> implementation`. Plugins *define* categories; other plugins
   *register* into them. `machine.resolve("model_provider", "ollama")` is how one plugin
   finds another.

2. **The plugin lifecycle.** A `Machine` starts **empty**. `machine.start()` discovers
   manifests and loads **only** the plugins declared in `[tool.machine-core].plugins`.
   Category-defining plugins load first, then implementers, then your `when_ready`
   callbacks run so you can register your own items into categories that now exist.

3. **Capabilities.** A plugin's `manifest.json` declares what it is allowed to do. The
   `PluginContext` handed to a plugin is capability-gated: calling a method without the
   matching capability raises `CapabilityDenied`. The manifest is the contract.

> **Note:** The kernel does *not* auto-discover or auto-load plugins. If a plugin is not in
> `[tool.machine-core].plugins`, it is not loaded. This is intentional — runtimes are
> explicit and reproducible.

## What the kernel provides

From `src/machine_core/`:

- `Machine` — the generic registry with ownership tracking.
- `MachineConfig` — project config loaded from `[tool.machine-core]`.
- `PluginManager` — plugin discovery, loading, unloading, config resolution, transports.
- `PluginContext` — the capability-gated API plugins use to register and subscribe.
- `HookSystem` — plugin-defined hooks with ordering and first-result support.
- `DataBus` — typed event pub/sub.
- plugin data persistence for plugin-owned runtime state.
- transports for in-process Python plugins and out-of-process JSON-RPC plugins.
- `bootstrap_secrets()` — `.env` and Infisical secret loading.

## What the plugins provide

The `machine-plugins` catalog ships two tiers:

- **`framework/*`** define the vocabulary: `agent_support`, `tool_support`,
  `model_provider_support`, `embeddings`, `vectorstore_support`, `memory_support`,
  `workflow_support`, `voice_support`, `server_support`, `studio_support`, and more.
- **`community/*`** implement it: `provider_ollama`, `provider_deepseek`,
  `agent_runtime_basic`, `agent_runtime_pydantic`, `rag_support`, `tool_openapi`,
  `tool_filter_rag`, `deployer_support`, `browser_support`, `workspace_support`, and more.

There are also **external** plugins in their own repositories, catalogued in
`registry.json`: `eval_support` and `vectorstore_lancedb`.

## What you can build

Because behavior is composed from plugins, the same kernel produces very different products:

- **A chatbot.** An agent + a model provider + `server_support`, with a chat UI in Studio.
  Start with [Build a chatbot](guides/build-a-chatbot.md).
- **A RAG assistant.** Add `rag_support`, an embedder, and a vector store, then an agent
  that retrieves before it answers. See [Build a RAG assistant](guides/build-a-rag-assistant.md).
- **A tool-using agent.** Register typed Python tools with `@tool` and let an agent call
  them. See [Build a tool-using agent](guides/build-a-tool-using-agent.md).
- **An automation service.** Workflows, browser automation, workspaces, and deployers turn
  the runtime into a service you can host. See [Workflows](guides/workflows.md) and
  [Deployers](guides/deployers.md).

You can also use the kernel *without* plugins as a plain generic registry:

```python
from machine_core import Machine

machine = Machine()
machine.register_category("tool")
machine.register("tool", "calculator", object())

tool = machine.resolve("tool", "calculator")
```

## The smallest possible runtime

```python
from machine_core import Machine, MachineConfig, bootstrap_secrets

bootstrap_secrets()
machine = Machine(config=MachineConfig.from_pyproject())

@machine.when_ready
async def _register():
    machine.register("tool", "calculator", object())

await machine.start()
```

Everything else — agents that call the calculator, an HTTP endpoint that executes it, a web
UI that lists it — comes from plugins you add to `[tool.machine-core].plugins`.

Ready to build one? Head to [Installation](getting-started/installation.md).

---

**Read next:** [Installation](getting-started/installation.md) ·
[Architecture](concepts/architecture.md) · [Plugins](concepts/plugins.md)

**Source:** `src/machine_core/machine.py`, `src/machine_core/plugin/manager.py`,
`src/machine_core/plugin/context.py`.
