"""
api_v2.domain.theory — pure theory compute, no Flask, no FastAPI, no DB.

All functions accept a `data: dict` and return `(body, http_status)`.
Re-exports the pure workers extracted from `app.routes.theory` so the
FastAPI side can import them without touching the Flask blueprint.

When Phase 4 retires Flask, these aliases will be replaced with the
canonical implementations moved here for real.
"""
from app.routes.theory import (
    _agenda_manipulation_worker,
    _apportionment_worker,
    _arrow_worker,
    _democratic_backsliding_worker,
    _epistocracy_worker,
    _iia_rate_worker,
    _intergenerational_worker,
    _judgment_aggregation_worker,
    _majority_tyranny_worker,
    _manipulation_analysis_worker,
    _plott_chaos_worker,
    _sen_paradox_worker,
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


# ── Phase 4 batch 2 ─────────────────────────────────────────────────────────

def agenda_manipulation(data: dict) -> tuple[dict, int]:
    """Binary-elimination agenda manipulation (McKelvey-style)."""
    return _agenda_manipulation_worker(data)


def apportionment(data: dict) -> tuple[dict, int]:
    """Compare apportionment methods + Balinski-Young impossibility."""
    return _apportionment_worker(data)


def sen_paradox(data: dict) -> tuple[dict, int]:
    """Sen's Paretian Liberal impossibility (1970)."""
    return _sen_paradox_worker(data)


def manipulation_analysis(data: dict) -> tuple[dict, int]:
    """Gibbard-Satterthwaite manipulator identification."""
    return _manipulation_analysis_worker(data)


# ── Phase 4 batch 3 ─────────────────────────────────────────────────────────

def majority_tyranny(data: dict) -> tuple[dict, int]:
    """Tocqueville's tyranny of the majority across decision rules."""
    return _majority_tyranny_worker(data)


def democratic_backsliding(data: dict) -> tuple[dict, int]:
    """Path toward autocracy across successive elections."""
    return _democratic_backsliding_worker(data)


def intergenerational(data: dict) -> tuple[dict, int]:
    """Future-generation representation in long-horizon decisions."""
    return _intergenerational_worker(data)


def epistocracy(data: dict) -> tuple[dict, int]:
    """Caplan/Brennan epistocracy vs standard democracy comparison."""
    return _epistocracy_worker(data)
