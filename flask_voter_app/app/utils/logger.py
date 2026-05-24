"""
Structured logger for Vote Lab.

Wraps structlog with a dev-friendly console renderer in development and
machine-parseable JSON in production. Use this instead of
`current_app.logger.*` everywhere — it works without a Flask app context
(important for code that runs inside `eventlet.tpool` real threads or in
future FastAPI workers).

Usage:
    from app.utils.logger import get_logger
    log = get_logger(__name__)

    log.info("simulation.completed", method="irv", winner="Alice", duration_ms=237)
    log.warning("cache.miss", key="election:simulate:abc123")
    log.error("simulate.crashed", method="combined_effects", exc_info=True)

Why structured logging:
  - One log line = one dict with named fields, not a printf string.
  - Easy to grep + parse in production (`jq '. | select(.event == "...")'`).
  - When we add Sentry / Loki / ELK later, the pipeline is already JSON.
  - Replaces 30+ inconsistent `print()` / `logger.info(f"{x} {y}")` calls.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Any

import structlog


_CONFIGURED = False


def configure_logging(level: str | None = None) -> None:
    """Idempotent setup. Called once at app startup.

    Environment-aware:
      - FLASK_ENV=production  → JSON output (one log line = one JSON object)
      - otherwise             → human-friendly coloured console output
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_level = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    is_prod = os.environ.get("FLASK_ENV") == "production"

    # Route stdlib logging through structlog so Flask/SQLAlchemy/etc.
    # output is also captured uniformly.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level, logging.INFO),
    )

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if is_prod:
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _CONFIGURED = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a configured logger for the given module name.

    Always safe to call — auto-configures on first use.
    """
    configure_logging()
    return structlog.get_logger(name)
