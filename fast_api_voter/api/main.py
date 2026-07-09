"""
api.main — FastAPI app entrypoint.

Run locally:

    cd fast_api_voter
    uvicorn api.main:app --reload --port 4434

The app intentionally mounts everything under `/api/v2/...` so it can run
alongside the existing Flask app (port 4433, mount `/api/...`) without
URL collision during the strangler-fig migration.
"""
from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# Re-use the project's existing structlog config so logs look identical
# to the Flask side. Sys.path is already correct when api is invoked
# from fast_api_voter/ as the cwd.
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.engine.utils.logger import configure_logging, get_logger
from api.core.config import get_settings
from api.core.ratelimit import limiter
from api.routes import election as election_routes
from api.routes import export as export_routes
from api.routes import health as health_routes
from api.routes import public as public_routes
from api.routes import simulations as simulations_routes
from api.routes import tech as tech_routes
from api.routes import theory as theory_routes
from api.sockets import sio


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Runs once at startup, once at shutdown. Use to warm caches, open
    DB pools, etc. For now: just verify config and emit a banner."""
    settings = get_settings()
    configure_logging(level=settings.log_level)
    log = get_logger("api.main")

    log.info(
        "api.startup",
        env=settings.app_env,
        cors_origins=settings.allowed_origins,
        log_level=settings.log_level,
    )
    yield
    log.info("api.shutdown")


app = FastAPI(
    title="Vote Lab API v2",
    description=(
        "FastAPI sibling backend introduced in Phase 2 of the strategic "
        "refactor. Routes are migrated incrementally from Flask; see "
        "STRATEGIC_REFACTOR_PLAN.md for the schedule."
    ),
    version="2.0.0-alpha",
    docs_url="/api/v2/docs",          # Swagger UI
    redoc_url="/api/v2/redoc",        # ReDoc
    openapi_url="/api/v2/openapi.json",
    lifespan=lifespan,
)


# ── Rate limiting (public /api/v1 surface — Phase 4.5.a.4) ───────────────────
# slowapi attaches the limiter to app.state and converts a tripped limit into
# a 429. Only the public router declares @limiter.limit decorators today.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]


# ── CORS ────────────────────────────────────────────────────────────────────
# Mirrors the Flask config — origins read from CORS_ORIGINS env var.
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.allowed_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


# ── Access log middleware ───────────────────────────────────────────────────
_access_log = get_logger("api.access")


@app.middleware("http")
async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """One JSON line per request, with duration_ms. Skips /api/v2/health
    to keep uptime-monitor noise out of the stream."""
    t0 = time.perf_counter()
    response = await call_next(request)
    if request.url.path != "/api/v2/health":
        _access_log.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round((time.perf_counter() - t0) * 1000, 1),
        )
    return response


# ── Routers ─────────────────────────────────────────────────────────────────
app.include_router(health_routes.router)
app.include_router(election_routes.router)
app.include_router(export_routes.router)
app.include_router(public_routes.router)
app.include_router(simulations_routes.router)
app.include_router(tech_routes.router)
app.include_router(theory_routes.router)


@app.get("/api/v2", tags=["meta"])
def root() -> dict[str, Any]:
    """Tiny landing endpoint so visiting /api/v2 directly doesn't 404."""
    return {
        "name":    "Vote Lab API v2",
        "version": "2.0.0-alpha",
        "docs":    "/api/v2/docs",
        "health":  "/api/v2/health",
        "socketio": "/api/v2/socket.io",
    }


# ── Static frontend (single-container deploy) ───────────────────────────────
# When FRONTEND_DIR points at a built Vite bundle, this same process serves the
# SPA + its assets, so the API and the app share one origin (no CORS, same-origin
# websockets). Unset (dev / tests) → API-only, unchanged. Registered LAST so every
# /api route and the docs win over this catch-all.
_frontend_dir = os.environ.get("FRONTEND_DIR", "")
if _frontend_dir and os.path.isdir(_frontend_dir):
    _frontend_dir = os.path.abspath(_frontend_dir)
    _index_html = os.path.join(_frontend_dir, "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        """Serve a real build file when it exists (assets, icons, manifest,
        service worker); otherwise return index.html so the client-side router
        owns the route (deep links / refresh on /playground, /laboratoire …)."""
        candidate = os.path.abspath(os.path.join(_frontend_dir, full_path))
        # Guard path traversal: never serve outside the build dir.
        if (
            full_path
            and (candidate == _frontend_dir or candidate.startswith(_frontend_dir + os.sep))
            and os.path.isfile(candidate)
        ):
            return FileResponse(candidate)
        return FileResponse(_index_html)


# ── Socket.IO (Phase 4.4) ─────────────────────────────────────────────────
# Wrap the FastAPI app with python-socketio's ASGIApp. Socket.IO traffic
# under /api/v2/socket.io is handled by `sio`; everything else (HTTP) falls
# through to the FastAPI `app` defined above. This is how python-socketio
# integrates with any other ASGI framework — see
# https://python-socketio.readthedocs.io/en/stable/server.html#asgi-applications
# Keep a stable handle to the raw FastAPI instance — `app` below becomes the
# Socket.IO ASGI wrapper, which has no `.openapi()`. scripts/gen_openapi.py and
# any tooling that needs the spec import `api.main:fastapi_app`.
fastapi_app = app

import socketio as _socketio_lib  # noqa: E402
app = _socketio_lib.ASGIApp(sio, fastapi_app, socketio_path="/api/v2/socket.io")
