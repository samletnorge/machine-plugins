"""Session-based authorization helpers for Studio routes."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException, Request

from studio_support.oidc import config_from_env
from studio_support.session import SESSION_COOKIE, verify


def current_user(request: Request) -> dict[str, Any] | None:
    """Return the signed-in user from the session cookie, if any."""
    payload = verify(request.cookies.get(SESSION_COOKIE))
    if not payload:
        return None
    user = payload.get("user")
    return user if isinstance(user, dict) else None


def auth_configured() -> bool:
    """Whether Zitadel credentials are configured for this process."""
    try:
        return config_from_env().configured
    except Exception:  # noqa: BLE001 - treat any config error as not configured
        return False


def require_role(*roles: str) -> Callable[[Request], Any]:
    """Return a dependency that enforces one of ``roles`` (when auth is on).

    When authentication is not configured (e.g. local dev / tests) the
    dependency is a no-op so the control plane stays usable.
    """

    async def dependency(request: Request) -> dict[str, Any] | None:
        if not auth_configured():
            return current_user(request)

        user = current_user(request)
        if user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        if roles and not (set(roles) & set(user.get("roles") or [])):
            raise HTTPException(
                status_code=403,
                detail=f"Requires one of the roles: {', '.join(roles)}",
            )
        return user

    return dependency
