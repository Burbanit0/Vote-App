"""
api.domain.simulations.whatif — "What-if" comparative analysis worker.

Runs the same base scenario repeatedly while varying a single parameter,
returning winners and support scores for each method at every value. Relocated
from app/routes/simulation_whatif.py (Phase 4.5.b.3). Flask-free.
"""
from __future__ import annotations

from typing import Any, Dict

from api.engine.utils.simulation_voting_utils import Voter, create_voter, create_candidate
from api.engine.utils.simulation_metrics import compare_all_methods
from api.engine.constants import DEFAULT_ISSUES
from api.engine.utils.logger import get_logger

log = get_logger(__name__)

# ── Supported variant parameters ───────────────────────────────────────────

_VARIANT_PARAMS: dict[str, dict[str, Any]] = {
    "num_voters":    {"min": 100,  "max": 10_000, "cast": lambda v: max(10, min(10_000, int(v)))},
    "num_candidates":{"min": 2,    "max": 8,      "cast": lambda v: max(2, min(8, int(v)))},
    "blank_pct":     {"min": 0.0,  "max": 0.5,    "cast": lambda v: max(0.0, min(0.5, float(v)))},
    "polarization":  {"min": 0.1,  "max": 2.0,    "cast": lambda v: max(0.1, min(2.0, float(v)))},
}

_PARTY_CYCLE = ["Green", "Conservative", "Liberal", "Independent", "Social", "National"]

# Polarization value → ideology distribution string
def _polarization_to_dist(p: float) -> str:
    if p < 0.5:
        return "centrist"
    if p < 1.1:
        return "random"
    return "polarized"


def _generate_candidate_names(n: int) -> list[str]:
    """Return n candidate names: Alice, Bob, Carol, Dave, …"""
    names = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hugo"]
    return names[:n]


def _build_what_if_population(
    num_voters: int,
    num_candidates: int,
    ideology_dist: str,
    blank_pct: float,
) -> tuple[list[Voter], list[Dict[str, Any]], list[str]]:
    """
    Create voters and candidates for one what-if simulation run.
    When blank_pct > 0, the first round(num_voters * blank_pct) voters
    have blank_threshold=1.0 (always vote blank first).
    """
    issues = DEFAULT_ISSUES
    names  = _generate_candidate_names(num_candidates)

    candidates = [
        create_candidate(issues, i, name, _PARTY_CYCLE[i % len(_PARTY_CYCLE)])
        for i, name in enumerate(names)
    ]
    voters = [
        create_voter(issues, i, ideology_distribution=ideology_dist)
        for i in range(num_voters)
    ]

    if blank_pct > 0:
        n_blank = round(num_voters * blank_pct)
        for i, v in enumerate(voters):
            # threshold > 1 ensures blank always goes first for these voters
            v["blank_threshold"] = 1.1 if i < n_blank else -0.1
    else:
        for v in voters:
            v["blank_threshold"] = -0.1  # blank always last

    return voters, candidates, issues


def _what_if_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Compare winners across methods while varying a single parameter.
    Pure-compute core shared by Flask + FastAPI. Returns (body, status)."""
    base           = data.get("base") or {}
    variant_param  = str(data.get("variant_param", "num_voters"))
    raw_values     = data.get("variant_values") or []

    # ── Validate ───────────────────────────────────────────────────────────
    if variant_param not in _VARIANT_PARAMS:
        return {"error": f"Unknown variant_param '{variant_param}'. "
                         f"Allowed: {list(_VARIANT_PARAMS)}"}, 400

    if not raw_values or len(raw_values) < 1:
        return {"error": "variant_values must be a non-empty list"}, 400

    cast        = _VARIANT_PARAMS[variant_param]["cast"]
    values      = [cast(v) for v in raw_values[:10]]  # cap at 10

    # ── Base parameters ────────────────────────────────────────────────────
    base_num_voters    = max(10, min(10_000, int(base.get("num_voters",    1000))))
    base_num_cands     = max(2,  min(8,      int(base.get("num_candidates", 4))))
    base_ideo_dist     = str(base.get("ideology_distribution", "random"))
    base_blank_pct     = max(0.0, min(0.5, float(base.get("blank_pct", 0.0))))

    # ── Run simulation for each variant value ──────────────────────────────
    results = []
    for value in values:
        num_voters    = base_num_voters
        num_cands     = base_num_cands
        ideo_dist     = base_ideo_dist
        blank_pct     = base_blank_pct

        if variant_param == "num_voters":
            num_voters = cast(value)
        elif variant_param == "num_candidates":
            num_cands  = cast(value)
        elif variant_param == "blank_pct":
            blank_pct  = cast(value)
        elif variant_param == "polarization":
            ideo_dist  = _polarization_to_dist(cast(value))

        try:
            voters, candidates, issues = _build_what_if_population(
                num_voters, num_cands, ideo_dist, blank_pct,
            )
            sim = compare_all_methods(
                voters, candidates, issues,
                blank_vote=(blank_pct > 0),
            )
        except Exception as exc:
            log.warning("simulation.whatif.value_failed", value=value, exc_info=True)
            results.append({
                "value": value,
                "error": str(exc),
                "methods": {},
                "condorcet_winner": None,
            })
            continue

        methods_out: dict[str, dict[str, Any]] = {}
        for method_key, md in sim.get("methods", {}).items():
            winner  = md.get("winner")
            # majority_satisfaction ∈ [0, 1]: fraction of voters who
            # prefer the winner over all other candidates simultaneously.
            ms      = md.get("majority_satisfaction")
            br      = md.get("bayesian_regret")
            methods_out[method_key] = {
                "winner": winner,
                "score":  round(ms * 100, 1) if ms is not None else None,
                "regret": round(br, 4)        if br is not None else None,
            }

        results.append({
            "value":            value,
            "methods":          methods_out,
            "condorcet_winner": sim.get("condorcet_winner"),
        })

    return {"variant_param": variant_param, "results": results}, 200
