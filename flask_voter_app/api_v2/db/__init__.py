"""
api_v2.db — the Flask-independent async SQLAlchemy data layer (Phase 4.5.b.2).

Replaces the Flask-SQLAlchemy models + the `run_in_flask_db` bridge. Models are
defined on a plain Declarative `Base`; sessions come from an async engine
(asyncpg in prod, aiosqlite in tests). Nothing here imports Flask.

During the transition (until Flask is deleted in 4.5.b.3) these models map the
SAME tables as `app/models.py` (Flask-SQLAlchemy) — they live in independent
mapper registries, so both can coexist in one process.
"""
from api_v2.db.base import Base
from api_v2.db.models import GalleryScenario, SimulationScenario, User
from api_v2.db.session import (
    async_session_maker,
    get_async_session,
    get_engine,
)

__all__ = [
    "Base",
    "User",
    "SimulationScenario",
    "GalleryScenario",
    "get_engine",
    "async_session_maker",
    "get_async_session",
]
