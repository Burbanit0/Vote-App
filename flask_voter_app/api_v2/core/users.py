"""
api_v2.core.users — fastapi-users wiring on the async DB layer (Phase 4.5.b.2).

The user-database adapter now talks to the Flask-independent async SQLAlchemy
session (`api_v2.db`) instead of the old `run_in_flask_db` Flask bridge. It stays
a *custom* adapter (rather than the stock SQLAlchemyUserDatabase) because our
table keeps legacy column names/extra columns: `password_hash` (exposed as the
`hashed_password` attribute), `role` (kept in sync with `is_superuser`), and
`google_id`/`github_id` columns instead of a separate oauth_accounts table.

Exposed objects:
  - `fastapi_users` : the central FastAPIUsers wrapper used by routers
  - `auth_backend`  : Bearer transport + HS256 JWT strategy (same secret as
                      Flask-JWT-Extended, so tokens stay interchangeable)
  - `current_active_user` / `current_superuser` : route dependencies
"""
from __future__ import annotations

from typing import Annotated, Any, AsyncGenerator, Optional

from fastapi import Depends
from fastapi_users import BaseUserManager, FastAPIUsers, IntegerIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import BaseUserDatabase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_v2.core.config import Settings, get_settings
from api_v2.db import User
from api_v2.db.session import get_async_session


# ── User database adapter ──────────────────────────────────────────────────

class AsyncUserDatabase(BaseUserDatabase):
    """fastapi-users adapter over an async SQLAlchemy session + our User model.

    The User model exposes `hashed_password` (mapped to the DB column
    `password_hash`), so fastapi-users' attribute access is transparent.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id: int) -> Optional[User]:
        return await self.session.get(User, id)

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_oauth_account(self, oauth: str, account_id: str) -> Optional[User]:
        """OAuth ids live in columns (google_id / github_id), preserving the
        legacy Flask-side semantics rather than a separate oauth_accounts table."""
        column = getattr(User, f"{oauth}_id")
        result = await self.session.execute(select(User).where(column == account_id))
        return result.scalar_one_or_none()

    async def create(self, create_dict: dict[str, Any]) -> User:
        # The legacy `role` column is still NOT NULL — default it from is_superuser.
        if "role" not in create_dict:
            create_dict = {
                **create_dict,
                "role": "Admin" if create_dict.get("is_superuser") else "User",
            }
        user = User(**create_dict)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update(self, user: User, update_dict: dict[str, Any]) -> User:
        for key, value in update_dict.items():
            setattr(user, key, value)
        # Keep the legacy `role` column in sync when admin status flips.
        if "is_superuser" in update_dict:
            user.role = "Admin" if update_dict["is_superuser"] else "User"
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self.session.delete(user)
        await self.session.commit()


async def get_user_db(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AsyncGenerator[AsyncUserDatabase, None]:
    yield AsyncUserDatabase(session)


# ── User manager ───────────────────────────────────────────────────────────

class UserManager(IntegerIDMixin, BaseUserManager):
    """Lifecycle hooks for register / login / password reset / verify.

    Reset + verification token secrets reuse `settings.jwt_secret_key` so we
    don't introduce another env var — same secret as the Bearer JWT below.
    """
    reset_password_token_secret:  str = ""   # set in __init__
    verification_token_secret:    str = ""

    def __init__(self, user_db: AsyncUserDatabase, settings: Settings) -> None:
        super().__init__(user_db)
        self.reset_password_token_secret = settings.jwt_secret_key
        self.verification_token_secret   = settings.jwt_secret_key


async def get_user_manager(
    user_db: Annotated[AsyncUserDatabase, Depends(get_user_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db, settings)


# ── Auth backend ───────────────────────────────────────────────────────────

_bearer_transport = BearerTransport(tokenUrl="/api/v2/auth/jwt/login")


def _get_jwt_strategy(
    settings: Annotated[Settings, Depends(get_settings)],
) -> JWTStrategy:
    """One-hour HS256 tokens, same secret as Flask-JWT-Extended so the
    cross-backend token bridge stays valid."""
    return JWTStrategy(secret=settings.jwt_secret_key, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=_bearer_transport,
    get_strategy=_get_jwt_strategy,
)


# ── FastAPIUsers entrypoint ────────────────────────────────────────────────

fastapi_users = FastAPIUsers[Any, int](
    get_user_manager,
    [auth_backend],
)

current_active_user = fastapi_users.current_user(active=True)
current_superuser   = fastapi_users.current_user(active=True, superuser=True)
