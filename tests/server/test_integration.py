"""Integration tests — full round-trip through every endpoint."""

import pytest


class TestFullRoundTrip:
    """Test a complete workflow through all endpoints."""

    def test_health_with_categories(self, test_client):
        """Health check reveals all categories dynamically."""
        resp = test_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["categories"]["agent"] == 2
        assert data["categories"]["tool"] == 2
        assert data["categories"]["workflow"] == 1
        assert data["categories"]["memory"] == 1

    def test_openapi_has_dynamic_paths(self, test_client):
        """OpenAPI spec includes dynamically generated routes."""
        resp = test_client.get("/openapi.json")
        paths = resp.json()["paths"]
        assert "/api/agent" in paths
        assert "/api/agent/{name}" in paths
        assert "/api/agent/{name}/run" in paths
        assert "/api/tool/{name}/execute" in paths
        assert "/api/workflow/{name}/start" in paths
        assert "/api/memory/{name}/threads" in paths

    def test_agent_run_and_stream(self, test_client):
        """Run agent synchronously and via stream."""
        resp = test_client.post("/api/agent/chat/run", json={"prompt": "Sync test"})
        assert resp.status_code == 200

        resp = test_client.post(
            "/api/agent/chat/stream", json={"prompt": "Stream test"}
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    def test_tool_execution(self, test_client):
        resp = test_client.post("/api/tool/web_search/execute", json={"query": "test"})
        assert resp.status_code == 200

    def test_workflow_lifecycle(self, test_client):
        resp = test_client.post("/api/workflow/data_pipeline/start", json={"x": 1})
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]

        resp = test_client.get(f"/api/workflow/data_pipeline/runs/{run_id}")
        assert resp.status_code == 200

        resp = test_client.get("/api/workflow/data_pipeline/runs")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_memory_lifecycle(self, test_client):
        resp = test_client.post(
            "/api/memory/manager/threads", json={"metadata": {"test": True}}
        )
        assert resp.status_code == 200
        thread_id = resp.json()["id"]

        resp = test_client.post(
            f"/api/memory/manager/threads/{thread_id}/messages",
            json={"role": "user", "content": "Integration test"},
        )
        assert resp.status_code == 200

        resp = test_client.get(f"/api/memory/manager/threads/{thread_id}")
        assert resp.status_code == 200

        resp = test_client.delete(f"/api/memory/manager/threads/{thread_id}")
        assert resp.status_code == 204

    def test_dynamic_client_round_trip(self, test_client):
        from server_support.client import MachineClient

        client = MachineClient(base_url="http://testserver", http_client=test_client)

        agents = client.agent.list()
        assert len(agents) >= 1
        result = client.agent.run("chat", prompt="SDK test")
        assert isinstance(result, dict)

        tools = client.tool.list()
        assert len(tools) >= 1

        workflows = client.workflow.list()
        assert len(workflows) >= 1

        thread = client.memory.create_thread("manager", metadata={"sdk": True})
        assert "id" in thread
        client.memory.delete_thread("manager", thread_id=thread["id"])
