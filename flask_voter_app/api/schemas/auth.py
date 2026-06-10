"""
Pydantic schemas for fastapi-users register / read / update on top of the
existing Flask User model.

The model carries some legacy fields (username, role, first_name, last_name,
bio, profile_picture, google_id, github_id) that we keep exposing through
Read/Update so the existing frontend doesn't lose information mid-migration.
The fastapi-users core fields (email, password, is_active, is_superuser,
is_verified) are inherited from `schemas.BaseUser*`.
"""
from __future__ import annotations

from typing import Optional

from fastapi_users import schemas
from pydantic import ConfigDict, Field


class UserRead(schemas.BaseUser[int]):
    """Public view of a user (what /users/me and similar return)."""
    model_config = ConfigDict(from_attributes=True)

    username:        str
    role:            str = Field(..., description="Legacy 'Admin' | 'User' — shadowed by is_superuser.")
    first_name:      Optional[str] = None
    last_name:       Optional[str] = None
    bio:             Optional[str] = None
    profile_picture: Optional[str] = None


class UserCreate(schemas.BaseUserCreate):
    """Registration body. Email + password come from BaseUserCreate."""
    username:   str = Field(..., min_length=1, max_length=50)
    role:       str = Field("User", description="'User' or 'Admin' — admin creation gated server-side.")
    first_name: Optional[str] = Field(None, max_length=100)
    last_name:  Optional[str] = Field(None, max_length=100)


class UserUpdate(schemas.BaseUserUpdate):
    """PATCH body for /users/me. Everything optional."""
    username:        Optional[str] = Field(None, min_length=1, max_length=50)
    first_name:      Optional[str] = Field(None, max_length=100)
    last_name:       Optional[str] = Field(None, max_length=100)
    bio:             Optional[str] = None
    profile_picture: Optional[str] = Field(None, max_length=200)
