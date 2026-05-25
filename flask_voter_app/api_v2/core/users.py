"""
api_v2.core.users — fastapi-users wiring for the existing Flask User model.

Bridges fastapi-users' async BaseUserDatabase to our sync Flask SQLAlchemy
session via `run_in_flask_db` (introduced in Phase 4.2). No async engine,
no model duplication — the same User row backs both `/api/*` and `/api/v2/*`.

Exposed objects:
  - `fastapi_users` : the central FastAPIUsers wrapper used by routers
  - `auth_backend`  : Bearer transport + HS256 JWT strategy (same secret
                      as Flask-JWT-Extended, so tokens are interchangeable)
  - `current_active_user` / `current_superuser` : route dependencies

Phase 4.3.b: register / login / logout / verify routes.
Phase 4.3.c: profile + admin CRUD on top of these primitives.
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

from api_v2.core.config import Settings, get_settings
from api_v2.core.db import run_in_flask_db


# ── User database adapter ──────────────────────────────────────────────────

class FlaskUserDatabase(BaseUserDatabase):
    """fastapi-users adapter on top of the Flask-SQLAlchemy session.

    Every method runs the actual SQLAlchemy work in a worker thread with
    a Flask app context active. The User model carries the
    `hashed_password` Python alias defined in `app.models.User`, so
    fastapi-users' attribute access works transparently.
    """

    async def get(self, id: int) -> Optional[Any]:
        def _q():
            from app.models import User
            return User.query.get(id)
        return await run_in_flask_db(_q)

    async def get_by_email(self, email: str) -> Optional[Any]:
        def _q():
            from app.models import User
            return User.query.filter_by(email=email).first()
        return await run_in_flask_db(_q)

    async def get_by_oauth_account(self, oauth: str, account_id: str) -> Optional[Any]:
        """We store OAuth IDs as columns (google_id / github_id) rather
        than in a separate oauth_accounts table — keep the legacy
        Flask-side semantics during the migration."""
        column = f"{oauth}_id"
        def _q():
            from app.models import User
            return User.query.filter_by(**{column: account_id}).first()
        return await run_in_flask_db(_q)

    async def create(self, create_dict: dict[str, Any]) -> Any:
        def _q():
            from app import db
            from app.models import User
            user = User(**create_dict)
            # fastapi-users supplies hashed_password — the alias takes care of
            # writing to the actual column. Provide a non-null `role` default
            # since the legacy column is still NOT NULL.
            if "role" not in create_dict:
                user.role = "Admin" if create_dict.get("is_superuser") else "User"
            db.session.add(user)
            db.session.commit()
            db.session.refresh(user)
            return user
        return await run_in_flask_db(_q)

    async def update(self, user: Any, update_dict: dict[str, Any]) -> Any:
        def _q():
            from app import db
            from app.models import User
            # Re-attach the user to the current session, then apply updates.
            attached = db.session.merge(user)
            for key, value in update_dict.items():
                setattr(attached, key, value)
            # Keep the legacy `role` column in sync when admin status flips.
            if "is_superuser" in update_dict:
                attached.role = "Admin" if update_dict["is_superuser"] else "User"
            db.session.commit()
            db.session.refresh(attached)
            return attached
        return await run_in_flask_db(_q)

    async def delete(self, user: Any) -> None:
        def _q():
            from app import db
            attached = db.session.merge(user)
            db.session.delete(attached)
            db.session.commit()
            return None
        await run_in_flask_db(_q)


async def get_user_db() -> AsyncGenerator[FlaskUserDatabase, None]:
    """fastapi-users dependency. Instantiated per request — cheap, no I/O."""
    yield FlaskUserDatabase()


# ── User manager ───────────────────────────────────────────────────────────

class UserManager(IntegerIDMixin, BaseUserManager):
    """Lifecycle hooks for register / login / password reset / verify.

    Secrets reuse `settings.jwt_secret_key` for the password-reset and
    verification tokens so we don't introduce yet-another env var. Same
    secret as the Bearer JWT below.
    """
    reset_password_token_secret:  str = ""   # set in __init__
    verification_token_secret:    str = ""

    def __init__(self, user_db: FlaskUserDatabase, settings: Settings) -> None:
        super().__init__(user_db)
        self.reset_password_token_secret = settings.jwt_secret_key
        self.verification_token_secret   = settings.jwt_secret_key


async def get_user_manager(
    user_db: Annotated[FlaskUserDatabase, Depends(get_user_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db, settings)


# ── Auth backend ───────────────────────────────────────────────────────────

# Token URL points at the fastapi-users login route we mount in
# api_v2/routes/auth.py.
_bearer_transport = BearerTransport(tokenUrl="/api/v2/auth/jwt/login")


def _get_jwt_strategy(
    settings: Annotated[Settings, Depends(get_settings)],
) -> JWTStrategy:
    """One-hour tokens, HS256, same secret as Flask-JWT-Extended so the
    Phase 4.2 bridge stays valid for migrated routes."""
    return JWTStrategy(
        secret=settings.jwt_secret_key,
        lifetime_seconds=3600,
    )


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

# Route dependencies — re-export the common ones for convenience.
current_active_user = fastapi_users.current_user(active=True)
current_superuser   = fastapi_users.current_user(active=True, superuser=True)
