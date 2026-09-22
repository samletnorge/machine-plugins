# provider_deepseek

DeepSeek model provider for machine-core. DeepSeek exposes an
OpenAI-compatible chat completions API, so this plugin implements the
`model_provider` contract with plain `httpx` (no vendor SDK) and also bridges to
`pydantic-ai` for agent runtimes that need a native model object.

## Config

| Key | Env | Default |
| --- | --- | --- |
| `base_url` | `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` |
| `api_key` | `DEEPSEEK_API_KEY` | — (required to register) |
| `model` | `DEEPSEEK_MODEL` | `deepseek-chat` |

Registers as `model_provider/deepseek`.
