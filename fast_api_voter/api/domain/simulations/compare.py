"""
simulation_compare.py — Method-comparison endpoints.

Serves SimulationComparePage (/simulation/compare) tabs:
Winner Matrix, Metrics, Strategic Impact, Condorcet Matrix,
Arrow Criteria, Sensitivity.

All endpoints use the spatial utility pipeline.

Phase 4.5.a.7: the request logic lives in framework-agnostic `_*_worker`
functions (return `(body, status)`) so the FastAPI sibling
(api/routes/simulations.py) can reuse it. The Flask routes below are thin
delegates kept as a rollback target.
"""
from contextlib import suppress
from itertools import chain
from typing import Any, Dict, List, Optional, Tuple


import random as _rng

import numpy as _np

from api.engine.utils.simulation_voting_utils import calculate_utility, create_candidate, create_voter
from api.domain.simulations.helpers import (
    _build_population,
)
from api.engine.constants import DEFAULT_ISSUES, ECONOMY_ISSUES, ENV_ISSUES, SOCIAL_ISSUES
from api.engine.utils.error_handling import log_and_error_response
from api.engine.utils.logger import get_logger

log = get_logger(__name__)



# ── /simulations/compare ────────────────────────────────────────────────────





# ── /simulations/strategic-impact ───────────────────────────────────────────





# ── /simulations/condorcet-matrix ───────────────────────────────────────────





# ── /simulations/sensitivity ────────────────────────────────────────────────





# ── /simulations/arrow-criteria ─────────────────────────────────────────────





# ── /simulations/scenario ─────────────────────────────────────────────────





# ── /simulations/manipulability ──────────────────────────────────────────────

_MANIPULABILITY_METHODS = [
    "plurality", "borda", "irv", "two_round", "approval",
    "schulze", "coombs", "bucklin", "minimax",
]


def _manipulability_worker(params: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Estimate the Gibbard-Satterthwaite manipulability index for multiple
    voting methods on a synthetic population. `params` carries the (string or
    typed) query parameters: num_candidates, num_voters, num_trials, ideology,
    methods.
    """
    try:
        num_candidates  = max(2, min(8,    int(params.get("num_candidates", 4))))
        num_voters      = max(50, min(2000, int(params.get("num_voters",     500))))
        num_trials_arg  = max(10, min(500,  int(params.get("num_trials",     200))))
        ideology_dist   = params.get("ideology", "random") or "random"
        methods_arg     = params.get("methods", "all") or "all"
    except (TypeError, ValueError) as e:
        return {"error": f"Invalid query parameter: {e}"}, 400

    # ── Build synthetic population ─────────────────────────────────────────
    _NAMES = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hugo"]
    candidate_names = _NAMES[:num_candidates]
    candidate_configs = [
        {"name": n, "party": "Independent", "ideology_position": None}
        for n in candidate_names
    ]

    try:
        voters, candidates, issues = _build_population(
            candidate_configs, num_voters, ideology_dist
        )
    except Exception as exc:
        return log_and_error_response(
            log, "simulation.manipulability.population_build_failed",
            {"error": f"Population build failed: {exc}"},
        )

    # ── Build sincere rankings ─────────────────────────────────────────────
    utilities: Dict[Any, Dict[str, float]] = {
        v["id"]: {
            c["name"]: calculate_utility(v, c, issues)["utility"]
            for c in candidates
        }
        for v in voters
    }
    rankings: list[list[str]] = [
        sorted(candidate_names, key=lambda n: -utilities[v["id"]][n])
        for v in voters
    ]

    # ── Select methods ─────────────────────────────────────────────────────
    if str(methods_arg).strip().lower() == "all":
        target_methods = _MANIPULABILITY_METHODS
    else:
        target_methods = [m.strip() for m in str(methods_arg).split(",") if m.strip()]
        if not target_methods:
            return {"error": "No valid methods specified"}, 400

    # ── Compute manipulability per method ──────────────────────────────────
    from api.engine.utils.gibbard_satterthwaite import compute_manipulability_index

    results = []
    for method in target_methods:
        try:
            result = compute_manipulability_index(method, rankings, num_trials=num_trials_arg)
            results.append(result)
        except Exception as exc:
            log.warning("simulation.manipulability.method_failed", method=method, exc_info=True)
            results.append({
                "method": method,
                "manipulability_rate": None,
                "average_gain": 0.0,
                "num_manipulators": 0,
                "num_sampled": 0,
                "examples": [],
                "error": str(exc),
            })

    # Sort: unknown/error last, then by rate descending
    results.sort(
        key=lambda r: (r.get("manipulability_rate") is None, -(r.get("manipulability_rate") or 0)),
    )

    return {
        "num_candidates": num_candidates,
        "num_voters":     num_voters,
        "ideology":       ideology_dist,
        "num_trials":     num_trials_arg,
        "results":        results,
    }, 200




# ── Vote-steps (step-by-step counting animation) ──────────────────────────────

_VOTE_STEPS_METHODS = {"irv", "borda", "plurality", "schulze", "approval"}
_PARTY_CYCLE_STEPS  = ("Green", "Conservative", "Liberal", "Independent")


def _irv_steps(rankings: list[list[str]], n_voters: int) -> list[dict[str, Any]]:
    """
    Return a list of round dicts for IRV animation.

    Each non-final round:
        { "round": N, "scores": {name: pct}, "eliminated": name|null, "transfers": {name: pct}|null }
    Final round:
        { "round": N, "winner": name }

    The "eliminated" / "transfers" fields on round N describe what happened
    at the *end of round N-1* (i.e. why the scores changed from N-1 to N).
    """
    from collections import Counter

    rounds: list[dict[str, Any]] = []
    active: set[str]             = set(chain.from_iterable(rankings))
    last_eliminated: Optional[str]                  = None
    last_transfers:  Optional[dict[str, float]]     = None

    while True:
        counts: Counter[str] = Counter()
        for r in rankings:
            for c in r:
                if c in active:
                    counts[c] += 1
                    break

        total = sum(counts.values()) or 1
        scores = {c: round(counts.get(c, 0) / total, 4) for c in sorted(active)}
        rnum = len(rounds) + 1

        # Majority winner?
        winner = next((c for c, v in counts.items() if v * 2 > total), None)
        if winner or len(active) == 1:
            winner = winner or next(iter(active))
            rounds.extend((
                {"round": rnum, "scores": scores,
                 "eliminated": last_eliminated, "transfers": last_transfers},
                {"round": rnum + 1, "winner": winner},
            ))
            break

        # Find ALL candidates at the minimum count (canonical IRV: eliminate
        # all ties at once, matching app/utils/simulation_ranked_utils.py
        # get_irv_winner). Importantly: get_irv_winner ignores candidates with
        # 0 first-choice votes (they are not in votes_count), so they survive
        # the round. We mirror that to keep the same elimination sequence.
        if not counts:
            # No one has any votes left → pick any active as winner placeholder
            rounds.append({"round": rnum + 1, "winner": next(iter(active))})
            break
        min_c = min(counts.values())
        eliminated_set = {c for c, v in counts.items() if v == min_c}

        # Compute vote transfers: voters whose top active choice was eliminated
        # transfer to their next non-eliminated preference.
        transfers: Counter[str] = Counter()
        new_active = active - eliminated_set
        for r in rankings:
            active_r = [c for c in r if c in active]
            if active_r and active_r[0] in eliminated_set:
                rest = [c for c in active_r if c not in eliminated_set]
                if rest:
                    transfers[rest[0]] += 1
        transfer_pct = {c: round(v / n_voters, 4) for c, v in transfers.items()} if transfers else None

        # Display label: sorted list of eliminated names joined by " + "
        elim_label = " + ".join(sorted(eliminated_set))

        rounds.append({"round": rnum, "scores": scores,
                       "eliminated": last_eliminated, "transfers": last_transfers})
        active = new_active
        last_eliminated = elim_label
        last_transfers  = transfer_pct

        # Safety: if we eliminated everyone (all tied at 0), break to avoid loop
        if not active:
            rounds.append({"round": rnum + 1, "winner": elim_label.split(" + ")[0]})
            break

    return rounds


def _borda_steps(
    rankings: list[list[str]],
) -> tuple[list[dict[str, Any]], Optional[str]]:
    """Return (steps_list, winner) for Borda animation (one step per rank)."""
    all_candidates = sorted(set(chain.from_iterable(rankings)))
    n = max((len(r) for r in rankings), default=0)
    cumulative: dict[str, int] = {c: 0 for c in all_candidates}
    steps: list[dict[str, Any]] = []

    for rank_idx in range(n):
        points = n - 1 - rank_idx
        for r in rankings:
            if rank_idx < len(r):
                cumulative[r[rank_idx]] += points
        steps.append({
            "rank":           rank_idx + 1,
            "points_awarded": points,
            "tally":          cumulative.copy(),
        })

    winner: Optional[str] = max(cumulative, key=lambda k: cumulative[k]) if cumulative else None
    return steps, winner


def _schulze_matrices(
    rankings: list[list[str]],
    candidate_names: list[str],
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]], Optional[str]]:
    """Return (duel_pct, path_pct, winner) for Schulze animation."""
    from itertools import combinations, permutations

    n       = len(rankings) or 1
    cands   = candidate_names

    pref: dict[str, dict[str, int]] = {c1: {c2: 0 for c2 in cands if c2 != c1} for c1 in cands}
    for c1, c2 in combinations(cands, 2):
        for r in rankings:
            with suppress(ValueError):
                p1, p2 = r.index(c1), r.index(c2)
                if p1 < p2:
                    pref[c1][c2] += 1
                else:
                    pref[c2][c1] += 1

    duel_pct = {c1: {c2: round(pref[c1][c2] / n, 4) for c2 in cands if c2 != c1} for c1 in cands}

    # Strongest-path (Floyd-Warshall style)
    strength: dict[str, dict[str, int]] = {c1: {c2: pref[c1][c2] for c2 in cands if c2 != c1} for c1 in cands}
    for c1, c2, c3 in permutations(cands, 3):
        strength[c1][c2] = max(strength[c1][c2], min(strength[c1][c3], strength[c3][c2]))

    path_pct = {c1: {c2: round(strength[c1][c2] / n, 4) for c2 in cands if c2 != c1} for c1 in cands}

    wins: dict[str, int] = {c: 0 for c in cands}
    for c1, c2 in combinations(cands, 2):
        if strength[c1][c2] > strength[c2][c1]:
            wins[c1] += 1
        elif strength[c2][c1] > strength[c1][c2]:
            wins[c2] += 1
    winner: Optional[str] = (
        max(wins, key=lambda k: wins[k]) if any(wins.values()) else (cands[0] if cands else None)
    )
    return duel_pct, path_pct, winner


def _vote_steps_worker(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Per-step intermediate data for animating how a single method counts the
    same set of ballots.
    """
    from collections import Counter

    method        = str(data.get("method",    "plurality")).lower()
    num_voters    = max(10, min(500, int(data.get("num_voters", 100))))
    # Align cap with /api/election/simulate (SINGLE_WINNER_CAP=8) so animation
    # and main endpoints always operate on the SAME set of candidates. Mismatched
    # caps were the root cause of Le Pen / Megret winner divergence on France 2002.
    raw_cands_in  = data.get("candidates", ["Alice", "Bob", "Charlie"])[:8]
    ideology      = str(data.get("ideology",  "random"))
    seed          = int(data.get("seed",       42))

    # Accept either ["name", "name"] or [{"name": ..., "x": ..., "y": ...}, ...]
    # When positions are provided, build candidates from them (same logic as
    # /api/election/simulate) so that animation winners match the main sim.
    raw_cands: List[str]                                = []
    cand_positions: List[Optional[Tuple[float, float]]] = []
    for c in raw_cands_in:
        if isinstance(c, dict):
            raw_cands.append(str(c.get("name", f"Cand{len(raw_cands)}")))
            x = float(c.get("x", 0.0))
            y = float(c.get("y", 0.0))
            cand_positions.append((max(-1.0, min(1.0, x)), max(-1.0, min(1.0, y))))
        else:
            raw_cands.append(str(c))
            cand_positions.append(None)

    if len(raw_cands) < 2:
        return {"error": "At least 2 candidates required"}, 400
    if method not in _VOTE_STEPS_METHODS:
        return {"error": f"method must be one of: {', '.join(sorted(_VOTE_STEPS_METHODS))}"}, 400

    _rng.seed(seed)
    _np.random.seed(seed)

    issues     = DEFAULT_ISSUES

    def _build_from_xy(i: int, name: str, x: float, y: float) -> Dict[str, Any]:
        """Mirror /api/election/simulate's _build_candidate_from_xy for consistency."""
        econ_pos = (x + 1) / 2
        soc_pos  = (y + 1) / 2
        env_pos  = 1.0 - econ_pos
        policies = {
            iss: (
                econ_pos if iss in ECONOMY_ISSUES else
                env_pos  if iss in ENV_ISSUES     else
                soc_pos  if iss in SOCIAL_ISSUES  else
                (econ_pos + soc_pos) / 2
            )
            for iss in issues
        }
        return {
            "id":                i,
            "name":              name,
            "party":             _PARTY_CYCLE_STEPS[i % len(_PARTY_CYCLE_STEPS)],
            "party_lean":        x,
            "ideology_position": econ_pos,
            "policies":          policies,
            "charisma":          0.7, "scandals": 0,
            "campaign_funds":    500_000, "experience": 10, "popularity": 0.6,
        }

    candidates = []
    for i, (name, pos) in enumerate(zip(raw_cands, cand_positions)):
        if pos is not None:
            candidates.append(_build_from_xy(i, name, pos[0], pos[1]))
        else:
            candidates.append(create_candidate(
                issues, i, name, _PARTY_CYCLE_STEPS[i % len(_PARTY_CYCLE_STEPS)]
            ))
    voters = [create_voter(issues, i, ideology_distribution=ideology) for i in range(num_voters)]

    cand_names: list[str] = [str(c["name"]) for c in candidates]
    utilities: Dict[Any, Dict[str, float]] = {
        v["id"]: {str(c["name"]): calculate_utility(v, c, issues)["utility"] for c in candidates}
        for v in voters
    }

    # Build rankings without default-argument lambda (mypy-safe closure)
    rankings: list[list[str]] = []
    for v in voters:
        vid = v["id"]
        rankings.append(sorted(cand_names, key=lambda n: -utilities[vid][n]))

    if method == "irv":
        return {"method": "irv", "rounds": _irv_steps(rankings, num_voters)}, 200

    if method == "borda":
        steps, winner = _borda_steps(rankings)
        return {"method": "borda", "num_candidates": len(cand_names),
                "steps": steps, "winner": winner}, 200

    if method == "plurality":
        fc: Counter[str] = Counter(r[0] for r in rankings if r)
        pct = {c: round(fc.get(c, 0) / num_voters, 4) for c in cand_names}
        winner_p: Optional[str] = max(pct, key=lambda k: pct[k]) if pct else None
        return {"method": "plurality", "first_choices": pct, "winner": winner_p}, 200

    if method == "schulze":
        duel, path, winner_s = _schulze_matrices(rankings, cand_names)
        return {"method": "schulze", "duel_matrix": duel,
                "path_matrix": path, "winner": winner_s}, 200

    # approval
    approval: Counter[str] = Counter()
    threshold = 0.5
    for v in voters:
        u = utilities[v["id"]]
        for cname, score in u.items():
            if score >= threshold:
                approval[cname] += 1
    approval_pct = {c: round(approval.get(c, 0) / num_voters, 4) for c in cand_names}
    winner_a: Optional[str] = max(approval_pct, key=lambda k: approval_pct[k]) if approval_pct else None
    return {"method": "approval", "threshold_used": threshold,
            "approval_scores": approval_pct, "winner": winner_a}, 200




# ── Ideology map ──────────────────────────────────────────────────────────────

_IDEOLOGY_MAP_PARTIES = ("Green", "Liberal", "Conservative", "Independent")


