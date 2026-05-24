"""
api_v2.domain.election — pure election compute, no Flask, no FastAPI, no DB.

The body of `simulate()` was already extracted as a pure function in
Sprint 2 commit ca37dcd (`app.services.election_service.ElectionService.simulate`).
Re-exposed here under the `api_v2.domain` namespace so the FastAPI side
can import it as `from api_v2.domain.election import simulate`, without
reaching back into `app.services` (which is a Flask-era namespace).

When Phase 4 retires Flask, `app.services.election_service` will be
deleted and `api_v2.domain.election.simulate` becomes the canonical
implementation. For now, this is a thin alias so we don't duplicate the
210-line orchestration twice.
"""
from app.services.election_service import ElectionService


def simulate(data: dict) -> tuple[dict, int]:
    """Run the unified election pipeline. Pure function — same input
    always produces the same output (modulo the `seed` field).

    Returns (body, http_status). `http_status` is 200 on success, 400
    when validation fails inside the worker (e.g. fewer than 2 candidates).
    """
    return ElectionService.simulate(data)
