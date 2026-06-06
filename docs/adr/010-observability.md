# ADR 010 — Observability: Sentry + structured logging + health checks

**Status:** Accepted (Phase 0 / Phase 7, 2026)

## Context

A publicly reachable app needs to surface errors and let uptime monitors and deploy
scripts probe readiness, without leaking internals.

## Decision

- **Sentry** for error tracking (frontend + backend), gated on a DSN env var so it is
  a no-op in dev/test.
- **Structured request logging** via the FastAPI access-log middleware in `main.py`.
- A **readiness endpoint** `GET /api/v2/health` returns `200`/`503` with per-dependency
  checks (currently Redis; uptime + version from `GIT_SHA`). It is the contract uptime
  monitors and the deploy healthcheck call.

## Consequences

- Observability degrades gracefully: no DSN / no Redis URL ⇒ checks report cleanly
  instead of crashing.
- **Deferred to deployment (need secrets / a live environment, not code):** a DB ping
  in `/health`, Sentry DSN wiring in prod, an external status page (e.g. UptimeRobot),
  CAPTCHA on `/login`+`/register`, CSP response headers, and a daily `pg_dump` cron in
  the prod compose. These are tracked in `STRATEGIC_REFACTOR_PLAN.md` Phase 7.
