"""
api.core.config — Pydantic Settings.

Reads env vars (12-factor) and exposes a typed Settings object. All
runtime configuration lives here; no `os.environ.get(...)` scattered
around the codebase.

Shares env var names with the existing Flask app so a single .env file
works for both — see flask_voter_app/.env.example.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",          # Flask vars unknown to us are fine
        case_sensitive=False,
    )

    # ── Environment ─────────────────────────────────────────────────────────
    # development | testing | production. Same vocabulary as Flask's FLASK_ENV.
    flask_env: str = Field(default="development")

    # ── HTTP ────────────────────────────────────────────────────────────────
    # Comma-separated allowed origins, matches the Flask CORS_ORIGINS var.
    cors_origins: str = Field(default="http://localhost:3000")

    # ── Database / cache ────────────────────────────────────────────────────
    database_url: str = Field(default="postgresql://myuser:mypassword@db:5432/mydatabase")
    redis_url:    str = Field(default="redis://redis:6379")

    # ── Secrets (validated in production via main.py startup) ──────────────
    secret_key:     str = Field(default="dev-secret-CHANGE-IN-PROD")
    jwt_secret_key: str = Field(default="dev-jwt-secret-CHANGE-IN-PROD")

    # ── OAuth (Phase 4.3.d) ────────────────────────────────────────────────
    # Same env vars Flask reads (see config.py). Either empty → 501 on the
    # corresponding /auth/{provider} route, so dev environments without
    # OAuth credentials degrade gracefully instead of 500-ing.
    google_client_id:     str = Field(default="")
    github_client_id:     str = Field(default="")
    github_client_secret: str = Field(default="")
    base_url:             str = Field(default="http://localhost:4433")
    frontend_url:         str = Field(default="http://localhost:3000")

    # ── Logging ─────────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")

    # ── Derived ─────────────────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.flask_env == "production"

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
