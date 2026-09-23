# FAQ

## What is machine-core, in one sentence?

A small, language-agnostic plugin kernel for AI agent runtimes: it provides a registry, a
plugin lifecycle, hooks, events, config resolution, and transports; everything else is a
plugin.

## Is machine-core an agent framework?

Not by itself. The kernel has no agents, tools, providers, RAG, or HTTP server. Those live in
plugins, which is what makes the kernel small and swappable.

## Do I have to use plugins?

At runtime, a `Machine` starts **empty**. You can use it as a plain generic registry:

```python
from machine_core import Machine

machine = Machine()
machine.register_category("tool")
machine.register("tool", "calculator", object())
```

If you want agents, providers, an HTTP API, or Studio, you load the plugins that provide
them.

## Why must I list plugins explicitly?

Reproducibility. `Machine.start()` loads **only** the plugins in
`[tool.machine-core].plugins`. Nothing is auto-discovered or auto-loaded. If a plugin is not
listed, it does not exist as far as the runtime is concerned.

## What is a "category"?

A namespace in the registry: `category -> name -> implementation`. Plugins **define**
categories (`categories:define`) and other plugins **register** into them
(`{category}:register`). `machine.resolve("model_provider", "ollama")` is how one plugin finds
another.

## Hooks or events?

Hooks ask "what do you think?" and collect answers; events announce "this happened" and are
fire-and-forget. If the caller needs a result, use a hook. See
[Hooks and events](concepts/hooks-and-events.md).

## Is this Python-only?

No. Python plugins run in-process by default, but the plugin boundary supports out-of-process
JSON-RPC (spawned or connected). A manifest declares its `language` and transport. That said,
all shipped plugins today are Python, and in-process is the common path.

## Why does my agent `run` operation ignore `prompt`?

The generated operation routes are generic. They pass path params plus the JSON body as
keyword arguments, and on `TypeError` they fall back to passing the body as a **single
positional argument**. A method like `run(self, input, context=None)` therefore receives the
whole body as `input`. To pass a plain string, send a JSON string (`-d '"hello"'`); to pass a
Pydantic model, send the object. This is covered in
[HTTP API](guides/http-api.md#how-an-operation-is-invoked).

## Why does `POST /api/tool/{name}/execute` fail for my `@tool`?

A `ToolDefinition` has a `handler`, not an `execute` method, and the generated route calls
`item.execute`. Studio's tool tester is handler-aware and works. See
[Tools](guides/tools.md#run-a-tool-directly).

## Where does machine-core store data?

- Synced manifests: `<data_dir>/plugins/<name>/manifest.json`
- User plugin config: `<data_dir>/plugins/<name>.json`
- Plugin runtime state: `<data_dir>/plugin-data/<name>.json`
- Registry cache: `~/.machine/cache/registry.json`

`data_dir` defaults to `~/.config/machine-core` and is configurable via `MachineConfig`.

## How do I install a plugin?

Add it to `[tool.machine-core].plugins` and to `[tool.uv.sources]`, then `uv sync`. Or use the
CLI: `machine plugin install <name>`. See [Registry](reference/registry.md).

## Can I deploy to Vercel or Cloudflare?

Yes — the respective deployers generate config. Remember that serverless platforms have size
and duration limits; long-running agents and SQLite storage fit containers better. See
[Cloud](deployment/cloud.md).

## Does `machine deploy --target dokploy` work?

No, not out of the box. A `DokployDeployer` exists but is not registered and is not in the
CLI fallback map. Register it yourself. See
[Deployers](guides/deployers.md#built-in-deployers).

## Does `machine eval run` actually score?

Not yet. It validates and summarizes the dataset; the `eval_support` plugin provides the
scoring contracts. See [Evals](guides/evals.md).

## Do I need an API key to start?

The kernel starts fine without one. A provider plugin that declares a required key logs a
warning at config resolution, and calls fail until the key is set. DeepSeek requires
`DEEPSEEK_API_KEY`; Ollama needs no key.

## Can I use a hosted model like Gemini or Groq?

Yes. Add the provider plugin and set its key (`GCP_API_KEY`, `GROQ_API_KEY`, ...). See
[Model providers](guides/model-providers.md).

## How do I add memory to an agent?

Register a `MemoryManager`, then pass prior messages via `context["messages"]`. See
[Memory](guides/memory.md) and [Build a chatbot](guides/build-a-chatbot.md#5-add-conversation-memory).

## Where is the API documentation?

FastAPI serves OpenAPI at `/openapi.json`, Swagger at `/docs`, and ReDoc at `/redoc`
alongside the generated routes.

---

**Still stuck?** See [Troubleshooting](troubleshooting.md).
