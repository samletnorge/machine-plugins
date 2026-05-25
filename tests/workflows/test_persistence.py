"""Task 9: JsonRunStore persistence tests."""

import json
import pytest
from pathlib import Path
from datetime import datetime, timezone

from workflow_support.run import WorkflowRun, RunStatus, StepResult
from workflow_support.persistence import JsonRunStore


class TestJsonRunStore:
    def test_save_and_load_run(self, tmp_path: Path):
        store = JsonRunStore(directory=tmp_path)
        run = WorkflowRun(workflow_name="test-wf")
        run.start()
        run.record_step(
            StepResult(
                step_name="s1",
                status="completed",
                output={"x": 1},
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
        )
        run.complete(output={"final": 42})

        store.save(run)
        loaded = store.load(run.run_id)

        assert loaded.workflow_name == "test-wf"
        assert loaded.run_id == run.run_id
        assert loaded.status == RunStatus.COMPLETED
        assert len(loaded.step_results) == 1
        assert loaded.step_results[0].step_name == "s1"

    def test_load_nonexistent_returns_none(self, tmp_path: Path):
        store = JsonRunStore(directory=tmp_path)
        assert store.load("nonexistent") is None

    def test_list_runs(self, tmp_path: Path):
        store = JsonRunStore(directory=tmp_path)
        for i in range(3):
            run = WorkflowRun(workflow_name=f"wf-{i}")
            store.save(run)

        runs = store.list_runs()
        assert len(runs) == 3

    def test_list_runs_by_workflow(self, tmp_path: Path):
        store = JsonRunStore(directory=tmp_path)
        for i in range(3):
            store.save(WorkflowRun(workflow_name="alpha"))
        store.save(WorkflowRun(workflow_name="beta"))

        alpha_runs = store.list_runs(workflow_name="alpha")
        assert len(alpha_runs) == 3

    def test_delete_run(self, tmp_path: Path):
        store = JsonRunStore(directory=tmp_path)
        run = WorkflowRun(workflow_name="wf")
        store.save(run)
        assert store.load(run.run_id) is not None
        store.delete(run.run_id)
        assert store.load(run.run_id) is None

    def test_save_overwrites_existing(self, tmp_path: Path):
        store = JsonRunStore(directory=tmp_path)
        run = WorkflowRun(workflow_name="wf")
        store.save(run)

        run.start()
        run.complete(output={"done": True})
        store.save(run)

        loaded = store.load(run.run_id)
        assert loaded.status == RunStatus.COMPLETED
