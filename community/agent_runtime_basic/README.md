# agent_runtime_basic

Lightweight agent runtime with a manual model and tool loop.

## Provides

- the `agent/basic` runtime
- a custom model -> tool-call -> execute -> repeat loop
- standard `AgentRunResult` output compatible with `agent_support`

## Key Files

- `manifest.json`
- `__init__.py`
- `runtime.py`
- `messages.py`

## Role

This runtime avoids a dependency on pydantic-ai and serves as a simple reference runtime for Machine agents.
