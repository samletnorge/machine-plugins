# observability_support

Tracing and observability helpers for Machine runtimes.

## Provides

- the `observability_exporter` category
- tracing helpers and tracer wrappers
- decorator-based instrumentation helpers
- token and cost tracking helpers
- exporter integrations for console, OTLP, Langfuse, LangSmith, Datadog, Jaeger, and Sentry

## Key Files

- `manifest.json`
- `__init__.py`
- `tracer.py`
- `decorator.py`
- `cost.py`
- `config.py`

## Role

This plugin adds a reusable observability layer around Machine agents, tools, and model execution.
