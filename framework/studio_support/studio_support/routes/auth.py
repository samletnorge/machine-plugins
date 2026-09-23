"""Studio auth routes — Zitadel OIDC (Authorization Code) + signed session cookie."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from loguru import logger

from studio_support.oidc import ZitadelOIDC, config_from_env, extract_roles, generate_pkce
from studio_support.session import (
    SESSION_COOKIE,
    STATE_COOKIE,
    new_session,
    new_state,
    verify,
)

router = APIRouter(prefix="/auth", tags=["studio-auth"])

_BUILD_DIR = Path(__file__).resolve().parent.parent / "web" / "build"


def _is_secure(request: Request) -> bool:
    return request.url.scheme == "https"


def _root_path(request: Request) -> str:
    return request.scope.get("root_path", "") or ""


def _app_url(request: Request) -> str:
    return f"{_root_path(request)}/app/"


def _oidc() -> ZitadelOIDC:
    return ZitadelOIDC(config_from_env())


def _set_cookie(
    response, name: str, value: str, request: Request, max_age: int
) -> None:
    response.set_cookie(
        name,
        value,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=_is_secure(request),
        path=_root_path(request) or "/",
    )


def _delete_cookie(response, name: str, request: Request) -> None:
    response.delete_cookie(name, path=_root_path(request) or "/")


@router.get("/login")
async def login(request: Request, next: str | None = None) -> RedirectResponse:
    oidc = _oidc()
    if not oidc.config.configured:
        raise HTTPException(status_code=503, detail="Zitadel is not configured")

    verifier = None
    challenge = None
    if oidc.config.use_pkce:
        verifier, challenge = generate_pkce()

    state = new_state(next or _app_url(request), verifier)
    try:
        url = await oidc.authorize_url(state, challenge)
    except Exception as exc:  # noqa: BLE001 - surface as a 502
        logger.warning("Zitadel discovery failed: {}", exc)
        raise HTTPException(status_code=502, detail="Zitadel is unreachable") from exc

    response = RedirectResponse(url, status_code=307)
    _set_cookie(response, STATE_COOKIE, state, request, max_age=600)
    return response


@router.get("/callback")
async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if error:
        raise HTTPException(status_code=400, detail=f"Zitadel error: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    state_cookie = request.cookies.get(STATE_COOKIE)
    payload = verify(state_cookie)
    if payload is None or state_cookie != state:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    oidc = _oidc()
    try:
        tokens = await oidc.exchange_code(code, payload.get("verifier"))
        access_token = tokens.get("access_token")
        info = await oidc.userinfo(access_token) if access_token else {}
    except Exception as exc:  # noqa: BLE001 - surface as a 502
        logger.warning("Zitadel token exchange failed: {}", exc)
        raise HTTPException(status_code=502, detail="Zitadel token exchange failed") from exc

    user = {
        "sub": info.get("sub") or tokens.get("sub"),
        "email": info.get("email"),
        "name": info.get("name") or info.get("preferred_username"),
        "roles": extract_roles(info),
    }

    response = RedirectResponse(payload.get("next") or _app_url(request))
    _set_cookie(response, SESSION_COOKIE, new_session(user, tokens.get("id_token")), request, 60 * 60 * 8)
    _delete_cookie(response, STATE_COOKIE, request)
    return response


@router.get("/me")
async def me(request: Request) -> dict:
    payload = verify(request.cookies.get(SESSION_COOKIE))
    if payload is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"user": payload["user"]}


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    payload = verify(request.cookies.get(SESSION_COOKIE))
    oidc = _oidc()
    try:
        url = await oidc.logout_url(payload.get("id_token") if payload else None)
    except Exception:  # noqa: BLE001 - fall back to the app
        url = _app_url(request)
    response = RedirectResponse(url)
    _delete_cookie(response, SESSION_COOKIE, request)
    return response
