"""Tests for the dynamic route generator."""

import pytest


class TestListAndGet:
    """Every category gets list + get routes automatically."""

    def test_list_agents(self, test_client):
        resp = test_client.get("/api/agent")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = [item["name"] for item in data]
        assert "chat" in names
        assert "coder" in names

    def test_get_agent(self, test_client):
        resp = test_client.get("/api/agent/chat")
        assert resp.status_code == 200
        assert resp.json()["name"] == "chat"

    def test_get_agent_not_found(self, test_client):
        resp = test_client.get("/api/agent/nonexistent")
        assert resp.status_code == 404

    def test_list_tools(self, test_client):
        resp = test_client.get("/api/tool")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_workflows(self, test_client):
        resp = test_client.get("/api/workflow")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_memory(self, test_client):
        resp = test_client.get("/api/memory")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestAgentOperations:
    """Agent category operations: run, stream, generate."""

    def test_run_agent(self, test_client):
        resp = test_client.post("/api/agent/chat/run", json={"prompt": "Hello"})
        assert resp.status_code == 200
        data = resp.json()
        assert "output" in data or "result" in data

    def test_stream_agent(self, test_client):
        resp = test_client.post("/api/agent/chat/stream", json={"prompt": "Hi"})
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    def test_run_agent_not_found(self, test_client):
        resp = test_client.post("/api/agent/missing/run", json={"prompt": "Hello"})
        assert resp.status_code == 404


class TestToolOperations:
    """Tool category operations: execute."""

    def test_execute_tool(self, test_client):
        resp = test_client.post("/api/tool/web_search/execute", json={"query": "test"})
        assert resp.status_code == 200

    def test_execute_tool_not_found(self, test_client):
        resp = test_client.post("/api/tool/missing/execute", json={})
        assert resp.status_code == 404


class TestWorkflowOperations:
    """Workflow operations: start, runs, get_run, resume."""

    def test_start_workflow(self, test_client):
        resp = test_client.post("/api/workflow/data_pipeline/start", json={"x": 1})
        assert resp.status_code == 200
        assert "run_id" in resp.json()

    def test_list_workflow_runs(self, test_client):
        resp = test_client.get("/api/workflow/data_pipeline/runs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_workflow_run(self, test_client):
        resp = test_client.get("/api/workflow/data_pipeline/runs/run-001")
        assert resp.status_code == 200

    def test_resume_workflow(self, test_client):
        resp = test_client.post(
            "/api/workflow/data_pipeline/runs/run-001/resume", json={"data": {}}
        )
        assert resp.status_code == 200

    def test_start_workflow_not_found(self, test_client):
        resp = test_client.post("/api/workflow/missing/start", json={})
        assert resp.status_code == 404


class TestMemoryOperations:
    """Memory operations — note: uses /{name}/ pattern now."""

    def test_create_thread(self, test_client):
        resp = test_client.post(
            "/api/memory/manager/threads", json={"metadata": {"test": True}}
        )
        assert resp.status_code == 200
        assert "id" in resp.json()

    def test_list_threads(self, test_client):
        resp = test_client.get("/api/memory/manager/threads")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_thread(self, test_client):
        resp = test_client.get("/api/memory/manager/threads/thread-1")
        assert resp.status_code == 200

    def test_add_message(self, test_client):
        resp = test_client.post(
            "/api/memory/manager/threads/thread-1/messages",
            json={"role": "user", "content": "Hello"},
        )
        assert resp.status_code == 200

    def test_delete_thread(self, test_client):
        resp = test_client.delete("/api/memory/manager/threads/thread-1")
        assert resp.status_code == 204

    def test_memory_item_not_found(self, test_client):
        resp = test_client.get("/api/memory/nonexistent/threads")
        assert resp.status_code == 404


class TestHealthIncludesAllCategories:
    """Health endpoint lists all categories dynamically."""

    def test_health_lists_categories(self, test_client):
        resp = test_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "categories" in data
        assert "agent" in data["categories"]
        assert data["categories"]["agent"] == 2
