# workflow_support

Framework plugin for workflow orchestration in Machine.

## Provides

- the `workflow` and `execution-engine` registry categories
- workflow operations such as `start`, `runs`, `get_run`, and `resume`
- typed workflow, step, run, and engine abstractions
- execution engines, persistence helpers, evented execution, and nested workflow support
- workflow lifecycle hooks such as `collectWorkflows`, `beforeWorkflowRun`, and `afterWorkflowRun`

## Key Files

- `manifest.json`
- `workflow_support/__init__.py`
- `workflow_support/workflow.py`
- `workflow_support/step.py`
- `workflow_support/engine.py`
- `workflow_support/run.py`
- `workflow_support/persistence.py`

## Role

This plugin defines the workflow vocabulary and execution primitives used to build higher-level orchestration behavior in Machine projects.
