# agent_runtime_pydantic

Pydantic-AI based runtime for Machine agents.

## Provides

- the `agent/pydantic-ai` runtime
- conversion from Machine tool definitions to pydantic-ai tools
- normalization of pydantic-ai outputs back into Machine agent result models

## Key Files

- `manifest.json`
- `__init__.py`
- `runtime.py`
- `converters.py`

## Role

This runtime integrates Machine agent definitions with the pydantic-ai execution model while preserving the shared Machine result schema.
