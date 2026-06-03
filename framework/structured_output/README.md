# structured_output

Framework plugin for schema-validated structured generation.

## Provides

- the `structured_output` registry category
- request and response schemas for object generation
- hooks for `before_generate_object`, `after_generate_object`, and validation retries

## Key Files

- `manifest.json`
- `structured_output/__init__.py`
- `structured_output/schemas.py`
- `structured_output/hooks.py`

## Role

This plugin defines the shared contract for asking a model-backed implementation to return validated structured objects.
