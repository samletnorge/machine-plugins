# agent_support

Framework plugin that defines the `agent` category for Machine.

## Provides

- the `agent` registry category
- standard agent operations: `run`, `stream`, `generate`
- shared schemas such as `AgentDefinition`, `AgentStep`, `AgentRunResult`, and `HandoffRequest`
- agent lifecycle hooks including `before_agent_run`, `after_agent_run`, `on_agent_step`, `on_agent_handoff`, and `on_agent_error`

## Key Files

- `manifest.json`
- `agent_support/__init__.py`
- `agent_support/schemas.py`
- `agent_support/hooks.py`

## Role

This plugin defines the shared contract that agent runtimes and agent-producing plugins build on top of.
