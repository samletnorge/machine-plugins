# tool_openapi

OpenAPI-to-tool generator for Machine.

## Provides

- an internal tool-registry utility named `tool/__openapi_generator__`
- helpers for converting OpenAPI operations into executable `ToolDefinition` objects
- generated `httpx`-backed handlers for API calls

## Key Files

- `manifest.json`
- `__init__.py`
- `generator.py`

## Role

This plugin turns OpenAPI specs into Machine tools so other plugins and projects can synthesize live API integrations at runtime.
