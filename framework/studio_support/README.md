# studio_support

Framework support package for the Machine Studio web UI.

## Provides

- a Studio FastAPI sub-application
- project, tenant, and environment context loading from `pyproject.toml`
- runtime attachment helpers for local and remote runtimes
- shared UI helpers and routes for browsing runtime state and interacting with a Machine app

## Key Files

- `manifest.json`
- `studio_support/app.py`
- `studio_support/ui.py`
- `studio_support/context_catalog.py`
- `studio_support/context_models.py`
- `studio_support/runtime_client.py`
- `studio_support/runtime_access.py`

## Role

This package is the main Studio layer for browsing and operating Machine runtimes from a web UI.
