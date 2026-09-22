"""GitHub Copilot auth: two-tier token system.

1. GitHub OAuth access token (long-lived) — obtained via device flow, cached to disk
2. Copilot session token (short-lived, ~30min) — exchanged from access token

Reference: https://github.com/uriyyo/gh-pydantic-ai
"""

from __future__ import annotations

import asyncio
import time
import uuid
import webbrowser
from pathlib import Path
from typing import Any, AsyncGenerator, Generator, cast

import httpx

# --- Constants ---
GITHUB_CLIENT_ID = "Iv1.b507a08c87ecfe98"  # VS Code Copilot Chat
GITHUB_APP_SCOPES = ["read:user"]

COPILOT_CHAT_BASE_URL = "https://api.githubcopilot.com"
COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"

VSCODE_VERSION = "1.105.1"
COPILOT_VERSION = "0.32.3"
API_VERSION = "2025-04-01"

CONFIG_DIR = Path.home() / ".config" / "machine-core" / "github-copilot"
TOKEN_FILE = CONFIG_DIR / "access_token"


def _standard_headers() -> dict[str, str]:
    return {
        "accept": "application/json",
        "content-type": "application/json",
    }


def github_headers() -> dict[str, str]:
    """Headers for GitHub API calls (token exchange)."""
    return {
        **_standard_headers(),
        "editor-version": "vscode/1.101.2",
        "editor-plugin-version": f"copilot-chat/{COPILOT_VERSION}",
        "user-agent": f"GitHubCopilotChat/{COPILOT_VERSION}",
        "x-github-api-version": API_VERSION,
        "x-vscode-user-agent-library-version": "electron-fetch",
    }


def copilot_headers() -> dict[str, str]:
    """Headers for Copilot API calls (chat completions)."""
    return {
        **_standard_headers(),
        "copilot-integration-id": "vscode-chat",
        "editor-version": f"vscode/{VSCODE_VERSION}",
        "editor-plugin-version": f"copilot-chat/{COPILOT_VERSION}",
        "user-agent": f"GitHubCopilotChat/{COPILOT_VERSION}",
        "openai-intent": "conversation-panel",
        "x-github-api-version": API_VERSION,
        "x-request-id": str(uuid.uuid4()),
        "x-vscode-user-agent-library-version": "electron-fetch",
    }


# --- Device Flow Login ---


async def device_flow_login() -> str:
    """Interactive OAuth device flow login. Returns GitHub OAuth access token."""
    async with httpx.AsyncClient(
        base_url="https://github.com",
        headers=_standard_headers(),
    ) as client:
        # Step 1: Request device code
        resp = await client.post(
            "/login/device/code",
            json={
                "client_id": GITHUB_CLIENT_ID,
                "scope": " ".join(GITHUB_APP_SCOPES),
            },
        )
        resp.raise_for_status()
        data = resp.json()

        user_code = data["user_code"]
        verification_uri = data["verification_uri"]
        device_code = data["device_code"]
        interval = data.get("interval", 5)
        expires_in = data.get("expires_in", 900)

        # Step 2: Prompt user
        print(
            f"\n  GitHub Copilot: Open {verification_uri} and enter code: {user_code}\n"
        )
        try:
            webbrowser.open_new_tab(verification_uri)
        except Exception:
            pass

        # Step 3: Poll for access token
        async with asyncio.timeout(expires_in):
            while True:
                poll_resp = await client.post(
                    "/login/oauth/access_token",
                    json={
                        "client_id": GITHUB_CLIENT_ID,
                        "device_code": device_code,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    },
                )
                result = poll_resp.json()
                if "access_token" in result:
                    access_token = result["access_token"]
                    # Cache to disk
                    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                    TOKEN_FILE.write_text(access_token)
                    return access_token
                await asyncio.sleep(interval)


def get_cached_access_token() -> str | None:
    """Read cached GitHub OAuth access token from disk."""
    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text().strip()
        if token:
            return token
    return None


# --- Copilot Token Exchange ---


async def exchange_copilot_token(access_token: str) -> dict[str, Any]:
    """Exchange GitHub OAuth token for a short-lived Copilot session token."""
    async with httpx.AsyncClient(base_url="https://api.github.com/") as client:
        resp = await client.get(
            "copilot_internal/v2/token",
            headers={
                **github_headers(),
                "Authorization": f"Bearer {access_token}",
            },
        )
        resp.raise_for_status()
        return resp.json()


# --- httpx Auth class (used by provider) ---


class CopilotAuth(httpx.Auth):
    """httpx Auth that manages the two-tier Copilot token system.

    Automatically exchanges the GitHub OAuth access token for a
    short-lived Copilot session token, refreshing when expired.
    """

    def __init__(self, access_token: str) -> None:
        self._access_token = access_token
        self._copilot_token: str | None = None
        self._expires_at: float = 0

    @property
    def is_expired(self) -> bool:
        if not self._copilot_token:
            return True
        return self._expires_at <= (time.time() + 300)  # 5 min buffer

    async def _refresh(self) -> None:
        data = await exchange_copilot_token(self._access_token)
        self._copilot_token = data["token"]
        self._expires_at = data["expires_at"]

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        if self.is_expired:
            await self._refresh()

        request.headers.update(copilot_headers())
        request.headers["Authorization"] = f"Bearer {self._copilot_token}"
        yield request

    @property
    def base_url(self) -> str:
        return COPILOT_CHAT_BASE_URL
