# Tools

A **tool** is a typed function an agent can call. The `tool` category is defined by
`tool_support`, which also ships a `@tool` decorator that derives a schema from your type
hints.

## The pieces

| Piece | Location | What it is |
|-------|----------|------------|
| `tool` category | `tool_support` | Category + the `execute` operation. |
| `ToolDefinition` | `tool_support.schemas` | `name`, `description`, `parameters`, `handler`, `metadata`. |
| `ToolResult` | `tool_support.schemas` | `tool_name`, `output`, `error`, `duration_ms`. |
| `@tool` | `tool_support.decorator` | Builds a `ToolDefinition` from a typed callable. |

## Define a tool with `@tool`

```python
from tool_support import tool

@tool(name="word_count", description="Count the words in a piece of text.")
async def word_count(text: str) -> int:
    """Return the number of whitespace-separated words in ``text``."""
    return len(text.split())
```

The decorator:

- infers **JSON Schema** from the function's type hints (`_params_schema`),
- treats parameters without defaults and not Optional as `required`,
- uses the docstring as the description if none is given,
- attaches the definition at `word_count.__tool_definition__`,
- returns a wrapper that awaits the underlying function.

Supported annotations include `str`, `int`, `float`, `bool`, `bytes`, `list`/`set`/`tuple`,
`dict`, `Literal`, `Optional`/`Union`, `Enum`, and any Pydantic model (via
`model_json_schema()`).

```python
from typing import Literal
from pydantic import BaseModel
from tool_support import tool


class WeatherArgs(BaseModel):
    city: str
    units: Literal["metric", "imperial"] = "metric"


@tool(name="weather", description="Get the current temperature for a city.")
async def weather(city: str, units: str = "metric") -> str:
    return f"{city}: 21°{'C' if units == 'metric' else 'F'}"
```

## Register a tool

```python
WORD_COUNT_TOOL = word_count.__tool_definition__

@machine.when_ready
async def _register():
    machine.register("tool", WORD_COUNT_TOOL.name, WORD_COUNT_TOOL)
```

Registration requires the `tool` category to exist, which is why it happens inside
`when_ready`. Project code registers at `owner="core"`; plugins register via
`ctx.register("tool", name, definition)` with the `tool:register` capability.

## `ToolDefinition`

```python
class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict = {}        # JSON Schema for the arguments
    return_type: dict | None = None
    handler: Callable            # excluded from serialization
    metadata: dict = {}
```

> **Note (important):** A `ToolDefinition` has a `handler`, **not** an `execute` method.
> The server's generated `POST /api/tool/{name}/execute` route (`server_support`) looks for
> `item.execute`, so a raw `ToolDefinition` is **not** executable through that route. Studio's
> tool tester (`studio_support`) is handler-aware and will call `handler(**body)` instead.
> If you need an HTTP-executable tool, register an item that exposes an `execute` method (or
> a wrapper object with `execute`) rather than a bare `ToolDefinition`. This is a known
> inconsistency between the `tool` category's declared `execute` operation and the
> `ToolDefinition` shape.

## How a runtime executes a tool

`agent_runtime_basic` converts tools to OpenAI tool schemas and, when the model returns a
tool call, looks up the `ToolDefinition` and invokes its handler:

```python
tool_map = {td.name: td for td in tools}
...
result = td.handler(**args)   # args parsed from the model's tool_call
```

This is the path that actually works today for `@tool`-defined tools.

## Run a tool directly

```python
tool = machine.resolve("tool", "word_count")
result = await tool.handler(text="hello there world")
# 3
```

## Auto-generated utility tools

Two community plugins register internal toolkit entries into the `tool` category:

- `tool_openapi` registers `tool/__openapi_generator__` with `generate_tools` and
  `simplify_schema`, turning an OpenAPI spec into executable tool definitions.
- `tool_filter_rag` registers `tool/__filter_rag__`, a lazy manager with `index_tools` and
  `filter(prompt, top_k)` for semantic tool selection.

These are helper objects, not agent-callable tools; they show that the `tool` category is a
generic registry, not only a function list.

```python
gen = machine.resolve("tool", "__openapi_generator__")
tools = gen["generate_tools"](spec, base_url="https://api.example.com")
for t in tools:
    machine.register("tool", t.name, t)
```

## Tool lifecycle hooks

`tool_support` declares:

| Hook | When |
|------|------|
| `before_tool_call` | Before a handler runs. |
| `after_tool_call` | After a handler returns. |
| `on_tool_error` | When a handler raises. |

Audit or instrument calls by subscribing:

```python
ctx.subscribe_hook("before_tool_call", lambda tool_name=None, **kw: log(tool_name))
```

## HTTP and Studio

- **Studio tool tester:** open `/_studio/tools/{tool_name}` and post a JSON body. Studio
  prefers `execute()`, then `handler(**body)`, then a `filter()` method.
- **Generated API:** `GET /api/tool` and `GET /api/tool/{name}` list and fetch tools;
  `POST /api/tool/{name}/execute` calls `execute` (see the note above).

## Best practices

- Give every tool a clear `description`; the model uses it to choose tools.
- Keep argument schemas tight — use `Literal` and Pydantic models for structured input.
- Return JSON-serializable values (strings, dicts, lists). The server redacts sensitive keys
  such as `api_key`, `secret`, and `password` when serializing.
- Raise on failure rather than returning an error string, so `on_tool_error` fires and the
  runtime can report it.

---

**Read next:** [Model providers](model-providers.md) ·
[Build a tool-using agent](build-a-tool-using-agent.md) · [MCP](mcp.md)

**Source:** `framework/tool_support/`, `community/tool_openapi/`,
`community/tool_filter_rag/`, `framework/studio_support/studio_support/routes/tools.py`.
