# Studio

Studio is the control plane for a machine-core runtime: a web UI for browsing the registry,
chatting with agents, testing tools, switching between projects and environments, and
inspecting domain data (memory, RAG, evals, storage, deploy, observe, auth, workspace,
browser, voice, pubsub).

## Launch it

```bash
machine studio                              # http://127.0.0.1:3177/_studio/
machine studio --port 4000 --host 0.0.0.0
```

`machine studio` requires `studio_support`, finds the project root, syncs manifests, and runs
a generated host app:

```python
from studio_support.app import create_studio_host_app
app = create_studio_host_app(machine)
```

The environment is set to `MACHINE_STUDIO_ENABLED=1`, `MACHINE_CORE_ENTRY=<entry>`, and
`MACHINE_CORE_ROOT=<root>`. If the project has no `.venv`, the CLI falls back to its own
interpreter and warns.

## What the host app serves

| Path | What it is |
|------|------------|
| `/` | Studio landing page. |
| `/_studio/` | The Studio sub-application. |
| `/health` | `{"status": "healthy", "studio_mount": "/_studio"}` |
| `/favicon.ico` | The Machine mark. |

The host app starts the machine in its lifespan (if it has not been started), so plugins and
`when_ready` callbacks run before any request is served.

## Studio routes

All Studio routes are mounted under `/_studio`:

| Path | Purpose |
|------|---------|
| `/_studio/` | Dashboard ("Mission Control"). |
| `/_studio/dashboard` | Dashboard alias. |
| `/_studio/account` | Account preferences (theme). |
| `/_studio/sections/{key}` | A domain page (`memory`, `rag`, `evals`, `storage`, `deploy`, `observe`, `auth`, `workspace`, `browser`, `voice`, `pubsub`). |
| `/_studio/islands/{domain}` | The Svelte island for a domain. |
| `/_studio/registry` | Registry browser. |
| `/_studio/config` | Configuration view. |
| `/_studio/services` | Services view. |
| `/_studio/resources` | Resources view. |
| `/_studio/chat` | Chat UI. |
| `/_studio/chat/send` | Form POST that runs an agent and returns chat HTML. |
| `/_studio/tools/{tool_name}` | Tool tester. |
| `/_studio/tools/{tool_name}/execute` | Execute a tool (handler-aware). |
| `/_studio/api/...` | Control-plane JSON endpoints. |

## Chat

Open <http://127.0.0.1:3177/_studio/chat>. The page lists agents from
`machine.list_category("agent")` and lets you pick one. Sending a message posts to
`/_studio/chat/send` with form fields `agent` and `message`; Studio calls
`agent_instance.run(message)` and renders the reply.

The control-plane chat API (used by rich surfaces) exposes:

| Method | Path |
|--------|------|
| `GET` | `/_studio/api/chat/threads` |
| `POST` | `/_studio/api/chat/sessions` |
| `POST` | `/_studio/api/chat/threads/{thread_id}/messages` |

> **Tip:** For chat to work, the agent item's `run` method must accept a single message
> argument (like the scaffold's `ExampleAgent.run(input, context=None)`). Studio's runtime
> routes prefer agents whose `run` has at most one required parameter. Agent **runtimes**
> registered as `agent/basic` and `agent/pydantic-ai` are intentionally skipped because
> their `run` needs a definition and tool list.

## Context: tenants, projects, environments

Studio models "where am I operating" as a three-level context. It is loaded from
`[tool.machine-core.studio]` in `pyproject.toml`:

```toml
[tool.machine-core.studio]
active_tenant = "tenant-default"
active_project = "project-my-project"
active_environment = "env-dev"

[[tool.machine-core.studio.tenants]]
id = "tenant-default"
slug = "default"
name = "Default"

[[tool.machine-core.studio.projects]]
id = "project-my-project"
tenant_id = "tenant-default"
slug = "my-project"
name = "my-project"
entry = "src.main:machine"

[[tool.machine-core.studio.environments]]
id = "env-dev"
project_id = "project-my-project"
name = "dev"
connection_kind = "local"
connection_ref = "src.main:machine"
status = "healthy"
```

The catalog resolves to dataclasses: `StudioTenant`, `StudioProject`, `StudioEnvironment`,
`StudioContext`, and `RuntimeAttachment` (`attached`, `attaching`, `failed`, `detached`).

### Switching context

| Method | Path | Body |
|--------|------|------|
| `GET` | `/_studio/api/context` | Current context. |
| `GET` | `/_studio/api/tenants` | List tenants. |
| `GET` | `/_studio/api/tenants/{tenant_slug}/projects` | Projects in a tenant. |
| `GET` | `/_studio/api/projects/{project_slug}/environments` | Environments in a project. |
| `PUT` | `/_studio/api/context` | `{"tenant_slug", "project_slug", "environment_name"}` |

```bash
curl -s -X PUT http://127.0.0.1:3177/_studio/api/context \
  -H 'content-type: application/json' \
  -d '{"tenant_slug":"default","project_slug":"my-project","environment_name":"dev"}'
```

This is how Studio scales from one project to many without changing the underlying system.

## Domains

Each domain page renders live control-plane data from a JSON endpoint:

| Domain | Categories | Endpoint |
|--------|-----------|----------|
| Memory | `memory` | `/_studio/api/memory/threads` |
| RAG | `rag_pipeline`, `chunker`, `reranker`, `metadata_extractor` | `/_studio/api/rag/pipelines` |
| Evals | `scorer`, `dataset` | `/_studio/api/evals/runs` |
| Storage | `storage-backend` | `/_studio/api/storage/files` |
| Deploy | `deployer` | `/_studio/api/deploy/targets` |
| Observe | `observability_exporter` | `/_studio/api/observe/traces` |
| Auth | `auth_provider` | `/_studio/api/auth/keys` |
| Workspace | `sandbox`, `filesystem` | `/_studio/api/workspace/files` |
| Browser | `browser` | `/_studio/api/browser/sessions` |
| Voice | `voice_provider` | `/_studio/api/voice/voices` |
| PubSub | `pubsub` | `/_studio/api/pubsub/events` |

A domain page with no registered categories renders an empty state rather than an error.

## Tool tester

`/_studio/tools/{tool_name}` tests a registered tool. `/_studio/tools/{tool_name}/execute`
prefers, in order:

1. `tool.execute(body)` (if callable),
2. `tool.handler(**body)` (for `@tool`-defined `ToolDefinition`s),
3. `tool.filter(prompt, top_k)`.

This is why Studio can execute `@tool` tools even though the generic
`POST /api/tool/{name}/execute` route cannot (it only looks for `execute`).

## Registry browser

`/_studio/api/registry` and the `/_studio/registry` page browse the current machine's
categories and items, showing owners and serialized metadata (sensitive keys redacted).

## Next steps

- [HTTP API](http-api.md) — the runtime's own `/api` and `/gateway`.
- [Deployers](deployers.md) — the Deploy domain.
- [Cloud deployment](../deployment/cloud.md) — run Studio in the cloud.

---

**Source:** `framework/studio_support/`, `framework/cli_support/cli_support/commands/studio_cmd.py`.
