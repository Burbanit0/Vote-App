"""
api/routes/auth.py — fastapi-users register / login / logout routes.

Mounts the built-in fastapi-users routers under /api/v2/auth/* and exposes
them through the unified app. Tokens issued here are interchangeable with
the ones issued by Flask-JWT-Extended on the Flask side (same secret,
same HS256 algorithm), so a user can hold a single token through both
backends during the migration.

Routes added by this module:
    POST /api/v2/auth/register          (fastapi-users)
    POST /api/v2/auth/jwt/login         (fastapi-users)
    POST /api/v2/auth/jwt/logout        (fastapi-users — token blacklist
                                         is a future enhancement; for now
                                         the client just drops the token)

Phase 4.3.c adds /users/me and the admin CRUD.
Phase 4.3.d adds /auth/google + /auth/github.
"""
from __future__ import annotations

from fastapi import APIRouter

from api.schemas.auth import UserCreate, UserRead
from api.core.users import auth_backend, fastapi_users

router = APIRouter(prefix="/api/v2/auth", tags=["auth"])

# Register: POST /api/v2/auth/register
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="",
)

# Login / logout (JWT backend): POST /api/v2/auth/jwt/login + /logout
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/jwt",
)
