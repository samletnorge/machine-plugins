import pytest
from datetime import datetime, timezone

from workflow_support.run import WorkflowRun, RunStatus, StepResult


class TestRunStatus:
    def test_status_values(self):
        assert RunStatus.PENDING == "pending"
        assert RunStatus.RUNNING == "running"
        assert RunStatus.COMPLETED == "completed"
        assert RunStatus.FAILED == "failed"
        assert RunStatus.SUSPENDED == "suspended"


class TestStepResult:
    def test_create_step_result(self):
        sr = StepResult(
            step_name="fetch",
            status="completed",
            output={"data": [1, 2, 3]},
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        assert sr.step_name == "fetch"
        assert sr.output == {"data": [1, 2, 3]}

    def test_step_result_duration(self):
        start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 1, 1, 0, 0, 5, tzinfo=timezone.utc)
        sr = StepResult(
            step_name="x",
            status="completed",
            output=None,
            started_at=start,
            completed_at=end,
        )
        assert sr.duration_seconds == 5.0

    def test_step_result_duration_none_when_incomplete(self):
        sr = StepResult(
            step_name="x",
            status="running",
            output=None,
            started_at=datetime.now(timezone.utc),
        )
        assert sr.duration_seconds is None


class TestWorkflowRun:
    def test_create_run(self):
        run = WorkflowRun(workflow_name="test-wf")
        assert run.workflow_name == "test-wf"
        assert run.status == RunStatus.PENDING
        assert run.run_id is not None
        assert len(run.step_results) == 0

    def test_run_has_unique_id(self):
        r1 = WorkflowRun(workflow_name="wf")
        r2 = WorkflowRun(workflow_name="wf")
        assert r1.run_id != r2.run_id

    def test_start_run(self):
        run = WorkflowRun(workflow_name="wf")
        run.start()
        assert run.status == RunStatus.RUNNING
        assert run.started_at is not None

    def test_complete_run(self):
        run = WorkflowRun(workflow_name="wf")
        run.start()
        run.complete(output={"final": 42})
        assert run.status == RunStatus.COMPLETED
        assert run.completed_at is not None
        assert run.output == {"final": 42}

    def test_fail_run(self):
        run = WorkflowRun(workflow_name="wf")
        run.start()
        run.fail(error="boom")
        assert run.status == RunStatus.FAILED
        assert run.error == "boom"

    def test_suspend_run(self):
        run = WorkflowRun(workflow_name="wf")
        run.start()
        run.suspend_at(node_index=2, message="Need approval")
        assert run.status == RunStatus.SUSPENDED
        assert run.suspended_at_node == 2
        assert run.suspend_message == "Need approval"

    def test_resume_run(self):
        run = WorkflowRun(workflow_name="wf")
        run.start()
        run.suspend_at(node_index=2, message="Need approval")
        run.resume(resume_data={"approved": True})
        assert run.status == RunStatus.RUNNING
        assert run.resume_data == {"approved": True}

    def test_record_step_result(self):
        run = WorkflowRun(workflow_name="wf")
        run.start()
        sr = StepResult(
            step_name="s1",
            status="completed",
            output={"x": 1},
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        run.record_step(sr)
        assert len(run.step_results) == 1
        assert run.step_results[0].step_name == "s1"

    def test_get_state_at_step(self):
        run = WorkflowRun(workflow_name="wf")
        run.start()
        for i in range(3):
            sr = StepResult(
                step_name=f"s{i}",
                status="completed",
                output={"val": i},
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
            run.record_step(sr)
        history = run.state_at_step(1)
        assert len(history) == 2
        assert history[-1].output == {"val": 1}

    def test_to_dict_serializable(self):
        run = WorkflowRun(workflow_name="wf")
        d = run.to_dict()
        assert d["workflow_name"] == "wf"
        assert "run_id" in d
        assert "status" in d
