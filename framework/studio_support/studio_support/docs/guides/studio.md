# Studio

Studio is the control plane for a machine-core runtime: a web UI for browsing the registry,
inspecting agents, tools and workflows, switching between projects and environments, and
inspecting domain data (memory, RAG, evals, storage, deploy, observe, auth, workspace,
browser, voice, pubsub).

The UI is a **SvelteKit single-page app** (Svelte 5 + Tailwind v4 + shadcn-svelte) served at
`/_studio/app`. The FastAPI sub-application serves the SPA build and the JSON API, and owns
the Zitadel OIDC login flow.

## Launch it

```bash
machine studio                              # http://127.0.0.1:3177/_studio/app/
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
| `/_studio/app/...` | The Studio SPA (all UI routes). |
| `/_studio/api/...` | Control-plane JSON endpoints. |
| `/_studio/auth/...` | Zitadel OIDC login, callback, session and logout. |
| `/health` | `{"status": "healthy", "studio_mount": "/_studio"}` |

The host app starts the machine in its lifespan (if it has not been started), so plugins and
`when_ready` callbacks run before any request is served.

## Studio routes

| Path | Purpose |
|------|---------|
| `/_studio/app/` | Overview dashboard. |
| `/_studio/app/registry` | Registry browser. |
| `/_studio/app/store` | Plugin store (install into the project). |
| `/_studio/app/services` | Control-plane endpoints and service actions. |
| `/_studio/app/runtime` | Agents, tools and workflows. |
| `/_studio/app/domain/{key}` | A domain page (`memory`, `rag`, `evals`, `storage`, `deploy`, `observe`, `auth`, `workspace`, `browser`, `voice`, `pubsub`). |
| `/_studio/app/context` | Tenant / project / environment switcher. |
| `/_studio/app/config` | Configuration view. |
| `/_studio/tools/{tool_name}/execute` | Execute a tool (handler-aware). |

The legacy server-rendered URLs (`/_studio/`, `/_studio/registry`, `/_studio/chat`, ...)
permanently redirect to their SPA equivalents, so old links keep working.

## Authentication

Studio delegates sign-in to **Zitadel** (OIDC authorization-code flow, confidential client).
The backend performs the token exchange and stores an HttpOnly session cookie; the SPA never
sees tokens. Configure via environment:

| Variable | Purpose |
|----------|---------|
| `ZITADEL_ISSUER` | Issuer URL (default `https://zitadel.samletnorge.no`). |
| `ZITADEL_CLIENT_ID` / `ZITADEL_CLIENT_SECRET` | Web app credentials. |
| `ZITADEL_REDIRECT_URI` | Must match the registered callback (`/_studio/auth/callback`). |
| `ZITADEL_PROJECT_ID` | Optional; adds the audience scope so project roles resolve. |
| `SESSION_SECRET` | HMAC key for the signed session cookie. |

`GET /_studio/auth/login` starts the flow, `/_studio/auth/callback` completes it,
`GET /_studio/auth/me` returns the signed-in user and roles, and `/_studio/auth/logout` ends
the session.

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
The sidebar tenant switcher and the Context page both use the endpoints below.

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

## Overview

`GET /_studio/api/overview` returns the full machine/context snapshot the SPA dashboard uses:
machine and context names, category counts, plugin manifests, project targets, and the
registered agents, tools and workflows.

## Plugin store

The store installs plugins **into the project** (not just the machine data dir):

1. resolves the plugin from the registry (`registry.json`),
2. runs `uv add "<package> @ <git url>#subdirectory=<path>"`,
3. declares the name in `[tool.machine-core].plugins`,
4. syncs the plugin's bundled manifest so the runtime loads it on restart.

Use it from the CLI or the Studio:

```bash
machine plugin available          # list the registry
machine plugin search brreg       # search
machine plugin add auth_support   # install + declare in this project
machine plugin list               # declared vs installed
machine plugin remove auth_support
```

| Method | Path | Body |
|--------|------|------|
| `GET` | `/_studio/api/store` | Catalog with `declared`/`installed` status. |
| `POST` | `/_studio/api/store/install` | `{"name": "...", "dev": false}` |
| `POST` | `/_studio/api/store/uninstall` | `{"name": "..."}` |

Installed plugins are discovered from their wheel's bundled `manifest.json`
(via `importlib.metadata`), so a plain `uv add` plus a declaration is enough —
no manual copying.

## Domains

Each domain page renders live control-plane data from a JSON endpoint:

| Domain | Endpoint |
|--------|----------|
| Memory | `/_studio/api/memory/threads` |
| RAG | `/_studio/api/rag/pipelines` |
| Evals | `/_studio/api/evals/runs` |
| Storage | `/_studio/api/storage/files` |
| Deploy | `/_studio/api/deploy/targets` |
| Observe | `/_studio/api/observe/traces` |
| Auth | `/_studio/api/auth/keys` |
| Workspace | `/_studio/api/workspace/files` |
| Browser | `/_studio/api/browser/sessions` |
| Voice | `/_studio/api/voice/voices` |
| PubSub | `/_studio/api/pubsub/events` |

A domain page with no registered categories renders an empty state rather than an error.

## Tool execution

`POST /_studio/tools/{tool_name}/execute` runs a registered tool, preferring, in order:

1. `tool.execute(body)` (if callable),
2. `tool.handler(**body)` (for `@tool`-defined `ToolDefinition`s),
3. `tool.filter(prompt, top_k)`.

This is why Studio can execute `@tool` tools even though the generic
`POST /api/tool/{name}/execute` route cannot (it only looks for `execute`).

## Registry browser

`/_studio/api/registry/plugins` returns the installed plugin manifests, and
`/_studio/api/registry/plugins/{name}` returns one. The SPA's Registry page groups them by
name prefix and supports search and filtering.

## Developing the SPA

```bash
cd framework/studio_support/studio_support/web
pnpm install
pnpm run dev      # SvelteKit dev server
pnpm run check    # svelte-check
pnpm run build    # writes ./build, committed so git installs can serve it
```

## Next steps

- [HTTP API](http-api.md) — the runtime's own `/api` and `/gateway`.

---

**Source:** `framework/studio_support/`, `framework/cli_support/cli_support/commands/studio_cmd.py`.
