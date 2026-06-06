# ADR 001 — FastAPI over Flask

**Status:** Accepted (Phase 3–4.5, 2026-05)

## Context

The original backend was Flask + Flask-SQLAlchemy + eventlet, with hand-written
request parsing and no machine-readable API contract. The simulation surface (35
election endpoints + 15 theory endpoints) was growing and the frontend duplicated
every request/response shape by hand.

## Decision

Migrate the backend to **FastAPI** (uvicorn, ASGI) with SQLAlchemy 2.0 **async**
and python-socketio for the WebSocket stream. Flask + eventlet were fully retired.

## Consequences

- Request/response validation comes from Pydantic for free, and FastAPI emits an
  OpenAPI schema we generate TypeScript types from (see [ADR 002](002-pydantic-source-of-truth.md)).
- Async I/O (asyncpg/aiosqlite) replaces eventlet monkey-patching; the Monte Carlo
  stream runs on a native ASGI socket.io server.
- `main.py` wraps the FastAPI app in `socketio.ASGIApp`, so the FastAPI instance is
  exposed under a stable name (`fastapi_app`) for offline OpenAPI dumps.
- The package is still named `flask_voter_app/` for historical/path reasons — there
  is no Flask inside it.
