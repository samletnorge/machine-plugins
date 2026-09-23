# Build a tool-using agent

You will build an agent that can call your own Python functions. Along the way you will see
exactly how tools are defined, registered, selected by the model, and executed.

## What you need

- A scaffolded project with `tool_support`, `agent_support`, `agent_runtime_basic`, and a
  model provider ([Quickstart](../getting-started/quickstart.md)).

## 1. Define tools

Create `src/tools/units.py`:

```python
"""Unit conversion and time tools."""
from tool_support import tool


@tool(name="celsius_to_fahrenheit", description="Convert a temperature from Celsius to Fahrenheit.")
async def celsius_to_fahrenheit(celsius: float) -> float:
    """Return the Fahrenheit equivalent of a Celsius temperature."""
    return celsius * 9 / 5 + 32


@tool(name="parse_duration", description="Parse a human duration like '2h30m' into total seconds.")
async def parse_duration(text: str) -> int:
    """Parse hours/minutes/seconds tokens into a total number of seconds."""
    import re

    total = 0
    for value, unit in re.findall(r"(\d+)\s*([hms])", text.lower()):
        total += int(value) * {"h": 3600, "m": 60, "s": 1}[unit]
    return total
```

Each decorated function gets a JSON Schema from its type hints and a
`__tool_definition__` attribute. See [Tools](tools.md#define-a-tool-with-tool).

## 2. Register them

Edit `src/main.py`:

```python
@machine.when_ready
async def _register_project_items() -> None:
    from .tools.units import celsius_to_fahrenheit, parse_duration

    for fn in (celsius_to_fahrenheit, parse_duration):
        td = fn.__tool_definition__
        machine.register("tool", td.name, td)
```

Registration happens in `when_ready` so the `tool` category exists. Confirm with:

```bash
curl -s http://127.0.0.1:8008/api/tool
```

## 3. Wire them into an agent

Add the agent definition and wrapper to `src/agents/converter.py`:

```python
"""A unit-conversion agent that uses tools."""
from typing import Any

from agent_support.schemas import AgentDefinition


CONVERTER_DEFINITION = AgentDefinition(
    name="converter",
    description="Converts units and durations using tools.",
    model_ref="deepseek/deepseek-chat",
    tool_refs=["celsius_to_fahrenheit", "parse_duration"],
    instruction=(
        "You convert units. Call a tool whenever one applies, then state the result "
        "clearly with the unit. Never guess a conversion."
    ),
    max_steps=6,
)


class ConverterAgent:
    description = CONVERTER_DEFINITION.description

    def __init__(self, machine: Any) -> None:
        self._machine = machine

    async def run(self, input: str, context: dict | None = None) -> Any:
        runtime = self._machine.resolve("agent", "basic")
        tools = [
            self._machine.resolve("tool", name)
            for name in CONVERTER_DEFINITION.tool_refs
        ]
        result = await runtime.run(CONVERTER_DEFINITION, input, tools, context)
        return result.output
```

Register it:

```python
from .agents.converter import ConverterAgent

machine.register("agent", "converter", ConverterAgent(machine))
```

## 4. Run it

```bash
machine dev
```

Python:

```python
import asyncio
from src.main import machine

async def main():
    await machine.start()
    agent = machine.resolve("agent", "converter")
    print(await agent.run("What is 21 degrees Celsius in Fahrenheit?"))
    print(await agent.run("Convert 2h30m to seconds."))

asyncio.run(main())
```

Studio: open `/_studio/chat`, choose `converter`, and ask.

HTTP:

```bash
curl -s -X POST http://127.0.0.1:8008/api/agent/converter/run \
  -H 'content-type: application/json' \
  -d '"Convert 100C to F"'
```

## 5. Watch the tool calls

Register a hook to see each step. In `src/main.py`:

```python
@machine.when_ready
async def _register_project_items() -> None:
    # ... tool + agent registration ...

    def on_step(step=None, **kwargs):
        print("[step]", step.step_type, step.detail)

    machine.hooks.subscribe("on_agent_step", on_step)
```

The basic runtime emits `on_agent_step` after each model and tool call. See
[Hooks and events](../concepts/hooks-and-events.md).

## 6. Test a tool directly

Studio's handler-aware tool tester:

```bash
curl -s -X POST http://127.0.0.1:3177/_studio/tools/celsius_to_fahrenheit/execute \
  -H 'content-type: application/json' \
  -d '{"celsius": 100}'
```

> **Note:** The generic `POST /api/tool/{name}/execute` route does **not** work for
> `ToolDefinition` items, because it calls `item.execute` and a `ToolDefinition` has a
> `handler`. Studio is handler-aware. See [Tools](tools.md#run-a-tool-directly).

## 7. Add a tool that returns structured data

Tools can return dicts and lists; the runtime serializes them for the model.

```python
@tool(name="stats", description="Return basic statistics for a list of numbers.")
async def stats(numbers: list[float]) -> dict:
    """Return count, mean, min, and max."""
    return {
        "count": len(numbers),
        "mean": sum(numbers) / len(numbers),
        "min": min(numbers),
        "max": max(numbers),
    }
```

## 8. Safety and quality

- **Close the loop.** Tell the model to call tools rather than guess.
- **Validate input.** `@tool` derives a schema, but the model can still send odd values;
  validate inside the handler if it matters.
- **Keep tools small.** One clear job per tool makes selection reliable.
- **Limit steps.** `max_steps` caps runaway loops.
- **Handle errors.** Raise inside the handler so `on_tool_error` fires; return user-safe
  messages from the agent.

## Recap

```
@tool ──▶ ToolDefinition ──▶ machine.register("tool", ...) ──▶ agent tool_refs ──▶ runtime
```

You added capabilities, not framework code.

---

**Read next:** [Tools](tools.md) · [Agents](agents.md) · [MCP](mcp.md)

**Source:** `framework/tool_support/`, `community/agent_runtime_basic/`,
`framework/studio_support/studio_support/routes/tools.py`.
