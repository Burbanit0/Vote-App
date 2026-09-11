"""
api.core.config — Pydantic Settings.

Reads env vars (12-factor) and exposes a typed Settings object. All
runtime configuration lives here; no `os.environ.get(...)` scattered
around the codebase.

Shares env var names with the existing Flask app so a single .env file
works for both — see fast_api_voter/.env.example.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Environment ─────────────────────────────────────────────────────────
    # development | testing | production. Reads APP_ENV, with a FLASK_ENV
    # fallback for backward compatibility with older env files / CI.
    app_env: str = Field(
        default="development",
        validation_alias=AliasChoices("APP_ENV", "FLASK_ENV"),
    )

    # ── HTTP ────────────────────────────────────────────────────────────────
    # Comma-separated allowed origins, matches the Flask CORS_ORIGINS var.
    cors_origins: str = Field(default="http://localhost:3000")

    # ── Cache ───────────────────────────────────────────────────────────────
    # The app is stateless (no SQL DB, no auth); Redis is only a compute cache
    # for the voting engine and degrades gracefully to no-cache if unavailable.
    redis_url: str = Field(default="redis://redis:6379")

    # ── Logging ─────────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")

    # ── Error tracking (Lot 10.1, PLAN_SOLIDITE_TECHNIQUE.md) ─────────────────
    # Self-hosted GlitchTip (docker-compose.observability.yml), never Sentry
    # SaaS — an empty DSN means "disabled, no error", same optional-dependency
    # pattern as redis_url above (see api/routes/health.py's _check_redis
    # comment). sentry-sdk is the correct client either way: GlitchTip
    # implements the same event-ingestion API, only the DSN host differs.
    glitchtip_dsn: str = Field(default="")

    # ── Metrics (Lot 10, PLAN_SOLIDITE_TECHNIQUE.md — "/metrics Prometheus") ──
    # Optional shared secret gating GET /api/v2/metrics. Unset (default) =
    # unauthenticated, matching this app's overall posture (no auth system
    # exists anywhere else either) — fine for local/dev. Set it in production
    # to require `Authorization: Bearer <token>` and avoid handing anyone on
    # the public internet a live view of endpoint traffic. See
    # api/routes/metrics.py's `_check_metrics_auth`.
    metrics_auth_token: Optional[str] = Field(default=None)

    # ── Observability — tracing (Lot 10.2, PLAN_SOLIDITE_TECHNIQUE.md) ───────
    # Same optional-dependency pattern as redis_url above: empty (the default)
    # means tracing is fully disabled, no TracerProvider is installed, and the
    # FastAPI auto-instrumentation is never applied. Point this at an OTLP/HTTP
    # collector's base URL (e.g. "http://localhost:4318" for the Jaeger
    # all-in-one in docker-compose.observability-tracing.yml) to enable it —
    # "/v1/traces" is appended by api/core/tracing.py, don't include it here.
    otel_exporter_otlp_endpoint: str = Field(default="")
    otel_service_name: str = Field(default="vote-lab-api")

    # ── Derived ─────────────────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def allowed_origins(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached so import-time cost is paid once. Use FastAPI's Depends()
    in routes when you want to inject a fresh copy in tests:

        from api.core.config import get_settings
        def my_route(settings: Annotated[Settings, Depends(get_settings)]):
            ...
    """
    return Settings()
