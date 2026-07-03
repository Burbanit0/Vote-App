"""
Shared async-DB test harness for api (Phase 4.5.b.2).

Provides a Flask-independent test database: a file-backed aiosqlite engine with
NullPool (so connections are never reused across TestClient's per-request event
loop and the fixtures' asyncio.run loops — that reuse is the classic source of
"Future attached to a different loop" errors with aiosqlite). Data is shared via
the on-disk SQLite file.

Only tests that request these fixtures get them — non-DB api suites are
untouched.
"""
import asyncio
from typing import Callable

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from api.core.config import get_settings
from api.db import Base, GalleryScenario, User
from api.db import session as db_session

JWT_SECRET = "test-secret-key-at-least-32-bytes-long!!"


def _run(coro):
    """Run a coroutine to completion on a throwaway loop (fixtures are sync)."""
    return asyncio.run(coro)


@pytest.fixture
def db(tmp_path, monkeypatch):
    """File-backed aiosqlite engine wired into api.db.session for the test,
    with the schema created and the JWT secret aligned."""
    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    engine = create_async_engine(url, poolclass=NullPool)

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    _run(_init())
    db_session.set_engine(engine)
    monkeypatch.setattr(get_settings(), "jwt_secret_key", JWT_SECRET)

    yield engine

    _run(engine.dispose())


def make_token(user_id: int, secret: str = JWT_SECRET) -> str:
    """Mint a Bearer token in the shape api.core.auth expects (sub=str(id))."""
    return jwt.encode({"sub": str(user_id)}, secret, algorithm="HS256")


@pytest.fixture
def seed_user(db) -> Callable[..., int]:
    """Insert a user via the async session and return its id."""
    def _seed(username: str = "user", email: str | None = None,
              role: str = "User", is_superuser: bool = False,
              hashed_password: str = "x") -> int:
        async def _do() -> int:
            async with db_session.async_session_maker()() as s:
                u = User(
                    username=username,
                    email=email or f"{username}@vote-app.local",
                    hashed_password=hashed_password,
                    role=role,
                    is_superuser=is_superuser,
                )
                s.add(u)
                await s.commit()
                return u.id
        return _run(_do())
    return _seed


@pytest.fixture
def seed_gallery(db) -> Callable[..., int]:
    """Insert a GalleryScenario via the async session and return its id."""
    def _seed(**overrides) -> int:
        async def _do() -> int:
            async with db_session.async_session_maker()() as s:
                g = GalleryScenario(
                    title=overrides.get("title", "Demo scenario"),
                    description=overrides.get("description", "A test scenario"),
                    params=overrides.get("params", {"num_voters": 100}),
                    results_summary=overrides.get("results_summary", {"winner": "A"}),
                    tags=overrides.get("tags", ["condorcet", "arrow"]),
                    is_featured=overrides.get("is_featured", False),
                    views=overrides.get("views", 0),
                )
                s.add(g)
                await s.commit()
                return g.id
        return _run(_do())
    return _seed


@pytest.fixture
def fetch_user(db) -> Callable[[str], dict | None]:
    """Return a snapshot dict of a user (by email) via the async session, or None."""
    def _fetch(email: str) -> dict | None:
        async def _do() -> dict | None:
            async with db_session.async_session_maker()() as s:
                u = (await s.execute(select(User).where(User.email == email))).scalar_one_or_none()
                if u is None:
                    return None
                return {
                    "id": u.id, "email": u.email, "username": u.username,
                    "is_superuser": u.is_superuser, "role": u.role,
                    "first_name": u.first_name, "google_id": u.google_id,
                    "github_id": u.github_id,
                }
        return _run(_do())
    return _fetch


@pytest.fixture
def promote_admin(db) -> Callable[[str], None]:
    """Promote a user (by email) to superuser + role='Admin' via the async session."""
    def _promote(email: str) -> None:
        async def _do() -> None:
            async with db_session.async_session_maker()() as s:
                u = (await s.execute(select(User).where(User.email == email))).scalar_one()
                u.is_superuser = True
                u.role = "Admin"
                await s.commit()
        _run(_do())
    return _promote


@pytest.fixture
def client(db):
    """FastAPI TestClient bound to the test DB engine (set via the `db` fixture)."""
    from api.main import app
    with TestClient(app) as c:
        yield c
