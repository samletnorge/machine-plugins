# Agents

An **agent** is a model-driven loop that can call tools and produce a result. In machine-core
the `agent` category is defined by `agent_support`, and the actual loop is supplied by an
**agent runtime** from a community plugin.

## The pieces

| Piece | Plugin | What it is |
|-------|--------|------------|
| `agent` category + schemas | `agent_support` | `AgentDefinition`, `AgentRunResult`, hooks. |
| `agent/basic` runtime | `agent_runtime_basic` | Manual model → tool → execute loop, no extra deps. |
| `agent/pydantic-ai` runtime | `agent_runtime_pydantic` | Pydantic-AI based loop. |

Add both the framework and a runtime to `[tool.machine-core].plugins`:

```toml
plugins = [
    "agent_support",
    "tool_support",
    "model_provider_support",
    "provider_ollama",
    "agent_runtime_basic",
]
```

## `AgentDefinition`

```python
from agent_support.schemas import AgentDefinition

ASSISTANT = AgentDefinition(
    name="assistant",
    description="A concise assistant that can use tools.",
    model_ref="ollama/llama3.2",          # "<provider>/<model>"
    tool_refs=["word_count"],              # names in the `tool` category
    instruction="Use tools when they help, then answer in one short paragraph.",
    max_steps=10,
    metadata={},
)
```

| Field | Type | Notes |
|-------|------|-------|
| `name` | `str` | Agent name. |
| `description` | `str` | Human-readable. |
| `model_ref` | `str?` | `"<provider>/<model>"` resolved against `model_provider`. |
| `tool_refs` | `list[str]` | Tool names resolved against `tool`. |
| `instruction` | `str?` | System instruction. |
| `max_steps` | `int` | Loop cap; default `10`. |
| `metadata` | `dict` | Free-form. |

`AgentRunResult` is what a run returns:

```python
class AgentRunResult(BaseModel):
    agent_name: str
    output: Any = None
    steps: list[AgentStep] = []
    duration_ms: float | None = None
```

## Two ways to have an `agent` item

The `agent` category's operations are `run`, `stream`, and `generate`. The HTTP server calls
those methods on whatever item you register under `agent`. There are two common shapes.

### 1. Register a runtime directly

The runtimes themselves are registered as `agent/basic` and `agent/pydantic-ai`. Their
signature is:

```python
async def run(
    definition: AgentDefinition,
    input: str,
    tools: list[ToolDefinition],
    context: dict | None = None,
) -> AgentRunResult
```

### 2. Register a thin agent wrapper (what the scaffold does)

The scaffold registers `agent/assistant` as an `ExampleAgent` whose `run(input, context)`
resolves the runtime and tools, then calls it:

```python
class ExampleAgent:
    description = "Example assistant agent (basic runtime + tools)"

    def __init__(self, machine):
        self._machine = machine

    async def run(self, input: str, context: dict | None = None):
        runtime = self._machine.resolve("agent", "basic")
        tools = [self._machine.resolve("tool", n) for n in ASSISTANT_DEFINITION.tool_refs]
        result = await runtime.run(ASSISTANT_DEFINITION, input, tools, context)
        return result.output
```

This wrapper is what makes a single-message `run(message)` call work from Studio chat. See
[Studio](studio.md#chat).

Register it in `when_ready`:

```python
@machine.when_ready
async def _register():
    machine.register("agent", "assistant", ExampleAgent(machine))
```

## Running an agent in Python

```python
import asyncio
from src.main import machine

async def main():
    await machine.start()

    runtime = machine.resolve("agent", "basic")
    defn = ASSISTANT_DEFINITION
    tools = [machine.resolve("tool", n) for n in defn.tool_refs]

    result = await runtime.run(defn, "How many words are in this sentence?", tools)
    print(result.output)
    for step in result.steps:
        print(step.step_type, step.detail)

asyncio.run(main())
```

## Lifecycle hooks

`agent_support` declares hooks that runtimes call around a run:

| Hook | When |
|------|------|
| `before_agent_run` | Before the loop starts. |
| `after_agent_run` | After the loop returns. |
| `on_agent_step` | After each step (model call, tool call). |
| `on_agent_handoff` | On a handoff between agents (`firstresult`). |
| `on_agent_error` | On an error. |

Subscribe from a plugin:

```python
ctx.subscribe_hook("on_agent_step", lambda step=None, **kw: print(step.step_type))
```

See [Hooks and events](../concepts/hooks-and-events.md).

## Handoffs

`agent_support` also ships a `HandoffRequest` schema:

```python
class HandoffRequest(BaseModel):
    from_agent: str
    to_agent: str
    message: Any = None
    context: dict = {}
```

Handoffs are a protocol, not an implementation — a multi-agent orchestration plugin (or your
project) decides how to route them and emits `on_agent_handoff`.

## Memory

To give an agent conversation memory, register a `MemoryManager` under `memory` and pass the
thread's prior messages through `context["messages"]`. The basic runtime reads
`context["messages"]` and prepends prior `user`/`assistant` turns. See
[Memory](memory.md).

## Which runtime?

| Runtime | Dependency | Use when |
|---------|------------|----------|
| `agent/basic` (`agent_runtime_basic`) | none beyond providers | You want a small reference loop, or a non-Pydantic stack. |
| `agent/pydantic-ai` (`agent_runtime_pydantic`) | `pydantic-ai` | You want Pydantic-AI's execution model. Requires the provider to expose `get_pydantic_model()`. |

> **Note:** `agent_runtime_pydantic` raises if a provider does not implement
> `get_pydantic_model()`. `provider_ollama` and `provider_deepseek` do; check the plugin's
> README for others.

## HTTP

With `server_support` loaded, agents get generated routes:

```
GET  /api/agent                 # list agents
GET  /api/agent/{name}          # one agent
POST /api/agent/{name}/run      # run it
POST /api/agent/{name}/stream   # SSE stream
POST /api/agent/{name}/generate # structured output
```

See [HTTP API](http-api.md#agent) for the body conventions.

---

**Read next:** [Tools](tools.md) · [Model providers](model-providers.md) ·
[Build a tool-using agent](build-a-tool-using-agent.md)

**Source:** `framework/agent_support/`, `community/agent_runtime_basic/`,
`community/agent_runtime_pydantic/`, `scaffolds/project/src/agents/example.py.j2`.
