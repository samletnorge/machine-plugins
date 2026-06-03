# server_support

Framework support package for exposing a `Machine` runtime over HTTP.

## Provides

- a FastAPI app factory built around a `Machine` instance
- automatic route generation from registry categories and category operations
- SSE helpers for streaming responses
- a dynamic Python client generated from the runtime OpenAPI surface
- server lifecycle hook specs such as `beforeServerStart`, `afterServerStart`, `beforeRequest`, and `afterRequest`

## Key Files

- `manifest.json`
- `server_support/app.py`
- `server_support/route_generator.py`
- `server_support/client.py`
- `server_support/sse.py`
- `server_support/models.py`

## Role

This package is the bridge from registry-driven runtime composition to HTTP APIs and web-facing execution.
