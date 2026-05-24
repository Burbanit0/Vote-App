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
    _ballot_complexity_worker,
    _behavioral_biases_worker,
    _campaign_sensitivity_worker,
    _cascade_worker,
    _choice_overload_worker,
    _coalition_worker,
    _combined_effects_worker,
    _deliberation_worker,
    _electoral_fatigue_worker,
    _nota_worker,
    _shy_voter_worker,
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


# ── Perturber endpoints (Phase 3 batch 3) ──────────────────────────────────

def nota(data: dict) -> tuple[dict, int]:
    """NOTA (None Of The Above) as an official ballot option."""
    return _nota_worker(data)


def ballot_complexity(data: dict) -> tuple[dict, int]:
    """Null-vote rate per method as a function of ballot complexity."""
    return _ballot_complexity_worker(data)


def shy_voter(data: dict) -> tuple[dict, int]:
    """Bradley / Shy Tory effect: socially-sensitive candidates underpolled."""
    return _shy_voter_worker(data)


def electoral_fatigue(data: dict) -> tuple[dict, int]:
    """Turnout decay over repeated elections; residual electorate drifts toward partisans."""
    return _electoral_fatigue_worker(data)


# ── Perturber endpoints (Phase 3 batch 4) ──────────────────────────────────

def cascade(data: dict) -> tuple[dict, int]:
    """Sequential voting with information cascades (Bikhchandani 1992)."""
    return _cascade_worker(data)


def behavioral_biases(data: dict) -> tuple[dict, int]:
    """Expressive voting + bullet voting + primacy effect on outcomes."""
    return _behavioral_biases_worker(data)


def choice_overload(data: dict) -> tuple[dict, int]:
    """Schwartz 2004 paradox: heuristics dominate beyond overload_threshold."""
    return _choice_overload_worker(data)


def deliberation(data: dict) -> tuple[dict, int]:
    """DeGroot opinion update across a network, then vote."""
    return _deliberation_worker(data)
