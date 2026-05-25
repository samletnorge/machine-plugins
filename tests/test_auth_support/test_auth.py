"""Tests for auth_support plugin."""

import pytest
from auth_support import (
    AuthSupportPlugin,
    JWTAuthProvider,
    APIKeyAuthProvider,
    AuthUser,
    AuthToken,
    Permission,
    Role,
)


# --- Model tests ---


def test_permission_equality():
    p1 = Permission(resource="stations", action="read")
    p2 = Permission(resource="stations", action="read")
    assert p1 == p2


def test_role_has_permission():
    role = Role(name="admin", permissions=[Permission(resource="stations", action="*")])
    assert role.has_permission("stations", "read")
    assert role.has_permission("stations", "delete")
    assert not role.has_permission("users", "read")


def test_auth_user_has_permission():
    role = Role(name="viewer", permissions=[Permission(resource="data", action="read")])
    user = AuthUser(user_id="u1", username="alice", roles=[role])
    assert user.has_permission("data", "read")
    assert not user.has_permission("data", "write")


def test_auth_token_expiry():
    import time

    token = AuthToken(token="t", user_id="u1", expires_at=time.time() - 10)
    assert token.is_expired
    token2 = AuthToken(token="t", user_id="u1", expires_at=time.time() + 3600)
    assert not token2.is_expired


# --- JWT tests ---


@pytest.mark.asyncio
async def test_jwt_create_and_verify_token():
    role = Role(name="user", permissions=[Permission(resource="api", action="read")])
    user = AuthUser(user_id="u1", username="bob", roles=[role])
    jwt = JWTAuthProvider(secret="test-secret")
    jwt.add_user(user, "password123")
    token = await jwt.create_token(user)
    assert token.token
    verified = await jwt.verify_token(token.token)
    assert verified.user_id == "u1"


@pytest.mark.asyncio
async def test_jwt_authenticate():
    user = AuthUser(user_id="u1", username="bob", roles=[])
    jwt = JWTAuthProvider(secret="s")
    jwt.add_user(user, "pass")
    result = await jwt.authenticate({"username": "bob", "password": "pass"})
    assert result.user_id == "u1"


@pytest.mark.asyncio
async def test_jwt_authenticate_bad_password():
    user = AuthUser(user_id="u1", username="bob", roles=[])
    jwt = JWTAuthProvider(secret="s")
    jwt.add_user(user, "pass")
    with pytest.raises(PermissionError):
        await jwt.authenticate({"username": "bob", "password": "wrong"})


@pytest.mark.asyncio
async def test_jwt_revoke_token():
    user = AuthUser(user_id="u1", username="bob", roles=[])
    jwt = JWTAuthProvider(secret="s")
    jwt.add_user(user, "pass")
    token = await jwt.create_token(user)
    await jwt.revoke_token(token.token)
    with pytest.raises(PermissionError):
        await jwt.verify_token(token.token)


@pytest.mark.asyncio
async def test_jwt_authorize():
    role = Role(name="admin", permissions=[Permission(resource="x", action="write")])
    user = AuthUser(user_id="u1", username="bob", roles=[role])
    jwt = JWTAuthProvider(secret="s")
    assert await jwt.authorize(user, "x", "write")
    assert not await jwt.authorize(user, "x", "delete")


# --- API Key tests ---


@pytest.mark.asyncio
async def test_apikey_create_and_authenticate():
    user = AuthUser(user_id="u1", username="svc", roles=[])
    provider = APIKeyAuthProvider()
    key = provider.create_api_key(user)
    assert key.startswith("mk_")
    result = await provider.authenticate({"api_key": key})
    assert result.user_id == "u1"


@pytest.mark.asyncio
async def test_apikey_invalid_key():
    provider = APIKeyAuthProvider()
    with pytest.raises(PermissionError):
        await provider.authenticate({"api_key": "invalid"})


@pytest.mark.asyncio
async def test_apikey_revoke():
    user = AuthUser(user_id="u1", username="svc", roles=[])
    provider = APIKeyAuthProvider()
    key = provider.create_api_key(user)
    await provider.revoke_token(key)
    with pytest.raises(PermissionError):
        await provider.verify_token(key)


# --- Plugin tests ---


def test_plugin_instantiation():
    plugin = AuthSupportPlugin()
    assert hasattr(plugin, "initialize")
    assert hasattr(plugin, "setup")
    assert hasattr(plugin, "shutdown")
