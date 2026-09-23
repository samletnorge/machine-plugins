# Build a chatbot

You will build a working chatbot: a model-backed agent, a chat UI in Studio, and an HTTP
endpoint — all composed from plugins. Every command and file matches the real scaffold.

## What you need

- The `machine` CLI installed ([Installation](../getting-started/installation.md)).
- A DeepSeek API key (or Ollama running locally).

## 1. Scaffold and install

```bash
machine init chatbot
cd chatbot
uv sync
```

## 2. Configure the model

```bash
echo 'DEEPSEEK_API_KEY=sk-your-key-here' > .env
```

The scaffold's example agent already references `deepseek/deepseek-chat` and
`provider_deepseek` is in `plugins`, so nothing else is needed.

## 3. Make the assistant yours

Edit `src/agents/example.py`:

```python
from agent_support.schemas import AgentDefinition

ASSISTANT_DEFINITION = AgentDefinition(
    name="assistant",
    description="A friendly support assistant.",
    model_ref="deepseek/deepseek-chat",
    instruction=(
        "You are a friendly support assistant for an online store. "
        "Answer in at most three sentences. If you do not know, say so and offer to "
        "connect the user to a human."
    ),
    max_steps=5,
)
```

`src/main.py` already registers `agent/assistant` in `when_ready`, so the changes take
effect on the next start.

## 4. Run and chat

```bash
machine dev
```

In another terminal:

```bash
machine studio
```

Open <http://127.0.0.1:3177/_studio/chat>, choose `assistant`, and send a message. Studio
calls `ExampleAgent.run(message)` and renders the reply.

## 5. Add conversation memory

So far each message is independent. Add a thread per session using `memory_support`
(already in `plugins`).

Edit `src/main.py`:

```python
@machine.when_ready
async def _register_project_items() -> None:
    from memory_support.in_memory_storage import InMemoryStorage
    from memory_support.manager import MemoryManager

    from .agents.example import ExampleAgent

    machine.register("memory", "default", MemoryManager(storage=InMemoryStorage()))
    machine.register("agent", "assistant", ExampleAgent(machine))
```

Then pass prior turns when running the agent:

```python
class ExampleAgent:
    def __init__(self, machine):
        self._machine = machine
        self._thread = None
        self._memory = None

    async def run(self, input: str, context=None):
        self._memory = self._machine.resolve("memory", "default")
        if self._thread is None:
            self._thread = await self._memory.create_thread(title="chat")
        messages = await self._memory.get_messages(self._thread.id)
        runtime = self._machine.resolve("agent", "basic")
        result = await runtime.run(
            ASSISTANT_DEFINITION,
            input,
            [],
            {"messages": [m.model_dump() for m in messages]},
        )
        await self._memory.add_message(self._thread.id, role="user", content=input)
        await self._memory.add_message(self._thread.id, role="assistant", content=str(result.output))
        return result.output
```

Now the agent sees prior turns. See [Memory](memory.md) for windowing and facts.

## 6. Talk to it over HTTP

The auto-generated routes already expose the agent:

```bash
# list agents
curl -s http://127.0.0.1:8008/api/agent

# run the assistant, sending a JSON string for the single positional argument
curl -s -X POST http://127.0.0.1:8008/api/agent/assistant/run \
  -H 'content-type: application/json' \
  -d '"What is your return policy?"'
```

For a plain model completion without the agent, use the gateway:

```bash
curl -s http://127.0.0.1:8008/gateway/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "model": "deepseek/deepseek-chat",
    "messages": [{"role": "user", "content": "Say hello."}]
  }'
```

## 7. (Optional) Build a tiny web UI

Any static page can call the gateway. For example, save this as `static/index.html` and serve
it with any static host:

```html
<!doctype html>
<meta charset="utf-8" />
<h1>Chatbot</h1>
<form id="f">
  <input id="q" placeholder="Ask something" autocomplete="off" />
  <button>Send</button>
</form>
<pre id="out"></pre>
<script>
  const f = document.getElementById("f");
  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    const q = document.getElementById("q").value;
    const res = await fetch("http://127.0.0.1:8008/gateway/chat/completions", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        model: "deepseek/deepseek-chat",
        messages: [{ role: "user", content: q }],
      }),
    });
    const data = await res.json();
    document.getElementById("out").textContent =
      data.choices?.[0]?.message?.content ?? JSON.stringify(data);
  });
</script>
```

Studio's chat is the batteries-included option; this page shows how little is needed to
build your own.

## 8. Deploy it

See [Cloud deployment](../deployment/cloud.md). The short version:

```bash
machine deploy --target docker
docker compose up --build
```

## Recap

| You added | It came from |
|-----------|--------------|
| A model-backed reply | `provider_deepseek` |
| The agent loop | `agent_runtime_basic` |
| A chat UI | `studio_support` |
| HTTP + gateway | `server_support` |
| Memory | `memory_support` |

You composed a chatbot without writing a framework.

---

**Read next:** [Build a RAG assistant](build-a-rag-assistant.md) ·
[Build a tool-using agent](build-a-tool-using-agent.md) · [Deployers](deployers.md)

**Source:** `scaffolds/project/`, `framework/agent_support/`,
`community/agent_runtime_basic/`, `framework/memory_support/`.
