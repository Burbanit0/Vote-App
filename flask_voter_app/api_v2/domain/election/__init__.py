"""
api_v2.domain.election — pure election compute, no Flask, no FastAPI, no DB.

All functions accept a `data: dict` and return `(body, http_status)`.
They are pure: same input = same output (modulo any `seed` field).

The bodies of these functions were already extracted as workers in
Sprint A2 (combined-effects / campaign-sensitivity / simulate-pipeline)
and Sprint C1 (simulate). This module re-exports them under the
`api_v2.domain` namespace so the FastAPI side can import them without
reaching back into `app.routes.election` (Flask-era namespace).

When Phase 4 retires Flask, these aliases will be replaced with the
canonical implementations moved here for real, and the corresponding
Flask workers will be deleted.
"""
from app.routes.election import (
    _abstention_worker,
    _campaign_sensitivity_worker,
    _coalition_worker,
    _combined_effects_worker,
)
from app.services.election_service import ElectionService


def simulate(data: dict) -> tuple[dict, int]:
    """Run the unified election pipeline."""
    return ElectionService.simulate(data)


def combined_effects(data: dict) -> tuple[dict, int]:
    """2x2x2 factorial: run the same electorate under all 8 combinations
    of blank-vote / campaign / information-model ON-OFF."""
    return _combined_effects_worker(data)


def campaign_sensitivity(data: dict) -> tuple[dict, int]:
    """Snapshot the same electorate at multiple campaign days to measure
    method-by-method winner stability over time."""
    return _campaign_sensitivity_worker(data)


def coalition(data: dict) -> tuple[dict, int]:
    """Per-method D'Hondt seat allocation + greedy coalition formation."""
    return _coalition_worker(data)


def abstention(data: dict) -> tuple[dict, int]:
    """Iterated abstention model with poll-feedback over N rounds."""
    return _abstention_worker(data)
