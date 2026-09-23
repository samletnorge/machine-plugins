# Quickstart

From nothing to a running agent with a tool and a chat UI. This page assumes the `machine`
CLI is installed; if not, start with [Installation](installation.md).

## 1. Scaffold

```bash
machine init my-agent
cd my-agent
uv sync
```

You now have a project whose `[tool.machine-core].plugins` already includes a tool category,
a model provider, an agent category, an agent runtime, memory, RAG, and the HTTP server.

## 2. Give the model provider a key

The scaffold uses `provider_deepseek`. Put its key in `.env`:

```bash
echo 'DEEPSEEK_API_KEY=sk-your-key-here' > .env
```

Prefer fully local? Replace `provider_deepseek` with `provider_ollama` in both
`dependencies` and `[tool.machine-core].plugins`, run `uv sync`, and `ollama pull llama3.2`.

## 3. Start the dev server

```bash
machine dev
```

You should see the manifest sync, then uvicorn:

```
Syncing plugin manifests...
Starting dev server...
  URL: http://127.0.0.1:8008
  Entry: src.main:machine
```

Check it is alive:

```bash
curl -s http://127.0.0.1:8008/health
# {"status":"healthy","categories":{"tool":1,"agent":1,"memory":1, ...}}
```

The `categories` map is built at request time, so it reflects exactly what loaded.

## 4. Meet the example agent

The scaffold registered one tool and one agent in `src/agents/example.py`:

```python
from agent_support.schemas import AgentDefinition
from tool_support import tool


@tool(name="word_count", description="Count the words in a piece of text.")
async def word_count(text: str) -> int:
    return len(text.split())


WORD_COUNT_TOOL = word_count.__tool_definition__

ASSISTANT_DEFINITION = AgentDefinition(
    name="assistant",
    description="A concise assistant that can use tools.",
    model_ref="deepseek/deepseek-chat",
    tool_refs=["word_count"],
    instruction="You are a concise assistant. Use the available tools when they help.",
)
```

`src/main.py` registers both once plugins have loaded:

```python
@machine.when_ready
async def _register_project_items() -> None:
    machine.register("tool", WORD_COUNT_TOOL.name, WORD_COUNT_TOOL)
    machine.register("agent", "assistant", ExampleAgent(machine))
    machine.register("memory", "default", MemoryManager(storage=InMemoryStorage()))
```

## 5. Chat with it in Studio

In a second terminal:

```bash
machine studio
```

Open <http://127.0.0.1:3177/_studio/chat> and pick `assistant`. Type a message and send.
Studio calls the agent's `run(message)` and renders the reply. This is the fastest way to see
the whole stack working.

## 6. Talk to it over HTTP

machine-core auto-generates routes from the registry. List what loaded:

```bash
curl -s http://127.0.0.1:8008/api/agent | python -m json.tool
curl -s http://127.0.0.1:8008/api/tool   | python -m json.tool
```

The example agent's `run(self, input, context=None)` takes a single value, so the generated
`POST /api/agent/{name}/run` route passes the JSON body as that single positional argument.
Send a JSON string:

```bash
curl -s -X POST http://127.0.0.1:8008/api/agent/assistant/run \
  -H 'content-type: application/json' \
  -d '"How many words are in this sentence?"'
```

> **Tip:** The generated operation routes are deliberately generic. If an item method takes
> a Pydantic model, send that model as a JSON object; if it takes one positional value, send
> that value. See [HTTP API](../guides/http-api.md) for the exact rules.

## 7. Or use the OpenAI-compatible gateway

`server_support` mounts an OpenAI-compatible proxy at `/gateway/chat/completions` that talks
to whatever `model_provider` you registered:

```bash
curl -s http://127.0.0.1:8008/gateway/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "model": "deepseek/deepseek-chat",
    "messages": [{"role": "user", "content": "Say hello in five words."}]
  }'
```

The `provider/model` form selects a provider directly. See
[HTTP API](../guides/http-api.md#the-model-gateway).

## 8. Add your own tool

Create `src/tools/` and a tool module:

```python
# src/tools/weather.py
from tool_support import tool

@tool(name="weather", description="Get the current temperature for a city.")
async def weather(city: str) -> str:
    # Replace with a real API call.
    return f"{city}: 21°C"
```

Register it in `src/main.py`:

```python
from .tools.weather import weather  # the decorated function

@machine.when_ready
async def _register_project_items() -> None:
    # ...
    machine.register("tool", weather.__tool_definition__.name, weather.__tool_definition__)
```

Then reference it from the agent:

```python
ASSISTANT_DEFINITION = AgentDefinition(
    name="assistant",
    model_ref="deepseek/deepseek-chat",
    tool_refs=["word_count", "weather"],
    instruction="Use tools when they help.",
)
```

The dev server reloads on save; the new tool is registered on the next startup.

## What just happened

You composed a runtime instead of writing one:

| Piece | Provided by |
|-------|-------------|
| Model calls | `provider_deepseek` (a `model_provider`) |
| Tool contract | `tool_support` (the `tool` category) |
| Agent contract | `agent_support` (the `agent` category) |
| The agent loop | `agent_runtime_basic` (the `agent/basic` runtime) |
| HTTP API | `server_support` |
| Chat UI | `studio_support` |
| Registration | your `@machine.when_ready` callback |

## Next steps

- [Project anatomy](project-anatomy.md) — understand the generated files.
- [Build a tool-using agent](../guides/build-a-tool-using-agent.md) — go deeper on tools.
- [Build a RAG assistant](../guides/build-a-rag-assistant.md) — add retrieval.
- [Studio](../guides/studio.md) — the control plane.

---

**Source:** `scaffolds/project/`, `framework/tool_support/`, `framework/agent_support/`,
`community/agent_runtime_basic/`, `framework/server_support/`, `framework/studio_support/`.
