# Secrets

Secrets are loaded into the process environment once at startup by
`bootstrap_secrets()`. It is deliberately the **only** module in machine-core that mutates
`os.environ`, and application entry points call it before any component resolves
configuration.

## Why an environment-based design

Plugins declare config keys with an `env` field. The config chain reads those environment
variables at step 4. That means a plugin never needs to know *where* a secret came from —
only what variable name convention it follows. `bootstrap_secrets()` fills the environment
from two sources, and the rest of the system is unchanged.

## Call it first

```python
from machine_core import Machine, MachineConfig, bootstrap_secrets

bootstrap_secrets()                 # 1. secrets into os.environ

config = MachineConfig.from_pyproject()
machine = Machine(config=config)
```

The scaffold's `src/main.py` already does this. `server_support.create_app()` also calls it
when it is available, so the dev server is covered even if you forget.

## The two sources, in order

1. **Local `.env`** — read from `$MACHINE_CORE_ROOT/.env` (if `MACHINE_CORE_ROOT` is set),
   falling back to `./.env`. Existing environment variables **always win**; the parser uses
   `os.environ.setdefault`, so it never overrides them.
2. **Infisical** — enabled when both `INFISICAL_CLIENT_ID` and `INFISICAL_CLIENT_SECRET` are
   set. Fetched secrets **overwrite** the same keys, so production values win over the local
   `.env` fallback.

```
.bashrc / container env ──(wins over)──▶ .env
        │
        └─▶ Infisical (overwrites matching keys)
                │
                ▼
           os.environ ──▶ config chain step 4 ──▶ initialize(config=...)
```

## Local `.env`

The parser is intentionally tiny — the kernel has no `python-dotenv` dependency — so it
supports a practical subset:

```bash
# .env
DEEPSEEK_API_KEY=sk-...
OLLAMA_HOST=http://localhost:11434
export MY_FLAG=yes
QUOTED="value with spaces"
```

- `#` lines and blank lines are skipped,
- `export KEY=...` is accepted,
- surrounding single or double quotes are stripped,
- keys already present in the environment are left untouched.

`MACHINE_CORE_ROOT` is set by `machine dev` and `machine studio` to the project root, so the
project's `.env` is the default.

## Infisical

Set a Machine Identity and an optional environment/project to enable remote secrets:

| Env var | Default | Purpose |
|---------|---------|---------|
| `INFISICAL_CLIENT_ID` | — | Machine Identity client ID (enables Infisical). |
| `INFISICAL_CLIENT_SECRET` | — | Machine Identity client secret. |
| `INFISICAL_HOST` | `https://infisical.valiantlynx.com` | Infisical host. |
| `INFISICAL_PROJECT_ID` | `""` | Project to read secrets from. |
| `INFISICAL_ENVIRONMENT` | `dev` | Environment slug. |
| `INFISICAL_TIMEOUT_SECONDS` | `10` | Bootstrap timeout. |

Install the optional SDK with the `secrets` extra (the scaffold already does):

```toml
dependencies = ["machine-core[secrets]"]
```

The integration is **soft**:

- a missing Machine Identity → debug log, plain environment preserved,
- an unreachable Infisical or unimportable SDK → warning, plain environment preserved,
- a timeout → warning, plain environment preserved,
- it **never raises**.

Secrets are fetched with `view_secret_value=True`, `include_imports=True`, and
`recursive=True`. Imported secrets are used as a fallback when a key is not defined directly.
Keys returned *masked* (no read-value permission) are skipped and reported by name:

```
Infisical returned 2 masked secret(s); skipped (no read-value permission): API_KEY, DB_URL
Infisical bootstrap attached 7 secret(s)
```

> **Note:** Only counts and key names are logged. Secret **values** are never logged.

## How a plugin consumes a secret

Declare it in the manifest with `env` and `secret: true`:

```json
"config_schema": {
  "api_key": { "type": "string", "env": "DEEPSEEK_API_KEY", "secret": true }
}
```

The config chain reads `DEEPSEEK_API_KEY` at step 4 and passes it to the plugin's
`initialize(config=...)`. Because `secret: true`, the debug log lists only the key name:

```
Plugin 'provider_deepseek' config resolved: {base_url: ...} | secrets: ['api_key']
```

## Rotating secrets

Because secrets live in the environment, rotation is a restart:

1. update the value in Infisical or `.env`,
2. restart the process (`machine dev` reloads on code changes, not env changes),
3. `bootstrap_secrets()` runs again at startup.

## Testing secrets

`tests/test_secrets.py` in the kernel covers the env parser (no override, quotes, `export`,
comments). A useful local check is to print only the *names* of the variables you expect:

```python
import os
from machine_core import bootstrap_secrets
bootstrap_secrets()
print([k for k in os.environ if k.startswith("INFISICAL_")])
```

Never print values in shared logs.

---

**Read next:** [Configuration](configuration.md) · [Model providers](../guides/model-providers.md)

**Source:** `src/machine_core/secrets.py`, `src/machine_core/plugin/context.py`
(`load_data`/`save_data`).
