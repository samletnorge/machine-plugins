"""Signed-cookie sessions for Studio auth.

No third-party dependency: an HMAC-SHA256 signed, base64url JSON payload. The
signing key comes from ``SESSION_SECRET`` (falls back to a hash of the Zitadel
client secret so local dev works, with a warning).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from loguru import logger

SESSION_COOKIE = os.getenv("SESSION_COOKIE_NAME", "machine_studio_session")
STATE_COOKIE = "machine_studio_oauth_state"
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", str(60 * 60 * 8)))


def _secret() -> bytes:
    secret = os.getenv("SESSION_SECRET")
    if secret:
        return secret.encode("utf-8")
    fallback = os.getenv("ZITADEL_CLIENT_SECRET", "")
    if not fallback:
        logger.warning(
            "SESSION_SECRET is not set; using an insecure development fallback"
        )
        fallback = "insecure-machine-studio-dev-secret"
    return hashlib.sha256(f"machine-studio::{fallback}".encode()).digest()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def sign(payload: dict[str, Any]) -> str:
    body = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64(signature)}"


def verify(token: str | None) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None
    body, _, signature = token.partition(".")
    expected = hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest()
    try:
        if not hmac.compare_digest(expected, _unb64(signature)):
            return None
        payload = json.loads(_unb64(body))
    except (ValueError, json.JSONDecodeError):
        return None
    if payload.get("exp", 0) < time.time():
        return None
    return payload


def new_session(user: dict[str, Any], id_token: str | None = None) -> str:
    return sign(
        {
            "user": user,
            "id_token": id_token,
            "exp": int(time.time()) + SESSION_TTL_SECONDS,
        }
    )


def new_state(next_url: str, code_verifier: str | None) -> str:
    return sign(
        {
            "next": next_url,
            "verifier": code_verifier,
            "exp": int(time.time()) + 600,
        }
    )
