"""
api_v2.domain.theory — pure theory compute, no Flask, no FastAPI, no DB.

All functions accept a `data: dict` and return `(body, http_status)`.
Re-exports the pure workers extracted from `app.routes.theory` so the
FastAPI side can import them without touching the Flask blueprint.

When Phase 4 retires Flask, these aliases will be replaced with the
canonical implementations moved here for real.
"""
from app.routes.theory import (
    _arrow_worker,
    _iia_rate_worker,
    _judgment_aggregation_worker,
    _plott_chaos_worker,
)


def arrow(data: dict) -> tuple[dict, int]:
    """Per-method Arrow axiom violation analysis."""
    return _arrow_worker(data)


def iia_rate(data: dict) -> tuple[dict, int]:
    """Empirical IIA violation rate vs number of candidates."""
    return _iia_rate_worker(data)


def plott_chaos(data: dict) -> tuple[dict, int]:
    """Plott's Chaos Theorem in 2-D policy space."""
    return _plott_chaos_worker(data)


def judgment_aggregation(data: dict) -> tuple[dict, int]:
    """Discursive dilemma (List & Pettit 2002)."""
    return _judgment_aggregation_worker(data)
