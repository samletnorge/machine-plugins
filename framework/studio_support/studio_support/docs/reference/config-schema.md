# Config schema reference

`config_schema` is the manifest's declaration of the config keys a plugin accepts. The kernel
resolves each key and pushes the assembled dict to `initialize(config=...)`.

## Shape

```json
"config_schema": {
  "base_url": {
    "type": "string",
    "default": "http://localhost:11434",
    "env": "OLLAMA_HOST",
    "secret": false,
    "required": false,
    "description": "Ollama server URL"
  }
}
```

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `type` | `str` | — | Declared type. Drives env coercion. |
| `default` | `Any` | `null` | Step 5 of the chain. |
| `env` | `str?` | `null` | Step 4 of the chain. |
| `secret` | `bool` | `false` | Never log the value. |
| `required` | `bool` | `false` | Warn when nothing resolves. |
| `description` | `str?` | `null` | Human-readable. |

## Resolution order

Per key, the **first non-`None`** value wins:

1. Explicit override — `MachineConfig.plugin_configs` or the `config=` passed to `load()`.
2. User config file — `<data_dir>/plugins/<name>.json`.
3. Plugin persisted state — `load_plugin_data()` (self-acquired credentials).
4. Environment variable — the key's `env`, coerced to `type`.
5. Manifest default.

```
overrides ─┐
user file ─┤
persisted ─┼─▶ first non-None per key
env var   ─┤
default   ─┘
```

If nothing resolves and `required` is `true`, the kernel logs:

```
Plugin 'my_plugin': required config key 'api_key' has no value. Set via MachineConfig,
user config, env var (MY_API_KEY), or provide a default.
```

## Env coercion (`_coerce_env_value`)

| `type` | Coercion |
|--------|----------|
| `number` | `int(value)` if it has no `.`, else `float(value)`; raw string on `ValueError`. |
| `boolean` | `value.lower() in ("true", "1", "yes")`. |
| anything else | string, unchanged. |

> **Note:** The manifest model comment lists `"string"`, `"number"`, `"boolean"`, but shipped
> manifests also use `"integer"` and `"json"`. Those fall through to the string branch — a
> `"json"` env value is **not** parsed automatically. Plugins that need structured config
> parse it themselves (for example, `mcp_support` converts its `servers` string with
> `json.loads`).

## `secret` handling

Secret keys are excluded from the "resolved values" debug log; only their names appear:

```
Plugin 'provider_deepseek' config resolved: {base_url: 'https://api.deepseek.com', model: 'deepseek-chat'} | secrets: ['api_key']
```

Secret values reach the plugin through `initialize(config=...)` like any other key — the
marker only affects logging.

## Setting values

### Project override (highest priority)

```toml
[tool.machine-core.plugin_configs.provider_ollama]
base_url = "http://gpu-box:11434"
model = "qwen2.5:14b"
```

### User config file

`~/.config/machine-core/plugins/provider_ollama.json`:

```json
{ "base_url": "http://gpu-box:11434" }
```

### Environment variable

```bash
export OLLAMA_HOST=http://gpu-box:11434
```

### Manifest default

Nothing to do — it applies automatically when nothing else resolves.

## Alias normalization

`MachineConfig.from_pyproject()` duplicates `plugin_configs` and `disabled_plugins` keys
under both `-` and `_` forms, and `_plugin_config_for()` checks aliases. `provider-ollama`
and `provider_ollama` therefore configure the same plugin.

## Example: resolving a real schema

`provider_ollama` declares:

```json
{
  "base_url": { "type": "string", "default": "http://localhost:11434", "env": "OLLAMA_HOST" },
  "model":    { "type": "string", "default": "llama3.2", "env": "OLLAMA_MODEL" }
}
```

Resolution outcomes:

| Setup | `base_url` | `model` |
|-------|------------|---------|
| No config | `http://localhost:11434` | `llama3.2` |
| `OLLAMA_MODEL=qwen2.5` | `http://localhost:11434` | `qwen2.5` |
| `plugin_configs` `base_url` + env `model` | override wins | env wins |
| Required key with no value | — | warning logged |

---

**Read next:** [Configuration](../concepts/configuration.md) · [Manifest](manifest.md)

**Source:** `src/machine_core/plugin/manifest.py`,
`src/machine_core/plugin/manager.py` (`_resolve_plugin_config`, `_coerce_env_value`).
