"""
api_v2.core.db — bridge to the Flask SQLAlchemy session.

Phase 4 intermediate: the SimulationScenario / User / GalleryScenario
models are still defined on Flask-SQLAlchemy's `db` (in app.models).
Rather than duplicate them, we lend the existing Flask app context
to FastAPI routes. When Phase 4.5 retires Flask, models move to a
Flask-independent layer and this module becomes a no-op.

Usage pattern:

    from api_v2.core.db import run_in_flask_db

    async def my_endpoint(...):
        return await run_in_flask_db(lambda: do_some_query())

`run_in_flask_db` runs the callable in a real worker thread (no event
loop blocking) with a Flask application context active so
`SQLAlchemy db.session` works as it does on the Flask side.
"""
from __future__ import annotations

import asyncio
from typing import Callable, TypeVar

T = TypeVar("T")

_app = None  # lazily-constructed Flask app singleton


def _get_app():
    """Build one Flask app and reuse it for every DB call."""
    global _app
    if _app is None:
        # Import lazily so api_v2 doesn't import Flask at module load.
        from app import create_app
        _app = create_app()
    return _app


def _wrap_with_context(func: Callable[[], T]) -> T:
    """Synchronously run `func()` inside a Flask app context."""
    app = _get_app()
    with app.app_context():
        return func()


async def run_in_flask_db(func: Callable[[], T]) -> T:
    """Run a sync DB callable in a worker thread with a Flask app context.

    Mirrors `asyncio.to_thread(func)` but adds the Flask app context
    that Flask-SQLAlchemy needs for `db.session`. The callable should
    be self-contained — typically a small closure that opens a query,
    serializes the result, and commits/rollbacks as needed.
    """
    return await asyncio.to_thread(_wrap_with_context, func)
