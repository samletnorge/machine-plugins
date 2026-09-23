# Manifest reference

Every plugin ships a `manifest.json` describing its metadata, capabilities, config, and
transport. The kernel's `PluginManifest` (a Pydantic model) parses it.

## Example

```json
{
  "name": "provider_deepseek",
  "version": "0.1.0",
  "description": "DeepSeek LLM provider over the OpenAI-compatible chat completions API",
  "schema_version": "1.0.0",
  "language": "python",
  "author": "samletnorge",
  "capabilities": ["model_provider:register"],
  "dependencies": ["httpx>=0.28"],
  "config_schema": {
    "base_url": { "type": "string", "default": "https://api.deepseek.com", "env": "DEEPSEEK_BASE_URL" },
    "api_key": { "type": "string", "env": "DEEPSEEK_API_KEY" },
    "model": { "type": "string", "default": "deepseek-chat", "env": "DEEPSEEK_MODEL" }
  },
  "hooks_subscribed": {},
  "events_subscribed": [],
  "transport": {
    "type": "in-process",
    "entry_point": "provider_deepseek:DeepSeekProviderPlugin"
  }
}
```

## Top-level fields

| Field | Type | Default | Required | Notes |
|-------|------|---------|----------|-------|
| `name` | `str` | — | yes | Plugin name; the config/sync key. |
| `version` | `str` | — | yes | Plugin version. |
| `description` | `str?` | `null` | no | Human-readable. |
| `schema_version` | `str` | `"1.0.0"` | no | Manifest schema version. |
| `language` | `str` | `"python"` | no | Informs the language-agnostic boundary. |
| `author` | `str?` | `null` | no | — |
| `capabilities` | `list[str]` | — | yes | Enforced by `PluginContext`. |
| `dependencies` | `list[str]` | `[]` | no | **PyPI package names**, not plugin names. |
| `config_schema` | `dict[str, ConfigSchemaEntry]` | `{}` | no | Declares config keys. |
| `hooks_subscribed` | `dict[str, dict]` | `{}` | no | Hook name → options. |
| `events_subscribed` | `list[str]` | `[]` | no | Event class names. |
| `transport` | `TransportConfig` | — | yes | How the kernel talks to the plugin. |

## `config_schema` entry

```json
{
  "api_key": {
    "type": "string",
    "default": null,
    "env": "MY_API_KEY",
    "secret": true,
    "required": true,
    "description": "API key for the service"
  }
}
```

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `type` | `str` | — | Declared type (`string`, `number`, `boolean`; some manifests also use `integer`/`json`). |
| `default` | `Any` | `null` | Value used if nothing else resolves. |
| `env` | `str?` | `null` | Environment variable for step 4 of the chain. |
| `secret` | `bool` | `false` | Never logged; only the name appears in logs. |
| `required` | `bool` | `false` | Warns if nothing resolves. |
| `description` | `str?` | `null` | Human-readable. |

See [Config schema](config-schema.md) for resolution and coercion.

## `hooks_subscribed`

Maps a hook name to its subscription options. The only recognized option is `priority`:

```json
"hooks_subscribed": {
  "before_agent_run": { "priority": "first" }
}
```

Valid priorities: `first`, `normal` (default), `last`.

## `events_subscribed`

A list of event class names from `machine_core.plugin.events`:

```json
"events_subscribed": ["ItemRegistered", "PluginEnabled"]
```

Unknown names are logged at debug level and skipped.

## `transport`

```json
{
  "type": "in-process",
  "entry_point": "my_pkg:MyPlugin"
}
```

| Field | Type | Used by |
|-------|------|---------|
| `type` | `str` | `in-process` or `json-rpc`. |
| `entry_point` | `str?` | `in-process`: the `module:Class`. |
| `mode` | `str?` | `json-rpc`: `spawn` or `connect`. |
| `binary` | `str?` | `spawn`: the executable. |
| `args` | `list[str]` | `spawn`: arguments (default `[]`). |
| `address` | `str?` | `connect`: `unix://`, `tcp://`, or `host:port`. |

Examples for each mode are in
[Write a plugin](../guides/write-a-plugin.md#6-in-process-vs-json-rpc).

## Where manifests live

- **Source:** at the plugin package root (e.g. `framework/tool_support/manifest.json`).
- **Build:** force-included into the wheel (e.g.
  `site-packages/tool_support/manifest.json`).
- **Runtime:** synced by the CLI into `~/.config/machine-core/plugins/<name>/manifest.json`,
  which is where the kernel reads declared plugins.

## Validation rules

- `name`, `version`, `capabilities`, and `transport` are required.
- `transport.type` must be `in-process` or `json-rpc`.
- `json-rpc` requires `mode`; `spawn` requires `binary`; `connect` requires `address`.
- `schema_version` should match the manifest schema the plugin targets.

---

**Read next:** [Registry](registry.md) · [Config schema](config-schema.md)

**Source:** `src/machine_core/plugin/manifest.py`.
