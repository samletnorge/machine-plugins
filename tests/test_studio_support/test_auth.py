"""Tests for the Studio Zitadel auth flow (mocked OIDC)."""

from __future__ import annotations

import base64
import json
from urllib.parse import parse_qs, urlparse

import pytest

from studio_support.oidc import ZitadelOIDC, decode_claims, extract_roles

_DISCOVERY = {
    "authorization_endpoint": "https://zitadel.test/oauth/v2/authorize",
    "token_endpoint": "https://zitadel.test/oauth/v2/token",
    "userinfo_endpoint": "https://zitadel.test/oidc/v1/userinfo",
    "end_session_endpoint": "https://zitadel.test/oidc/v1/end_session",
}


@pytest.fixture
def auth_env(monkeypatch):
    monkeypatch.setenv("ZITADEL_CLIENT_ID", "client-id")
    monkeypatch.setenv("ZITADEL_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")

    async def fake_discovery(self):
        return _DISCOVERY

    async def fake_exchange(self, code, code_verifier=None):
        return {"access_token": "access-token", "id_token": "id-token"}

    async def fake_userinfo(self, access_token):
        return {
            "sub": "user-1",
            "email": "ada@example.com",
            "name": "Ada",
            "urn:zitadel:iam:org:project:roles": {"admin": {"org": "acme"}},
        }

    monkeypatch.setattr(ZitadelOIDC, "discovery", fake_discovery)
    monkeypatch.setattr(ZitadelOIDC, "exchange_code", fake_exchange)
    monkeypatch.setattr(ZitadelOIDC, "userinfo", fake_userinfo)


def _state_from(login_response) -> tuple[str, str]:
    query = parse_qs(urlparse(login_response.headers["location"]).query)
    return query["state"][0], login_response.cookies["machine_studio_oauth_state"]


def test_extract_roles():
    assert extract_roles(
        {"urn:zitadel:iam:org:project:roles": {"admin": {}, "editor": {}}}
    ) == ["admin", "editor"]
    assert extract_roles({}) == []


def _jwt(payload: dict) -> str:
    def seg(data: dict) -> str:
        raw = json.dumps(data).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    return f"{seg({'alg': 'none'})}.{seg(payload)}.sig"


def test_decode_claims():
    assert decode_claims(_jwt({"sub": "x"})) == {"sub": "x"}
    assert decode_claims("not-a-jwt") == {}


def test_login_redirects_to_zitadel(studio_client, auth_env):
    response = studio_client.get("/auth/login", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"].startswith(
        "https://zitadel.test/oauth/v2/authorize?"
    )
    query = parse_qs(urlparse(response.headers["location"]).query)
    assert query["client_id"] == ["client-id"]
    assert query["response_type"] == ["code"]
    assert "machine_studio_oauth_state" in response.cookies


def test_me_requires_session(studio_client, auth_env):
    assert studio_client.get("/auth/me").status_code == 401


def test_callback_sets_session_and_me_returns_user(studio_client, auth_env):
    login = studio_client.get("/auth/login", follow_redirects=False)
    state, _ = _state_from(login)

    callback = studio_client.get(
        f"/auth/callback?code=auth-code&state={state}", follow_redirects=False
    )
    assert callback.status_code == 307
    assert "machine_studio_session" in callback.cookies

    me = studio_client.get("/auth/me")
    assert me.status_code == 200
    user = me.json()["user"]
    assert user["email"] == "ada@example.com"
    assert user["roles"] == ["admin"]


def test_callback_rejects_bad_state(studio_client, auth_env):
    response = studio_client.get(
        "/auth/callback?code=abc&state=tampered", follow_redirects=False
    )
    assert response.status_code == 400


def test_roles_merge_from_id_token(studio_client, auth_env, monkeypatch):
    roles_claim = "urn:zitadel:iam:org:project:roles"
    token = _jwt({"sub": "user-1", roles_claim: {"editor": {"acme": "org"}}})

    async def exchange(self, code, code_verifier=None):
        return {"access_token": "access-token", "id_token": token}

    async def userinfo(self, access_token):
        return {"sub": "user-1", "email": "ada@example.com", "name": "Ada"}

    monkeypatch.setattr(ZitadelOIDC, "exchange_code", exchange)
    monkeypatch.setattr(ZitadelOIDC, "userinfo", userinfo)

    login = studio_client.get("/auth/login", follow_redirects=False)
    state, _ = _state_from(login)
    studio_client.get(
        f"/auth/callback?code=auth-code&state={state}", follow_redirects=False
    )

    assert studio_client.get("/auth/me").json()["user"]["roles"] == ["editor"]


def test_logout_clears_session(studio_client, auth_env):
    response = studio_client.get("/auth/logout", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"].startswith(
        "https://zitadel.test/oidc/v1/end_session?"
    )


def test_spa_index_is_served(studio_client, auth_env):
    response = studio_client.get("/app")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
