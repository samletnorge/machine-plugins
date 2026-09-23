# Registry reference

The plugin **registry** is a catalog of framework, community, and external plugins. The CLI
uses it to install plugins; the kernel does not need it at runtime.

## `registry.json`

The registry lives at the root of the `machine-plugins` repository:

```json
{
  "version": "1.0.0",
  "plugins": {
    "tool_support": {
      "version": "0.5.0",
      "description": "Defines the 'tool' category with ToolDefinition schema and @tool decorator",
      "tier": "framework",
      "runtime": "python",
      "source": { "type": "registry", "path": "framework/tool_support" }
    },
    "vectorstore_lancedb": {
      "version": "0.1.0",
      "description": "LanceDB vector store plugin for machine-core",
      "tier": "external",
      "runtime": "python",
      "source": {
        "type": "git",
        "url": "https://github.com/samletnorge/machine-plugin-vectorstore-lancedb.git"
      }
    }
  }
}
```

### Entry fields

| Field | Type | Notes |
|-------|------|-------|
| `version` | `str` | Plugin version (defaults to `0.0.0` if missing). |
| `description` | `str` | Human-readable. |
| `tier` | `str` | `framework`, `community`, or `external`. |
| `runtime` | `str` | `python`, `binary`, `node`, `go`, `docker`, or `any`. |
| `source` | `dict` | How to fetch it (see below). |

### Source types

| `source.type` | Meaning | Fields |
|---------------|---------|--------|
| `registry` | Lives inside the `machine-plugins` repo. | `path` (e.g. `framework/tool_support`). |
| `git` | Lives in its own repository. | `url`. |

### Tiers

- **`framework`** — category and support plugins: `agent_support`, `tool_support`,
  `model_provider_support`, `embeddings`, `vectorstore_support`, `memory_support`,
  `mcp_support`, `prompt_support`, `structured_output`, `processor_support`,
  `workflow_support`, `voice_support`, `server_support`, `studio_support`, `storage_support`,
  `auth_support`, `cli_support`.
- **`community`** — implementations: providers (`provider_*`), embeddings (`embeddings_*`),
  runtimes (`agent_runtime_*`), `rag_support`, `tool_openapi`, `tool_filter_rag`,
  `browser_support`, `deployer_support`, `workspace_support`, `observability_support`,
  `pubsub_support`, `channel_support`, and the domain plugin `agent_brreg_expert`.
- **`external`** — plugins in separate repositories: `eval_support`,
  `vectorstore_lancedb`.

## `manifests/`

The repository also has a `manifests/` directory with standalone descriptor files for
external plugins (`eval_support.json`, `vectorstore_lancedb.json`). These are lighter than a
full `manifest.json` and describe the git source.

## The registry client

`machine_core.plugin.registry.RegistryClient` fetches and caches the registry:

```python
from machine_core.plugin.registry import RegistryClient

client = RegistryClient()            # remote by default
plugins = await client.list_plugins(tier="framework")
entry = await client.get_plugin("tool_support")
matches = await client.search_plugins("embedding")
source = await client.resolve_source("tool_support")
```

| Member | Behavior |
|--------|----------|
| `DEFAULT_REGISTRY_URL` | `https://raw.githubusercontent.com/samletnorge/machine-plugins/main/registry.json`. |
| `fetch_registry(force_refresh=False)` | Fetch with caching; falls back to cache on error. |
| `list_plugins(tier=None)` | All entries, optionally filtered by tier. |
| `get_plugin(name)` | One entry, or `None`. |
| `search_plugins(query)` | Case-insensitive match on name/description. |
| `resolve_source(name)` | The `source` dict for install. |

The cache is written to `~/.machine/cache/registry.json`. With `offline=True`, only the cache
is used; a missing cache raises `FileNotFoundError`.

## The installer

`machine_core.plugin.installer.PluginInstaller` installs a plugin into
`~/.config/machine-core/plugins/<name>/` (the same directory the kernel reads manifests
from):

```python
from machine_core.plugin.installer import PluginInstaller

installer = PluginInstaller()
await installer.install("tool_support")          # no-op if already installed
await installer.install("tool_support", force=True)
installer.is_installed("tool_support")
installer.installed_plugins()
await installer.uninstall("tool_support")
```

Install flow:

- **`registry` source** — clone (or pull) `machine-plugins`, then copy
  `registry/<path>` to the install dir.
- **`git` source** — `git clone --depth=1 <url>` into the install dir.
- Both then try `uv pip install -e <path>`, falling back to `pip install -e <path>`.

## CLI

```bash
machine plugin list
machine plugin install tool_support
machine plugin install --all-framework
machine plugin search embedding
machine plugin remove tool_support
```

See [`machine plugin`](cli.md#machine-plugin).

## Adding a plugin to a project

The registry is for discovery/install; projects still declare plugins explicitly. Add the
name to `[tool.machine-core].plugins` and a source to `[tool.uv.sources]`:

```toml
[tool.machine-core]
plugins = ["tool_support", "my_plugin"]

[tool.uv.sources]
my_plugin = { git = "git+ssh://git@github.com/you/machine-plugin-my.git", subdirectory = "plugins/my_plugin" }
```

Then run `uv sync` and `machine dev` (which syncs the manifest).

---

**Read next:** [Manifest](manifest.md) · [CLI](cli.md)

**Source:** `registry.json`, `manifests/`, `src/machine_core/plugin/registry.py`,
`src/machine_core/plugin/installer.py`.
