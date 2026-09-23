# Installation

This page installs the `machine` CLI, scaffolds a project, and runs your first dev server.
It mirrors the real installer and scaffold code, command for command.

## Requirements

| Requirement | Why |
|-------------|-----|
| Python `>= 3.12` | The kernel and plugins target 3.12. |
| [`uv`](https://docs.astral.sh/uv/) | The installer uses it; projects use `uv sync`. |
| Git SSH access to the `samletnorge` GitHub repos | The CLI and every plugin are installed from git sources. |

> **Note:** In the current ecosystem, the CLI and plugin packages live in the private
> `samletnorge` GitHub organization and are fetched over SSH
> (`git+ssh://git@github.com/...`). If you do not have access to those repositories, the
> install will fail at the git step. The rest of these docs describe the intended public
> workflow.

## 1. Install the `machine` CLI

```bash
curl -fsSL https://gist.githubusercontent.com/valiantlynx/c3eaf552adf9aecff7c0366a25ff1e99/raw/install.sh | bash
```

The installer (`scripts/install.sh`):

1. ensures `uv` is available, installing it from `astral.sh` if needed,
2. warns if GitHub SSH access is not confirmed,
3. runs `uv tool install` against the `cli_support` framework plugin
   (`machine-plugins#subdirectory=framework/cli_support`),
4. falls back to a dedicated venv at `$MACHINE_HOME` (default `~/.machine`) with a shim in
   `$MACHINE_BIN` (default `~/.local/bin`) if `uv tool install` fails,
5. makes sure `~/.local/bin` is on your `PATH`.

Verify:

```bash
machine --help
machine --version
```

## 2. Scaffold a project

```bash
machine init my-project
cd my-project
```

`machine init <dir>` refuses to write into a non-empty directory and creates:

```
my-project/
├── pyproject.toml          # [tool.machine-core] + [tool.uv.sources]
├── .gitignore
└── src/
    ├── __init__.py
    ├── main.py             # entry point: src.main:machine
    └── agents/
        ├── __init__.py
        └── example.py
```

Use `--name/-n` to set the project name explicitly; otherwise the directory name is used:

```bash
machine init my-project --name my_agent_app
```

## 3. Resolve dependencies

```bash
uv sync
```

`uv sync` reads the generated `pyproject.toml`. Every plugin is pinned to a git source, most
as a `subdirectory` of the `machine-plugins` workspace:

```toml
[tool.uv.sources]
machine-core = { git = "git+ssh://git@github.com/samletnorge/machine-core.git" }
tool_support = { git = "git+ssh://git@github.com/samletnorge/machine-plugins.git", subdirectory = "framework/tool_support" }
provider_ollama = { git = "git+ssh://git@github.com/samletnorge/machine-plugins.git", subdirectory = "community/provider_ollama" }
vectorstore_lancedb = { git = "git+ssh://git@github.com/samletnorge/machine-plugin-vectorstore-lancedb.git" }
eval_support = { git = "git+ssh://git@github.com/samletnorge/machine-plugin-eval-support.git" }
```

`uv` resolves the transitive bare dependencies each plugin declares in its own
`pyproject.toml`.

> **Note:** `uv sync` must be run before `machine dev` or `machine studio`. Both commands
> require the project's `.venv`.

## 4. Configure a model provider

The scaffold selects `provider_deepseek`. DeepSeek is OpenAI-compatible and needs an API
key. The simplest way to supply it is a `.env` file in the project root:

```bash
# my-project/.env
DEEPSEEK_API_KEY=sk-...
```

The project loads `.env` through `bootstrap_secrets()` at startup. See
[Secrets](../concepts/secrets.md) for the full story, including Infisical.

If you would rather run everything locally, swap the provider in `pyproject.toml` and install
Ollama:

```bash
# In pyproject.toml dependencies and [tool.machine-core].plugins, replace
# provider_deepseek with provider_ollama, then:
uv sync
ollama pull llama3.2
```

See [Model providers](../guides/model-providers.md) for every provider.

## 5. Run the dev server

```bash
machine dev                       # http://127.0.0.1:8008
machine dev --port 9000 --host 0.0.0.0
```

`machine dev`:

1. walks up from the current directory to find the project (`pyproject.toml` with
   `[tool.machine-core]`),
2. reads the `entry` point (default `src.main:machine`),
3. **syncs plugin manifests** from the project's `site-packages` into
   `~/.config/machine-core/plugins/<name>/manifest.json` — this is what the kernel reads,
4. ensures `server_support`, `agent_support`, and `tool_support` are importable, installing
   them from git subdirectories if missing,
5. writes a temporary `_machine_dev_server.py` that imports the entry machine, calls
   `server_support.app.create_app(machine)`, and runs `uvicorn --reload` against the
   project's `.venv` Python.

Then open <http://127.0.0.1:8008/health> or the Swagger UI at
<http://127.0.0.1:8008/docs>.

## 6. Run Studio

```bash
machine studio                    # http://127.0.0.1:3177/_studio/
machine studio --port 4000
```

`machine studio` requires the `studio_support` plugin, finds the project root, syncs
manifests, and launches a host app via `studio_support.app.create_studio_host_app(machine)`
with `MACHINE_STUDIO_ENABLED=1`. See [Studio](../guides/studio.md).

## 7. The interactive TUI

Running `machine` with no subcommand launches the interactive TUI and auto-starts the dev
server in the background on port `8008` if it is not already running.

```bash
machine
```

## Troubleshooting the install

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `uv: command not found` | `uv` is not on `PATH`. | Re-run the installer; it installs `uv` to `~/.local/bin`. |
| Git clone prompts for credentials | No SSH key for GitHub. | Add an SSH key (`ssh -T git@github.com`). |
| `machine` not found after install | `~/.local/bin` not on `PATH`. | `export PATH="$HOME/.local/bin:$PATH"`. |
| `machine dev` says "No .venv found" | `uv sync` was not run. | `uv sync` in the project root. |
| Plugin "not found" warning at startup | Manifest not synced. | Run `machine dev` (it syncs) or `machine plugin install <name>`. |

---

**Read next:** [Quickstart](quickstart.md) · [Project anatomy](project-anatomy.md)

**Source:** `scripts/install.sh`, `framework/cli_support/cli_support/commands/init_cmd.py`,
`.../commands/dev_cmd.py`, `.../commands/studio_cmd.py`, `.../manifest_sync.py`,
`.../scaffolds/project/`.
