"""Task 10 — Tool tester route tests."""


def test_tool_page_returns_200(studio_client):
    resp = studio_client.get("/tools/echo")
    assert resp.status_code == 200
    assert "echo" in resp.text


def test_tool_page_unknown_404(studio_client):
    resp = studio_client.get("/tools/nonexistent")
    assert resp.status_code == 404


def test_tool_execute_returns_result(studio_client):
    resp = studio_client.post(
        "/tools/echo/execute",
        json={"input": "test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data


def test_tool_execute_unknown_404(studio_client):
    resp = studio_client.post(
        "/tools/nonexistent/execute",
        json={},
    )
    assert resp.status_code == 404
