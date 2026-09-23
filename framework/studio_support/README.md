# studio_support

Framework support package for the Machine Studio web UI.

## Provides

- a Studio FastAPI sub-application that serves a SvelteKit SPA at `/_studio/app`
- a JSON control-plane API at `/_studio/api`
- Zitadel OIDC authentication with a signed, HttpOnly session cookie
- project, tenant, and environment context loading from `pyproject.toml`
- runtime attachment helpers for local and remote runtimes

## Architecture

The UI is a Svelte 5 + Tailwind v4 + shadcn-svelte single-page app under `studio_support/web`.
`build/` is committed so a git install can serve the SPA without a Node toolchain. Legacy
server-rendered URLs redirect into the SPA (see `routes/legacy.py`).

## Key Files

- `manifest.json`
- `studio_support/app.py` — host app, SPA mount, router wiring
- `studio_support/oidc.py`, `studio_support/session.py` — Zitadel OIDC + session cookies
- `studio_support/routes/auth.py` — login/callback/me/logout
- `studio_support/routes/legacy.py` — legacy URL redirects
- `studio_support/ui.py` — machine/context snapshot for the API
- `studio_support/web/` — the SvelteKit SPA
- `studio_support/context_catalog.py`, `studio_support/context_models.py`
- `studio_support/runtime_client.py`, `studio_support/runtime_access.py`
