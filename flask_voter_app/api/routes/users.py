"""
api/routes/users.py — profile + admin user CRUD.

Provided by fastapi-users' `get_users_router(UserRead, UserUpdate)`:

    GET    /api/v2/users/me         current user's profile
    PATCH  /api/v2/users/me         update current user (username, names, bio, …)
    GET    /api/v2/users/{id}       admin-only — fetch any user
    PATCH  /api/v2/users/{id}       admin-only — update any user (incl. role flips)
    DELETE /api/v2/users/{id}       admin-only — hard delete

Listing all users (the Flask `GET /api/users/` route) is NOT provided by
fastapi-users out of the box; Phase 4.3.c keeps the legacy Flask route for
that until Phase 4.5 retires Flask.
"""
from __future__ import annotations

from fastapi import APIRouter

from api.schemas.auth import UserRead, UserUpdate
from api.core.users import fastapi_users

router = APIRouter(prefix="/api/v2/users", tags=["users"])

router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="",
)
