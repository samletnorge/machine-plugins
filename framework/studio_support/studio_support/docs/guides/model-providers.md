# Model providers

A **model provider** wraps a model API and exposes a uniform `generate` / `stream` surface.
The `model_provider` category is defined by `model_provider_support`; concrete providers live
in `community/`.

## The contract

```python
from model_provider_support.schemas import ModelRequest, ModelResponse, ModelProviderConfig

class ModelRequest(BaseModel):
    provider: str
    model: str
    input: Any
    parameters: dict = {}
    stream: bool = False

class ModelResponse(BaseModel):
    provider: str
    model: str
    output: Any
    usage: dict = {}
    duration_ms: float | None = None
    tool_calls: list[dict] | None = None
```

The category declares operations `generate` (POST), `stream` (POST), and `list` (GET). A
provider plugin registers an implementation under `model_provider/<name>` with the
`model_provider:register` capability.

```python
# inside a provider plugin's setup()
ctx.register("model_provider", "ollama", OllamaProvider(base_url=..., model=...))
```

`model_ref` values elsewhere in the system use the form `"<provider>/<model>"`, for example
`"ollama/llama3.2"` or `"deepseek/deepseek-chat"`. Runtimes split on the first `/` and
`machine.resolve("model_provider", provider_name)`.

## Available providers

| Plugin | Registry name | Tier |
|--------|---------------|------|
| `provider_ollama` | `model_provider/ollama` | community |
| `provider_deepseek` | `model_provider/deepseek` | community |
| `provider_groq` | `model_provider/groq` | community |
| `provider_google_gemini` | `model_provider/google-gemini` | community |
| `provider_grok` | `model_provider/grok` | community |
| `provider_azure_openai` | `model_provider/azure-openai` | community |
| `provider_vertex_gemini` | `model_provider/vertex-gemini` | community |
| `provider_vertex_claude` | `model_provider/vertex-claude` | community |
| `provider_github_copilot` | `model_provider/github-copilot` | community |

Every provider declares its config in `config_schema`, so the five-step config chain applies.

## Provider config reference

### Ollama (`provider_ollama`)

| Key | Env | Default |
|-----|-----|---------|
| `base_url` | `OLLAMA_HOST` | `http://localhost:11434` |
| `model` | `OLLAMA_MODEL` | `llama3.2` |

Pure `httpx`, no vendor SDK. Also exposes a pydantic-ai compatible model.

```toml
[tool.machine-core.plugin_configs.provider_ollama]
base_url = "http://localhost:11434"
model = "llama3.2"
```

### DeepSeek (`provider_deepseek`)

| Key | Env | Default |
|-----|-----|---------|
| `base_url` | `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` |
| `api_key` | `DEEPSEEK_API_KEY` | — (required to register) |
| `model` | `DEEPSEEK_MODEL` | `deepseek-chat` |

OpenAI-compatible chat completions over `httpx`, with a pydantic-ai bridge.

### Groq (`provider_groq`)

| Key | Env | Default |
|-----|-----|---------|
| `api_key` | `GROQ_API_KEY` | — (required) |
| `model` | `GROQ_MODEL` | `llama-3.3-70b-versatile` |

### Google Gemini (`provider_google_gemini`)

| Key | Env | Default |
|-----|-----|---------|
| `api_key` | `GCP_API_KEY` | — (required) |
| `model` | `GOOGLE_GEMINI_MODEL` | `gemini-2.0-flash` |

### Grok / xAI (`provider_grok`)

| Key | Env | Default |
|-----|-----|---------|
| `api_key` | `GROK_API_KEY` | — (required) |
| `model` | `GROK_MODEL` | `grok-3` |

### Azure OpenAI (`provider_azure_openai`)

| Key | Env | Default |
|-----|-----|---------|
| `endpoint` | `AZURE_OPENAI_ENDPOINT` | — (required) |
| `api_key` | `AZURE_OPENAI_API_KEY` | — (secret; not needed with token auth) |
| `deployment` | `AZURE_OPENAI_DEPLOYMENT` | `gpt-4o` |
| `api_version` | `AZURE_OPENAI_API_VERSION` | `2024-12-01-preview` |
| `use_token_auth` | `AZURE_USE_TOKEN_AUTH` | `false` |

### Vertex Gemini (`provider_vertex_gemini`)

| Key | Env | Default |
|-----|-----|---------|
| `project` | `GCP_PROJECT` | — (required) |
| `location` | `GCP_LOCATION` | `us-central1` |
| `model` | `VERTEX_GEMINI_MODEL` | `gemini-2.0-flash` |

### Vertex Claude (`provider_vertex_claude`)

| Key | Env | Default |
|-----|-----|---------|
| `project` | `GCP_PROJECT` | — (required) |
| `location` | `GCP_LOCATION` | `us-east5` |
| `model` | `VERTEX_CLAUDE_MODEL` | `claude-sonnet-4-20250514` |

### GitHub Copilot (`provider_github_copilot`)

| Key | Env | Default |
|-----|-----|---------|
| `access_token` | `GITHUB_COPILOT_TOKEN` | — (secret; can be acquired via device flow) |
| `model` | — | `gpt-4o` |

## Selecting a provider

In an agent definition:

```python
AgentDefinition(model_ref="deepseek/deepseek-chat", ...)
```

In the gateway (see below), either use the `provider/model` form or pass `provider`:

```json
{ "model": "ollama/llama3.2",   "messages": [{ "role": "user", "content": "Hi" }] }
{ "model": "llama3.2", "provider": "ollama", "messages": [] }
```

## Calling a provider directly

```python
provider = machine.resolve("model_provider", "ollama")
response = await provider.generate(ModelRequest(
    provider="ollama",
    model="llama3.2",
    input=[{"role": "user", "content": "Say hello."}],
))
print(response.output)
print(response.usage)
```

## The OpenAI-compatible gateway

`server_support` mounts `POST /gateway/chat/completions`, which proxies to a registered
provider and returns an OpenAI `chat.completion` object. It adds:

- provider selection (explicit `provider`, `provider/model`, `GatewayConfig.providers`, or
  the first registered provider),
- a TTL response cache (`cache_enabled`, `cache_ttl_seconds`, `cache_max_size`),
- per-client rate limiting (`rate_limit_rpm`, default 60),
- optional bearer-token auth (`api_keys`).

```bash
curl -s http://127.0.0.1:8008/gateway/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "model": "ollama/llama3.2",
    "messages": [{"role": "user", "content": "Say hello."}]
  }'
```

Forwarded parameters: `temperature`, `top_p`, `max_tokens`, `presence_penalty`,
`frequency_penalty`, `stop`, `tools`, `tool_choice`, `response_format`, `seed`.

See [HTTP API](http-api.md#the-model-gateway) for status codes and details.

## Writing your own provider

Implement an object with an async `generate(request) -> ModelResponse` (and ideally
`stream`), declare `model_provider:register`, and register it:

```python
class MyProvider:
    def __init__(self, api_key: str, model: str):
        ...

    async def generate(self, request):
        ...
        return ModelResponse(provider="mine", model=request.model, output=text)

class MyProviderPlugin:
    async def initialize(self, config=None, **kwargs):
        self._config = config or {}

    async def setup(self, ctx):
        ctx.register("model_provider", "mine", MyProvider(**self._config))
```

If you want `agent_runtime_pydantic` to work with it, also implement
`get_pydantic_model(model_name)`.

---

**Read next:** [Agents](agents.md) · [Memory](memory.md) · [HTTP API](http-api.md)

**Source:** `framework/model_provider_support/`, `community/provider_*/manifest.json`,
`framework/server_support/server_support/gateway.py`.
