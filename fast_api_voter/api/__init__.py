"""
api — FastAPI sibling backend to the existing Flask app.

This is Phase 2 of the strategic refactor (see STRATEGIC_REFACTOR_PLAN.md):
FastAPI lives alongside Flask using the *strangler fig* pattern. Each
migrated endpoint is exposed under `/api/v2/*` while Flask continues to
serve `/api/*` (and `/api/v1/*` as an alias) for everything not yet
migrated. When all routes are migrated, Flask is removed and v2 becomes
the default mount point.

Run locally (development):

    cd fast_api_voter
    uvicorn api.main:app --reload --port 4434

Run alongside Flask via docker-compose: see docker-compose.yml (the
`api` service will be added in Phase 3 once more endpoints are
migrated).

Structure:
    api/
        main.py            FastAPI app + lifespan + middleware
        core/
            config.py      Settings (Pydantic Settings)
        domain/
            election/      Pure-Python compute (no Flask, no FastAPI, no DB)
        routes/            Thin HTTP adapters that call services
        tests/             pytest + httpx async client

The schemas live in `app.schemas` (already created in Phase 1) and are
shared between Flask and FastAPI as the single source of truth.
"""
