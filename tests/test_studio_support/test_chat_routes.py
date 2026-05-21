"""Task 10 — Chat route tests."""


def test_chat_page_returns_200(studio_client):
    resp = studio_client.get("/chat")
    assert resp.status_code == 200
    assert "greeter" in resp.text


def test_chat_page_selects_agent(studio_client):
    resp = studio_client.get("/chat?agent=greeter")
    assert resp.status_code == 200


def test_chat_send_returns_response(studio_client):
    resp = studio_client.post(
        "/chat/send",
        data={"agent": "greeter", "message": "world"},
    )
    assert resp.status_code == 200
    assert "Hello, world" in resp.text


def test_chat_send_unknown_agent_404(studio_client):
    resp = studio_client.post(
        "/chat/send",
        data={"agent": "nonexistent", "message": "hi"},
    )
    assert resp.status_code == 404
