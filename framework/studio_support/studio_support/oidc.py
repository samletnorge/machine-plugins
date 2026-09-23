"""Zitadel OIDC client (Authorization Code flow, confidential Web app).

Reads configuration from the environment (populated by ``bootstrap_secrets`` /
Infisical and/or a local ``.env``):

- ``ZITADEL_ISSUER`` (default ``https://zitadel.samletnorge.no``)
- ``ZITADEL_CLIENT_ID`` / ``ZITADEL_CLIENT_SECRET``
- ``ZITADEL_REDIRECT_URI`` (default ``http://localhost:8000/_studio/auth/callback``)
- ``ZITADEL_POST_LOGOUT_REDIRECT_URI`` (default ``http://localhost:8000/_studio/app/``)
- ``ZITADEL_PROJECT_ID`` (optional — adds the audience scope so project roles resolve)
- ``ZITADEL_USE_PKCE`` (optional; PKCE is not required for a confidential client)
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

DEFAULT_ISSUER = "https://zitadel.samletnorge.no"


@dataclass(frozen=True)
class OIDCConfig:
    issuer: str
    client_id: str
    client_secret: str
    redirect_uri: str
    post_logout_redirect_uri: str
    project_id: str | None = None
    use_pkce: bool = False

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)


def config_from_env() -> OIDCConfig:
    return OIDCConfig(
        issuer=os.getenv("ZITADEL_ISSUER", DEFAULT_ISSUER).rstrip("/"),
        client_id=os.getenv("ZITADEL_CLIENT_ID", ""),
        client_secret=os.getenv("ZITADEL_CLIENT_SECRET", ""),
        redirect_uri=os.getenv(
            "ZITADEL_REDIRECT_URI", "http://localhost:8000/_studio/auth/callback"
        ),
        post_logout_redirect_uri=os.getenv(
            "ZITADEL_POST_LOGOUT_REDIRECT_URI", "http://localhost:8000/_studio/app/"
        ),
        project_id=os.getenv("ZITADEL_PROJECT_ID") or None,
        use_pkce=os.getenv("ZITADEL_USE_PKCE", "").lower() in ("1", "true", "yes"),
    )


def _base64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def generate_pkce() -> tuple[str, str]:
    """Return ``(code_verifier, code_challenge)`` using S256."""
    verifier = _base64url(secrets.token_bytes(48))
    challenge = _base64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def extract_roles(userinfo: dict[str, Any]) -> list[str]:
    """Extract Zitadel project roles from a userinfo/id-token claim."""
    claim = userinfo.get("urn:zitadel:iam:org:project:roles") or {}
    if isinstance(claim, dict):
        return sorted(claim.keys())
    if isinstance(claim, list):
        return sorted(str(role) for role in claim)
    return []


class ZitadelOIDC:
    """Thin async OIDC client over Zitadel's discovery endpoints."""

    def __init__(self, config: OIDCConfig) -> None:
        self.config = config
        self._discovery: dict[str, Any] | None = None

    def scopes(self) -> list[str]:
        scopes = ["openid", "profile", "email", "urn:zitadel:iam:org:project:roles"]
        if self.config.project_id:
            scopes.append(f"urn:zitadel:iam:org:project:id:{self.config.project_id}:aud")
        return scopes

    async def discovery(self) -> dict[str, Any]:
        if self._discovery is None:
            url = f"{self.config.issuer}/.well-known/openid-configuration"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                self._discovery = response.json()
        return self._discovery

    async def authorize_url(self, state: str, code_challenge: str | None = None) -> str:
        endpoints = await self.discovery()
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes()),
            "state": state,
        }
        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"
        return f"{endpoints['authorization_endpoint']}?{urlencode(params)}"

    async def exchange_code(
        self, code: str, code_verifier: str | None = None
    ) -> dict[str, Any]:
        endpoints = await self.discovery()
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }
        if code_verifier:
            data["code_verifier"] = code_verifier
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                endpoints["token_endpoint"],
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            return response.json()

    async def userinfo(self, access_token: str) -> dict[str, Any]:
        endpoints = await self.discovery()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                endpoints["userinfo_endpoint"],
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()

    async def logout_url(self, id_token_hint: str | None = None) -> str:
        endpoints = await self.discovery()
        params = {"post_logout_redirect_uri": self.config.post_logout_redirect_uri}
        if id_token_hint:
            params["id_token_hint"] = id_token_hint
        return f"{endpoints['end_session_endpoint']}?{urlencode(params)}"
