# AGENTS.md — machine-plugins

Plugin catalog for the [machine-core](../machine-core) kernel: `framework/` (category
definitions and contracts) and `community/` (implementations). Each plugin is a package
with a `manifest.json`; the repo root is a `uv` workspace.

## Layout

- `framework/<plugin>/` and `community/<plugin>/` — one package per plugin, `manifest.json`
  shipped inside the package (hatch `force-include`).
- `registry.json` — plugin catalog used by `machine plugin install`.
- `tests/` — workspace test suite (`uv run pytest tests`).
- `.agents/skills/` — agent skills (shadcn-svelte, GSAP). See
  `../machine-core/docs/frontend/README.md`.

## Commands

```bash
uv sync --all-packages          # install every workspace member
uv run pytest tests -q          # run the suite
uvx ruff check framework community tests
```

## Frontend (Machine Studio)

`framework/studio_support/` is migrating to a **SvelteKit + Tailwind v4 + shadcn-svelte**
app (static build served by FastAPI). Use shadcn-svelte components first, charts
(LayerChart) over bare numbers, and the conventions in
`../machine-core/docs/frontend/README.md`. The `shadcn-svelte` skill (in `.agents/skills`)
activates on any project with a `components.json`.

## Conventions

- Python 3.12+, full type hints, `loguru`, ruff (line length 100, correctness rules).
- No stubs: implement or delete; remove dead code.
- Tests live under `tests/`; keep the suite green and add coverage for new behaviour.
