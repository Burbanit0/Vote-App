"""
api_v2.core.auth — JWT Bearer dependency compatible with Flask-JWT-Extended.

Decodes the same access tokens issued by `flask_jwt_extended.create_access_token`
on the Flask side, so users can hold a single token for both /api/* and /api/v2/*.

This is a Phase 4 intermediate step: when Phase 4.3 migrates auth to
fastapi-users, this module is replaced by the fastapi-users User dependency.
Until then it lets the rest of Phase 4 (scenarios, etc.) ship without
blocking on the full auth rewrite.

Token format produced by Flask-JWT-Extended (algorithm HS256 by default):
    header  = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": "<user_id as string>", "exp": <ts>, ...}
    signed  = HMAC-SHA256 with settings.jwt_secret_key
"""
from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api_v2.core.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)


def _credentials_dep() -> HTTPBearer:
    """Indirection so tests can override the security scheme."""
    return _bearer


def current_user_id(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
) -> int:
    """Validate the Bearer token and return the user_id encoded in `sub`.

    Mirrors `flask_jwt_extended.get_jwt_identity()`'s contract: the
    identity stored in the token is `str(user.id)`, decoded back to an
    int here for SQLAlchemy queries.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        # `audience=...` accepts the fastapi-users default audience while
        # `options={"verify_aud": False}` would also accept tokens minted by
        # Flask-JWT-Extended (which has no `aud` claim). Pass both knobs so a
        # single secret round-trips through both backends.
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=["HS256"],
            audience="fastapi-users:auth",
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing sub claim",
        )
    try:
        return int(sub)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sub is not an integer user id",
        ) from exc


CurrentUserId = Annotated[int, Depends(current_user_id)]
