# Workflows

A **workflow** is a DAG of steps executed by an **execution engine**. `workflow_support`
defines both categories and ships step primitives, a fluent DAG builder, and a default
engine.

## The pieces

| Piece | What it is |
|-------|------------|
| `workflow` category | Holds workflow definitions; operations `start`, `runs`, `get_run`, `resume`. |
| `execution-engine` category | Executes a `Workflow`; `workflow_support` registers `default`. |
| `Step` / `@step` | A typed, validated unit of work. |
| `Workflow` | Fluent DAG builder: `then`, `parallel`, `branch`, `foreach`, `dowhile`, `dountil`, `sleep`, `suspend`. |
| `WorkflowRun` | The state of one execution, including per-step results. |
| `RunStore` / `JsonRunStore` | Persistence for runs. |

## Enable it

```toml
plugins = ["workflow_support", "..."]
```

`workflow_support` registers `execution-engine/default` and declares the `workflow` and
`execution-engine` categories.

## Define a step

`@step` needs input and output Pydantic schemas:

```python
from pydantic import BaseModel
from workflow_support.step import StepContext, step


class FetchInput(BaseModel):
    url: str


class FetchOutput(BaseModel):
    text: str


@step(name="fetch", input_schema=FetchInput, output_schema=FetchOutput)
async def fetch(ctx: StepContext) -> FetchOutput:
    # ctx.input_data is the validated input for this step
    return FetchOutput(text=f"fetched {ctx.input_data.url}")
```

`Step.execute` awaits your function and validates the return value against `output_schema`,
raising `TypeError` if it does not match. `StepContext` carries `input_data`, a mutable
`state` dict, `previous_output`, and the `machine`.

## Build a workflow

```python
from workflow_support.workflow import Workflow

workflow = (
    Workflow("etl")
    .then(fetch)
    .parallel([clean, enrich])
    .branch(lambda state: state.get("needs_review"), {True: review, False: publish})
    .foreach(items_step=fetch, body_step=process_one)
    .sleep(2.0)
)
```

| Builder | Node |
|---------|------|
| `.then(step)` | Sequential step. |
| `.parallel([steps])` | Run steps concurrently (`asyncio.gather`). |
| `.branch(condition, {value: step})` | Conditional branch. |
| `.foreach(items_step, body_step)` | Iterate over a produced list. |
| `.dowhile(condition, body)` / `.dountil(condition, body)` | Loops. |
| `.sleep(seconds)` | Wait. |
| `.suspend(message="")` | Pause for human input (resumable). |

## Execute it

The engine is registered as `execution-engine/default`:

```python
from src.main import machine
from pydantic import BaseModel

class EtlInput(BaseModel):
    source: str

engine = machine.resolve("execution-engine", "default")
run = await engine.execute(workflow, EtlInput(source="s3://bucket"))

print(run.status)                  # RunStatus.COMPLETED
print(run.output)
for step_result in run.step_results:
    print(step_result.step_name, step_result.status)
```

`DefaultExecutionEngine.execute(workflow, input_data, initial_state=None, run=None)`
walks the node list, threading each node's output into the next. It emits
`hooks/beforeWorkflowRun` and `hooks/afterWorkflowRun`, and on `suspend` records
`run.suspend_at(node_index, message)` and returns early.

## Runs and resumption

`WorkflowRun` tracks `current_node_index`, status, step results, and output. Resume by
passing the existing run back in:

```python
run = await engine.execute(workflow, EtlInput(source="..."), run=existing_run)
```

Persist runs with `JsonRunStore`:

```python
from workflow_support.persistence import JsonRunStore

store = JsonRunStore("./runs")
store.save(run)
loaded = store.load(run.run_id)
store.list_runs(workflow_name="etl")
```

| `RunStatus` | Meaning |
|-------------|---------|
| `PENDING` | Created, not started. |
| `RUNNING` | In progress. |
| `SUSPENDED` | Paused at a suspend node. |
| `COMPLETED` | Finished successfully. |
| `FAILED` | Raised during execution. |

## Reuse agents and workflows as steps

```python
from workflow_support.agent_step import agent_as_step
from workflow_support.nested import workflow_as_step

research = agent_as_step(agent, StartInput, ResearchOutput, name="research")
sub = workflow_as_step(other_workflow, name="sub")
```

`agent_as_step` supports two protocols: the `AgentRunner` protocol
(`run(definition, input, tools, context)`, with `agent_definition` in `ctx.state`) and a
simple `run(input_data)` protocol.

## External engines

`workflow_support.adapters` ships adapters for external orchestrators:

- `InngestAdapter(base_url="http://localhost:8288")`
- `TemporalAdapter(...)`

Both implement `ExternalEngineAdapter` with `register_workflow`, `build_function_config`, and
`trigger`.

## HTTP routes

The `workflow` category declares:

```
POST /api/workflow/{name}/start
GET  /api/workflow/{name}/runs
GET  /api/workflow/{name}/runs/{run_id}
POST /api/workflow/{name}/runs/{run_id}/resume
```

> **Note:** `Workflow` itself is a DAG **description**; it has no `start`/`runs`/`get_run`
> methods. To expose a workflow over HTTP, register an item under `workflow` that provides
> those methods (typically a thin wrapper around `DefaultExecutionEngine.execute` plus a
> `JsonRunStore`). The generated routes call whatever you registered, so the wrapper is the
> contract — the server test suite uses a mock with exactly those four methods.

A minimal wrapper:

```python
class WorkflowService:
    description = "ETL workflow"

    def __init__(self, engine, workflow, store):
        self._engine = engine
        self._workflow = workflow
        self._store = store

    async def start(self, **kwargs):
        run = await self._engine.execute(self._workflow, InputModel(**kwargs))
        self._store.save(run)
        return run

    async def runs(self):
        return self._store.list_runs(self._workflow.name)

    async def get_run(self, run_id: str):
        return self._store.load(run_id)

    async def resume(self, run_id: str, **kwargs):
        run = self._store.load(run_id)
        return await self._engine.execute(self._workflow, InputModel(), run=run)


machine.register("workflow", "etl", WorkflowService(engine, workflow, store))
```

## Hooks

`workflow_support` declares `hooks/collectWorkflows`, `hooks/beforeWorkflowRun`
(`firstresult`), and `hooks/afterWorkflowRun` (`firstresult`).

---

**Read next:** [Evals](evals.md) · [HTTP API](http-api.md) ·
[Build a tool-using agent](build-a-tool-using-agent.md)

**Source:** `framework/workflow_support/`.
