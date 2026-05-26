"""Run persistence — serialize/deserialize WorkflowRun."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path

from workflow_support.run import WorkflowRun


class RunStore(ABC):
    """Abstract base for persisting workflow runs."""

    @abstractmethod
    def save(self, run: WorkflowRun) -> None: ...

    @abstractmethod
    def load(self, run_id: str) -> WorkflowRun | None: ...

    @abstractmethod
    def list_runs(self, workflow_name: str | None = None) -> list[WorkflowRun]: ...

    @abstractmethod
    def delete(self, run_id: str) -> None: ...


class JsonRunStore(RunStore):
    """File-based run persistence using JSON files."""

    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: str) -> Path:
        return self.directory / f"{run_id}.json"

    def save(self, run: WorkflowRun) -> None:
        data = run.to_dict()
        self._path(run.run_id).write_text(json.dumps(data, indent=2, default=str))

    def load(self, run_id: str) -> WorkflowRun | None:
        path = self._path(run_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return WorkflowRun.model_validate(data)

    def list_runs(self, workflow_name: str | None = None) -> list[WorkflowRun]:
        runs = []
        for path in self.directory.glob("*.json"):
            data = json.loads(path.read_text())
            run = WorkflowRun.model_validate(data)
            if workflow_name is None or run.workflow_name == workflow_name:
                runs.append(run)
        return runs

    def delete(self, run_id: str) -> None:
        path = self._path(run_id)
        if path.exists():
            path.unlink()
