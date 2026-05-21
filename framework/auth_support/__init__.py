"""Auth support plugin — registers auth_provider category with Machine.

Provides JWT and API Key authentication providers.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# --- Models ---


@dataclass
class Permission:
    resource: str
    action: str  # e.g. "read", "write", "delete", "admin"

    def __eq__(self, other):
        if not isinstance(other, Permission):
            return False
        return self.resource == other.resource and self.action == other.action

    def __hash__(self):
        return hash((self.resource, self.action))


@dataclass
class Role:
    name: str
    permissions: list[Permission] = field(default_factory=list)

    def has_permission(self, resource: str, action: str) -> bool:
        return any(
            p.resource == resource and (p.action == action or p.action == "*")
            for p in self.permissions
        )


@dataclass
class AuthUser:
    user_id: str
    username: str
    roles: list[Role] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_permission(self, resource: str, action: str) -> bool:
        return any(role.has_permission(resource, action) for role in self.roles)


@dataclass
class AuthToken:
    token: str
    user_id: str
    expires_at: float  # unix timestamp
    token_type: str = "bearer"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


# --- Base class ---


class AuthProvider(ABC):
    @abstractmethod
    async def authenticate(self, credentials: dict[str, Any]) -> AuthUser: ...

    @abstractmethod
    async def authorize(self, user: AuthUser, resource: str, action: str) -> bool: ...

    @abstractmethod
    async def create_token(self, user: AuthUser, ttl: int = 3600) -> AuthToken: ...

    @abstractmethod
    async def verify_token(self, token: str) -> AuthUser: ...

    @abstractmethod
    async def revoke_token(self, token: str) -> bool: ...


# --- JWT Auth Provider ---


class JWTAuthProvider(AuthProvider):
    """JWT-based auth using HMAC-SHA256."""

    def __init__(self, secret: str, users: dict[str, AuthUser] | None = None):
        self._secret = secret.encode()
        self._users: dict[str, AuthUser] = users or {}
        self._revoked: set[str] = set()

    def _b64encode(self, data: bytes) -> str:
        import base64

        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    def _b64decode(self, s: str) -> bytes:
        import base64

        padding = 4 - len(s) % 4
        return base64.urlsafe_b64decode(s + "=" * padding)

    def _sign(self, payload: str) -> str:
        header = self._b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        body = self._b64encode(payload.encode())
        sig_input = f"{header}.{body}"
        sig = hmac.new(self._secret, sig_input.encode(), hashlib.sha256).digest()
        return f"{sig_input}.{self._b64encode(sig)}"

    def _verify_sig(self, token: str) -> dict[str, Any]:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        sig_input = f"{parts[0]}.{parts[1]}"
        expected_sig = hmac.new(
            self._secret, sig_input.encode(), hashlib.sha256
        ).digest()
        actual_sig = self._b64decode(parts[2])
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("Invalid token signature")
        return json.loads(self._b64decode(parts[1]))

    def add_user(self, user: AuthUser, password: str):
        self._users[user.username] = user
        self._users[f"__pw__{user.username}"] = AuthUser(
            user_id=password, username=password
        )

    async def authenticate(self, credentials: dict[str, Any]) -> AuthUser:
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        pw_entry = self._users.get(f"__pw__{username}")
        if not pw_entry or pw_entry.user_id != password:
            raise PermissionError("Invalid credentials")
        return self._users[username]

    async def authorize(self, user: AuthUser, resource: str, action: str) -> bool:
        return user.has_permission(resource, action)

    async def create_token(self, user: AuthUser, ttl: int = 3600) -> AuthToken:
        exp = time.time() + ttl
        payload = json.dumps({"sub": user.user_id, "usr": user.username, "exp": exp})
        token_str = self._sign(payload)
        return AuthToken(token=token_str, user_id=user.user_id, expires_at=exp)

    async def verify_token(self, token: str) -> AuthUser:
        if token in self._revoked:
            raise PermissionError("Token revoked")
        claims = self._verify_sig(token)
        if time.time() > claims["exp"]:
            raise PermissionError("Token expired")
        user = None
        for u in self._users.values():
            if u.user_id == claims["sub"] and not u.username.startswith("__pw__"):
                user = u
                break
        if not user:
            raise PermissionError("User not found")
        return user

    async def revoke_token(self, token: str) -> bool:
        self._revoked.add(token)
        return True


# --- API Key Auth Provider ---


class APIKeyAuthProvider(AuthProvider):
    """API key-based auth with hashed key storage."""

    def __init__(self):
        self._keys: dict[str, tuple[str, AuthUser]] = {}  # hash -> (key, user)
        self._revoked: set[str] = set()

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    def create_api_key(self, user: AuthUser) -> str:
        key = f"mk_{secrets.token_hex(24)}"
        key_hash = self._hash_key(key)
        self._keys[key_hash] = (key, user)
        return key

    async def authenticate(self, credentials: dict[str, Any]) -> AuthUser:
        api_key = credentials.get("api_key", "")
        key_hash = self._hash_key(api_key)
        if key_hash in self._revoked:
            raise PermissionError("API key revoked")
        entry = self._keys.get(key_hash)
        if not entry:
            raise PermissionError("Invalid API key")
        return entry[1]

    async def authorize(self, user: AuthUser, resource: str, action: str) -> bool:
        return user.has_permission(resource, action)

    async def create_token(self, user: AuthUser, ttl: int = 3600) -> AuthToken:
        key = self.create_api_key(user)
        return AuthToken(token=key, user_id=user.user_id, expires_at=time.time() + ttl)

    async def verify_token(self, token: str) -> AuthUser:
        return await self.authenticate({"api_key": token})

    async def revoke_token(self, token: str) -> bool:
        key_hash = self._hash_key(token)
        self._revoked.add(key_hash)
        return True


# --- Plugin ---


class AuthSupportPlugin:
    """Plugin that registers the auth_provider category and built-in providers."""

    async def initialize(self, **kwargs):
        """No-op — category plugins define schemas, not runtime state."""
        pass

    async def setup(self, ctx):
        ctx.register_category(
            "auth_provider",
            operations={
                "authenticate": {"method": "POST", "on": "item"},
                "authorize": {"method": "POST", "on": "item"},
                "create_token": {"method": "POST", "on": "item"},
                "verify_token": {"method": "POST", "on": "item"},
                "revoke_token": {"method": "POST", "on": "item"},
            },
        )
        ctx.register("auth_provider", "jwt", JWTAuthProvider(secret="default-secret"))
        ctx.register("auth_provider", "api_key", APIKeyAuthProvider())

    async def shutdown(self, **kwargs):
        """No-op — no resources to release."""
        pass
