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

import sentry_sdk
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import Scope

# Re-use the project's existing structlog config so logs look identical
# to the Flask side. Sys.path is already correct when api is invoked
# from fast_api_voter/ as the cwd.
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.engine.utils.logger import configure_logging, get_logger
from api.core.config import Settings, get_settings
from api.core.ratelimit import limiter
from api.core.tracing import configure_tracing, instrument_app
from api.routes import election as election_routes
from api.routes import export as export_routes
from api.routes import health as health_routes
from api.routes.metrics import setup_metrics
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


# ── Error tracking (Lot 10.1, PLAN_SOLIDITE_TECHNIQUE.md) ────────────────────
# Self-hosted GlitchTip (docker-compose.observability.yml), never Sentry SaaS.
# Empty GLITCHTIP_DSN (the default) means "disabled, no error" — same
# optional-dependency pattern as REDIS_URL (api/routes/health.py's
# _check_redis comment). No explicit `integrations=[...]` needed: sentry-sdk
# auto-detects installed frameworks ("auto-enabling integrations") and wires
# up FastAPI + Starlette on its own — verified live against sentry-sdk
# 2.69.1, not assumed. That, plus its default LoggingIntegration, means a
# single call captures BOTH an exception that reaches this file's catch-all
# handler below AND every already-existing `log.error(..., exc_info=True)`
# call inside a domain worker's own try/except (api/domain/**), with zero
# per-file changes — confirmed live (see api/tests/test_error_tracking.py and
# docs/exploration/EXP-013).
def _init_sentry(settings: Settings) -> None:
    if settings.glitchtip_dsn:
        sentry_sdk.init(dsn=settings.glitchtip_dsn, environment=settings.app_env)


# Must run before `FastAPI(...)` so instrumentation is live for the very
# first request.
_init_sentry(get_settings())


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


# ── Catch-all exception handler ──────────────────────────────────────────────
# Most domain workers already catch their own exceptions and return a (body,
# 500) tuple, which never reaches this handler — see the `log.error(...,
# exc_info=True)` calls added alongside each of those. This handler is the
# backstop for anything that still escapes uncaught (a route or middleware bug,
# not a worker's own try/except), so a genuinely unhandled exception is logged
# with a traceback instead of surfacing only as a bare 500 in the access log.
_unhandled_log = get_logger("api.unhandled")


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    _unhandled_log.error(
        "http.unhandled_exception",
        method=request.method,
        path=request.url.path,
        exc_info=True,
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ── CORS ────────────────────────────────────────────────────────────────────
# Mirrors the Flask config — origins read from CORS_ORIGINS env var.
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.allowed_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


# ── Tracing (Lot 10.2, PLAN_SOLIDITE_TECHNIQUE.md — "Observabilité") ────────
# No-op unless OTEL_EXPORTER_OTLP_ENDPOINT is set — see api/core/tracing.py's
# module docstring for the Jaeger-vs-hosted-APM reasoning and the full
# no-op-by-default contract. `app` is still the raw FastAPI instance here
# (the socket.io ASGI wrap that reassigns `app` happens at the bottom of this
# file, well after this point) — instrument_app() must run against the real
# FastAPI object, not that wrapper, since it patches FastAPI's own routing.
configure_tracing()
instrument_app(app)


# ── Security headers ──────────────────────────────────────────────────────
# Lot 9, PLAN_SOLIDITE_TECHNIQUE.md ("DAST — ZAP baseline"): confirmed live via
# a real OWASP ZAP baseline scan (docs/exploration/EXP-009) that every response
# was missing this header — a real, previously-invisible finding, not a
# hypothetical one (SAST tools never look at response headers, only source).
# `nosniff` stops a browser from MIME-sniffing a response into a more
# dangerous content-type than the one this API actually declares — zero
# behavioural risk (every route already sets an explicit Content-Type) so
# there is nothing to verify beyond "the header is present". The remaining
# baseline findings (CSP, Permissions-Policy, anti-clickjacking, …) are left
# as documented, non-blocking backlog — see EXP-009 — deliberately not
# addressed here to keep this change reviewable as the single, narrow fix the
# ZAP verification loop targets, not a full header-hardening pass.
@app.middleware("http")
async def security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


# ── Rate-limit state default (Lot 3, PLAN_SOLIDITE_TECHNIQUE.md — "Résilience
# Redis") ─────────────────────────────────────────────────────────────────────
# Pairs with `swallow_errors=True` on the Limiter in api/core/ratelimit.py.
# slowapi's own decorator always reads `request.state.view_rate_limit` after
# the rate-limit check runs (to populate response headers) — normally that
# attribute was just set by the check itself, but when the check's own
# exception gets swallowed (Redis unreachable), it never was, and Starlette's
# State.__getattr__ raises a bare AttributeError for a missing key. This
# middleware runs before any route dependency (including check_v2_rate_limit),
# so the attribute always exists — a real gap in slowapi's swallow_errors
# path, not something fixable in api/core/ratelimit.py alone. Confirmed live:
# without this, `swallow_errors=True` on its own still crashed every request.
@app.middleware("http")
async def default_rate_limit_state(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request.state.view_rate_limit = None
    return await call_next(request)


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
        "metrics": "/api/v2/metrics",
        "socketio": "/api/v2/socket.io",
    }


# ── Metrics (Lot 10, PLAN_SOLIDITE_TECHNIQUE.md — "/metrics Prometheus") ────
# Must run BEFORE the catch-all SPA mount below: Instrumentator.expose() adds
# a plain route, and a "/" mount registered first would shadow it (Starlette
# matches routes in registration order). See api/routes/metrics.py.
setup_metrics(app)


# ── Static frontend (single-container deploy) ───────────────────────────────
# When FRONTEND_DIR points at a built Vite bundle, this same process serves the
# SPA + its assets, so the API and the app share one origin (no CORS, same-origin
# websockets). Unset (dev / tests) → API-only, unchanged. Mounted LAST so every
# /api route and the docs win over this catch-all mount.
_frontend_dir = os.environ.get("FRONTEND_DIR", "")
if _frontend_dir and os.path.isdir(_frontend_dir):

    class _SPAStaticFiles(StaticFiles):
        """Serve the built bundle (assets, icons, manifest, service worker) and
        fall back to index.html for client-side routes (deep links / refresh on
        /playground, /laboratoire …). StaticFiles does its own path-traversal
        containment, and the fallback path is a constant — no user-supplied value
        is ever used to build a filesystem path."""

        async def get_response(self, path: str, scope: Scope) -> Response:
            try:
                return await super().get_response(path, scope)
            except StarletteHTTPException as exc:
                # Missing file → hand back the SPA shell so the client router owns
                # the route. Re-raise anything else (e.g. 405).
                if exc.status_code == 404:
                    return await super().get_response("index.html", scope)
                raise

    app.mount("/", _SPAStaticFiles(directory=_frontend_dir, html=True), name="spa")


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
