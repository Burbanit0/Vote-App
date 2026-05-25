"""
api_v2.main — FastAPI app entrypoint.

Run locally:

    cd flask_voter_app
    uvicorn api_v2.main:app --reload --port 4434

The app intentionally mounts everything under `/api/v2/...` so it can run
alongside the existing Flask app (port 4433, mount `/api/...`) without
URL collision during the strangler-fig migration.
"""
from __future__ import annotations

import sys
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Re-use the project's existing structlog config so logs look identical
# to the Flask side. Sys.path is already correct when api_v2 is invoked
# from flask_voter_app/ as the cwd.
from app.utils.logger import configure_logging, get_logger
from api_v2.core.config import get_settings
from api_v2.routes import election as election_routes
from api_v2.routes import health as health_routes
from api_v2.routes import theory as theory_routes


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Runs once at startup, once at shutdown. Use to warm caches, open
    DB pools, etc. For now: just verify config and emit a banner."""
    settings = get_settings()
    configure_logging(level=settings.log_level)
    log = get_logger("api_v2.main")

    # Mirror the production validation Flask's create_app does, so the v2
    # backend also refuses to boot with weak secrets in prod.
    if settings.is_production:
        weak = {
            "secret_key":     "dev-secret-CHANGE-IN-PROD",
            "jwt_secret_key": "dev-jwt-secret-CHANGE-IN-PROD",
        }
        bad = [k for k, v in weak.items() if getattr(settings, k) == v]
        if bad:
            log.error("startup.weak_secrets", vars=bad)
            sys.exit(1)

    log.info(
        "api_v2.startup",
        env=settings.flask_env,
        cors_origins=settings.allowed_origins,
        log_level=settings.log_level,
    )
    yield
    log.info("api_v2.shutdown")


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


# ── CORS ────────────────────────────────────────────────────────────────────
# Mirrors the Flask config — origins read from CORS_ORIGINS env var.
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# ── Access log middleware ───────────────────────────────────────────────────
_access_log = get_logger("api_v2.access")


@app.middleware("http")
async def log_requests(request, call_next):
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
app.include_router(theory_routes.router)


@app.get("/api/v2", tags=["meta"])
def root() -> dict:
    """Tiny landing endpoint so visiting /api/v2 directly doesn't 404."""
    return {
        "name":    "Vote Lab API v2",
        "version": "2.0.0-alpha",
        "docs":    "/api/v2/docs",
        "health":  "/api/v2/health",
    }
