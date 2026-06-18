"""
api/routes/oauth.py — Google + GitHub social login.

Mirrors the three Flask routes in app/routes/users.py:
    POST /api/v2/auth/google          ID-token exchange (Google Sign-In SDK)
    GET  /api/v2/auth/github          redirect to GitHub consent
    GET  /api/v2/auth/github/callback code exchange + redirect to frontend

Token issuance reuses the fastapi-users JWT strategy from
api.core.users.auth_backend so tokens minted here are indistinguishable
from /auth/jwt/login tokens.

User account lookup/creation is handled inline by `_social_login` (the async
port of the old `UserService.social_login_or_register`), which does google_id /
github_id linking and email-based account merging on the async session.
"""
from __future__ import annotations

import random
from types import SimpleNamespace
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import Settings, get_settings
from api.core.users import auth_backend
from api.db import User
from api.db.session import get_async_session


router = APIRouter(prefix="/api/v2/auth", tags=["auth"])

DbSession = Annotated[AsyncSession, Depends(get_async_session)]


# ── Shared helpers ─────────────────────────────────────────────────────────

class _GoogleTokenBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(..., min_length=1, description="Google ID token from the JS SDK.")


async def _social_login(db: AsyncSession, provider: str, provider_id: str, *,
                        email: str | None,
                        first_name: str | None,
                        last_name: str | None) -> SimpleNamespace:
    """Find or create the user (async port of UserService.social_login_or_register).

    Returns a session-independent snapshot — write_token() only reads `id`, and
    the response payload needs a few scalar fields, so we avoid handing back a
    live ORM entity that could lazy-load after the session closes.
    """
    id_field = f"{provider}_id"

    # 1. Lookup by provider ID.
    user = (await db.execute(
        select(User).where(getattr(User, id_field) == provider_id)
    )).scalar_one_or_none()

    # 2. Lookup by email and link the provider ID.
    if user is None and email:
        user = (await db.execute(
            select(User).where(User.email == email)
        )).scalar_one_or_none()
        if user is not None:
            setattr(user, id_field, provider_id)

    # 3. Create a new account.
    if user is None:
        base_username = email.split("@")[0] if email else f"user{provider_id[:8]}"
        username = base_username
        while (await db.execute(
            select(User).where(User.username == username)
        )).scalar_one_or_none() is not None:
            username = f"{base_username}_{random.randint(1000, 9999)}"
        effective_email = email or f"{username}@{provider}.vote-app.local"
        user = User(
            username=username,
            email=effective_email,
            first_name=first_name,
            last_name=last_name,
            role="User",
            hashed_password="*",   # unusable password — OAuth-only account
            **{id_field: provider_id},
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)
    return SimpleNamespace(
        id=user.id, username=user.username, email=user.email,
        role=user.role, first_name=user.first_name, last_name=user.last_name,
    )


async def _issue_token(user: SimpleNamespace, settings: Settings) -> str:
    """Mint a fastapi-users-compatible JWT for `user`."""
    strategy = auth_backend.get_strategy(settings)
    # get_strategy is a DependencyCallable (sync/async/generator union); ours is
    # the plain sync _get_jwt_strategy, so write_token is always present.
    return await strategy.write_token(user)  # type: ignore[union-attr]


def _user_payload(user: SimpleNamespace, access_token: str) -> dict[str, Any]:
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
    db: DbSession,
) -> dict[str, Any]:
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
        info = google_id_token.verify_oauth2_token(  # type: ignore[no-untyped-call]
            body.token, google_requests.Request(), settings.google_client_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        ) from exc

    user = await _social_login(
        db, "google", provider_id=info["sub"],
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
    db: DbSession,
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
        db, "github", provider_id=github_id,
        email=email or None, first_name=first_name, last_name=last_name,
    )
    token = await _issue_token(user, settings)
    return RedirectResponse(
        f"{settings.frontend_url}/oauth/callback?token={token}",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
