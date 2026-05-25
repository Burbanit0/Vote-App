"""
api_v2/routes/oauth.py — Google + GitHub social login.

Mirrors the three Flask routes in app/routes/users.py:
    POST /api/v2/auth/google          ID-token exchange (Google Sign-In SDK)
    GET  /api/v2/auth/github          redirect to GitHub consent
    GET  /api/v2/auth/github/callback code exchange + redirect to frontend

Token issuance reuses the fastapi-users JWT strategy from
api_v2.core.users.auth_backend so tokens minted here are indistinguishable
from /auth/jwt/login tokens.

User account lookup/creation goes through the existing
`UserService.social_login_or_register` helper (which already handles
the google_id / github_id linking and email-based account merging),
wrapped in `run_in_flask_db` to stay off the event loop.
"""
from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field

from api_v2.core.config import Settings, get_settings
from api_v2.core.db import run_in_flask_db
from api_v2.core.users import auth_backend


router = APIRouter(prefix="/api/v2/auth", tags=["auth"])


# ── Shared helpers ─────────────────────────────────────────────────────────

class _GoogleTokenBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(..., min_length=1, description="Google ID token from the JS SDK.")


from types import SimpleNamespace


async def _social_login(provider: str, provider_id: str, *,
                        email: str | None,
                        first_name: str | None,
                        last_name: str | None) -> SimpleNamespace:
    """Find or create the user. Returns a session-independent snapshot —
    the SQLAlchemy session that loaded the row is closed by the time
    we mint the token, so we can't return the live ORM entity (lazy
    loads would raise DetachedInstanceError). A SimpleNamespace is
    enough for write_token() (which only reads `id`) and for our
    response payload."""
    def _q() -> SimpleNamespace:
        from app.services.user_service import UserService
        user, _is_new = UserService.social_login_or_register(
            provider_id=provider_id, email=email,
            first_name=first_name, last_name=last_name,
            provider=provider,
        )
        return SimpleNamespace(
            id=user.id, username=user.username, email=user.email,
            role=user.role, first_name=user.first_name,
            last_name=user.last_name,
        )
    return await run_in_flask_db(_q)


async def _issue_token(user: SimpleNamespace, settings: Settings) -> str:
    """Mint a fastapi-users-compatible JWT for `user`."""
    strategy = auth_backend.get_strategy(settings)
    return await strategy.write_token(user)


def _user_payload(user: SimpleNamespace, access_token: str) -> dict:
    """Same shape the Flask Google route returns — frontend doesn't have
    to switch on backend version."""
    return {
        "access_token": access_token,
        "user_id":      user.id,
        "username":     user.username,
        "role":         user.role,
        "first_name":   user.first_name,
        "last_name":    user.last_name,
    }


# ── /auth/google ───────────────────────────────────────────────────────────

@router.post(
    "/google",
    summary="Exchange a Google ID token for a Vote Lab JWT",
    response_description="JWT access token + user summary, identical shape "
                         "to the Flask route.",
)
async def google_login(
    body: _GoogleTokenBody,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """The Google Sign-In SDK on the frontend produces a JWT-encoded ID
    token. We verify it against Google's public keys (via the official
    google-auth library), trust the `sub`/`email` claims, then mint our
    own JWT."""
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google login not configured",
        )

    # Lazy import so the route module stays importable without google-auth.
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token as google_id_token

    try:
        info = google_id_token.verify_oauth2_token(
            body.token, google_requests.Request(), settings.google_client_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        ) from exc

    user = await _social_login(
        "google", provider_id=info["sub"],
        email=info.get("email"),
        first_name=info.get("given_name", ""),
        last_name=info.get("family_name", ""),
    )
    token = await _issue_token(user, settings)
    return _user_payload(user, token)


# ── /auth/github ───────────────────────────────────────────────────────────

@router.get(
    "/github",
    summary="Redirect the user to the GitHub OAuth consent page",
    response_class=RedirectResponse,
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
)
async def github_redirect(
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedirectResponse:
    if not settings.github_client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub login not configured",
        )
    redirect_uri = f"{settings.base_url}/api/v2/auth/github/callback"
    github_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        f"&redirect_uri={redirect_uri}"
        "&scope=read:user"
    )
    return RedirectResponse(github_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get(
    "/github/callback",
    summary="Handle GitHub's OAuth callback and bounce to the frontend",
    response_class=RedirectResponse,
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
)
async def github_callback(
    settings: Annotated[Settings, Depends(get_settings)],
    code: Annotated[str | None, Query(description="Authorization code from GitHub.")] = None,
) -> RedirectResponse:
    """Exchange the OAuth code for a GitHub access token, fetch the user
    profile, find-or-create the local account, mint our own JWT, and
    redirect the browser to `<FRONTEND>/oauth/callback?token=...`."""
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code",
        )
    if not (settings.github_client_id and settings.github_client_secret):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub login not configured",
        )

    async with httpx.AsyncClient(timeout=10.0) as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id":     settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code":          code,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()
        gh_token = token_data.get("access_token")
        if not gh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange GitHub code for token",
            )

        gh_headers = {"Authorization": f"Bearer {gh_token}",
                      "Accept": "application/json"}
        user_resp  = await client.get("https://api.github.com/user", headers=gh_headers)
        gh_user    = user_resp.json()
        github_id  = str(gh_user.get("id"))
        email      = gh_user.get("email") or ""
        name_parts = (gh_user.get("name") or "").split(" ", 1)
        first_name = name_parts[0] if name_parts else ""
        last_name  = name_parts[1] if len(name_parts) > 1 else ""

        # If the public email is hidden, fetch the user's email list and
        # take the primary one.
        if not email:
            emails_resp = await client.get(
                "https://api.github.com/user/emails", headers=gh_headers,
            )
            for entry in emails_resp.json():
                if entry.get("primary"):
                    email = entry.get("email", "")
                    break

    user = await _social_login(
        "github", provider_id=github_id,
        email=email or None, first_name=first_name, last_name=last_name,
    )
    token = await _issue_token(user, settings)
    return RedirectResponse(
        f"{settings.frontend_url}/oauth/callback?token={token}",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
