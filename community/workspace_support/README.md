# workspace_support

Workspace, filesystem, sandbox, and skills support for Machine.

## Provides

- the `sandbox` and `filesystem` categories
- local and Docker-backed sandbox implementations
- a root-scoped local filesystem abstraction
- markdown-based skills discovery and loading
- an `AgentWorkspace` convenience wrapper that composes those pieces

## Key Files

- `manifest.json`
- `__init__.py`
- `workspace.py`
- `sandbox.py`
- `filesystem.py`
- `skills.py`

## Role

This plugin provides the execution and workspace primitives needed by coding and task-oriented agents.
