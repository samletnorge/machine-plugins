# Memory

Memory gives agents conversation history, small key-value "working memory", and extracted
facts. `memory_support` defines the `memory` and `storage-backend` categories and ships a
`MemoryManager` plus in-memory and SQLite storage.

## The pieces

| Piece | What it is |
|-------|------------|
| `memory` category | Thread + message operations, backed by a `MemoryManager`. |
| `storage-backend` category | Pluggable persistence (`InMemoryStorage`, `SqliteStorage`, ...). |
| `MemoryManager` | Coordinates threads, messages, working memory, and facts. |
| `WorkingMemory` | Per-thread key-value store for explicit remembers. |
| `ObservationalMemory` | Extracts and stores facts from messages. |
| Windowing strategies | `LastNWindow`, `TokenLimitedWindow`, `SummarizedWindow`. |

## Enable it

```toml
plugins = ["memory_support", "..."]
```

Optionally persist to SQLite:

```toml
[tool.machine-core.plugin_configs.memory_support]
sqlite_path = "./data/memory.db"
```

With `sqlite_path` unset, `memory_support` registers an **in-memory** manager. With it set,
it registers a SQLite-backed one. Either way the manager is registered as `memory/default`.

## Use a `MemoryManager`

The scaffold registers one in `when_ready`:

```python
from memory_support.manager import MemoryManager
from memory_support.in_memory_storage import InMemoryStorage

machine.register("memory", "default", MemoryManager(storage=InMemoryStorage()))
```

> **Note:** `memory_support` already registers `memory/default` in its `setup()`. Registering
> your own under the same name overwrites it. That is what the scaffold does — it replaces
> the plugin's default manager with one that uses its own storage. Use a different name if
> you want both.

### Threads and messages

```python
memory = machine.resolve("memory", "default")

thread = await memory.create_thread(title="Support chat")
await memory.add_message(thread.id, role="user", content="Hi, I need help.")
await memory.add_message(thread.id, role="assistant", content="Sure — what's up?")

messages = await memory.get_messages(thread.id)
threads = await memory.list_threads()
await memory.delete_thread(thread.id)
```

`role` is one of `user`, `assistant`, `system` (validated by the server's models).

### Working memory

```python
wm = memory.working_memory(thread.id)
await wm.set("language", "Norwegian")
await wm.get("language")            # "Norwegian"
await wm.get_all()
await wm.delete("language")
prompt = await wm.to_system_prompt()
```

### Facts (observational memory)

```python
facts = await memory.extract_facts(messages, thread_id=thread.id)
relevant = await memory.get_relevant_facts(thread_id=thread.id, query="language", limit=10)
```

Fact extraction uses an optional `FactExtractor`; pass one to `MemoryManager` to enable LLM
extraction.

### Building agent context

```python
context = await memory.build_context(thread.id)
# {
#   "messages": [...],
#   "working_memory_prompt": "...",
#   "facts": [...],
# }
```

Pass `context["messages"]` to an agent runtime so prior turns are included. The basic runtime
reads `context["messages"]`.

## Windowing

Long threads do not fit in a model's context. Apply a strategy:

```python
from memory_support.windowing import LastNWindow, TokenLimitedWindow, SummarizedWindow

context = await memory.build_context(thread.id, window=LastNWindow(n=20))
context = await memory.build_context(thread.id, window=TokenLimitedWindow(max_tokens=4000))
```

| Strategy | Keeps |
|----------|-------|
| `LastNWindow(n=20, preserve_system=True)` | The last N messages (optionally always keeping system messages). |
| `TokenLimitedWindow(max_tokens=4000, preserve_system=True)` | Messages until a rough token budget is hit. |
| `SummarizedWindow(keep_recent=10, summarize_after=20)` | Recent messages plus a summary of older ones. |

`MemoryManager` defaults to `LastNWindow(n=50)`.

## Native memory tools

`memory_support.tools` ships helpers designed to be wrapped as agent tools so the model can
manage working memory explicitly:

```python
from memory_support.tools import remember, recall, forget, list_memories
```

Each takes the manager and a `thread_id`. Wrap them in `@tool`-decorated functions bound to a
thread:

```python
from tool_support import tool

@tool(name="remember", description="Remember a fact for this conversation.")
async def remember_tool(key: str, value: str) -> str:
    return await remember(memory, thread_id, key=key, value=value)
```

## HTTP operations

`memory_support` declares these operations:

| Operation | Route |
|-----------|-------|
| `create_thread` | `POST /api/memory/{name}/threads` |
| `list_threads` | `GET /api/memory/{name}/threads` |
| `get_thread` | `GET /api/memory/{name}/threads/{thread_id}` |
| `add_message` | `POST /api/memory/{name}/threads/{thread_id}/messages` |
| `delete_thread` | `DELETE /api/memory/{name}/threads/{thread_id}` (204) |

For the default manager, `{name}` is `default`:

```bash
curl -s -X POST http://127.0.0.1:8008/api/memory/default/threads \
  -H 'content-type: application/json' -d '{"metadata": {"channel": "web"}}'
```

See [HTTP API](http-api.md#memory).

## Lifecycle hooks

`memory_support` declares `hooks/beforeMemoryStore`, `hooks/afterMemoryStore`,
`hooks/beforeFactExtraction`, and `hooks/afterFactExtraction`. `MemoryManager` calls them
when a hook caller is provided (the plugin passes `machine.hooks.call`).

## Storage backends

`storage-backend` is a separate category. The `storage_support` plugin adds `local` and
`s3`-style backends. A `MemoryManager` takes any `BaseStorage` implementation, so you can
point memory at your own backend:

```python
class MyStorage(BaseStorage):
    ...
```

---

**Read next:** [RAG](rag.md) · [Agents](agents.md) · [Workflows](workflows.md)

**Source:** `framework/memory_support/`.
