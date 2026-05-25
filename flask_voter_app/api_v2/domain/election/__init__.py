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
    _affective_polarization_worker,
    _ballot_complexity_worker,
    _behavioral_biases_worker,
    _campaign_sensitivity_worker,
    _cascade_worker,
    _choice_overload_worker,
    _coalition_worker,
    _combined_effects_worker,
    _compulsory_voting_worker,
    _deliberation_worker,
    _demographic_turnout_worker,
    _districts_worker,
    _electoral_fatigue_worker,
    _hotelling_worker,
    _jury_worker,
    _nota_worker,
    _party_dynamics_worker,
    _polarization_worker,
    _primary_worker,
    _shy_voter_worker,
    _simulate_pipeline_worker,
    _sortition_worker,
    _stv_worker,
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


# ── Perturber endpoints (Phase 3 batch 5) ──────────────────────────────────

def jury(data: dict) -> tuple[dict, int]:
    """Condorcet Jury Theorem: P(majority correct | per-voter competence p)."""
    return _jury_worker(data)


def hotelling(data: dict) -> tuple[dict, int]:
    """Hotelling-Downs iterative best-response Nash equilibrium."""
    return _hotelling_worker(data)


def polarization(data: dict) -> tuple[dict, int]:
    """Per-ideology Esteban-Ray index + method robustness scan."""
    return _polarization_worker(data)


def sortition(data: dict) -> tuple[dict, int]:
    """Elected vs sortition pure vs stratified assembly comparison."""
    return _sortition_worker(data)


# ── Perturber endpoints (Phase 3 batch 6) ──────────────────────────────────

def affective_polarization(data: dict) -> tuple[dict, int]:
    """Iyengar 2019: voters penalise candidates from the opposing political camp."""
    return _affective_polarization_worker(data)


def demographic_turnout(data: dict) -> tuple[dict, int]:
    """Full population vs effective electorate via age × education turnout gaps."""
    return _demographic_turnout_worker(data)


def compulsory_voting(data: dict) -> tuple[dict, int]:
    """Voluntary vs compulsory voting: reluctant voters add null/random ballots."""
    return _compulsory_voting_worker(data)


def party_dynamics(data: dict) -> tuple[dict, int]:
    """Multi-election party-system evolution (Duverger's Law)."""
    return _party_dynamics_worker(data)


# ── Phase 3 batch 7 ─────────────────────────────────────────────────────────

def simulate_pipeline(data: dict) -> tuple[dict, int]:
    """Step-by-step pipeline animation for the simulation hub."""
    return _simulate_pipeline_worker(data)


def districts(data: dict) -> tuple[dict, int]:
    """N districts with locally shifted ideology, FPTP vs proportional."""
    return _districts_worker(data)


def primary(data: dict) -> tuple[dict, int]:
    """Internal primaries + general election."""
    return _primary_worker(data)


def stv(data: dict) -> tuple[dict, int]:
    """Single Transferable Vote + D'Hondt + FPTP comparison."""
    return _stv_worker(data)
