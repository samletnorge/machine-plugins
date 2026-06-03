# tool_support

Framework plugin that defines the shared `tool` category.

## Provides

- the `tool` registry category
- the standard `execute` operation for registered tools
- shared models such as `ToolDefinition` and `ToolResult`
- tool lifecycle hooks including `before_tool_call`, `after_tool_call`, and `on_tool_error`
- a `@tool` decorator for deriving tool definitions from typed Python callables

## Key Files

- `manifest.json`
- `tool_support/__init__.py`
- `tool_support/schemas.py`
- `tool_support/hooks.py`
- `tool_support/decorator.py`

## Role

This plugin defines the common contract and convenience helpers used by tool-producing and tool-consuming parts of the ecosystem.
