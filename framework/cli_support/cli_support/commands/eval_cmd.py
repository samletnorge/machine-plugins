"""machine eval — run evaluations."""

from __future__ import annotations

import asyncio
import importlib.util
import inspect
import json
from pathlib import Path
from typing import Any, Awaitable, Callable

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from cli_support.utils import find_project_root, load_machine_config, load_machine_instance

console = Console()

eval_app = typer.Typer(name="eval", help="Run evaluations.")


def _fail(message: str) -> None:
    """Print an eval failure and exit non-zero."""
    console.print(f"[red]✗ Eval error: {escape(str(message))}[/red]")
    raise typer.Exit(code=1)


def _require_eval_support() -> None:
    if importlib.util.find_spec("eval_support") is None:
        _fail(
            "eval_support is not installed. Add it to your project with "
            "'uv add eval_support' (or 'machine plugin install eval_support') "
            "and re-run."
        )


def _load_dataset(dataset_path: Path):
    """Load a dataset using the real eval_support Dataset API."""
    from eval_support.dataset import Dataset, EvalSample

    try:
        raw = json.loads(dataset_path.read_text())
    except json.JSONDecodeError as e:
        _fail(f"dataset {dataset_path} is not valid JSON: {e}")

    if isinstance(raw, list):
        return Dataset.from_json(dataset_path)

    if isinstance(raw, dict) and "samples" in raw:
        samples = []
        for item in raw["samples"]:
            if not isinstance(item, dict):
                _fail(
                    "each dataset sample must be an object, "
                    f"got {type(item).__name__}"
                )
            normalized = dict(item)
            if "expected" in normalized and "expected_output" not in normalized:
                normalized["expected_output"] = normalized.pop("expected")
            samples.append(EvalSample(**normalized))
        return Dataset(name=raw.get("name", dataset_path.stem), samples=samples)

    _fail(
        "dataset JSON must be a list of samples or an object with a "
        "'samples' list."
    )


def _resolve_scorers(machine: Any, requested: list[str] | None) -> list[Any]:
    """Resolve scorer instances from the Machine 'scorer' category."""
    available = machine.list_category("scorer")
    if not available:
        _fail(
            "no scorers are configured. Declare 'eval_support' in "
            "[tool.machine-core].plugins and configure its 'judge_llm' plugin "
            "config (e.g. provider = \"ollama\"), then re-run 'machine eval run'."
        )

    if requested:
        unknown = [name for name in requested if name not in available]
        if unknown:
            _fail(
                "unknown scorer(s): "
                + ", ".join(unknown)
                + ". Available: "
                + ", ".join(sorted(available))
            )
        return [available[name] for name in requested]

    return list(available.values())


def _is_agent_runtime(obj: Any) -> bool:
    """Runtimes expose capability flags and take an AgentDefinition in run()."""
    if hasattr(obj, "supports_streaming") or hasattr(obj, "supports_tools"):
        return True
    run = getattr(obj, "run", None)
    if not callable(run):
        return True
    try:
        params = inspect.signature(run).parameters
    except (TypeError, ValueError):  # pragma: no cover - exotic callables
        return False
    return "definition" in params


def _make_agent_fn(agent: Any) -> Callable[[str], Awaitable[str]]:
    """Adapt a registered agent's run() into the ExperimentRunner agent_fn."""
    run = agent.run
    try:
        params = inspect.signature(run).parameters
    except (TypeError, ValueError):  # pragma: no cover - exotic callables
        params = {}
    accepts_context = "context" in params or any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
    )

    async def agent_fn(prompt: str) -> str:
        result = run(prompt, None) if accepts_context else run(prompt)
        if inspect.isawaitable(result):
            result = await result
        if isinstance(result, str):
            return result
        output = getattr(result, "output", result)
        return "" if output is None else str(output)

    return agent_fn


def _resolve_agent(machine: Any, agent_name: str | None):
    """Resolve a user agent (not a runtime) from the 'agent' category."""
    agents = machine.list_category("agent")
    candidates = {
        name: agent
        for name, agent in agents.items()
        if not _is_agent_runtime(agent)
    }

    if agent_name:
        agent = agents.get(agent_name)
        if agent is None:
            _fail(
                f"agent '{agent_name}' is not registered. Available: "
                + (", ".join(sorted(agents)) or "(none)")
            )
        if _is_agent_runtime(agent):
            _fail(f"'{agent_name}' is an agent runtime, not a runnable agent.")
        return agent_name, _make_agent_fn(agent)

    if not candidates:
        _fail(
            "no runnable agent is registered on the Machine. Register an agent "
            "(see the 'ExampleAgent' scaffold) or pass --agent NAME."
        )

    name, agent = next(iter(candidates.items()))
    return name, _make_agent_fn(agent)


def _shorten(value: str, limit: int = 48) -> str:
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


@eval_app.command("run")
def eval_run(
    dataset: str = typer.Argument(..., help="Path to dataset JSON file."),
    scorer: list[str] | None = typer.Option(
        None,
        "--scorer",
        "-s",
        help="Scorer name to run (repeatable). Defaults to all registered scorers.",
    ),
    agent: str | None = typer.Option(
        None,
        "--agent",
        "-a",
        help="Agent to evaluate. Defaults to the first registered agent.",
    ),
):
    """Run evaluations against a dataset."""
    root = find_project_root()
    if root is None:
        console.print("[red]Error: Not inside a machine-core project.[/red]")
        raise typer.Exit(code=1)

    dataset_path = Path(dataset)
    if not dataset_path.is_absolute():
        dataset_path = Path.cwd() / dataset_path

    if not dataset_path.exists():
        console.print(f"[red]Dataset file not found: {dataset_path}[/red]")
        raise typer.Exit(code=1)

    _require_eval_support()

    config = load_machine_config(root)
    entry = config.get("entry", "src.main:machine")

    console.print("[bold]Loading project machine...[/bold]")
    machine = load_machine_instance(root)

    async def _main():
        await machine.start()
        try:
            dataset_obj = _load_dataset(dataset_path)
            scorer_objs = _resolve_scorers(machine, scorer)
            agent_label, agent_fn = _resolve_agent(machine, agent)

            from eval_support.experiment import ExperimentRunner

            console.print(f"[bold]Running evaluation: {dataset_obj.name}[/bold]")
            console.print(f"  Dataset: {dataset_path}")
            console.print(f"  Entry: {entry}")
            console.print(f"  Samples: {len(dataset_obj)}")
            console.print(f"  Agent: {agent_label}")
            console.print(
                "  Scorers: "
                + ", ".join(getattr(s, "name", str(s)) for s in scorer_objs)
            )

            runner = ExperimentRunner(agent_fn=agent_fn, scorers=scorer_objs)
            return await runner.run(dataset_obj)
        finally:
            await machine.shutdown()

    try:
        result = asyncio.run(_main())
    except typer.Exit:
        raise
    except Exception as e:  # noqa: BLE001 - surface a clear CLI error
        _fail(f"evaluation failed: {type(e).__name__}: {e}")

    scorer_names = sorted(result.aggregate_scores)

    table = Table(title=f"Evaluation: {result.dataset_name}")
    table.add_column("#", justify="right")
    table.add_column("Input")
    table.add_column("Output")
    for name in scorer_names:
        table.add_column(name, justify="right")

    for index, sample in enumerate(result.sample_results, start=1):
        scores = {s.scorer: f"{s.score:.3f}" for s in sample.scores}
        output = sample.output if sample.output is not None else ""
        if sample.error:
            output = f"[error] {sample.error}"
        table.add_row(
            str(index),
            _shorten(sample.input),
            _shorten(output),
            *[scores.get(name, "-") for name in scorer_names],
        )

    console.print(table)

    console.print("[bold]Aggregate scores[/bold]")
    for name in scorer_names:
        console.print(f"  {name}: {result.aggregate_scores[name]:.3f}")

    if any(sample.error for sample in result.sample_results):
        console.print("[yellow]⚠ Some samples errored (see output column).[/yellow]")

    console.print("[green]✓ Evaluation complete[/green]")
