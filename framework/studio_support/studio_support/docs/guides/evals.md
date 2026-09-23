# Evals

Evaluation support lives in the external **`eval_support`** plugin and a small CLI command.
This page covers the dataset format the CLI understands and how evaluation plugs into the
rest of the system.

## Enable it

`eval_support` is an **external** plugin (its own repository), listed in `registry.json`:

```toml
plugins = ["eval_support", "..."]
```

```toml
[tool.uv.sources]
eval_support = { git = "git+ssh://git@github.com/samletnorge/machine-plugin-eval-support.git" }
```

Once loaded, the plugin contributes the `scorer` and `dataset` categories (the Studio
dashboard groups them under its **Evals** domain).

## The CLI command

```bash
machine eval run path/to/dataset.json
```

The command:

1. finds the project root,
2. resolves the dataset path (relative paths are resolved against the current directory),
3. parses it as JSON,
4. reads `name` (defaulting to the filename stem) and `samples`,
5. prints a summary.

Dataset shape:

```json
{
  "name": "support-quality",
  "samples": [
    { "input": "How do I reset my password?", "expected": "Use the reset link." },
    { "input": "What are your hours?", "expected": "9-5 on weekdays." }
  ]
}
```

Run it:

```bash
machine eval run datasets/support-quality.json
# Running evaluation: support-quality
#   Dataset: /path/to/datasets/support-quality.json
#   Samples: 2
# ✓ Evaluation complete
```

> **Note:** In the current `cli_support`, `machine eval run` is a **stub** — it validates and
> summarizes the dataset but does not execute scorers or produce metrics. The `eval_support`
> plugin provides the category contracts and runners; wire those into your project (or wait
> for the CLI to call them) for actual scoring.

## Using scorers from a project

Because categories are ordinary registries, you can resolve and run scorers yourself once
`eval_support` is loaded:

```python
@machine.when_ready
async def _run_eval():
    scorers = machine.list_category("scorer")
    # resolve a scorer and apply it to model/agent outputs
```

Consult the `eval_support` repository for the exact `Scorer` and `Dataset` interfaces, since
that plugin is versioned independently of this kernel.

## HTTP

The Studio control plane exposes evaluation data under its **Evals** domain. See
[Studio](studio.md#domains) for the domain endpoints.

## Tips

- Keep datasets in version control under `datasets/`.
- Give every dataset a stable `name` so runs are comparable.
- Score both `output` and `usage` (tokens/cost) — `observability_support` helps here.

---

**Read next:** [Studio](studio.md) · [HTTP API](http-api.md)

**Source:** `framework/cli_support/cli_support/commands/eval_cmd.py`, `registry.json`
(`eval_support`), `framework/studio_support/studio_support/routes/dashboard.py`.
