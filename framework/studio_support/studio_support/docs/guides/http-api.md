# HTTP API

`server_support` builds a FastAPI app from a live `Machine` instance and mounts a router at
`/api`. Routes are derived from the registry, so the API changes as you add categories and
operations. It also mounts a `/health` check and an OpenAI-compatible model gateway.

## Creating the app

```python
from server_support.app import create_app

app = create_app(machine, title="Machine Core API", version="0.1.0", cors_origins=None)
```

`machine dev` does this for you. In its lifespan, `create_app`:

1. calls `bootstrap_secrets()` if available,
2. calls the `hooks/beforeServerStart` hook,
3. starts the machine if it has no categories yet (loading plugins), then **re-generates
   routes** now that plugins are loaded,
4. calls `hooks/afterServerStart`.

CORS defaults to `allow_origins=["*"]`. A request-ID middleware sets `x-request-id` and calls
`hooks/beforeRequest` (firstresult) and `hooks/afterRequest`. A global exception handler
returns `{"detail": "Internal server error"}` with status 500.

## Generated routes

For every registered category `{category}`:

| Method | Path | Source | Description |
|--------|------|--------|-------------|
| `GET` | `/api/{category}` | every category | List items as `[{"name", "owner", ...serialized}]`. |
| `GET` | `/api/{category}/{name}` | every item | Fetch one item; 404 if absent. |
| `{op.method}` | `/api/{category}/{name}/{op.path}` | category `operations` | Invoke a method on the resolved item. |

`op.path` defaults to the operation name if not set. Operation route ids are
`{category}__{op}`, list is `{category}__list`, and get is `{category}__get`.

### How an operation is invoked

1. Resolve the item with `machine.resolve(category, name)`; 404 if missing.
2. Find the method named after the operation on the item. For streaming operations it falls
   back to `run_stream`.
3. Build `kwargs` from path parameters and, for `POST`/`PUT`/`PATCH`, the JSON body.
4. Coerce values to annotated Pydantic types (`_coerce_kwargs`).
5. Call it (awaiting if async).

If a call raises `TypeError`, the generator retries by inspecting the signature:

- if the first parameter is annotated with a Pydantic model, the whole body is validated as
  that model and passed positionally,
- otherwise the body is passed as a single positional value (`_coerce_single_value`).

> **Note:** This "single positional body" fallback is why a method like
> `run(self, input, context=None)` receives the JSON body as `input`. To pass a plain string,
> send a JSON string (`-d '"hello"'`); to pass an object for a Pydantic-annotated first
> parameter, send that object. The rules are generic by design and can be surprising — see
> the [FAQ](../faq.md#why-does-my-agent-operation-route-ignore-prompt).

### Streaming operations

An operation whose name is `stream` or contains `stream` (case-insensitive) is served as
Server-Sent Events. The handler calls the method, expects an async generator, and streams
`data: {json}\n\n` frames with `content-type: text/event-stream`.

### Deletes

If the operation's method is `DELETE`, the route returns `204 No Content`.

### Serialization and redaction

Responses are serialized with `_serialize`. Objects with `model_dump()` or `__dict__` become
dicts; values whose key contains `api_key`, `apikey`, `secret`, `password`, `passwd`,
`access_token`, `refresh_token`, `client_secret`, `authorization`, or `credential` are
replaced with `"***"`.

## `/health`

```json
{
  "status": "healthy",
  "categories": { "tool": 1, "agent": 1, "memory": 1, "model_provider": 2 }
}
```

Counts are read from the live registry at request time.

## Concrete routes by category

### Agent

```
GET  /api/agent
GET  /api/agent/{name}
POST /api/agent/{name}/run
POST /api/agent/{name}/stream
POST /api/agent/{name}/generate
```

### Tool

```
GET  /api/tool
GET  /api/tool/{name}
POST /api/tool/{name}/execute
```

> **Note:** `POST /api/tool/{name}/execute` calls `item.execute`. A bare `ToolDefinition`
> has a `handler`, not `execute`, so it will not work here. Use Studio's tool tester, an
> agent runtime, or a wrapper that exposes `execute`. See [Tools](tools.md).

### Model provider

```
GET  /api/model_provider
POST /api/model_provider/{name}/generate
POST /api/model_provider/{name}/stream
GET  /api/model_provider/{name}/list   # list operation is declared GET on collection
```

### Memory

```
GET    /api/memory/{name}/threads
POST   /api/memory/{name}/threads
GET    /api/memory/{name}/threads/{thread_id}
POST   /api/memory/{name}/threads/{thread_id}/messages
DELETE /api/memory/{name}/threads/{thread_id}
```

### Workflow

```
POST /api/workflow/{name}/start
GET  /api/workflow/{name}/runs
GET  /api/workflow/{name}/runs/{run_id}
POST /api/workflow/{name}/runs/{run_id}/resume
```

### RAG

```
GET  /api/chunker
POST /api/chunker/{name}/chunk
GET  /api/rag_pipeline
POST /api/rag_pipeline/{name}/ingest
POST /api/rag_pipeline/{name}/retrieve
```

### Others

`embedding` (`embed`, `list`), `vector_store` (`upsert`, `search`, `delete`, `list`),
`voice_provider` (`speak`, `listen`, `connect`, `list`), `browser` (`navigate`,
`screenshot`, `execute`, `list`), `sandbox` (`execute`, `list`), `filesystem` (`read`,
`write`, `list`), `deployer` (`deploy`, `teardown`, `list`), `auth_provider`, `processor`,
`pubsub`, `channel`.

FastAPI's standard `/openapi.json`, `/docs`, and `/redoc` remain available alongside these
routes.

## The model gateway

`POST /gateway/chat/completions` is an OpenAI-compatible proxy over registered
`model_provider`s.

```bash
curl -s http://127.0.0.1:8008/gateway/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "model": "deepseek/deepseek-chat",
    "messages": [{"role": "user", "content": "Say hello."}]
  }'
```

### Provider selection

In order:

1. an explicit `"provider"` field in the body,
2. `"<provider>/<model>"` in `model`,
3. `GatewayConfig.providers[model]` (a string or `{provider, model}`),
4. the first registered `model_provider` (alphabetically).

### Response shape

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1700000000,
  "model": "deepseek-chat",
  "provider": "deepseek",
  "choices": [{ "index": 0, "message": { "role": "assistant", "content": "..." }, "finish_reason": "stop" }],
  "usage": { "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0 }
}
```

### Features and status codes

- **Caching** — responses are cached by a SHA-256 of the body for `cache_ttl_seconds` (300).
- **Rate limiting** — 60 requests/minute per client by default; over the limit returns `429`.
- **Auth** — if `api_keys` is set, a Bearer token in `Authorization` must match, else `401`.
- **Forwarded parameters** — `temperature`, `top_p`, `max_tokens`, `presence_penalty`,
  `frequency_penalty`, `stop`, `tools`, `tool_choice`, `response_format`, `seed`.
- **`503`** — no provider available (or the selected provider has no `generate`).

`GatewayConfig` defaults: `cache_enabled=True`, `cache_ttl_seconds=300`,
`cache_max_size=1000`, `rate_limit_rpm=60`, `api_keys=[]`. `create_app` uses a default
`GatewayConfig`; to customize, construct the router yourself:

```python
from server_support.gateway import GatewayConfig, create_gateway_router

app.include_router(create_gateway_router(
    GatewayConfig(rate_limit_rpm=600, api_keys=["sk-local"], cache_enabled=False),
    machine=machine,
))
```

## Request/response models

`server_support.models` defines Pydantic models for common operations, including
`AgentRunRequest`, `AgentGenerateRequest`, `ToolExecuteRequest`, `WorkflowStartRequest`,
`ThreadCreateRequest`, `MessageCreateRequest` (validates `role` ∈ user/assistant/system),
and standard `ErrorResponse`. Use them as a contract reference when calling the API.

## Hooks

| Hook | When |
|------|------|
| `hooks/beforeServerStart` | Before the app starts. |
| `hooks/afterServerStart` | After startup. |
| `hooks/beforeRequest` | Before handling a request (firstresult; may short-circuit). |
| `hooks/afterRequest` | After handling a request. |

---

**Read next:** [Studio](studio.md) · [Build a chatbot](build-a-chatbot.md) ·
[CLI](../reference/cli.md)

**Source:** `framework/server_support/`.
