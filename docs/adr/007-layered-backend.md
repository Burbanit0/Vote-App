# ADR 007 — Layered backend (routes → domain → engine)

**Status:** Accepted (Phase 3, 2026-05)

## Context

In the Flask app, HTTP handling, business logic, and the simulation maths were
interleaved, which made the compute hard to test in isolation and coupled it to the
web framework.

## Decision

Enforce three layers in `flask_voter_app/api/`:

- **`routes/`** — thin HTTP adapters: validate → call a worker → return.
- **`domain/`** — pure workers, `(data: dict) -> (body, status)`, **zero** FastAPI/DB imports.
- **`engine/`** — the simulation engine (17 voting methods + metrics), zero web/DB imports.

DB-touching routes (auth/scenarios/gallery/oauth) inject `Depends(get_async_session)`
and use `select()` / `AsyncSession`.

## Consequences

- The engine and domain are unit-testable without a server or database.
- A new endpoint is a fixed recipe: pure worker → Pydantic schema → thin route → test.
- Keeps `domain/` and `engine/` portable (could power a CLI or batch job unchanged).
