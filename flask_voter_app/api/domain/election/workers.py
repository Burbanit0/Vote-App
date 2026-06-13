"""
election.py — Unified election simulation endpoint.

POST /api/election/simulate orchestrates all existing models in the correct
logical order:

  1. Build electorate (voters + candidates from explicit x/y positions)
  2. Campaign dynamics   — if campaign.enabled, adjust vote intentions
  3. Blank-vote contagion — if blank_vote.contagion.enabled, lower blank thresholds
  4. Information model   — if information_model.enabled, distort perceived utilities
  5. All voting methods  — compare_all_methods with possibly overridden utilities
  6. Blank-vote rules    — if blank_vote.enabled, apply constitutional rule to each winner
"""
from __future__ import annotations

import math
import random as _random
from collections import Counter
from typing import Any, Dict, List, Optional

import numpy as _np

from api.engine.constants import DEFAULT_ISSUES
from api.engine.utils.simulation_voting_utils import calculate_utility, create_candidate, create_voter
from api.engine.utils.simulation_metrics      import compare_all_methods
from api.engine.utils.profile_engine          import (
    build_profile, cycle_rate, project_ballot, ballot_metrics, compatible_methods,
)
from api.engine.utils.simulation_ranked_utils import (
    get_plurality_winner,
    get_condorcet_winner,
    get_irv_winner,
    get_approval_winner_sincere,
    get_borda_winner,
    get_schulze_winner,
)
from api.engine.utils.blank_vote_rules        import BlankVoteRule, apply_blank_rule
from api.engine.utils.simulation_multiwinner_utils import (
    get_stv_result, get_dhondt_winners,
    get_sainte_lague_winners, compute_proportionality_metrics,
    get_spav_result, get_phragmen_result,
)
from api.engine.utils.blank_contagion         import simulate_blank_contagion
from api.engine.utils.campaign_dynamics       import simulate_campaign
from api.engine.utils.information_model       import apply_information_asymmetry
from api.engine.utils.cache import cache_result

# Generic helpers extracted to _helpers.py during the incremental split of
# this package. Re-exported under their original private names so the
# 30+ existing call sites in this file continue to work unchanged.
from ._helpers import (
    PARTY_CYCLE       as _PARTY_CYCLE,
    SINGLE_WINNER_CAP,
    build_candidate_from_xy as _build_candidate_from_xy,
    inter_method_agreement  as _inter_method_agreement,
)



# ── Endpoint ──────────────────────────────────────────────────────────────────

@cache_result("election:simulate", ttl_seconds=3600)
def _simulate_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Thin route worker: delegates to ElectionService (pure orchestration).

    The cache + tpool wrappers stay at this layer (cross-cutting HTTP concern).
    The service is callable from anywhere — tests, CLIs, future entry points.

    Cached via Redis: identical input dicts (same seed = same result) return
    in ~5 ms instead of 200-500 ms. Cache is keyed by SHA-256 of the JSON-
    serialised data with a 1h TTL.
    """
    from api.domain.election.election_service import ElectionService
    return ElectionService.simulate(data)


# ── Shared helpers for divergence analysis ────────────────────────────────────

def _build_base_electorate(
    cand_specs: list[dict[str, Any]],
    num_voters: int,
    ideology: str,
    seed: int,
    issues: list[str],
) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]], Dict[Any, Dict[str, float]], list[str]]:
    """
    Build candidates, voters, and true utilities from spec.
    Returns (candidates, voters, true_utilities, cand_names).
    """
    import copy  # noqa: F401 — kept for symmetry, not actually needed here

    cand_names = [str(s.get("name", f"C{i}")) for i, s in enumerate(cand_specs)]

    candidates = [
        _build_candidate_from_xy(
            i,
            cand_names[i],
            max(-1.0, min(1.0, float(s.get("x", 0.0)))),
            max(-1.0, min(1.0, float(s.get("y", 0.0)))),
            issues,
        )
        for i, s in enumerate(cand_specs)
    ]

    voters = [
        create_voter(issues, i, ideology_distribution=ideology)
        for i in range(num_voters)
    ]

    true_utilities: Dict[Any, Dict[str, float]] = {
        v["id"]: {c["name"]: calculate_utility(v, c, issues)["utility"] for c in candidates}
        for v in voters
    }

    return candidates, voters, true_utilities, cand_names


def _run_methods_on_electorate(
    voters: list[Dict[str, Any]],
    candidates: list[Dict[str, Any]],
    utilities: Dict[Any, Dict[str, float]],
    issues: list[str],
    blank_enabled: bool,
    blank_rule: BlankVoteRule,
) -> Dict[str, Any]:
    """
    Run compare_all_methods and optionally apply blank-vote rule.
    Returns structured dict: { method_name: { winner, winner_after_rule, ... } }.
    """
    result        = compare_all_methods(
        voters, candidates, issues,
        blank_vote=blank_enabled,
        override_utilities=utilities,
    )
    condorcet_winner = result.get("condorcet_winner")
    blank_pct        = result.get("blank_pct") or 0.0
    methods_data     = result.get("methods", {})

    methods_out: Dict[str, Any] = {}
    for method_name, md in methods_data.items():
        winner = md.get("winner")
        entry: Dict[str, Any] = {"winner": winner}
        if blank_enabled:
            rule_result = apply_blank_rule(winner=winner, blank_pct=blank_pct, rule=blank_rule)
            entry["winner_after_rule"] = rule_result.get("winner")
            entry["blank_triggered"]   = rule_result.get("blank_triggered", False)
        methods_out[method_name] = entry

    return {
        "methods":               methods_out,
        "inter_method_agreement": _inter_method_agreement(methods_out),
        "condorcet_winner":      condorcet_winner,
        "blank_rate":            round(blank_pct, 4),
    }


# ── Divergence endpoint ───────────────────────────────────────────────────────

def _divergence_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /divergence — extracted for FastAPI v2."""
    num_voters  = max(10, min(500, int(data.get("num_voters", 200))))
    ideology    = str(data.get("ideology", "random"))
    seed        = int(data.get("seed", 42))
    cand_specs  = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ])[:6]

    blank_cfg      = data.get("blank_vote") or {}
    blank_rule_str = str(blank_cfg.get("rule", "symbolic"))
    contagion_cfg  = blank_cfg.get("contagion") or {}
    contagion_on   = bool(contagion_cfg.get("enabled", False))

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    try:
        blank_rule = BlankVoteRule(blank_rule_str)
    except ValueError:
        blank_rule = BlankVoteRule.SYMBOLIC

    # ── Seed (same electorate for both runs) ──────────────────────────────
    _random.seed(seed)
    _np.random.seed(seed)

    issues = DEFAULT_ISSUES
    candidates, voters, true_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    # ── Run A: without blank vote ─────────────────────────────────────────
    import copy
    voters_a = copy.deepcopy(voters)
    run_a = _run_methods_on_electorate(
        voters_a, candidates, true_utilities, issues,
        blank_enabled=False, blank_rule=BlankVoteRule.SYMBOLIC,
    )

    # ── Run B: with blank vote (optional contagion) ───────────────────────
    voters_b = copy.deepcopy(voters)

    if contagion_on:
        beta    = max(0.0, min(1.0, float(contagion_cfg.get("beta",  0.15))))
        gamma   = max(0.0, min(1.0, float(contagion_cfg.get("gamma", 0.10))))
        net_map = {"random": "random", "watts_strogatz": "small-world", "block": "clustered"}
        net     = net_map.get(str(contagion_cfg.get("network", "random")), "random")
        contagion_result = simulate_blank_contagion(
            num_voters=num_voters, initial_blank_rate=0.05,
            contagion_rate=beta, recovery_rate=gamma,
            num_rounds=10, network_type=net, seed=seed,
        )
        reduction = contagion_result.get("final_blank_rate", 0.05) * 0.4
        for v in voters_b:
            v["blank_threshold"] = max(0.05, v["blank_threshold"] - reduction)

    run_b = _run_methods_on_electorate(
        voters_b, candidates, true_utilities, issues,
        blank_enabled=True, blank_rule=blank_rule,
    )

    # ── Compute divergence metrics ────────────────────────────────────────
    all_methods   = sorted(run_a["methods"].keys())
    methods_changed: list[str] = []

    for method in all_methods:
        winner_a = run_a["methods"].get(method, {}).get("winner")
        # For run B, compare effective winner (after rule) if available
        md_b   = run_b["methods"].get(method, {})
        winner_b = md_b.get("winner_after_rule", md_b.get("winner"))
        if winner_a != winner_b:
            methods_changed.append(method)

    delta_agreement = round(
        run_b["inter_method_agreement"] - run_a["inter_method_agreement"], 4
    )
    pct_changed = round(
        len(methods_changed) / len(all_methods), 4
    ) if all_methods else 0.0

    return {
        "without_blank": {
            "methods":               run_a["methods"],
            "inter_method_agreement": run_a["inter_method_agreement"],
            "condorcet_winner":      run_a["condorcet_winner"],
        },
        "with_blank": {
            "methods":               run_b["methods"],
            "inter_method_agreement": run_b["inter_method_agreement"],
            "condorcet_winner":      run_b["condorcet_winner"],
            "blank_rate":            run_b["blank_rate"],
        },
        "delta_agreement":     delta_agreement,
        "methods_changed":     methods_changed,
        "pct_methods_changed": pct_changed,
        "blank_rule":          blank_rule_str,
    }, 200


# ── Campaign sensitivity ──────────────────────────────────────────────────────

def _snapshot_election_winners(
    voters:     list[Dict[str, Any]],
    candidates: list[Dict[str, Any]],
    utilities:  Dict[Any, Dict[str, float]],
    issues:     list[str],
    blank_enabled: bool,
    blank_rule: BlankVoteRule,
) -> Dict[str, Dict[str, Any]]:
    """
    Run all voting methods from pre-computed utilities.

    Lighter than compare_all_methods() — skips strategic_vulnerability so
    calling it once per snapshot day is tractable.
    """
    import copy
    from api.engine.utils.simulation_ranked_utils import (
        get_condorcet_winner,
        get_plurality_winner, get_two_round_winner, get_borda_winner,
        get_approval_winner, get_irv_winner, get_coombs_winner,
        get_bucklin_winner, get_minimax_winner, get_schulze_winner,
    )
    from api.engine.utils.simulation_score_utils import (
        get_simple_score_winner, get_star_voting_winner,
        get_median_voting_winner, get_mean_median_hybrid_winner,
        get_variance_based_winner,
    )

    cand_names = [str(c["name"]) for c in candidates]
    n          = len(voters) or 1

    # Build sincere rankings and score votes from the provided utilities
    rankings: list[list[str]] = [
        sorted(cand_names, key=lambda name: -utilities[v["id"]][name])
        for v in voters
    ]
    score_votes: list[dict[str, int]] = [
        {name: max(0, min(5, round(5 * utilities[v["id"]][name]))) for name in cand_names}
        for v in voters
    ]

    # Majority satisfaction helper (vote_share proxy)
    def _satisfaction(winner: Optional[str]) -> float:
        if not winner:
            return 0.0
        return round(sum(
            1 for v in voters
            if all(
                utilities[v["id"]].get(winner, 0) > utilities[v["id"]].get(other, 0)
                for other in cand_names if other != winner
            )
        ) / n, 4)

    # blank_pct: voters whose first ranking choice is the blank slot
    blank_pct = 0.0
    if blank_enabled:
        blank_pct = round(sum(
            1 for v, r in zip(voters, rankings)
            if max(utilities[v["id"]].values(), default=0.0) < v.get("blank_threshold", 0.375)
        ) / n, 4)

    ranked: dict[str, Any] = {
        "plurality":   get_plurality_winner(rankings),
        "two_round":   get_two_round_winner(rankings),
        "borda":       get_borda_winner(rankings),
        "approval":    get_approval_winner(rankings),
        "irv":         get_irv_winner(rankings),
        "coombs":      get_coombs_winner(rankings),
        "bucklin":     get_bucklin_winner(rankings),
        "minimax":     get_minimax_winner(rankings),
        "schulze":     get_schulze_winner(rankings),
    }
    def _sw(raw: Any) -> Optional[str]:
        """Extract winner string from a score-method result (dict or str)."""
        if isinstance(raw, dict):
            return str(raw["winner"]) if raw.get("winner") is not None else None
        return str(raw) if raw is not None else None

    scored: dict[str, Any] = {
        "simple_score":       _sw(get_simple_score_winner(score_votes)),       # type: ignore[no-untyped-call]
        "star_voting":        _sw(get_star_voting_winner(score_votes)),        # type: ignore[no-untyped-call]
        "median_voting":      get_median_voting_winner(score_votes),            # type: ignore[no-untyped-call]
        "mean_median_hybrid": get_mean_median_hybrid_winner(score_votes),      # type: ignore[no-untyped-call]
        "variance_based":     get_variance_based_winner(score_votes),          # type: ignore[no-untyped-call]
    }

    methods_out: Dict[str, Dict[str, Any]] = {}
    for method, winner in {**ranked, **scored}.items():
        # score methods may return dicts
        if isinstance(winner, dict):
            winner = winner.get("winner")
        entry: Dict[str, Any] = {
            "winner":     winner,
            "vote_share": _satisfaction(winner),
        }
        if blank_enabled:
            rule_res = apply_blank_rule(winner=winner, blank_pct=blank_pct, rule=blank_rule)
            entry["winner_after_rule"] = rule_res.get("winner")
        methods_out[method] = entry

    return methods_out


def _campaign_sensitivity_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure-compute worker for /campaign-sensitivity (multiple snapshots)."""
    import copy

    num_voters      = max(10, min(200, int(data.get("num_voters",  150))))  # cap for speed
    ideology        = str(data.get("ideology",   "random"))
    seed            = int(data.get("seed",        42))
    cand_specs      = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ])[:6]

    campaign_cfg   = data.get("campaign", {}) or {}
    num_days       = max(7,  min(60, int(campaign_cfg.get("num_days",        30))))
    polling_effect = max(0.0, min(1.0, float(campaign_cfg.get("polling_effect", 0.3))))

    blank_cfg      = data.get("blank_vote", {}) or {}
    blank_enabled  = bool(blank_cfg.get("enabled", False))
    blank_rule_str = str(blank_cfg.get("rule", "symbolic"))
    contagion_cfg  = blank_cfg.get("contagion", {}) or {}
    contagion_on   = bool(contagion_cfg.get("enabled", False))

    raw_snaps      = data.get("snapshot_days", [0, 7, 14, 21, 28, "final"])

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    try:
        blank_rule = BlankVoteRule(blank_rule_str)
    except ValueError:
        blank_rule = BlankVoteRule.SYMBOLIC

    # ── Seed and build base electorate ────────────────────────────────────
    _random.seed(seed)
    _np.random.seed(seed)

    issues = DEFAULT_ISSUES
    candidates, voters, true_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    # ── Apply blank-vote contagion once (threshold adjustments) ───────────
    if contagion_on and blank_enabled:
        beta    = max(0.0, min(1.0, float(contagion_cfg.get("beta",  0.15))))
        gamma   = max(0.0, min(1.0, float(contagion_cfg.get("gamma", 0.10))))
        net_map = {"random": "random", "watts_strogatz": "small-world", "block": "clustered"}
        net     = net_map.get(str(contagion_cfg.get("network", "random")), "random")
        contagion_result = simulate_blank_contagion(
            num_voters=num_voters, initial_blank_rate=0.05,
            contagion_rate=beta, recovery_rate=gamma,
            num_rounds=10, network_type=net, seed=seed,
        )
        reduction = contagion_result.get("final_blank_rate", 0.05) * 0.4
        for v in voters:
            v["blank_threshold"] = max(0.05, v["blank_threshold"] - reduction)

    # ── Run campaign to get day-by-day polling shares ─────────────────────
    camp       = simulate_campaign(
        num_candidates=len(candidates),
        num_voters=num_voters,
        num_days=num_days,
        events=[],
        seed=seed,
    )
    camp_cands   = camp.get("candidates", [])   # internal campaign candidate names
    daily_scores = camp.get("daily_scores", {})  # {camp_name: [pct_day0, …]}

    # Resolve snapshot days (convert "final" → num_days)
    resolved: list[int] = []
    for d in raw_snaps:
        resolved.append(num_days if d == "final" else min(int(d), num_days))
    snapshot_days = sorted(set(resolved))

    # ── Snapshot loop ─────────────────────────────────────────────────────
    snapshots: list[Dict[str, Any]] = []
    for day in snapshot_days:
        # Get polling shares for this specific day
        day_shares: Dict[str, float] = {}
        for camp_idx, camp_name in enumerate(camp_cands):
            if camp_idx < len(cand_names):
                our_name    = cand_names[camp_idx]
                shares_list = daily_scores.get(camp_name, [50.0])
                pct         = shares_list[min(day, len(shares_list) - 1)]
                day_shares[our_name] = pct / 100.0

        # Blend true utilities with day-specific polling shares
        day_utilities: Dict[Any, Dict[str, float]] = {}
        for v in voters:
            day_utilities[v["id"]] = {}
            for c_name in cand_names:
                share   = day_shares.get(c_name, 1.0 / len(cand_names))
                u       = true_utilities[v["id"]][c_name]
                blended = u * (1.0 - polling_effect * 0.4) + share * (polling_effect * 0.4)
                day_utilities[v["id"]][c_name] = max(0.0, min(1.0, blended))

        methods_out = _snapshot_election_winners(
            voters, candidates, day_utilities, issues, blank_enabled, blank_rule
        )

        snapshots.append({
            "day":                   day,
            "methods":               methods_out,
            "inter_method_agreement": _inter_method_agreement(methods_out),
        })

    # ── Stability metrics ─────────────────────────────────────────────────
    all_methods = sorted(snapshots[0]["methods"].keys()) if snapshots else []
    n_snaps     = len(snapshots)

    method_stability: Dict[str, Any] = {}
    for method in all_methods:
        winners = [s["methods"].get(method, {}).get("winner") for s in snapshots]
        changes = sum(1 for i in range(1, len(winners)) if winners[i] != winners[i - 1])
        final_w = winners[-1] if winners else None
        score   = round(1.0 - (changes / (n_snaps - 1)), 4) if n_snaps > 1 else 1.0
        method_stability[method] = {
            "winner_changes": changes,
            "final_winner":   final_w,
            "stability_score": score,
        }

    most_stable  = max(method_stability, key=lambda m: method_stability[m]["stability_score"]) \
                   if method_stability else None
    least_stable = min(method_stability, key=lambda m: method_stability[m]["stability_score"]) \
                   if method_stability else None

    return {
        "snapshots":           snapshots,
        "method_stability":    method_stability,
        "most_stable_method":  most_stable,
        "least_stable_method": least_stable,
    }, 200


# ── Combined effects (2³ factorial) ──────────────────────────────────────────

@cache_result("election:combined-effects", ttl_seconds=3600)
def _combined_effects_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure-compute worker for /combined-effects. Runs in eventlet.tpool via
    @heavy_endpoint so the matrix of 8 simulations doesn't block the event loop.

    Cached via Redis (1h TTL) — the factorial 2³ matrix is fully deterministic,
    so re-running the same input is a guaranteed cache hit.
    """
    import copy
    from api.engine.utils.simulation_ranked_utils import get_condorcet_winner

    num_voters      = max(10, min(200, int(data.get("num_voters",  150))))
    ideology        = str(data.get("ideology",   "random"))
    seed            = int(data.get("seed",        42))
    cand_specs      = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ])[:6]

    blank_cfg       = data.get("blank_vote", {}) or {}
    blank_rule_str  = str(blank_cfg.get("rule", "symbolic"))
    contagion_cfg   = blank_cfg.get("contagion", {}) or {}
    contagion_on    = bool(contagion_cfg.get("enabled", False))

    info_cfg        = data.get("information_model", {}) or {}

    campaign_cfg    = data.get("campaign", {}) or {}
    num_days        = max(7,  min(60, int(campaign_cfg.get("num_days",        28))))
    polling_effect  = max(0.0, min(1.0, float(campaign_cfg.get("polling_effect", 0.35))))

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    try:
        blank_rule = BlankVoteRule(blank_rule_str)
    except ValueError:
        blank_rule = BlankVoteRule.SYMBOLIC

    _random.seed(seed)
    _np.random.seed(seed)

    issues = DEFAULT_ISSUES
    candidates, voters, true_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    # ── Pre-compute campaign-adjusted utilities ────────────────────────────
    camp       = simulate_campaign(
        num_candidates=len(candidates),
        num_voters=num_voters,
        num_days=num_days,
        events=[],
        seed=seed,
    )
    camp_cands   = camp.get("candidates", [])
    daily_scores = camp.get("daily_scores", {})
    final_shares: Dict[str, float] = {}
    for camp_idx, camp_name in enumerate(camp_cands):
        if camp_idx < len(cand_names):
            shares_list = daily_scores.get(camp_name, [50.0])
            final_shares[cand_names[camp_idx]] = shares_list[-1] / 100.0

    campaign_utilities: Dict[Any, Dict[str, float]] = {}
    for v in voters:
        campaign_utilities[v["id"]] = {}
        for c_name in cand_names:
            share   = final_shares.get(c_name, 1.0 / len(cand_names))
            u       = true_utilities[v["id"]][c_name]
            blended = u * (1.0 - polling_effect * 0.4) + share * (polling_effect * 0.4)
            campaign_utilities[v["id"]][c_name] = max(0.0, min(1.0, blended))

    # ── Pre-compute information-adjusted utilities ─────────────────────────
    raw_bias   = info_cfg.get("media_bias", {}) or {}
    media_bias = {
        str(i): float(raw_bias.get(c["name"], 0.0))
        for i, c in enumerate(candidates)
    }
    vseg = info_cfg.get("voter_segments") or {}
    voter_segments = {
        "low_info":    float(vseg.get("low_info",    0.3)),
        "medium_info": float(vseg.get("medium_info", 0.5)),
        "high_info":   float(vseg.get("high_info",   0.2)),
    }

    def _apply_info(
        base: Dict[Any, Dict[str, float]]
    ) -> Dict[Any, Dict[str, float]]:
        mat  = [[base[v["id"]][c["name"]] for c in candidates] for v in voters]
        perc = apply_information_asymmetry(mat, media_bias, voter_segments, seed=seed)
        return {
            v["id"]: {c["name"]: perc[idx][j] for j, c in enumerate(candidates)}
            for idx, v in enumerate(voters)
        }

    info_utilities: Dict[Any, Dict[str, float]]      = _apply_info(true_utilities)
    camp_info_utilities: Dict[Any, Dict[str, float]] = _apply_info(campaign_utilities)

    # ── Pre-compute blank-vote adjusted voters ────────────────────────────
    blank_voters = copy.deepcopy(voters)
    if contagion_on:
        beta    = max(0.0, min(1.0, float(contagion_cfg.get("beta",  0.15))))
        gamma   = max(0.0, min(1.0, float(contagion_cfg.get("gamma", 0.10))))
        net_map = {"random": "random", "watts_strogatz": "small-world", "block": "clustered"}
        net     = net_map.get(str(contagion_cfg.get("network", "random")), "random")
        contagion_result = simulate_blank_contagion(
            num_voters=num_voters, initial_blank_rate=0.05,
            contagion_rate=beta, recovery_rate=gamma,
            num_rounds=10, network_type=net, seed=seed,
        )
        reduction = contagion_result.get("final_blank_rate", 0.05) * 0.4
        for v in blank_voters:
            v["blank_threshold"] = max(0.05, v["blank_threshold"] - reduction)

    # (campaign_on, info_on) → utilities dict
    utility_map: Dict[tuple[bool, bool], Dict[Any, Dict[str, float]]] = {
        (False, False): true_utilities,
        (False, True):  info_utilities,
        (True,  False): campaign_utilities,
        (True,  True):  camp_info_utilities,
    }

    # ── Run 8 combinations ────────────────────────────────────────────────
    combinations: list[Dict[str, Any]] = []

    for blank_on in (False, True):
        for campaign_on_flag in (False, True):
            for info_on in (False, True):
                combo_id = (
                    f"blank={'on' if blank_on else 'off'},"
                    f"campaign={'on' if campaign_on_flag else 'off'},"
                    f"info={'on' if info_on else 'off'}"
                )
                cur_utils  = utility_map[(campaign_on_flag, info_on)]
                cur_voters = blank_voters if blank_on else voters

                methods_out = _snapshot_election_winners(
                    cur_voters, candidates, cur_utils, issues,
                    blank_enabled=blank_on, blank_rule=blank_rule,
                )

                # Condorcet winner from adjusted rankings
                rankings_c: list[list[str]] = [
                    sorted(cand_names, key=lambda n: -cur_utils[v["id"]][n])
                    for v in cur_voters
                ]
                condorcet_w = get_condorcet_winner(rankings_c)

                pl_md  = methods_out.get("plurality", {})
                pl_win = (pl_md.get("winner_after_rule") or pl_md.get("winner")) \
                         if blank_on else pl_md.get("winner")

                combinations.append({
                    "id":                     combo_id,
                    "blank":                  blank_on,
                    "campaign":               campaign_on_flag,
                    "information_model":      info_on,
                    "plurality_winner":       pl_win,
                    "condorcet_winner":       condorcet_w,
                    "inter_method_agreement": _inter_method_agreement(methods_out),
                    "winner_differs_from_base": False,
                })

    base_winner = combinations[0]["plurality_winner"]
    for combo in combinations:
        combo["winner_differs_from_base"] = combo["plurality_winner"] != base_winner

    # ── Factor impact (agreement delta per factor) ────────────────────────
    def _factor_delta(key: str) -> float:
        on_  = [c["inter_method_agreement"] for c in combinations if     c[key]]
        off_ = [c["inter_method_agreement"] for c in combinations if not c[key]]
        avg_on  = sum(on_)  / len(on_)  if on_  else 0.0
        avg_off = sum(off_) / len(off_) if off_ else 0.0
        return round(avg_on - avg_off, 4)

    factor_deltas: Dict[str, float] = {
        "blank":             _factor_delta("blank"),
        "campaign":          _factor_delta("campaign"),
        "information_model": _factor_delta("information_model"),
    }
    most_disruptive  = min(factor_deltas, key=lambda k: factor_deltas[k])
    least_disruptive = max(factor_deltas, key=lambda k: factor_deltas[k])
    max_disrup_combo = min(
        combinations, key=lambda c: c["inter_method_agreement"]
    )["id"]

    return {
        "base_winner":                base_winner,
        "combinations":               combinations,
        "factor_deltas":              {k: round(v * 100, 1) for k, v in factor_deltas.items()},
        "most_disruptive_factor":     most_disruptive,
        "least_disruptive_factor":    least_disruptive,
        "max_disruption_combination": max_disrup_combo,
    }, 200


# ── Interpret endpoint ────────────────────────────────────────────────────────

# Translation templates keyed by language
_T: Dict[str, Dict[str, str]] = {
    "fr": {
        "consensus":         "✓ Large consensus : {pct}% des méthodes élisent {winner}.",
        "moderate_diverg":   "⚠ Divergence modérée : {n_groups} vainqueurs différents ({pct}% d'accord).",
        "strong_diverg":     "🚨 Forte divergence : seulement {pct}% des méthodes s'accordent.",
        "no_condorcet":      "Il n'existe pas de vainqueur de Condorcet dans cette configuration : les préférences sont cycliques (paradoxe d'Arrow) et les méthodes ne peuvent pas toutes s'accorder.",
        "condorcet_exists":  "{winner} est le vainqueur de Condorcet — il bat tous les autres candidats en duel direct.",
        "condorcet_spoiler": "Le vainqueur de Condorcet ({cw}) diffère du vainqueur à la pluralité ({pw}) : c'est un effet spoiler classique où la fragmentation du vote défavorise le candidat préféré par la majorité.",
        "high_blank":        "Le vote blanc élevé ({pct}%) fragilise la légitimité du vainqueur. Sous la règle '{rule}', ce taux peut invalider l'élection.",
        "best_regret":       "La méthode {method} minimise le régret bayésien ({score:.4f}) : elle maximise le bien-être collectif.",
        "worst_regret":      "La méthode {method} présente le régret bayésien le plus élevé ({score:.4f}) : elle 'rate' davantage le vrai consensus.",
        "ped_condorcet":     "Ce résultat illustre le critère de Condorcet (1785) : une méthode 'conforme' élit toujours le candidat préféré par la majorité en comparaison binaire. La pluralité ne respecte pas ce critère.",
        "ped_arrow":         "Ce résultat illustre le théorème d'impossibilité d'Arrow (1951) : avec des préférences cycliques, aucune méthode ne peut produire un résultat socialement cohérent sans sacrifier un critère de fairness.",
        "ped_consensus":     "Ce résultat illustre un cas idéal : quand un vainqueur de Condorcet existe et que l'électorat est peu polarisé, la plupart des méthodes convergent vers le même résultat.",
        "fact_pct":          "{pct}% des méthodes ({n}/{total}) élisent {winner}.",
        "fact_condorcet_y":  "Le vainqueur de Condorcet est {winner}.",
        "fact_condorcet_n":  "Il n'existe pas de vainqueur de Condorcet (cycle de préférences).",
        "fact_best":         "La méthode la plus 'juste' (régret bayésien minimal) : {method}.",
        "team":              "Équipe {winner}",
    },
    "en": {
        "consensus":         "✓ Broad consensus: {pct}% of methods elect {winner}.",
        "moderate_diverg":   "⚠ Moderate divergence: {n_groups} different winners ({pct}% agreement).",
        "strong_diverg":     "🚨 Strong divergence: only {pct}% of methods agree.",
        "no_condorcet":      "There is no Condorcet winner in this configuration: preferences cycle (Arrow's paradox) and methods cannot all agree.",
        "condorcet_exists":  "{winner} is the Condorcet winner — they beat every other candidate in direct head-to-head matchups.",
        "condorcet_spoiler": "The Condorcet winner ({cw}) differs from the plurality winner ({pw}): a classic spoiler effect where vote fragmentation hurts the majority's preferred candidate.",
        "high_blank":        "The high blank-vote rate ({pct}%) undermines the winner's legitimacy. Under the '{rule}' rule, this rate may invalidate the election.",
        "best_regret":       "Method {method} minimises Bayesian Regret ({score:.4f}): it maximises collective welfare.",
        "worst_regret":      "Method {method} has the highest Bayesian Regret ({score:.4f}): it deviates most from the true consensus.",
        "ped_condorcet":     "This result illustrates the Condorcet criterion (1785): a 'compliant' method always elects the candidate preferred by the majority in pairwise comparisons. Plurality does not satisfy this criterion.",
        "ped_arrow":         "This result illustrates Arrow's impossibility theorem (1951): with cyclical preferences, no method can produce a socially coherent result without sacrificing a fairness criterion.",
        "ped_consensus":     "This result illustrates an ideal case: when a Condorcet winner exists and the electorate is not highly polarised, most methods converge on the same outcome.",
        "fact_pct":          "{pct}% of methods ({n}/{total}) elect {winner}.",
        "fact_condorcet_y":  "The Condorcet winner is {winner}.",
        "fact_condorcet_n":  "No Condorcet winner exists (preference cycle).",
        "fact_best":         "Most 'fair' method (minimal Bayesian Regret): {method}.",
        "team":              "Team {winner}",
    },
}


def _interpret_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /interpret — extracted for FastAPI v2."""
    lang = str(data.get("lang", "fr")) if str(data.get("lang", "fr")) in ("fr", "en") else "fr"
    T    = _T[lang]

    methods_raw        = data.get("methods") or {}
    condorcet_winner   = data.get("condorcet_winner")
    condorcet_exists   = bool(data.get("condorcet_exists", condorcet_winner is not None))
    inter_agreement    = float(data.get("inter_method_agreement", 0.0))
    blank_rate         = float(data.get("blank_rate", 0.0))
    blank_rule         = str((data.get("config") or {}).get("blank_vote", {}).get("rule", "symbolic"))

    if not methods_raw:
        return {"error": "No methods data provided"}, 400

    # ── 1. Group methods by effective winner ──────────────────────────────
    winner_to_methods: Dict[str, list[str]] = {}
    for method_name, md in methods_raw.items():
        if not isinstance(md, dict):
            continue
        # Prefer winner_after_rule if blank vote applied
        effective = md.get("winner_after_rule") or md.get("winner")
        if not effective:
            continue
        winner_to_methods.setdefault(str(effective), []).append(method_name)

    n_methods = len(methods_raw)
    method_groups = [
        {
            "winner":  winner,
            "methods": sorted(methods),
            "pct":     round(len(methods) / n_methods, 4) if n_methods else 0.0,
        }
        for winner, methods in sorted(
            winner_to_methods.items(),
            key=lambda kv: -len(kv[1])
        )
    ]

    plurality_winner = winner_to_methods.get("plurality", [""])[0] if "plurality" in {
        method: md.get("winner") for method, md in methods_raw.items()
    } else (method_groups[0]["winner"] if method_groups else None)

    # Recompute plurality winner properly
    pl_md = methods_raw.get("plurality", {})
    plurality_winner = pl_md.get("winner_after_rule") or pl_md.get("winner") if pl_md else None

    # ── 2. Headline ───────────────────────────────────────────────────────
    pct_int = round(inter_agreement * 100)
    top_group = method_groups[0] if method_groups else None
    top_winner = top_group["winner"] if top_group else "?"

    if inter_agreement > 0.85:
        headline = T["consensus"].format(pct=pct_int, winner=top_winner)
    elif inter_agreement >= 0.5:
        headline = T["moderate_diverg"].format(n_groups=len(method_groups), pct=pct_int)
    else:
        headline = T["strong_diverg"].format(pct=pct_int)

    # ── 3. Condorcet analysis ─────────────────────────────────────────────
    if not condorcet_exists:
        condorcet_analysis = T["no_condorcet"]
    elif condorcet_winner and plurality_winner and condorcet_winner != plurality_winner:
        condorcet_analysis = T["condorcet_spoiler"].format(
            cw=condorcet_winner, pw=plurality_winner
        )
    else:
        condorcet_analysis = T["condorcet_exists"].format(
            winner=condorcet_winner or top_winner
        )

    # ── 4. Divergence reason ──────────────────────────────────────────────
    if len(method_groups) <= 1:
        divergence_reason = condorcet_analysis
    elif not condorcet_exists:
        divergence_reason = T["no_condorcet"]
    else:
        divergence_reason = T["condorcet_spoiler"].format(
            cw=condorcet_winner or "?", pw=plurality_winner or "?"
        ) if condorcet_winner and plurality_winner and condorcet_winner != plurality_winner \
          else condorcet_analysis

    # ── 5. Best / worst method by Bayesian Regret ─────────────────────────
    regrets: Dict[str, float] = {}
    for m, md in methods_raw.items():
        if isinstance(md, dict) and md.get("bayesian_regret") is not None:
            regrets[m] = float(md["bayesian_regret"])

    best_by_regret  = min(regrets, key=lambda k: regrets[k]) if regrets else None
    worst_by_regret = max(regrets, key=lambda k: regrets[k]) if regrets else None

    # ── 6. Blank analysis ─────────────────────────────────────────────────
    blank_analysis: Optional[str] = None
    if blank_rate > 0.2:
        blank_analysis = T["high_blank"].format(
            pct=round(blank_rate * 100, 1), rule=blank_rule
        )

    # ── 7. Pedagogical note ───────────────────────────────────────────────
    if not condorcet_exists:
        pedagogical_note = T["ped_arrow"]
    elif inter_agreement > 0.85:
        pedagogical_note = T["ped_consensus"]
    else:
        pedagogical_note = T["ped_condorcet"]

    # ── 8. Key facts ──────────────────────────────────────────────────────
    key_facts: list[str] = []
    if top_group:
        top_pct:     float     = top_group["pct"]      # type: ignore[assignment]
        top_methods: list[str] = top_group["methods"]  # type: ignore[assignment]
        key_facts.append(T["fact_pct"].format(
            pct=int(round(top_pct * 100, 0)),
            n=len(top_methods),
            total=n_methods,
            winner=top_group["winner"],
        ))
    if condorcet_exists and condorcet_winner:
        key_facts.append(T["fact_condorcet_y"].format(winner=condorcet_winner))
    else:
        key_facts.append(T["fact_condorcet_n"])
    if best_by_regret:
        key_facts.append(T["fact_best"].format(method=best_by_regret))

    return {
        "headline":           headline,
        "condorcet_analysis": condorcet_analysis,
        "divergence_reason":  divergence_reason,
        "method_groups":      method_groups,
        "best_by_regret":     best_by_regret,
        "worst_by_regret":    worst_by_regret,
        "blank_analysis":     blank_analysis,
        "pedagogical_note":   pedagogical_note,
        "key_facts":          key_facts,
    }, 200


# ── Pipeline animation ────────────────────────────────────────────────────────

def _voter_snap(
    voters: list[Dict[str, Any]],
    utilities: Dict[Any, Dict[str, float]],
    blank_enabled: bool = False,
) -> list[Dict[str, Any]]:
    """Capture a voter snapshot with current preference and blank status."""
    snaps: list[Dict[str, Any]] = []
    for v in voters:
        u = utilities.get(v["id"], {})
        pref: Optional[str] = max(u, key=lambda k: u[k]) if u else None
        is_blank = blank_enabled and (max(u.values(), default=0.0) < v.get("blank_threshold", 0.375))
        snaps.append({
            "id":         v["id"],
            "x":          round(2.0 * v["issue_positions"].get("economy",       0.5) - 1.0, 3),
            "y":          round(2.0 * v["issue_positions"].get("social_welfare", 0.5) - 1.0, 3),
            "preference": pref,
            "is_blank":   is_blank,
        })
    return snaps


def _count_changed(prev: list[Dict[str, Any]], curr: list[Dict[str, Any]]) -> int:
    prev_map = {s["id"]: (s["preference"], s["is_blank"]) for s in prev}
    return sum(
        1 for s in curr
        if (s["preference"], s["is_blank"]) != prev_map.get(s["id"], (None, False))
    )


def _simulate_pipeline_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure-compute worker for /simulate-pipeline (step-by-step animation)."""
    import copy

    num_voters     = max(10, min(200, int(data.get("num_voters",  150))))
    ideology       = str(data.get("ideology",   "random"))
    seed           = int(data.get("seed",        42))
    cand_specs     = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ])[:6]

    blank_cfg      = data.get("blank_vote", {}) or {}
    blank_enabled  = bool(blank_cfg.get("enabled", False))
    blank_rule_str = str(blank_cfg.get("rule", "symbolic"))
    contagion_cfg  = blank_cfg.get("contagion", {}) or {}
    contagion_on   = bool(contagion_cfg.get("enabled", False))

    info_cfg       = data.get("information_model", {}) or {}
    info_enabled   = bool(info_cfg.get("enabled", False))

    campaign_cfg   = data.get("campaign", {}) or {}
    campaign_on    = bool(campaign_cfg.get("enabled", False))
    num_days       = max(7,  min(60, int(campaign_cfg.get("num_days",        30))))
    polling_effect = max(0.0, min(1.0, float(campaign_cfg.get("polling_effect", 0.3))))

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)

    issues = DEFAULT_ISSUES
    candidates, voters, true_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    cands_out = [
        {
            "name":  c["name"],
            "x":     round(2.0 * c["ideology_position"] - 1.0, 3),
            "y":     round(2.0 * c["policies"].get("social_welfare", 0.5) - 1.0, 3),
            "party": c["party"],
        }
        for c in candidates
    ]

    steps:    list[Dict[str, Any]] = []
    prev_snap: list[Dict[str, Any]] = []
    current_utilities: Dict[Any, Dict[str, float]] = dict(true_utilities)

    # ── Step 1: Base electorate ───────────────────────────────────────────
    base_snap = _voter_snap(voters, true_utilities, blank_enabled)
    steps.append({
        "id":      "base",
        "label":   {"fr": "Électeurs créés",        "en": "Voters created"},
        "desc":    {"fr": f"{num_voters} électeurs générés avec distribution « {ideology} ».",
                    "en": f"{num_voters} voters generated with « {ideology} » distribution."},
        "voters":  base_snap,
        "metrics": {"num_voters": num_voters, "ideology": ideology},
    })
    prev_snap = base_snap

    # ── Step 2: Campaign ──────────────────────────────────────────────────
    if campaign_on:
        camp         = simulate_campaign(
            num_candidates=len(candidates), num_voters=num_voters,
            num_days=num_days, events=[], seed=seed,
        )
        camp_cands   = camp.get("candidates", [])
        daily_scores = camp.get("daily_scores", {})
        final_shares: Dict[str, float] = {}
        for ci, camp_name in enumerate(camp_cands):
            if ci < len(cand_names):
                shares = daily_scores.get(camp_name, [50.0])
                final_shares[cand_names[ci]] = shares[-1] / 100.0

        for v in voters:
            for c_name in cand_names:
                share   = final_shares.get(c_name, 1.0 / len(cand_names))
                u       = current_utilities[v["id"]][c_name]
                blended = u * (1.0 - polling_effect * 0.4) + share * (polling_effect * 0.4)
                current_utilities[v["id"]][c_name] = max(0.0, min(1.0, blended))

        camp_snap = _voter_snap(voters, current_utilities, blank_enabled)
        changed   = _count_changed(prev_snap, camp_snap)
        steps.append({
            "id":    "campaign",
            "label": {"fr": "Effet de campagne",    "en": "Campaign effect"},
            "desc":  {
                "fr": f"Campagne de {num_days} jours (bandwagon {round(polling_effect * 100)}%). "
                      f"{changed} électeur(s) ont changé de préférence.",
                "en": f"{num_days}-day campaign (bandwagon {round(polling_effect * 100)}%). "
                      f"{changed} voter(s) changed preference.",
            },
            "voters":  camp_snap,
            "metrics": {"changed": changed, "polling_effect": polling_effect},
        })
        prev_snap = camp_snap

    # ── Step 3: Blank-vote contagion ──────────────────────────────────────
    if contagion_on and blank_enabled:
        beta    = max(0.0, min(1.0, float(contagion_cfg.get("beta",  0.15))))
        gamma   = max(0.0, min(1.0, float(contagion_cfg.get("gamma", 0.10))))
        net_map = {"random": "random", "watts_strogatz": "small-world", "block": "clustered"}
        net     = net_map.get(str(contagion_cfg.get("network", "random")), "random")
        cont_r  = simulate_blank_contagion(
            num_voters=num_voters, initial_blank_rate=0.05,
            contagion_rate=beta, recovery_rate=gamma,
            num_rounds=10, network_type=net, seed=seed,
        )
        final_blank = cont_r.get("final_blank_rate", 0.05)
        reduction   = final_blank * 0.4
        for v in voters:
            v["blank_threshold"] = max(0.05, v["blank_threshold"] - reduction)

        cont_snap   = _voter_snap(voters, current_utilities, blank_enabled=True)
        blank_count = sum(1 for s in cont_snap if s["is_blank"])
        steps.append({
            "id":    "contagion",
            "label": {"fr": "Vote blanc contagieux", "en": "Blank-vote contagion"},
            "desc":  {
                "fr": f"SIS (β={beta:.2f}, γ={gamma:.2f}) — taux final : "
                      f"{round(final_blank * 100, 1)} %. "
                      f"{blank_count} électeur(s) votent blanc.",
                "en": f"SIS (β={beta:.2f}, γ={gamma:.2f}) — final rate: "
                      f"{round(final_blank * 100, 1)} %. "
                      f"{blank_count} voter(s) cast blank.",
            },
            "voters":  cont_snap,
            "metrics": {"blank_rate": round(final_blank, 4), "blank_count": blank_count},
        })
        prev_snap = cont_snap

    # ── Step 4: Information model ─────────────────────────────────────────
    effective_utilities: Dict[Any, Dict[str, float]] = current_utilities
    if info_enabled:
        raw_bias   = info_cfg.get("media_bias", {}) or {}
        media_bias = {
            str(i): float(raw_bias.get(c["name"], 0.0))
            for i, c in enumerate(candidates)
        }
        vseg = info_cfg.get("voter_segments") or {}
        voter_segments = {
            "low_info":    float(vseg.get("low_info",    0.3)),
            "medium_info": float(vseg.get("medium_info", 0.5)),
            "high_info":   float(vseg.get("high_info",   0.2)),
        }
        true_list = [[current_utilities[v["id"]][c["name"]] for c in candidates] for v in voters]
        perceived  = apply_information_asymmetry(true_list, media_bias, voter_segments, seed=seed)
        effective_utilities = {
            v["id"]: {c["name"]: perceived[idx][j] for j, c in enumerate(candidates)}
            for idx, v in enumerate(voters)
        }

        info_snap = _voter_snap(voters, effective_utilities, blank_enabled)
        changed   = _count_changed(prev_snap, info_snap)
        steps.append({
            "id":    "information",
            "label": {"fr": "Modèle d'information",   "en": "Information model"},
            "desc":  {
                "fr": f"Biais médias appliqué. {changed} électeur(s) ont changé de préférence perçue.",
                "en": f"Media bias applied. {changed} voter(s) changed perceived preference.",
            },
            "voters":  info_snap,
            "metrics": {"changed": changed},
        })
        prev_snap = info_snap

    # ── Step 5: Results ───────────────────────────────────────────────────
    result_mc       = compare_all_methods(
        voters, candidates, issues,
        blank_vote=blank_enabled,
        override_utilities=effective_utilities,
    )
    condorcet_w     = result_mc.get("condorcet_winner")
    blank_pct       = result_mc.get("blank_pct") or 0.0
    methods_data    = result_mc.get("methods", {})
    agreement       = _inter_method_agreement(methods_data)

    winner_map: Dict[str, list[str]] = {}
    for m, md in methods_data.items():
        w = md.get("winner")
        if w:
            winner_map.setdefault(w, []).append(m)

    steps.append({
        "id":    "results",
        "label": {"fr": "Résultats électoraux",   "en": "Election results"},
        "desc":  {
            "fr": f"Accord inter-méthodes : {round(agreement * 100)} %. "
                  + (f"Vainqueur de Condorcet : {condorcet_w}." if condorcet_w
                     else "Pas de vainqueur de Condorcet."),
            "en": f"Inter-method agreement: {round(agreement * 100)} %. "
                  + (f"Condorcet winner: {condorcet_w}." if condorcet_w
                     else "No Condorcet winner."),
        },
        "voters":  prev_snap,
        "metrics": {
            "inter_method_agreement": round(agreement, 4),
            "condorcet_winner":       condorcet_w,
            "blank_rate":             round(blank_pct, 4),
        },
        "winner_groups": [
            {"winner": w, "methods": ms, "pct": round(len(ms) / max(len(methods_data), 1), 4)}
            for w, ms in sorted(winner_map.items(), key=lambda kv: -len(kv[1]))
        ],
    })

    return {
        "steps":      steps,
        "candidates": cands_out,
        "num_steps":  len(steps),
    }, 200


# ── Coalition endpoint ────────────────────────────────────────────────────────

def _dhondt(vote_shares: Dict[str, float], total_seats: int) -> Dict[str, int]:
    """D'Hondt proportional seat allocation.

    vote_shares: {party_name: fraction_of_vote}  (values sum ≈ 1)
    Returns {party_name: seats_awarded}.
    """
    seats: Dict[str, int] = {p: 0 for p in vote_shares}
    for _ in range(total_seats):
        quotients = {p: vote_shares[p] / (seats[p] + 1) for p in vote_shares}
        winner = max(quotients, key=lambda k: quotients[k])
        seats[winner] += 1
    return seats


def _greedy_coalition(
    seats: Dict[str, int],
    positions: Dict[str, float],
    threshold: int,
) -> Dict[str, Any]:
    """
    Greedy coalition formation starting from the plurality party.
    Iteratively adds the ideologically closest available party until the
    coalition reaches `threshold` seats.

    Returns {parties, seats, coalition_spread, government_possible}.
    """
    total = sum(seats.values())
    if total == 0:
        return {"parties": [], "seats": 0, "coalition_spread": 0.0, "government_possible": False}

    sorted_parties = sorted(seats.keys(), key=lambda p: -seats[p])
    coalition: list[str] = [sorted_parties[0]]
    coalition_seats = seats[sorted_parties[0]]
    remaining = [p for p in sorted_parties[1:]]

    while coalition_seats < threshold and remaining:
        # Closest ideologically to current coalition centre
        centre = sum(positions[p] for p in coalition) / len(coalition)
        closest = min(remaining, key=lambda p: abs(positions[p] - centre))
        coalition.append(closest)
        coalition_seats += seats[closest]
        remaining.remove(closest)

    pos_vals = [positions[p] for p in coalition]
    spread = (
        float(_np.var(pos_vals)) if len(pos_vals) > 1 else 0.0
    )

    return {
        "parties":            coalition,
        "seats":              coalition_seats,
        "coalition_spread":   round(spread, 4),
        "government_possible": coalition_seats >= threshold,
    }


def _coalition_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /coalition — extracted so FastAPI v2 can call it
    without going through Flask context. Same signature as the other
    workers: (data dict) -> (body, http_status)."""

    num_voters  = max(10, min(1000, int(data.get("num_voters",  300))))
    ideology    = str(data.get("ideology",   "random"))
    seed        = int(data.get("seed",        42))
    cand_specs  = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ])[:6]
    total_seats          = max(10, min(1000, int(data.get("total_seats",          100))))
    government_threshold = max(0.0, min(1.0, float(data.get("government_threshold", 0.5))))

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)

    issues = DEFAULT_ISSUES
    candidates, voters, true_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    # Candidate ideological position (x axis, [-1, 1])
    positions: Dict[str, float] = {
        c["name"]: round(2.0 * c["ideology_position"] - 1.0, 3)
        for c in candidates
    }

    result_mc = compare_all_methods(
        voters, candidates, issues,
        blank_vote=False,
        override_utilities=true_utilities,
    )
    methods_data: Dict[str, Any] = result_mc.get("methods", {})

    seat_threshold = int(_np.ceil(total_seats * government_threshold))

    methods_out: list[Dict[str, Any]] = []
    for method_name, md in sorted(methods_data.items()):
        winner = md.get("winner") or ""
        scores: Dict[str, float] = md.get("scores") or {}

        # Derive vote-share proxy from scores (normalise to sum=1)
        if scores:
            total_score = sum(scores.values()) or 1.0
            vote_shares = {n: scores[n] / total_score for n in cand_names if n in scores}
        else:
            # Fallback: winner gets 1, others share remainder
            n = len(cand_names)
            vote_shares = {name: (0.6 if name == winner else 0.4 / max(n - 1, 1))
                           for name in cand_names}

        seats_alloc = _dhondt(vote_shares, total_seats)
        coal        = _greedy_coalition(seats_alloc, positions, seat_threshold)

        methods_out.append({
            "method":             method_name,
            "winner":             winner,
            "seats":              seats_alloc,
            "vote_shares":        {n: round(v, 4) for n, v in vote_shares.items()},
            "coalition_parties":  coal["parties"],
            "coalition_seats":    coal["seats"],
            "coalition_spread":   coal["coalition_spread"],
            "government_possible": coal["government_possible"],
        })

    # ── Summary across methods ─────────────────────────────────────────────
    possible = [m for m in methods_out if m["government_possible"]]
    spreads  = {m["method"]: m["coalition_spread"] for m in possible}
    most_centrist_method  = min(spreads, key=lambda k: spreads[k]) if spreads else None
    most_divergent_method = max(spreads, key=lambda k: spreads[k]) if spreads else None

    return {
        "methods":               methods_out,
        "candidates":            [
            {"name": c["name"], "x": positions[c["name"]]}
            for c in candidates
        ],
        "total_seats":           total_seats,
        "seat_threshold":        seat_threshold,
        "most_centrist_method":  most_centrist_method,
        "most_divergent_method": most_divergent_method,
        "inter_method_agreement": _inter_method_agreement(
            {m["method"]: {"winner": m["coalition_parties"][0] if m["coalition_parties"] else ""}
             for m in methods_out}
        ),
    }, 200


# ── Districts endpoint ────────────────────────────────────────────────────────

def _run_district_fptp(
    cand_names: list[str],
    candidates: list[Dict[str, Any]],
    num_voters: int,
    ideology_center: float,
    ideology_variance: float,
    issues: list[str],
    seed: int,
) -> Dict[str, Any]:
    """
    Simulate one district.

    ideology_center shifts the entire voter distribution along the x axis
    by displacing economy-related issue positions.  Returns winner (FPTP)
    and raw first-choice vote counts that can be turned into shares.
    """
    _random.seed(seed)
    _np.random.seed(seed)

    voters = [create_voter(issues, i, ideology_distribution="random") for i in range(num_voters)]

    # Shift every voter's economy position by ideology_center (clamped to [0,1])
    shift = ideology_center * 0.3          # max shift ≈ 0.3 to keep results legible
    for v in voters:
        old_econ = v["issue_positions"].get("economy", 0.5)
        v["issue_positions"]["economy"] = max(0.0, min(1.0, old_econ + shift))

    utilities: Dict[Any, Dict[str, float]] = {
        v["id"]: {c["name"]: calculate_utility(v, c, issues)["utility"] for c in candidates}
        for v in voters
    }

    rankings: list[list[str]] = []
    for v in voters:
        uid = v["id"]
        rankings.append(sorted(utilities[uid].keys(), key=lambda n: -utilities[uid][n]))

    # First-choice counts → vote shares
    first_choice: Counter[str] = Counter()
    for r in rankings:
        if r:
            first_choice[r[0]] += 1

    total = len(voters) or 1
    vote_shares = {n: round(first_choice.get(n, 0) / total, 4) for n in cand_names}
    winner = get_plurality_winner(rankings)

    return {"winner": winner, "vote_shares": vote_shares}


def _districts_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /districts — extracted for FastAPI v2."""
    num_districts            = max(5,   min(50,  int(data.get("num_districts",            10))))
    voters_per_district      = max(50,  min(500, int(data.get("voters_per_district",      100))))
    district_ideology_variance = max(0.0, min(1.0, float(data.get("district_ideology_variance", 0.3))))
    seed                     = int(data.get("seed", 42))
    cand_specs               = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ])[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    issues = DEFAULT_ISSUES
    _random.seed(seed)
    _np.random.seed(seed)

    cand_names = [str(s.get("name", f"C{i}")) for i, s in enumerate(cand_specs)]
    candidates = [
        _build_candidate_from_xy(
            i,
            cand_names[i],
            max(-1.0, min(1.0, float(s.get("x", 0.0)))),
            max(-1.0, min(1.0, float(s.get("y", 0.0)))),
            issues,
        )
        for i, s in enumerate(cand_specs)
    ]

    # Generate district ideology centers: N samples from N(0, variance)
    _np.random.seed(seed)
    ideology_centers = _np.random.normal(0.0, district_ideology_variance, num_districts).tolist()

    # ── Per-district simulation ────────────────────────────────────────────
    district_results: list[Dict[str, Any]] = []
    national_vote_totals: Dict[str, float] = {n: 0.0 for n in cand_names}

    for i, center in enumerate(ideology_centers):
        res = _run_district_fptp(
            cand_names, candidates, voters_per_district,
            float(center), district_ideology_variance, issues,
            seed=seed + i + 1,
        )
        district_results.append({
            "id":              i,
            "ideology_center": round(float(center), 3),
            "winner_fptp":     res["winner"],
            "vote_shares":     res["vote_shares"],
        })
        for n in cand_names:
            national_vote_totals[n] += res["vote_shares"].get(n, 0.0)

    # ── FPTP parliament: count district wins ───────────────────────────────
    parliament_fptp: Dict[str, int] = {n: 0 for n in cand_names}
    for dr in district_results:
        w = dr["winner_fptp"]
        if w and w in parliament_fptp:
            parliament_fptp[w] += 1

    # ── National vote shares (average across districts) ───────────────────
    national_vote_share: Dict[str, float] = {
        n: round(national_vote_totals[n] / num_districts, 4) for n in cand_names
    }

    # ── Proportional parliament: D'Hondt on national shares ───────────────
    parliament_proportional = _dhondt(national_vote_share, num_districts)

    # ── National Condorcet: quick pairwise from aggregated vote shares ─────
    # Build a representative ranking from national vote shares (sorted desc)
    # and compute Condorcet winner heuristically via pairwise dominance.
    sorted_by_share = sorted(cand_names, key=lambda n: -national_vote_share.get(n, 0))

    def _beats(a: str, b: str) -> bool:
        # In aggregate, a beats b in district-by-district pairwise
        a_wins = sum(
            1 for dr in district_results
            if dr["vote_shares"].get(a, 0) > dr["vote_shares"].get(b, 0)
        )
        return a_wins > num_districts / 2

    condorcet_national: Optional[str] = None
    for cand in sorted_by_share:
        if all(_beats(cand, other) for other in cand_names if other != cand):
            condorcet_national = cand
            break

    # ── Distortion index ──────────────────────────────────────────────────
    # Average absolute difference between seat share and vote share, per candidate
    total_seats = num_districts
    distortion_vals = [
        abs(parliament_fptp[n] / total_seats - national_vote_share.get(n, 0))
        for n in cand_names
    ]
    distortion = round(sum(distortion_vals) / max(len(distortion_vals), 1), 4)

    fptp_winner         = max(parliament_fptp,         key=lambda k: parliament_fptp[k])
    proportional_winner = max(parliament_proportional, key=lambda k: parliament_proportional[k])

    return {
        "districts":              district_results,
        "parliament_fptp":        parliament_fptp,
        "parliament_proportional": parliament_proportional,
        "national_vote_share":    national_vote_share,
        "distortion":             distortion,
        "condorcet_winner_national": condorcet_national,
        "fptp_winner":            fptp_winner,
        "proportional_winner":    proportional_winner,
        "num_districts":          num_districts,
    }, 200


# ── Primary endpoint ──────────────────────────────────────────────────────────

def _build_primary_candidate(
    i: int, name: str, ideology_pos: float, issues: list[str]
) -> Dict[str, Any]:
    """Build a candidate dict from a 1-D ideology position in [-1, 1]."""
    x = float(ideology_pos)
    return _build_candidate_from_xy(i, name, x, 0.0, issues)


def _run_primary(
    primary_candidates: list[Dict[str, Any]],
    party_voters: list[Dict[str, Any]],
    utilities: Dict[Any, Dict[str, float]],
    method: str,
) -> Dict[str, Any]:
    """
    Run a single party primary among party_voters.

    Returns {winner, runner_up, vote_shares}.
    """
    cand_names = [c["name"] for c in primary_candidates]
    if not party_voters or not cand_names:
        return {"winner": cand_names[0] if cand_names else "", "runner_up": None, "vote_shares": {}}

    rankings: list[list[str]] = []
    for v in party_voters:
        uid = v["id"]
        u = {n: utilities.get(uid, {}).get(n, 0.0) for n in cand_names}
        rankings.append(sorted(u.keys(), key=lambda n: -u[n]))

    # First-choice counts
    first: Counter[str] = Counter(r[0] for r in rankings if r)
    total = len(party_voters) or 1
    vote_shares = {n: round(first.get(n, 0) / total, 4) for n in cand_names}

    if method == "irv":
        winner = get_irv_winner(rankings)
    elif method == "approval":
        uid_utilities = {v["id"]: {n: utilities.get(v["id"], {}).get(n, 0.0) for n in cand_names}
                         for v in party_voters}
        winner = get_approval_winner_sincere(uid_utilities)
    else:  # plurality (default)
        winner = get_plurality_winner(rankings)

    winner = winner or (cand_names[0] if cand_names else "")

    sorted_by_share = sorted(cand_names, key=lambda n: -vote_shares.get(n, 0))
    runner_up = next((n for n in sorted_by_share if n != winner), None)

    return {"winner": winner, "runner_up": runner_up, "vote_shares": vote_shares}


def _primary_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /primary — extracted for FastAPI v2."""
    parties_raw        = data.get("parties", [])
    general_num_voters = max(50, min(2000, int(data.get("general_num_voters", 500))))
    general_ideology   = str(data.get("general_ideology", "random"))
    primary_method     = str(data.get("primary_method", "plurality"))
    general_method     = str(data.get("general_method",  "plurality"))
    seed               = int(data.get("seed", 42))

    if len(parties_raw) < 2:
        return {"error": "At least 2 parties required"}, 400

    for p in parties_raw:
        if len(p.get("primary_candidates", [])) < 2:
            return {"error": f"Party '{p.get('name')}' needs at least 2 primary candidates"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    # ── Build all primary candidates (flat list, per party) ───────────────
    all_primary_candidates: list[Dict[str, Any]] = []
    party_meta: list[Dict[str, Any]] = []
    cand_offset = 0

    for party in parties_raw:
        pname      = str(party.get("name", "Party"))
        pcenter    = float(party.get("ideology_center", 0.0))
        pvoters_pct = max(0.05, min(1.0, float(party.get("primary_voters_pct", 0.3))))
        prim_specs = party.get("primary_candidates", [])

        prim_cands = [
            _build_primary_candidate(
                cand_offset + i,
                str(s.get("name", f"{pname}_C{i}")),
                max(-1.0, min(1.0, float(s.get("ideology_position", pcenter)))),
                issues,
            )
            for i, s in enumerate(prim_specs)
        ]
        all_primary_candidates.extend(prim_cands)
        party_meta.append({
            "name":         pname,
            "center":       pcenter,
            "voters_pct":   pvoters_pct,
            "prim_cands":   prim_cands,
        })
        cand_offset += len(prim_specs)

    # ── Build the general electorate ──────────────────────────────────────
    _random.seed(seed)
    _np.random.seed(seed)
    general_voters = [
        create_voter(issues, i, ideology_distribution=general_ideology)
        for i in range(general_num_voters)
    ]

    # Pre-compute utilities for ALL candidates against ALL general voters
    all_utils: Dict[Any, Dict[str, float]] = {
        v["id"]: {
            c["name"]: calculate_utility(v, c, issues)["utility"]
            for c in all_primary_candidates
        }
        for v in general_voters
    }

    # ── Per-party primary ─────────────────────────────────────────────────
    primaries_out: list[Dict[str, Any]] = []
    general_ballot_cands: list[Dict[str, Any]] = []

    for pm in party_meta:
        pcenter = pm["center"]

        # Partisan voters: closest general voters to the party centre
        # Sort by distance and take top (voters_pct * total)
        def _dist_to_center(v: Dict[str, Any]) -> float:
            econ: float = float(v["issue_positions"].get("economy", 0.5))
            diff: float = econ - (pcenter + 1.0) / 2.0
            return diff if diff >= 0.0 else -diff

        sorted_voters = sorted(general_voters, key=_dist_to_center)
        n_primary = max(2, int(len(general_voters) * pm["voters_pct"]))
        party_voters = sorted_voters[:n_primary]

        prim_result = _run_primary(pm["prim_cands"], party_voters, all_utils, primary_method)
        winner_name = prim_result["winner"]

        # Find winner candidate object
        winner_cand = next(
            (c for c in pm["prim_cands"] if c["name"] == winner_name),
            pm["prim_cands"][0],
        )
        general_ballot_cands.append(winner_cand)

        # Primary distortion: |position of winner - centre of party|
        winner_pos = round(2.0 * winner_cand["ideology_position"] - 1.0, 3)
        distortion = round(abs(winner_pos - pcenter), 4)

        primaries_out.append({
            "party":       pm["name"],
            "winner":      winner_name,
            "runner_up":   prim_result["runner_up"],
            "distortion":  distortion,
            "winner_pos":  winner_pos,
            "party_center": pcenter,
            "vote_shares": prim_result["vote_shares"],
            "num_primary_voters": len(party_voters),
        })

    # ── General election ──────────────────────────────────────────────────
    gen_utils: Dict[Any, Dict[str, float]] = {
        v["id"]: {c["name"]: all_utils[v["id"]][c["name"]] for c in general_ballot_cands}
        for v in general_voters
    }

    gen_rankings: list[list[str]] = []
    for v in general_voters:
        uid = v["id"]
        gen_rankings.append(
            sorted(gen_utils[uid].keys(), key=lambda n: -gen_utils[uid][n])
        )

    first_gen: Counter[str] = Counter(r[0] for r in gen_rankings if r)
    total_gen = len(general_voters) or 1
    gen_vote_shares = {
        c["name"]: round(first_gen.get(c["name"], 0) / total_gen, 4)
        for c in general_ballot_cands
    }

    if general_method == "irv":
        general_winner_name = get_irv_winner(gen_rankings)
    elif general_method == "approval":
        general_winner_name = get_approval_winner_sincere(gen_utils)
    else:
        general_winner_name = get_plurality_winner(gen_rankings)
    general_winner_name = general_winner_name or general_ballot_cands[0]["name"]

    sorted_gen = sorted(general_ballot_cands, key=lambda c: -gen_vote_shares.get(c["name"], 0))
    general_runner_up = next((c["name"] for c in sorted_gen if c["name"] != general_winner_name), None)

    # ── Median voter distance ─────────────────────────────────────────────
    winner_cand_obj = next(
        (c for c in general_ballot_cands if c["name"] == general_winner_name),
        general_ballot_cands[0],
    )
    winner_econ = winner_cand_obj["ideology_position"]
    median_econ = float(_np.median([v["issue_positions"].get("economy", 0.5) for v in general_voters]))
    median_voter_distance = round(abs(winner_econ - median_econ), 4)

    # ── Without-primaries: party centres run directly ─────────────────────
    center_cands = [
        _build_primary_candidate(i, f"{pm['name']}Centre", pm["center"], issues)
        for i, pm in enumerate(party_meta)
    ]
    center_utils: Dict[Any, Dict[str, float]] = {
        v["id"]: {c["name"]: calculate_utility(v, c, issues)["utility"] for c in center_cands}
        for v in general_voters
    }
    center_rankings: list[list[str]] = []
    for v in general_voters:
        uid = v["id"]
        center_rankings.append(
            sorted(center_utils[uid].keys(), key=lambda n: -center_utils[uid][n])
        )

    if general_method == "irv":
        no_primary_winner = get_irv_winner(center_rankings)
    elif general_method == "approval":
        no_primary_winner = get_approval_winner_sincere(center_utils)
    else:
        no_primary_winner = get_plurality_winner(center_rankings)

    # Map back from "PartyNameCentre" → party name
    if no_primary_winner:
        party_name_map = {f"{pm['name']}Centre": pm["name"] for pm in party_meta}
        no_primary_winner = party_name_map.get(no_primary_winner, no_primary_winner)

    return {
        "primaries":              primaries_out,
        "general_ballot":         [c["name"] for c in general_ballot_cands],
        "general_winner":         general_winner_name,
        "general_runner_up":      general_runner_up,
        "general_vote_shares":    gen_vote_shares,
        "median_voter_distance":  median_voter_distance,
        "without_primaries_winner": no_primary_winner,
    }, 200


# ── Adaptive voting endpoint ──────────────────────────────────────────────────

_METHOD_WINNERS: Dict[str, Any] = {
    "plurality": get_plurality_winner,
    "irv":       get_irv_winner,
    "borda":     get_borda_winner,
    "schulze":   get_schulze_winner,
}


def _compute_winner(
    rankings: list[list[str]],
    utilities: Dict[Any, Dict[str, float]],
    method: str,
) -> Optional[str]:
    """Dispatch to the correct winner function for the given method."""
    if method == "approval":
        return get_approval_winner_sincere(utilities)
    fn = _METHOD_WINNERS.get(method, get_plurality_winner)
    result: Optional[str] = fn(rankings)
    return result


def _tactical_vote(
    voter_id: Any,
    sincere_ranking: list[str],
    utilities: Dict[str, float],
    polls: Dict[str, float],
    strategic_threshold: float,
) -> list[str]:
    """
    Compute a tactical ranking for one strategic voter.

    A voter becomes tactical when their 1st choice polls below
    `strategic_threshold` (as a fraction).  They then move the
    viable candidate with the highest personal utility to the top.
    Viable = polls ≥ strategic_threshold.  Ties broken by utility.
    """
    first_choice = sincere_ranking[0] if sincere_ranking else ""
    if polls.get(first_choice, 0) >= strategic_threshold:
        return sincere_ranking  # already competitive — stay sincere

    viable = [n for n in sincere_ranking if polls.get(n, 0) >= strategic_threshold]
    if not viable:
        return sincere_ranking  # no viable alternative — stay sincere

    # Best viable = highest utility among viable candidates
    best = max(viable, key=lambda n: utilities.get(n, 0.0))
    if best == first_choice:
        return sincere_ranking

    new_ranking = [best] + [n for n in sincere_ranking if n != best]
    return new_ranking


def _adaptive_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /adaptive — N rounds of adaptive/tactical voting."""
    num_voters          = max(50, min(1000, int(data.get("num_voters",          300))))
    ideology            = str(data.get("ideology",            "random"))
    seed                = int(data.get("seed",                 42))
    num_rounds          = max(1,  min(10,  int(data.get("num_rounds",           5))))
    method              = str(data.get("method",              "plurality"))
    strategic_threshold = max(0.0, min(1.0, float(data.get("strategic_threshold", 0.15))))
    cand_specs          = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ])[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, true_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    # Each voter's sincere ranking (fixed for the whole simulation)
    sincere_rankings: Dict[Any, list[str]] = {}
    for v in voters:
        uid = v["id"]
        sincere_rankings[uid] = sorted(
            true_utilities[uid].keys(), key=lambda n: -true_utilities[uid][n]
        )

    # ── Round 0: sincere vote ─────────────────────────────────────────────
    rounds_out: list[Dict[str, Any]] = []
    polls: Dict[str, float] = {n: 1.0 / len(cand_names) for n in cand_names}
    previous_winner: Optional[str] = None
    converged       = False
    convergence_round: Optional[int] = None
    stable_count    = 0

    # Compute global sincere winner (used for drift comparison at the end)
    sincere_all_rankings = [sincere_rankings[v["id"]] for v in voters]
    sincere_final_winner = _compute_winner(sincere_all_rankings, true_utilities, method)

    # Voter snapshot for ideology overlay (max 200 points)
    snap_indices = list(range(min(200, len(voters))))

    for rnd in range(num_rounds):
        # Determine effective ranking for each voter this round
        effective_rankings: list[list[str]] = []
        n_strategic = 0

        for v in voters:
            uid       = v["id"]
            propensity: float = float(v.get("strategic_propensity", 0.2))
            roll: float = float(_random.random())
            if rnd > 0 and propensity > roll:
                tactical = _tactical_vote(
                    uid, sincere_rankings[uid], true_utilities[uid], polls, strategic_threshold
                )
                effective_rankings.append(tactical)
                if tactical[0] != sincere_rankings[uid][0]:
                    n_strategic += 1
            else:
                effective_rankings.append(sincere_rankings[uid])

        # Run the chosen method
        eff_utils: Dict[Any, Dict[str, float]] = {
            v["id"]: true_utilities[v["id"]] for v in voters
        }
        winner = _compute_winner(effective_rankings, eff_utils, method)

        # Vote shares from first-choice counts
        first_choice_counts: Counter[str] = Counter(
            r[0] for r in effective_rankings if r
        )
        total = len(voters) or 1
        vote_shares = {n: round(first_choice_counts.get(n, 0) / total, 4) for n in cand_names}

        # Sincere vote shares (always from round-0 sincere vote for reference)
        sincere_fc: Counter[str] = Counter(
            sincere_rankings[v["id"]][0] for v in voters
            if sincere_rankings[v["id"]]
        )
        sincere_shares = {n: round(sincere_fc.get(n, 0) / total, 4) for n in cand_names}

        # Voter snapshot (strategic change indicator)
        voter_snaps = []
        for i in snap_indices:
            v   = voters[i]
            uid = v["id"]
            eff = effective_rankings[i] if i < len(effective_rankings) else sincere_rankings[uid]
            sx  = round(2.0 * v["issue_positions"].get("economy",       0.5) - 1.0, 3)
            sy  = round(2.0 * v["issue_positions"].get("social_welfare", 0.5) - 1.0, 3)
            voter_snaps.append({
                "id":            uid,
                "x":             sx,
                "y":             sy,
                "sincere_vote":  sincere_rankings[uid][0] if sincere_rankings[uid] else "",
                "effective_vote": eff[0] if eff else "",
                "tactical":      eff[0] != sincere_rankings[uid][0] if eff else False,
            })

        rounds_out.append({
            "round":               rnd,
            "vote_shares":         vote_shares,
            "sincere_shares":      sincere_shares,
            "winner":              winner,
            "sincere_winner":      sincere_final_winner,
            "strategic_voters_pct": round(n_strategic / total, 4),
            "voter_snapshot":      voter_snaps,
        })

        # Update polls for next round
        polls = vote_shares

        # Convergence check: winner stable for 2 consecutive rounds
        if winner == previous_winner:
            stable_count += 1
            if stable_count >= 2 and not converged:
                converged = True
                convergence_round = rnd - 1
        else:
            stable_count = 0
        previous_winner = winner

    # ── Strategic drift ────────────────────────────────────────────────────
    # Ideological distance between sincere winner and final winner
    def _ideology_pos(name: str) -> float:
        c = next((c for c in candidates if c["name"] == name), None)
        return round(2.0 * c["ideology_position"] - 1.0, 3) if c else 0.0

    final_winner = rounds_out[-1]["winner"] if rounds_out else sincere_final_winner
    if sincere_final_winner and final_winner:
        strategic_drift = round(
            abs(_ideology_pos(final_winner) - _ideology_pos(sincere_final_winner)), 4
        )
    else:
        strategic_drift = 0.0

    return {
        "rounds":             rounds_out,
        "converged":          converged,
        "convergence_round":  convergence_round,
        "final_winner":       final_winner,
        "sincere_winner":     sincere_final_winner,
        "strategic_drift":    strategic_drift,
        "candidates":         [
            {"name": c["name"], "x": _ideology_pos(c["name"])}
            for c in candidates
        ],
    }, 200


# ── Historical replay ─────────────────────────────────────────────────────────

_REPLAY_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "france2002": {
        "name":       "France 2002 — 1er tour",
        "ideology":   "left_skewed",
        "num_voters": 400,
        "real_winner": "Chirac",
        "candidates": [
            {"name": "Chirac",  "x":  0.30, "y":  0.10},
            {"name": "Jospin",  "x": -0.30, "y": -0.10},
            {"name": "Le Pen",  "x":  0.85, "y":  0.20},
            {"name": "Bayrou",  "x":  0.05, "y":  0.00},
        ],
    },
    "usa1992": {
        "name":       "USA 1992",
        "ideology":   "centrist",
        "num_voters": 400,
        "real_winner": "Clinton",
        "candidates": [
            {"name": "Clinton", "x": -0.20, "y":  0.00},
            {"name": "Bush",    "x":  0.30, "y":  0.10},
            {"name": "Perot",   "x":  0.00, "y": -0.10},
        ],
    },
    "germany2021": {
        "name":       "Allemagne 2021",
        "ideology":   "centrist",
        "num_voters": 400,
        "real_winner": "Scholz (SPD)",
        "candidates": [
            {"name": "Scholz (SPD)",     "x": -0.20, "y": -0.10},
            {"name": "Laschet (CDU)",    "x":  0.20, "y":  0.00},
            {"name": "Baerbock (Verts)", "x": -0.45, "y":  0.35},
            {"name": "Lindner (FDP)",    "x":  0.40, "y": -0.15},
            {"name": "Weidel (AfD)",     "x":  0.75, "y":  0.10},
        ],
    },
    "condorcet_cycle": {
        "name":       "Cycle de Condorcet",
        "ideology":   "polarized",
        "num_voters": 300,
        "real_winner": "—",
        "candidates": [
            {"name": "Alice", "x":  0.00, "y":  0.55},
            {"name": "Bob",   "x": -0.55, "y": -0.30},
            {"name": "Carol", "x":  0.55, "y": -0.30},
        ],
    },
}


def _historical_replay_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /historical-replay — extracted for FastAPI v2."""
    scenario_id = str(data.get("scenario_id", "france2002"))
    overrides   = data.get("overrides") or []
    num_days    = max(1, min(60, int(data.get("num_days", 30))))
    seed        = int(data.get("seed", 42))

    cfg = _REPLAY_SCENARIOS.get(scenario_id)
    if not cfg:
        return {"error": f"Unknown scenario: {scenario_id}"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    # Apply user overrides to candidate positions
    override_map: Dict[str, Dict[str, float]] = {
        o["name"]: {"x": float(o["x"]), "y": float(o["y"])}
        for o in overrides if "name" in o
    }
    cand_specs: list[Dict[str, Any]] = [
        {**c, **override_map[c["name"]]} if c["name"] in override_map else c
        for c in cfg["candidates"]
    ]

    candidates, voters, base_utilities, cand_names = _build_base_electorate(
        cand_specs, int(cfg["num_voters"]), str(cfg["ideology"]), seed, issues
    )

    # ── Day-by-day Brownian campaign simulation ────────────────────────────
    sigma = 0.018
    current_u: Dict[Any, Dict[str, float]] = {
        v["id"]: dict(base_utilities[v["id"]]) for v in voters
    }
    n_cands   = len(cand_names)
    days_out: list[Dict[str, Any]] = []

    for day in range(num_days + 1):
        if day > 0:
            shocks = {n: float(_np.random.normal(0, sigma)) for n in cand_names}
            for v in voters:
                uid = v["id"]
                for n in cand_names:
                    current_u[uid][n] = float(
                        max(0.01, min(0.99, current_u[uid][n] + shocks[n]))
                    )

        # First-choice vote shares
        fc: Counter[str] = Counter()
        for v in voters:
            uid  = v["id"]
            best = max(current_u[uid], key=lambda k: current_u[uid][k])
            fc[best] += 1
        total      = len(voters) or 1
        vote_shares = {n: round(fc.get(n, 0) / total, 4) for n in cand_names}

        # Rankings for Condorcet / Borda
        rankings: list[list[str]] = []
        for v in voters:
            uid = v["id"]
            rankings.append(
                sorted(current_u[uid].keys(), key=lambda k: -current_u[uid][k])
            )

        condorcet_w  = get_condorcet_winner(rankings)
        winner_fptp  = max(vote_shares, key=lambda k: vote_shares[k])
        borda_scores: Dict[str, float] = {n: 0.0 for n in cand_names}
        for r in rankings:
            for i, name in enumerate(r):
                borda_scores[name] += n_cands - 1 - i
        winner_borda = max(borda_scores, key=lambda k: borda_scores[k])

        days_out.append({
            "day":              day,
            "vote_shares":      vote_shares,
            "winner_fptp":      winner_fptp,
            "winner_condorcet": condorcet_w,
            "winner_borda":     winner_borda,
        })

    final_day   = days_out[-1]
    real_winner = str(cfg["real_winner"])
    differs     = final_day["winner_fptp"] != real_winner

    if differs and override_map:
        moved   = ", ".join(override_map.keys())
        note_fr = (f"En déplaçant {moved}, le vainqueur FPTP devient "
                   f"{final_day['winner_fptp']} au lieu de {real_winner}. "
                   "Le repositionnement idéologique a suffi à réécrire l'histoire.")
        note_en = (f"By moving {moved}, the FPTP winner becomes "
                   f"{final_day['winner_fptp']} instead of {real_winner}. "
                   "The ideological shift was enough to rewrite history.")
    elif differs:
        note_fr = (f"La simulation donne {final_day['winner_fptp']} "
                   f"(contre {real_winner} historiquement).")
        note_en = (f"The simulation gives {final_day['winner_fptp']} "
                   f"(vs {real_winner} historically).")
    else:
        note_fr = (f"La simulation converge vers {real_winner}, comme dans l'histoire réelle. "
                   "Déplacez un candidat pour explorer des scénarios alternatifs.")
        note_en = (f"The simulation converges on {real_winner}, matching historical reality. "
                   "Move a candidate to explore alternative scenarios.")

    return {
        "scenario": {"id": scenario_id, "name": cfg["name"], "real_winner": real_winner},
        "candidates": [
            {"name": c["name"], "x": float(c["x"]), "y": float(c["y"]),
             "modified": c["name"] in override_map}
            for c in cand_specs
        ],
        "days":  days_out,
        "final": {
            "winner_fptp":         final_day["winner_fptp"],
            "winner_condorcet":    final_day["winner_condorcet"],
            "winner_borda":        final_day["winner_borda"],
            "differs_from_real":   differs,
            "pedagogical_note":    note_fr,
            "pedagogical_note_en": note_en,
        },
    }, 200


# ── Jury theorem endpoint ─────────────────────────────────────────────────────

def _jury_theoretical(n: int, p: float) -> float:
    """
    Condorcet jury theorem: probability that majority is correct.
    P = Σ C(n,k) p^k (1-p)^(n-k)  for k = ceil((n+1)/2) … n
    """
    threshold = n // 2 + 1
    acc = 0.0
    q   = 1.0 - p
    for k in range(threshold, n + 1):
        acc += math.comb(n, k) * (p ** k) * (q ** (n - k))
    return min(1.0, acc)


def _generate_jury_ballots(
    num_voters: int,
    options: List[str],
    correct_idx: int,
    competence: float,
    rng: _random.Random,
) -> List[List[str]]:
    """
    Each voter independently ranks options.
    With probability `competence` they rank the correct option first;
    with probability 1-competence they rank a random wrong option first.
    The remainder of the ranking is shuffled uniformly.
    """
    correct = options[correct_idx]
    wrong   = [o for o in options if o != correct]
    ballots: List[List[str]] = []

    for _ in range(num_voters):
        rest = list(options)
        if rng.random() < competence:
            first = correct
        else:
            first = rng.choice(wrong)
        rest.remove(first)
        rng.shuffle(rest)
        ballots.append([first] + rest)

    return ballots


def _jury_approval_winner(
    ballots: List[List[str]],
    num_options: int,
) -> Optional[str]:
    """Approval: each voter approves top ceil(num_options/2) of their ranking."""
    top_k = max(1, (num_options + 1) // 2)
    counts: Counter[str] = Counter()
    for b in ballots:
        for opt in b[:top_k]:
            counts[opt] += 1
    return counts.most_common(1)[0][0] if counts else None


_JURY_METHODS = ["plurality", "borda", "irv", "approval", "schulze"]


def _run_jury_simulation(
    num_voters:   int,
    options:      List[str],
    correct_idx:  int,
    competence:   float,
    num_sims:     int,
    rng:          _random.Random,
) -> Dict[str, float]:
    """
    Run num_sims Monte Carlo trials.
    Returns {method: accuracy_fraction}.
    """
    correct   = options[correct_idx]
    successes: Dict[str, int] = {m: 0 for m in _JURY_METHODS}

    for _ in range(num_sims):
        ballots = _generate_jury_ballots(num_voters, options, correct_idx, competence, rng)

        winners = {
            "plurality": get_plurality_winner(ballots),
            "borda":     get_borda_winner(ballots),
            "irv":       get_irv_winner(ballots),
            "approval":  _jury_approval_winner(ballots, len(options)),
            "schulze":   get_schulze_winner(ballots),
        }

        for m, w in winners.items():
            if w == correct:
                successes[m] += 1

    return {m: round(successes[m] / num_sims, 4) for m in _JURY_METHODS}


def _jury_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /jury — extracted for FastAPI v2 reuse."""
    num_voters        = max(10, min(500, int(data.get("num_voters",        100))))
    num_options       = max(2,  min(5,   int(data.get("num_options",         2))))
    correct_idx       = max(0,  min(num_options - 1,
                                    int(data.get("correct_option_index",    0))))
    voter_competence  = max(0.50, min(1.0, float(data.get("voter_competence",  0.70))))
    num_simulations   = max(50,  min(500,  int(data.get("num_simulations",   200))))
    seed              = int(data.get("seed", 42))

    options = [f"Option {i}" for i in range(num_options)]
    rng     = _random.Random(seed)

    # ── Main simulation ───────────────────────────────────────────────────
    accuracies = _run_jury_simulation(
        num_voters, options, correct_idx, voter_competence, num_simulations, rng
    )

    theoretical = _jury_theoretical(num_voters, voter_competence)
    majority_acc = accuracies.get("plurality", 0.0)

    methods_out: Dict[str, Any] = {}
    for m, acc in accuracies.items():
        methods_out[m] = {
            "accuracy":       acc,
            "beats_majority": acc > majority_acc or m == "plurality",
            "beats_theory":   acc > theoretical,
        }

    best_method  = max(accuracies, key=lambda k: accuracies[k])
    worst_method = min(accuracies, key=lambda k: accuracies[k])

    # ── Competence curve (20 points, 100 sims each for speed) ────────────
    curve_rng = _random.Random(seed + 1)
    curve_sims = max(50, min(150, num_simulations // 2))
    curve_points: List[Dict[str, Any]] = []
    for step in range(20):
        p = 0.51 + step * (0.48 / 19)   # 0.51 → 0.99
        pt_acc = _run_jury_simulation(
            num_voters, options, correct_idx, round(p, 3), curve_sims, curve_rng
        )
        point: Dict[str, Any] = {
            "competence": round(p, 3),
            "theoretical": round(_jury_theoretical(num_voters, p), 4),
        }
        point.update({m: pt_acc[m] for m in _JURY_METHODS})
        curve_points.append(point)

    # ── Pedagogical note ──────────────────────────────────────────────────
    pct_theory = round(theoretical * 100, 1)
    pct_best   = round(accuracies[best_method] * 100, 1)
    delta      = round((accuracies[best_method] - theoretical) * 100, 1)
    if delta > 0:
        note_fr = (
            f"Avec P={voter_competence} et {num_voters} électeurs, "
            f"la théorie prédit {pct_theory}%. "
            f"{best_method.capitalize()} atteint {pct_best}% "
            f"(+{delta}% vs théorie) — il agrège mieux l'information collective "
            f"que la simple majorité."
        )
        note_en = (
            f"With P={voter_competence} and {num_voters} voters, "
            f"theory predicts {pct_theory}%. "
            f"{best_method.capitalize()} reaches {pct_best}% "
            f"(+{delta}% vs theory) — it aggregates collective information "
            f"better than simple majority."
        )
    else:
        note_fr = (
            f"Avec P={voter_competence} et {num_voters} électeurs, "
            f"la théorie prédit {pct_theory}%. "
            f"Aucune méthode ne dépasse la prédiction théorique — "
            f"la majorité reste la meilleure agrégation dans ce scénario."
        )
        note_en = (
            f"With P={voter_competence} and {num_voters} voters, "
            f"theory predicts {pct_theory}%. "
            f"No method exceeds the theoretical prediction — "
            f"majority rule is the best aggregation in this scenario."
        )

    return {
        "theoretical_accuracy": round(theoretical, 4),
        "methods":              methods_out,
        "best_method":          best_method,
        "worst_method":         worst_method,
        "voter_competence":     voter_competence,
        "num_voters":           num_voters,
        "competence_curve":     curve_points,
        "pedagogical_note":     note_fr,
        "pedagogical_note_en":  note_en,
    }, 200


# ── Differential abstention endpoint ─────────────────────────────────────────

def _sigmoid(x: float) -> float:
    """Numerically stable sigmoid."""
    return 1.0 / (1.0 + float(_np.exp(-min(max(x, -30.0), 30.0))))


def _abstention_prob(
    poll_gap:             float,
    utility_gap:          float,
    demobilization_factor: float,
    poll_influence:        float,
) -> float:
    """
    P(abstention) for one voter in one round.

    Scales to 0 when demobilization_factor=0 (guaranteed no abstention).
    Uses a sigmoid of the combined demobilization signal, multiplied by
    demobilization_factor and poll_influence as outer scale factors.

    poll_gap    = fraction of voters NOT preferring the same candidate as v
                  (high → v's candidate is trailing in the polls)
    utility_gap = 1 - max_utility of v (high → v is indifferent to outcome)
    """
    if demobilization_factor <= 0.0:
        return 0.0
    # Inner signal: shifts sigmoid so neutral inputs give ~0.2 probability
    signal = poll_gap * 3.0 + utility_gap * 1.5 - 1.0
    p = demobilization_factor * _sigmoid(signal) * poll_influence
    return max(0.0, min(1.0, p))


def _abstention_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /abstention — extracted for FastAPI v2 reuse."""

    num_voters             = max(50,  min(1000, int(data.get("num_voters", 300))))
    ideology               = str(data.get("ideology", "random"))
    seed                   = int(data.get("seed", 42))
    demobilization_factor  = max(0.0, min(1.0, float(data.get("demobilization_factor", 0.5))))
    poll_influence         = max(0.0, min(1.0, float(data.get("poll_influence", 0.8))))
    num_rounds             = max(1, min(5, int(data.get("num_rounds", 3))))
    cand_specs             = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ])[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, true_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    # Voter positions for the abstention_map (SVG ideology overlay)
    voter_positions: list[Dict[str, Any]] = [
        {
            "id": v["id"],
            "x":  round(2.0 * v["issue_positions"].get("economy", 0.5) - 1.0, 3),
            "y":  round(2.0 * v["issue_positions"].get("social_welfare", 0.5) - 1.0, 3),
        }
        for v in voters
    ]

    # Each voter's preferred candidate (highest true utility)
    voter_preferred: Dict[Any, str] = {
        v["id"]: max(true_utilities[v["id"]], key=lambda k: true_utilities[v["id"]][k])
        for v in voters
    }

    # Round 0: sincere vote (no polls → no abstention)
    sincere_fc: Counter[str] = Counter(voter_preferred.values())
    total_sincere = len(voters) or 1
    polls: Dict[str, float] = {n: sincere_fc.get(n, 0) / total_sincere for n in cand_names}

    def _run_round_fptp(active_voters: list[Dict[str, Any]]) -> str:
        fc: Counter[str] = Counter(voter_preferred[v["id"]] for v in active_voters)
        return max(fc, key=lambda k: fc[k]) if fc else cand_names[0]

    def _run_round_condorcet(active_voters: list[Dict[str, Any]]) -> Optional[str]:
        rankings = [
            sorted(true_utilities[v["id"]].keys(), key=lambda k: -true_utilities[v["id"]][k])
            for v in active_voters
        ]
        return get_condorcet_winner(rankings)

    sincere_winner = _run_round_fptp(voters)

    rounds_out: list[Dict[str, Any]] = []

    for rnd in range(num_rounds + 1):
        if rnd == 0:
            # Sincere round — everyone votes
            active   = voters
            abs_probs = {v["id"]: 0.0 for v in voters}
            abstained = set[Any]()
        else:
            # Determine P(abstention) for each voter from last-round polls
            abs_probs = {}
            abstained = set()
            for v in voters:
                uid      = v["id"]
                pref     = voter_preferred[uid]
                poll_gap = max(0.0, 1.0 - polls.get(pref, 0.0))
                max_util = max(true_utilities[uid].values(), default=0.5)
                util_gap = max(0.0, 1.0 - max_util)
                p        = _abstention_prob(poll_gap, util_gap,
                                             demobilization_factor, poll_influence)
                abs_probs[uid] = round(p, 4)
                if _random.random() < p:
                    abstained.add(uid)
            active = [v for v in voters if v["id"] not in abstained]

        # Vote shares among active voters
        fc: Counter[str] = Counter()
        for v in active:
            fc[voter_preferred[v["id"]]] += 1
        total_active = len(active) or 1
        vote_shares = {n: round(fc.get(n, 0) / total_active, 4) for n in cand_names}

        winner_fptp      = _run_round_fptp(active)
        winner_condorcet = _run_round_condorcet(active)

        # Build abstention_map (max 300 voters for performance)
        snap_indices = list(range(min(300, len(voters))))
        abs_map = [
            {
                **voter_positions[i],
                "preferred":        voter_preferred[voters[i]["id"]],
                "abstained":        voters[i]["id"] in abstained,
                "prob_abstention":  abs_probs.get(voters[i]["id"], 0.0),
            }
            for i in snap_indices
        ]

        rounds_out.append({
            "round":          rnd,
            "turnout":        round(len(active) / (len(voters) or 1), 4),
            "vote_shares":    vote_shares,
            "winner_fptp":    winner_fptp,
            "winner_condorcet": winner_condorcet,
            "abstention_map": abs_map,
        })

        # Update polls for next round
        polls = vote_shares

    final_winner   = rounds_out[-1]["winner_fptp"]
    winner_changed = final_winner != sincere_winner

    # Turnout by camp (average participation rate per preferred candidate)
    camp_votes:  Dict[str, int] = {n: 0 for n in cand_names}
    camp_total:  Dict[str, int] = {n: 0 for n in cand_names}
    last_abs_map = rounds_out[-1]["abstention_map"]
    for p in last_abs_map:
        pref = p["preferred"]
        camp_total[pref] = camp_total.get(pref, 0) + 1
        if not p["abstained"]:
            camp_votes[pref] = camp_votes.get(pref, 0) + 1
    turnout_by_camp = {
        n: round(camp_votes.get(n, 0) / max(camp_total.get(n, 1), 1), 4)
        for n in cand_names
    }

    # ── Per-method winners (with and without abstention) ──────────────────
    # Enables the LabCentralView pinned matrix to show how abstention
    # affects every voting method, not just plurality.
    try:
        sincere_compare = compare_all_methods(voters, candidates, issues)
        final_compare   = compare_all_methods(active, candidates, issues)
        sincere_winners_by_method = {
            m: data.get("winner")
            for m, data in sincere_compare.get("methods", {}).items()
        }
        winners_by_method = {
            m: data.get("winner")
            for m, data in final_compare.get("methods", {}).items()
        }
    except Exception:  # pylint: disable=broad-except
        sincere_winners_by_method = {}
        winners_by_method = {}

    return {
        "rounds":          rounds_out,
        "sincere_winner":  sincere_winner,
        "final_winner":    final_winner,
        "winner_changed":  winner_changed,
        "turnout_by_camp": turnout_by_camp,
        "candidates":      [{"name": c["name"]} for c in candidates],
        "sincere_winners_by_method": sincere_winners_by_method,
        "winners_by_method":         winners_by_method,
    }, 200


# ── STV endpoint ──────────────────────────────────────────────────────────────

def _stv_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /stv — extracted for FastAPI v2."""
    num_voters = max(50,  min(1000, int(data.get("num_voters",  300))))
    ideology   = str(data.get("ideology",  "random"))
    seed       = int(data.get("seed",        42))
    num_seats  = max(2,  min(10,  int(data.get("num_seats",     5))))
    quota_type = str(data.get("quota_type", "droop"))
    cand_specs = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
        {"name": "Dave",  "x": -0.2, "y":  0.5},
    ])[:8]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400
    if num_seats >= len(cand_specs):
        return {"error": "num_seats must be less than number of candidates"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, true_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    # Build full ranked ballots (sincere, by utility)
    rankings: list[list[str]] = []
    for v in voters:
        uid = v["id"]
        rankings.append(
            sorted(true_utilities[uid].keys(), key=lambda k: -true_utilities[uid][k])
        )

    # ── STV ────────────────────────────────────────────────────────────────
    stv_raw = get_stv_result(rankings, num_seats, quota_type)

    # ── D'Hondt (from first-choice vote shares) ───────────────────────────
    first_choice: Counter[str] = Counter(r[0] for r in rankings if r)
    total = len(rankings) or 1
    vote_shares = {n: first_choice.get(n, 0) / total for n in cand_names}
    dhondt_seats = get_dhondt_winners(vote_shares, num_seats)

    # ── FPTP multi-seat (top-N by first-choice votes) ─────────────────────
    top_n    = sorted(cand_names, key=lambda c: -first_choice.get(c, 0))[:num_seats]
    fptp_seats: Dict[str, int] = {c: (1 if c in top_n else 0) for c in cand_names}

    # ── Distortion metrics ────────────────────────────────────────────────
    stv_seat_dict: Dict[str, int] = {c: (1 if c in stv_raw["elected"] else 0) for c in cand_names}

    def _seat_distortion(a: Dict[str, int], b: Dict[str, int]) -> float:
        return sum(abs(a.get(c, 0) - b.get(c, 0)) for c in cand_names) / 2

    return {
        "stv": {
            "elected":  stv_raw["elected"],
            "quota":    stv_raw["quota"],
            "rounds":   stv_raw["rounds"],
            "seats":    stv_seat_dict,
        },
        "dhondt": {
            "seats":    dhondt_seats,
            "elected":  [c for c, s in sorted(dhondt_seats.items(), key=lambda kv: -kv[1]) if s > 0],
        },
        "fptp": {
            "seats":    fptp_seats,
            "elected":  top_n,
        },
        "vote_shares":           {n: round(vote_shares[n], 4) for n in cand_names},
        "num_seats":             num_seats,
        "quota":                 stv_raw["quota"],
        "quota_type":            quota_type,
        "distortion_stv_dhondt": round(_seat_distortion(stv_seat_dict, dhondt_seats), 3),
        "distortion_stv_fptp":   round(_seat_distortion(stv_seat_dict, fptp_seats), 3),
        "candidates":            cand_names,
    }, 200


# ── Gerrymandering endpoint ───────────────────────────────────────────────────

def _closest_district(
    vx: float, vy: float,
    districts: List[Dict[str, Any]],
) -> int:
    """Return the id of the district whose centroid is closest to (vx, vy)."""
    best_id: int = int(districts[0]["id"])
    best_dist = float("inf")
    for d in districts:
        b   = d["bounds"]
        cx  = (b["x_min"] + b["x_max"]) / 2
        cy  = (b["y_min"] + b["y_max"]) / 2
        dist = (vx - cx) ** 2 + (vy - cy) ** 2
        if dist < best_dist:
            best_dist = dist
            best_id   = int(d["id"])
    return best_id


def _gerrymander_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /gerrymander — extracted for FastAPI v2."""
    num_voters = max(50,  min(1000, int(data.get("num_voters",  300))))
    ideology   = str(data.get("ideology",  "random"))
    seed       = int(data.get("seed",        42))
    cand_specs = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
    ])[:6]
    districts_raw: List[Dict[str, Any]] = data.get("districts") or []

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400
    if not districts_raw:
        return {"error": "At least 1 district required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, true_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    # Map each voter's 2-D position
    voter_positions: Dict[Any, tuple[float, float]] = {
        v["id"]: (
            round(2.0 * v["issue_positions"].get("economy", 0.5) - 1.0, 3),
            round(2.0 * v["issue_positions"].get("social_welfare", 0.5) - 1.0, 3),
        )
        for v in voters
    }

    # Each voter's preferred candidate (highest true utility)
    voter_preferred: Dict[Any, str] = {
        v["id"]: max(true_utilities[v["id"]], key=lambda k: true_utilities[v["id"]][k])
        for v in voters
    }

    # ── Assign voters to districts ────────────────────────────────────────
    # district_id → list of voter ids
    district_members: Dict[int, List[Any]] = {d["id"]: [] for d in districts_raw}
    unassigned: List[Any] = []

    for v in voters:
        uid = v["id"]
        vx, vy = voter_positions[uid]
        matched = [
            d for d in districts_raw
            if d["bounds"]["x_min"] <= vx <= d["bounds"]["x_max"]
            and d["bounds"]["y_min"] <= vy <= d["bounds"]["y_max"]
        ]
        if len(matched) == 1:
            district_members[matched[0]["id"]].append(uid)
        elif len(matched) > 1:
            # Multiple districts overlap — pick the smallest area
            def _area(d: Dict[str, Any]) -> float:
                b = d["bounds"]
                return float(b["x_max"] - b["x_min"]) * float(b["y_max"] - b["y_min"])
            best = min(matched, key=_area)
            district_members[best["id"]].append(uid)
        else:
            unassigned.append(uid)

    # Assign unmatched voters to nearest district
    for uid in unassigned:
        vx, vy = voter_positions[uid]
        nearest = _closest_district(vx, vy, districts_raw)
        district_members[nearest].append(uid)

    # ── Per-district FPTP ─────────────────────────────────────────────────
    district_results: List[Dict[str, Any]] = []
    parliament_gerry: Dict[str, int] = {n: 0 for n in cand_names}

    national_fc:    Counter[str] = Counter()
    national_total: int          = 0

    for d in districts_raw:
        members = district_members[d["id"]]
        if not members:
            district_results.append({
                "id": d["id"], "num_voters": 0,
                "winner": None, "vote_shares": {},
            })
            continue

        fc: Counter[str] = Counter(voter_preferred[uid] for uid in members)
        total = len(members)
        vote_shares = {n: round(fc.get(n, 0) / total, 4) for n in cand_names}
        winner = max(fc, key=lambda k: fc[k])

        district_results.append({
            "id":          d["id"],
            "num_voters":  total,
            "winner":      winner,
            "vote_shares": vote_shares,
        })
        parliament_gerry[winner] = parliament_gerry.get(winner, 0) + 1
        national_fc    += fc
        national_total += total

    # ── National D'Hondt ──────────────────────────────────────────────────
    national_shares: Dict[str, float] = {
        n: round(national_fc.get(n, 0) / max(national_total, 1), 4)
        for n in cand_names
    }
    num_total_seats = len(districts_raw)
    parliament_prop  = _dhondt(national_shares, num_total_seats)

    # ── Distortion & gerrymander index ────────────────────────────────────
    distortion_vals = [
        abs(parliament_gerry.get(n, 0) / num_total_seats - national_shares.get(n, 0))
        for n in cand_names
    ]
    distortion = round(sum(distortion_vals) / max(len(distortion_vals), 1), 4)

    # Gerrymander index: how far from proportional is the leading party?
    leading         = max(parliament_gerry, key=lambda k: parliament_gerry[k])
    gerry_seat_pct  = parliament_gerry.get(leading, 0) / max(num_total_seats, 1)
    gerry_vote_pct  = national_shares.get(leading, 0)
    # Normalise to [0, 1]: 0 = seat% == vote%, 1 = seat% >> vote%
    gerrymander_index = round(
        max(0.0, min(1.0, (gerry_seat_pct - gerry_vote_pct) / max(gerry_vote_pct, 0.01))),
        4,
    )

    # Voter snapshot for the map (capped at 500 for performance)
    snap_voters = [
        {
            "id":        v["id"],
            "x":         voter_positions[v["id"]][0],
            "y":         voter_positions[v["id"]][1],
            "preferred": voter_preferred[v["id"]],
        }
        for v in voters[:500]
    ]

    return {
        "districts":              district_results,
        "voters":                 snap_voters,
        "parliament_gerrymander": parliament_gerry,
        "parliament_proportional": parliament_prop,
        "national_vote_share":    national_shares,
        "distortion":             distortion,
        "gerrymander_index":      gerrymander_index,
        "winner":                 leading,
        "candidates":             cand_names,
        "num_seats":              num_total_seats,
    }, 200


# ── Multi-winner compare endpoint ─────────────────────────────────────────────

def _multiwinner_compare_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /multiwinner_compare — STV, D'Hondt, SPAV, Phragmén, FPTP."""
    num_voters = max(50,  min(500, int(data.get("num_voters",  200))))
    ideology   = str(data.get("ideology",  "random"))
    seed       = int(data.get("seed",        42))
    num_seats  = max(2,  min(10,  int(data.get("num_seats",    5))))
    cand_specs = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
        {"name": "Dave",  "x": -0.2, "y":  0.5},
    ])[:8]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400
    if num_seats >= len(cand_specs):
        return {"error": "num_seats must be less than number of candidates"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, true_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    # ── Build ballots ──────────────────────────────────────────────────────
    # Full rankings for STV
    rankings: List[List[str]] = []
    for v in voters:
        uid = v["id"]
        rankings.append(
            sorted(true_utilities[uid].keys(), key=lambda k: -true_utilities[uid][k])
        )

    # Approval ballots: approve candidates above own mean utility
    approval_ballots: List[List[str]] = []
    for v in voters:
        uid        = v["id"]
        u          = true_utilities[uid]
        threshold  = sum(u.values()) / max(len(u), 1)
        approved   = [c for c in cand_names if u.get(c, 0) > threshold]
        if not approved:                          # always approve at least 1st choice
            approved = [max(u, key=lambda k: u[k])]
        approval_ballots.append(approved)

    # First-choice vote shares for D'Hondt / FPTP
    first_choice: Counter[str] = Counter(r[0] for r in rankings if r)
    total_voters  = len(voters) or 1
    vote_shares   = {n: first_choice.get(n, 0) / total_voters for n in cand_names}

    # ── Run all methods ────────────────────────────────────────────────────
    stv_raw    = get_stv_result(rankings, num_seats, "droop")
    dhondt_raw = get_dhondt_winners(vote_shares, num_seats)
    spav_raw   = get_spav_result(approval_ballots, num_seats)
    phrag_raw  = get_phragmen_result(approval_ballots, num_seats)
    top_n      = sorted(cand_names, key=lambda c: -first_choice.get(c, 0))[:num_seats]

    def _to_seat_dict(elected: List[str]) -> Dict[str, int]:
        d: Dict[str, int] = {c: 0 for c in cand_names}
        for c in elected:
            d[c] = d.get(c, 0) + 1
        return d

    methods: Dict[str, Dict[str, Any]] = {
        "stv":     {"seats": _to_seat_dict(stv_raw["elected"]),    "elected": stv_raw["elected"]},
        "dhondt":  {"seats": dhondt_raw,                           "elected": [c for c, s in sorted(dhondt_raw.items(), key=lambda kv: -kv[1]) if s > 0]},
        "spav":    {"seats": _to_seat_dict(spav_raw["elected"]),   "elected": spav_raw["elected"]},
        "phragmen":{"seats": _to_seat_dict(phrag_raw["elected"]),  "elected": phrag_raw["elected"]},
        "fptp":    {"seats": _to_seat_dict(top_n),                 "elected": top_n},
    }

    # ── Distortion metrics ─────────────────────────────────────────────────
    prop_seats = _dhondt(vote_shares, num_seats)   # proportional reference

    for method_name, mdata in methods.items():
        seat_dict = mdata["seats"]
        dist_vals = [
            abs(seat_dict.get(c, 0) / num_seats - vote_shares.get(c, 0))
            for c in cand_names
        ]
        mdata["distortion"]          = round(sum(dist_vals) / max(len(dist_vals), 1), 4)
        mdata["seat_vs_votes"]       = {
            c: {
                "seats":     seat_dict.get(c, 0),
                "seat_pct":  round(seat_dict.get(c, 0) / num_seats, 4),
                "vote_pct":  round(vote_shares.get(c, 0), 4),
                "delta":     round(seat_dict.get(c, 0) / num_seats - vote_shares.get(c, 0), 4),
            }
            for c in cand_names
        }

    best_method  = min(methods, key=lambda m: methods[m]["distortion"])
    worst_method = max(methods, key=lambda m: methods[m]["distortion"])

    return {
        "methods":      methods,
        "vote_shares":  {n: round(vote_shares[n], 4) for n in cand_names},
        "proportional_reference": prop_seats,
        "num_seats":    num_seats,
        "candidates":   cand_names,
        "best_method":  best_method,
        "worst_method": worst_method,
    }, 200


# ── Hotelling-Downs equilibrium ────────────────────────────────────────────────

def _hotelling_utility(
    voters_xy: _np.ndarray,      # shape (N, 2)
    cand_xy:   _np.ndarray,      # shape (C, 2)
) -> _np.ndarray:
    """
    Proximity-based utility matrix U[i, j] for voter i and candidate j.
    U = 1 - 0.5 * euclidean_distance / sqrt(2)  → ∈ [~0.3, 1.0]
    """
    diff = voters_xy[:, None, :] - cand_xy[None, :, :]   # (N, C, 2)
    dist = _np.sqrt((diff ** 2).sum(axis=2))              # (N, C)
    result: _np.ndarray = 1.0 - 0.5 * dist / _np.sqrt(2)
    return result


def _hotelling_score(
    utilities: _np.ndarray,   # (N, C) — utility matrix
    method:    str,
    cand_idx:  int,
) -> float:
    """
    Score for candidate cand_idx under the given method.
    Returns a continuous value in [0, 1] suitable for gradient ascent.
    """
    N, C = utilities.shape
    if N == 0 or C == 0:
        return 0.0

    score: float
    if method in ("plurality", "irv"):
        winners = utilities.argmax(axis=1)
        score = int((winners == cand_idx).sum()) / N

    elif method == "borda":
        ranks  = _np.argsort(-utilities, axis=1)
        points = _np.zeros((N, C))
        for k in range(C):
            points[_np.arange(N), ranks[:, k]] = C - 1 - k
        total_possible = N * (C - 1)
        score = int(points[:, cand_idx].sum()) / max(total_possible, 1)

    elif method == "approval":
        means    = utilities.mean(axis=1, keepdims=True)
        approved = utilities > means
        score = int(approved[:, cand_idx].sum()) / N

    else:
        winners = utilities.argmax(axis=1)
        score = int((winners == cand_idx).sum()) / N

    return score


def _hotelling_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /hotelling — extracted for FastAPI v2 reuse."""
    num_voters     = max(50,  min(500, int(data.get("num_voters",   200))))
    ideology       = str(data.get("ideology",   "random"))
    seed           = int(data.get("seed",         42))
    method         = str(data.get("method",     "plurality"))
    num_iterations = max(1,  min(20,  int(data.get("num_iterations", 10))))
    step_size      = max(0.01, min(0.15, float(data.get("step_size",   0.05))))
    cand_specs     = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ])[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    # ── Build fixed electorate ─────────────────────────────────────────────
    candidates, voters, _, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    # Voter 2-D positions (fixed throughout)
    voters_xy = _np.array([
        [
            2.0 * v["issue_positions"].get("economy", 0.5) - 1.0,
            2.0 * v["issue_positions"].get("social_welfare", 0.5) - 1.0,
        ]
        for v in voters
    ])  # (N, 2)

    # Initial candidate positions
    cand_xy = _np.array([
        [max(-1.0, min(1.0, float(s.get("x", 0.0)))),
         max(-1.0, min(1.0, float(s.get("y", 0.0))))]
        for s in cand_specs
    ])  # (C, 2)

    N = len(voters)
    C = len(cand_names)
    DIRS = _np.array([[step_size, 0], [-step_size, 0],
                      [0, step_size], [0, -step_size]])

    # ── Iterative Nash ─────────────────────────────────────────────────────
    iterations_out: list[Dict[str, Any]] = []
    converged_set: set[str] = set()

    for step in range(num_iterations):
        utilities = _hotelling_utility(voters_xy, cand_xy)

        scores: Dict[str, float] = {
            cand_names[j]: round(_hotelling_score(utilities, method, j), 4)
            for j in range(C)
        }

        # Record snapshot before moving
        iterations_out.append({
            "step":               step,
            "candidates":         [
                {"name": cand_names[j], "x": round(float(cand_xy[j, 0]), 4),
                 "y": round(float(cand_xy[j, 1]), 4)}
                for j in range(C)
            ],
            "scores":             scores,
            "converged_candidates": sorted(converged_set),
        })

        moved_any = False
        for j in range(C):
            if cand_names[j] in converged_set:
                continue

            current_score = _hotelling_score(utilities, method, j)
            best_score    = current_score
            best_delta    = _np.zeros(2)

            for delta in DIRS:
                new_pos = _np.clip(cand_xy[j] + delta, -1.0, 1.0)
                trial   = cand_xy.copy()
                trial[j] = new_pos
                trial_u  = _hotelling_utility(voters_xy, trial)
                s        = _hotelling_score(trial_u, method, j)
                if s > best_score + 1e-6:
                    best_score = s
                    best_delta = delta

            if _np.any(best_delta != 0):
                cand_xy[j] = _np.clip(cand_xy[j] + best_delta, -1.0, 1.0)
                moved_any = True
            else:
                converged_set.add(cand_names[j])

        if len(converged_set) == C:
            break

    # Final snapshot
    utilities = _hotelling_utility(voters_xy, cand_xy)
    final_scores = {
        cand_names[j]: round(_hotelling_score(utilities, method, j), 4)
        for j in range(C)
    }
    iterations_out.append({
        "step":               len(iterations_out),
        "candidates":         [
            {"name": cand_names[j], "x": round(float(cand_xy[j, 0]), 4),
             "y": round(float(cand_xy[j, 1]), 4)}
            for j in range(C)
        ],
        "scores":             final_scores,
        "converged_candidates": sorted(converged_set),
    })

    final_positions = iterations_out[-1]["candidates"]
    converged       = len(converged_set) == C
    convergence_step: Optional[int] = (
        next((i["step"] for i in iterations_out if len(i["converged_candidates"]) == C), None)
    )

    # Classify equilibrium type
    xs = [p["x"] for p in final_positions]
    spread = max(xs) - min(xs) if xs else 0
    if spread < 0.15:
        eq_type = "center_convergence"
    elif converged and spread >= 0.15:
        eq_type = "dispersed"
    else:
        eq_type = "unstable"

    # Voter snapshot (max 200 for performance)
    voter_snaps = [
        {
            "x": round(float(voters_xy[i, 0]), 3),
            "y": round(float(voters_xy[i, 1]), 3),
        }
        for i in range(min(200, N))
    ]

    return {
        "iterations":        iterations_out,
        "converged":         converged,
        "convergence_step":  convergence_step,
        "final_positions":   final_positions,
        "equilibrium_type":  eq_type,
        "voters":            voter_snaps,
        "candidates":        cand_names,
        "method":            method,
    }, 200


# ── Polarization endpoint ──────────────────────────────────────────────────────

def _esteban_ray_index(positions: List[float], n_bins: int = 20) -> float:
    """
    Esteban-Ray (1994) polarization index P = Σᵢ Σⱼ πᵢ² πⱼ |yᵢ - yⱼ|
    discretised into n_bins equal-width bins over [-1, 1].
    """
    if not positions:
        return 0.0

    bins     = _np.linspace(-1.0, 1.0, n_bins + 1)
    counts, _ = _np.histogram(positions, bins=bins)
    total    = counts.sum() or 1
    pi       = counts / total                          # bin proportions
    centres  = (bins[:-1] + bins[1:]) / 2.0           # bin centres

    p = 0.0
    for i in range(n_bins):
        if pi[i] == 0:
            continue
        for j in range(n_bins):
            if pi[j] == 0:
                continue
            p += float(pi[i] ** 2 * pi[j] * abs(centres[i] - centres[j]))
    return round(p, 6)


def _winner_entropy(winners: List[Optional[str]]) -> float:
    """Normalised Shannon entropy of winner distribution ∈ [0, 1]."""
    valid = [w for w in winners if w]
    if not valid:
        return 1.0
    counts = Counter(valid)
    total  = len(valid)
    probs  = [c / total for c in counts.values()]
    import math as _math
    entropy = -sum(p * _math.log2(p) for p in probs if p > 0)
    max_e   = _math.log2(len(counts)) if len(counts) > 1 else 1.0
    return round(entropy / max_e if max_e > 0 else 0.0, 4)


def _polarization_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /polarization — extracted for FastAPI v2 reuse."""
    num_voters     = max(50,  min(300, int(data.get("num_voters",   150))))
    seed           = int(data.get("seed", 42))
    num_simulations = max(5, min(50,  int(data.get("num_simulations", 20))))
    # Pydantic Optional[List[str]] may pass null — fall back to the default.
    ideology_range: List[str] = data.get("ideology_range") or [
        "centrist", "random", "left_skewed", "right_skewed", "polarized",
    ]
    cand_specs = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ])[:4]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    issues = DEFAULT_ISSUES
    results: List[Dict[str, Any]] = []

    for ideology in ideology_range:
        _random.seed(seed)
        _np.random.seed(seed)

        # ── Build reference electorate to compute polarization index ──────
        candidates, voters, true_utilities, cand_names = _build_base_electorate(
            cand_specs, num_voters, ideology, seed, issues
        )

        economy_positions: List[float] = [
            float(2.0 * v["issue_positions"].get("economy", 0.5) - 1.0)
            for v in voters
        ]
        pol_index = _esteban_ray_index(economy_positions)

        # ── Monte Carlo simulations ────────────────────────────────────────
        condorcet_count   = 0
        agreement_sum     = 0.0
        # Per-method: collect regrets and winner lists
        method_regrets:  Dict[str, List[float]] = {}
        method_winners:  Dict[str, List[Optional[str]]] = {}
        global_winners:  List[Optional[str]] = []

        for sim_idx in range(num_simulations):
            sim_seed = seed + sim_idx + 1
            _random.seed(sim_seed)
            _np.random.seed(sim_seed)

            _, sim_voters, sim_utils, _ = _build_base_electorate(
                cand_specs, num_voters, ideology, sim_seed, issues
            )

            mc_result = compare_all_methods(
                sim_voters, candidates, issues,
                blank_vote=False,
                override_utilities=sim_utils,
            )

            cw = mc_result.get("condorcet_winner")
            if cw:
                condorcet_count += 1

            methods_data: Dict[str, Any] = mc_result.get("methods", {})

            # Agreement: fraction of methods electing the most common winner
            winners_this = [
                md.get("winner") for md in methods_data.values() if md.get("winner")
            ]
            if winners_this:
                most_common_count = Counter(winners_this).most_common(1)[0][1]
                agreement_sum += most_common_count / len(winners_this)
                global_winners.append(Counter(winners_this).most_common(1)[0][0])
            else:
                global_winners.append(None)

            for method_name, md in methods_data.items():
                if method_name not in method_regrets:
                    method_regrets[method_name]  = []
                    method_winners[method_name]  = []
                r = md.get("bayesian_regret")
                if r is not None:
                    method_regrets[method_name].append(float(r))
                method_winners[method_name].append(md.get("winner"))

        condorcet_rate  = round(condorcet_count / num_simulations, 4)
        agreement_rate  = round(agreement_sum / num_simulations, 4)
        winner_stability = _winner_entropy(global_winners)

        # Best/worst method by average Bayesian Regret
        avg_regrets: Dict[str, float] = {
            m: round(sum(v) / len(v), 6)
            for m, v in method_regrets.items() if v
        }
        best_method  = min(avg_regrets, key=lambda k: avg_regrets[k]) if avg_regrets else ""
        worst_method = max(avg_regrets, key=lambda k: avg_regrets[k]) if avg_regrets else ""

        results.append({
            "ideology":          ideology,
            "polarization_index": pol_index,
            "condorcet_rate":    condorcet_rate,
            "agreement_rate":    agreement_rate,
            "winner_stability":  winner_stability,
            "best_method":       best_method,
            "worst_method":      worst_method,
            "method_regrets":    avg_regrets,
        })

    # ── Key findings ───────────────────────────────────────────────────────
    results_sorted = sorted(results, key=lambda r: r["polarization_index"])

    findings: List[str] = []

    # 1. Condorcet threshold
    low_cw = [r for r in results_sorted if r["condorcet_rate"] < 0.5]
    if low_cw:
        threshold = low_cw[0]["polarization_index"]
        pct       = round((1 - low_cw[0]["condorcet_rate"]) * 100)
        findings.append(
            f"À partir de P ≈ {threshold:.2f}, le vainqueur de Condorcet disparaît "
            f"dans {pct}% des simulations."
        )

    # 2. Most robust method under high polarization
    high_pol = [r for r in results_sorted if r["polarization_index"] > 0.2]
    if high_pol:
        all_best: Counter[str] = Counter(r["best_method"] for r in high_pol if r["best_method"])
        if all_best:
            robust = all_best.most_common(1)[0][0]
            # Compare to worst
            all_worst: Counter[str] = Counter(r["worst_method"] for r in high_pol if r["worst_method"])
            fragile = all_worst.most_common(1)[0][0] if all_worst else ""
            findings.append(
                f"{robust.capitalize()} est la méthode la plus robuste dans les "
                f"électorats polarisés — régret bayésien moyen inférieur à {fragile}."
            )

    # 3. Agreement drops
    if len(results_sorted) >= 2:
        first_agree = results_sorted[0]["agreement_rate"]
        last_agree  = results_sorted[-1]["agreement_rate"]
        if last_agree < first_agree - 0.1:
            delta = round((first_agree - last_agree) * 100, 1)
            findings.append(
                f"L'accord inter-méthodes chute de {delta} points de pourcentage "
                "entre l'électorat le moins et le plus polarisé."
            )

    if not findings:
        findings.append(
            "Les résultats montrent que la polarisation affecte la qualité "
            "démocratique mesurée par l'accord inter-méthodes et l'existence "
            "d'un vainqueur de Condorcet."
        )

    return {
        "results":      results,
        "key_findings": findings,
    }, 200


# ── Quadratic Funding endpoint ─────────────────────────────────────────────────

def _gini(values: List[float]) -> float:
    """Normalised Gini coefficient for a list of non-negative values ∈ [0,1]."""
    n = len(values)
    if n <= 1:
        return 0.0
    total = sum(values)
    if total == 0.0:
        return 0.0
    sv = sorted(values)
    cum = sum((2 * (i + 1) - n - 1) * x for i, x in enumerate(sv))
    return round(cum / (n * total), 4)


def _quadratic_funding_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /quadratic-funding — extracted for FastAPI v2."""
    num_voters       = max(20,  min(500, int(data.get("num_voters",   100))))
    ideology         = str(data.get("ideology",   "random"))
    seed             = int(data.get("seed",         42))
    budget_per_voter = max(1.0, min(1000.0, float(data.get("budget_per_voter", 100.0))))
    matching_pool    = max(0.0, float(data.get("matching_pool", 10000.0)))
    projects_raw     = data.get("projects", [
        {"name": "Éducation",    "x": -0.4},
        {"name": "Santé",        "x":  0.0},
        {"name": "Infrastructure","x":  0.5},
        {"name": "Environnement","x": -0.6},
    ])
    projects_raw = projects_raw[:8]

    if len(projects_raw) < 2:
        return {"error": "At least 2 projects required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)

    project_names: List[str] = [str(p.get("name", f"Project {i}")) for i, p in enumerate(projects_raw)]
    project_xs:   List[float] = [max(-1.0, min(1.0, float(p.get("x", 0.0)))) for p in projects_raw]

    # ── Generate electorate ────────────────────────────────────────────────
    issues = DEFAULT_ISSUES
    dummy_cands = [
        {"name": f"_P{i}", "x": project_xs[i], "y": 0.0}
        for i in range(len(project_names))
    ]
    _, voters, true_utilities, _ = _build_base_electorate(
        dummy_cands, num_voters, ideology, seed, issues
    )
    # Map dummy candidate names back to project names
    proj_utilities: Dict[Any, Dict[str, float]] = {
        v["id"]: {project_names[j]: true_utilities[v["id"]][f"_P{j}"]
                  for j in range(len(project_names))}
        for v in voters
    }

    # ── Individual contributions (proportional to utility) ─────────────────
    # c_ip = utility(v,p) / Σ_p utility(v,p) * budget_per_voter
    contributions: Dict[str, float] = {p: 0.0 for p in project_names}

    # Per-voter, per-project contributions matrix (for QF)
    voter_contribs: List[Dict[str, float]] = []
    for v in voters:
        uid = v["id"]
        u   = proj_utilities[uid]
        total_u = sum(u.values()) or 1.0
        vc: Dict[str, float] = {}
        for p in project_names:
            c = u.get(p, 0.0) / total_u * budget_per_voter
            vc[p]               = c
            contributions[p]   += c
        voter_contribs.append(vc)

    total_private = sum(contributions.values()) or 1.0

    # ── QF allocation ──────────────────────────────────────────────────────
    qf_scores: Dict[str, float] = {}
    for p in project_names:
        sqrt_sum = sum(_np.sqrt(max(0.0, vc[p])) for vc in voter_contribs)
        qf_scores[p] = float(sqrt_sum ** 2)

    total_qf = sum(qf_scores.values()) or 1.0
    qf_matching: Dict[str, float] = {
        p: qf_scores[p] / total_qf * matching_pool for p in project_names
    }

    # ── 1P1V allocation ────────────────────────────────────────────────────
    vote_counts: Counter[str] = Counter()
    for v in voters:
        uid = v["id"]
        u   = proj_utilities[uid]
        fav = max(u, key=lambda k: u[k])
        vote_counts[fav] += 1

    n_voters = len(voters) or 1
    p1v1_matching: Dict[str, float] = {
        p: vote_counts.get(p, 0) / n_voters * matching_pool for p in project_names
    }

    # ── Proportional allocation ────────────────────────────────────────────
    prop_matching: Dict[str, float] = {
        p: contributions[p] / total_private * matching_pool for p in project_names
    }

    # ── Assemble project results ───────────────────────────────────────────
    projects_out: List[Dict[str, Any]] = []
    for p in project_names:
        priv = round(contributions[p], 2)
        mtch = round(qf_matching[p],   2)
        projects_out.append({
            "name":            p,
            "private_funding": priv,
            "matching":        mtch,
            "total":           round(priv + mtch, 2),
            "qf_score":        round(qf_scores[p], 2),
        })

    winner = max(project_names,
                 key=lambda p: contributions[p] + qf_matching[p])

    # Mechanism comparison (total funding under each mechanism)
    def _totals(matching_dict: Dict[str, float]) -> Dict[str, float]:
        return {p: round(contributions[p] + matching_dict[p], 2) for p in project_names}

    mechanism_comparison = {
        "1p1v":        _totals(p1v1_matching),
        "proportional": _totals(prop_matching),
        "qf":           _totals(qf_matching),
    }

    # Gini of total allocations under each mechanism
    gini_coefficients = {
        m: _gini(list(mechanism_comparison[m].values()))
        for m in ("1p1v", "proportional", "qf")
    }

    # Pedagogical note
    qf_winner   = max(project_names, key=lambda p: mechanism_comparison["qf"][p])
    prop_winner = max(project_names, key=lambda p: mechanism_comparison["proportional"][p])
    if qf_winner != prop_winner:
        note = (
            f"QF élit '{qf_winner}' (Gini={gini_coefficients['qf']:.2f}) "
            f"tandis que le proportionnel élit '{prop_winner}' "
            f"(Gini={gini_coefficients['proportional']:.2f}). "
            "QF amplifie les projets avec beaucoup de petits donateurs."
        )
    else:
        note = (
            f"Les trois mécanismes s'accordent sur '{qf_winner}'. "
            f"QF est tout de même plus égalitaire "
            f"(Gini QF={gini_coefficients['qf']:.2f} vs "
            f"proportionnel={gini_coefficients['proportional']:.2f})."
        )

    return {
        "projects":              projects_out,
        "winner":                winner,
        "mechanism_comparison":  mechanism_comparison,
        "gini_coefficients":     gini_coefficients,
        "vote_shares":           {p: round(vote_counts.get(p, 0) / n_voters, 4)
                                  for p in project_names},
        "matching_pool":         matching_pool,
        "budget_per_voter":      budget_per_voter,
        "pedagogical_note":      note,
    }, 200


# ── Affective polarization endpoint ──────────────────────────────────────────

def _apply_affective(
    sincere_utilities: Dict[Any, Dict[str, float]],
    voter_camps:       Dict[Any, str],        # voter_id → "left" | "right" | "centre"
    candidate_camps:   Dict[str, str],        # cand_name → camp
    hostility:         float,
) -> Dict[Any, Dict[str, float]]:
    """
    Apply affective polarization: penalise candidates from the opposing camp.
    U_affective(v, c) =
        U_sincere(v, c)                          if c is in voter v's camp
        U_sincere(v, c) × (1 - hostility)        if c is in the opposing camp
    """
    affective: Dict[Any, Dict[str, float]] = {}
    for vid, utils in sincere_utilities.items():
        v_camp    = voter_camps.get(vid, "centre")
        new_utils = {}
        for cname, u in utils.items():
            c_camp = candidate_camps.get(cname, "centre")
            if c_camp == "centre" or v_camp == "centre" or c_camp == v_camp:
                new_utils[cname] = u
            else:
                new_utils[cname] = u * (1.0 - hostility)
        affective[vid] = new_utils
    return affective


def _run_all_on_utilities(
    voters:     List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    issues:     List[str],
    utilities:  Dict[Any, Dict[str, float]],
) -> Dict[str, Any]:
    """Run compare_all_methods with pre-computed utilities."""
    return compare_all_methods(
        voters, candidates, issues,
        blank_vote=False,
        override_utilities=utilities,
    )


def _affective_polarization_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /affective-polarization — extracted for FastAPI v2."""
    num_voters       = max(50,  min(500, int(data.get("num_voters",   200))))
    ideology         = str(data.get("ideology",    "random"))
    seed             = int(data.get("seed",          42))
    affect_hostility = max(0.0, min(1.0, float(data.get("affect_hostility", 0.5))))
    camp_threshold   = max(0.0, min(1.0, float(data.get("camp_threshold",   0.1))))
    num_simulations  = max(5,   min(50,  int(data.get("num_simulations",    20))))
    cand_specs       = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ])[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, sincere_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    # ── Assign camps ──────────────────────────────────────────────────────
    def _x_pos(cand: Dict[str, Any]) -> float:
        val: float = round(2.0 * float(cand["ideology_position"]) - 1.0, 3)
        return val

    candidate_camps: Dict[str, str] = {}
    for c in candidates:
        x = _x_pos(c)
        if x < -camp_threshold:
            candidate_camps[c["name"]] = "left"
        elif x > camp_threshold:
            candidate_camps[c["name"]] = "right"
        else:
            candidate_camps[c["name"]] = "centre"

    voter_camps: Dict[Any, str] = {}
    for v in voters:
        uid      = v["id"]
        best     = max(sincere_utilities[uid], key=lambda k: sincere_utilities[uid][k])
        voter_camps[uid] = candidate_camps.get(best, "centre")

    # ── Affective utilities ────────────────────────────────────────────────
    affective_utilities = _apply_affective(
        sincere_utilities, voter_camps, candidate_camps, affect_hostility
    )

    # ── Run elections ──────────────────────────────────────────────────────
    sincere_mc  = _run_all_on_utilities(voters, candidates, issues, sincere_utilities)
    affective_mc = _run_all_on_utilities(voters, candidates, issues, affective_utilities)

    sincere_winners  = {m: md.get("winner") for m, md in sincere_mc.get("methods", {}).items()}
    affective_winners = {m: md.get("winner") for m, md in affective_mc.get("methods", {}).items()}

    sincere_cw  = sincere_mc.get("condorcet_winner")
    affective_cw = affective_mc.get("condorcet_winner")

    winner_changed = any(
        sincere_winners.get(m) != affective_winners.get(m)
        for m in sincere_winners
    )
    condorcet_violation = (sincere_cw != affective_cw)

    # ── Method sensitivity via Monte Carlo ─────────────────────────────────
    method_changes: Counter[str] = Counter()
    for sim_idx in range(num_simulations):
        s = seed + sim_idx + 1
        _random.seed(s); _np.random.seed(s)
        _, sv, su, _ = _build_base_electorate(cand_specs, num_voters, ideology, s, issues)
        vcamps = {}
        for v in sv:
            uid  = v["id"]
            best = max(su[uid], key=lambda k: su[uid][k])
            vcamps[uid] = candidate_camps.get(best, "centre")
        au = _apply_affective(su, vcamps, candidate_camps, affect_hostility)
        sm = _run_all_on_utilities(sv, candidates, issues, su)
        am = _run_all_on_utilities(sv, candidates, issues, au)
        for m in sm.get("methods", {}):
            if sm["methods"][m].get("winner") != am.get("methods", {}).get(m, {}).get("winner"):
                method_changes[m] += 1

    method_sensitivity = {
        m: round(method_changes.get(m, 0) / num_simulations, 4)
        for m in sincere_winners
    }

    # ── Affect curve (hostility 0 → 1 in 11 steps) ────────────────────────
    _random.seed(seed); _np.random.seed(seed)
    affect_curve: List[Dict[str, Any]] = []
    for step in range(11):
        h = round(step / 10, 1)
        au_step = _apply_affective(sincere_utilities, voter_camps, candidate_camps, h)
        mc_step = _run_all_on_utilities(voters, candidates, issues, au_step)
        methods_step = mc_step.get("methods", {})
        winners_step = [md.get("winner") for md in methods_step.values() if md.get("winner")]
        cw_exists    = mc_step.get("condorcet_winner") is not None
        if winners_step:
            most_common_count = Counter(winners_step).most_common(1)[0][1]
            agr = most_common_count / len(winners_step)
        else:
            agr = 0.0
        affect_curve.append({
            "hostility":      h,
            "condorcet_rate": 1.0 if cw_exists else 0.0,
            "agreement_rate": round(agr, 4),
        })

    # ── Voter snapshot for the map ─────────────────────────────────────────
    voter_snaps = [
        {
            "id":        v["id"],
            "x":         round(2.0 * v["issue_positions"].get("economy", 0.5) - 1.0, 3),
            "y":         round(2.0 * v["issue_positions"].get("social_welfare", 0.5) - 1.0, 3),
            "camp":      voter_camps.get(v["id"], "centre"),
            "sincere_pref":   max(sincere_utilities[v["id"]], key=lambda k: sincere_utilities[v["id"]][k]),
            "affective_pref": max(affective_utilities[v["id"]], key=lambda k: affective_utilities[v["id"]][k]),
        }
        for v in voters[:300]
    ]

    # ── Pedagogical note ───────────────────────────────────────────────────
    changed_methods = [m for m in sincere_winners
                       if sincere_winners[m] != affective_winners[m]]
    if winner_changed:
        note = (
            f"La polarisation affective ({affect_hostility:.0%} d'hostilité) "
            f"change le vainqueur dans {len(changed_methods)} méthode(s) sur {len(sincere_winners)}. "
            f"Les méthodes les plus sensibles : {', '.join(sorted(changed_methods, key=lambda m: -method_sensitivity[m])[:3])}."
        )
    else:
        note = (
            f"Avec {affect_hostility:.0%} d'hostilité inter-partisane, "
            "aucune méthode ne change de vainqueur — "
            "l'électorat reste suffisamment consensuel pour résister à la polarisation affective."
        )

    return {
        "sincere_results":     sincere_winners,
        "affective_results":   affective_winners,
        "winner_changed":      winner_changed,
        "condorcet_violation": condorcet_violation,
        "sincere_cw":          sincere_cw,
        "affective_cw":        affective_cw,
        "method_sensitivity":  method_sensitivity,
        "affect_curve":        affect_curve,
        "candidate_camps":     candidate_camps,
        "voters":              voter_snaps,
        "candidates":          [{"name": c["name"], "x": _x_pos(c)} for c in candidates],
        "pedagogical_note":    note,
    }, 200


# ── Information Cascade ───────────────────────────────────────────────────────

def _cascade_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /cascade — extracted for FastAPI v2 reuse."""
    num_voters         = max(20,  min(500,  int(data.get("num_voters",         100))))
    ideology           = str(data.get("ideology",          "random"))
    seed               = int(data.get("seed",               42))
    cascade_strength   = max(0.0, min(1.0, float(data.get("cascade_strength",  0.5))))
    observation_window = max(0,   min(50,  int(data.get("observation_window",  10))))
    cand_specs         = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ])[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, sincere_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    def _sincere_choice(voter_id: Any) -> str:
        return max(sincere_utilities[voter_id], key=lambda k: sincere_utilities[voter_id][k])

    def _run_cascade(
        strength: float, rng: _random.Random
    ) -> tuple[list[Dict[str, Any]], str, Optional[int], float]:
        """Run one cascade pass. Returns (sequence, winner, cascade_start_at, cascade_rate)."""
        votes: list[str] = []
        sequence: list[Dict[str, Any]] = []
        cascade_start: Optional[int] = None
        cascade_count = 0

        for v in voters:
            vid     = v["id"]
            sincere = _sincere_choice(vid)
            followed = False

            if observation_window > 0 and votes and strength > 0:
                window      = votes[-observation_window:]
                pub_signal  = Counter(window).most_common(1)[0][0]
                if rng.random() < strength and pub_signal != sincere:
                    actual_vote = pub_signal
                    followed    = True
                else:
                    actual_vote = sincere
            else:
                actual_vote = sincere

            if followed:
                cascade_count += 1
                if cascade_start is None:
                    cascade_start = vid

            votes.append(actual_vote)
            sequence.append({
                "voter_id":        vid,
                "sincere_choice":  sincere,
                "actual_vote":     actual_vote,
                "followed_cascade": followed,
            })

        winner: str = Counter(votes).most_common(1)[0][0] if votes else cand_names[0]
        rate: float = round(cascade_count / len(voters), 4) if voters else 0.0
        return sequence, winner, cascade_start, rate

    # ── Main run ───────────────────────────────────────────────────────────
    rng  = _random.Random(seed)
    vote_sequence, cascade_winner, cascade_start_at, _ = _run_cascade(cascade_strength, rng)

    # Sincere winner (strength = 0, no randomness needed)
    sincere_votes   = [_sincere_choice(v["id"]) for v in voters]
    sincere_winner: str = Counter(sincere_votes).most_common(1)[0][0]

    cascade_occurred = (cascade_winner != sincere_winner)

    # ── Strength curve (11 steps 0 → 1) ───────────────────────────────────
    cascade_strength_curve: list[Dict[str, Any]] = []
    for step in range(11):
        s        = round(step / 10, 1)
        step_rng = _random.Random(seed)
        _, w, _, cr = _run_cascade(s, step_rng)
        cascade_strength_curve.append({
            "strength":     s,
            "winner":       w,
            "cascade_rate": cr,
        })

    # ── Comparison runs (strength 0, 0.5, 1.0) ────────────────────────────
    comparison_runs = [c for c in cascade_strength_curve if c["strength"] in (0.0, 0.5, 1.0)]

    # Trim sequence for large electorates (keep first 300 for timeline)
    visible_sequence = vote_sequence[:300]

    return {
        "sincere_winner":         sincere_winner,
        "cascade_winner":         cascade_winner,
        "cascade_occurred":       cascade_occurred,
        "vote_sequence":          visible_sequence,
        "cascade_start_at":       cascade_start_at,
        "cascade_strength_curve": cascade_strength_curve,
        "comparison_runs":        comparison_runs,
        "candidates":             cand_names,
    }, 200


# ── Behavioral Biases ─────────────────────────────────────────────────────────

def _behavioral_biases_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /behavioral-biases — extracted for FastAPI v2 reuse.

    Model three empirical voting biases and their impact on election outcomes:
      1. Expressive voting (Fiorina 1976): voters boost their ideal candidate ×10,
         inflating the approval threshold so they behave like bullet voters.
      2. Bullet voting: approval voters approve only their top choice, collapsing
         Approval Voting to Plurality for those voters.
      3. Primacy effect (Krosnick 1991): the first-listed candidate gains a vote
         bonus proportional to primacy_bonus.
    """
    import copy as _copy

    num_voters        = max(50,  min(500,  int(data.get("num_voters",         200))))
    ideology          = str(data.get("ideology",           "random"))
    seed              = int(data.get("seed",                42))
    expressive_pct    = max(0.0, min(1.0, float(data.get("expressive_pct",    0.2))))
    bullet_pct        = max(0.0, min(1.0, float(data.get("bullet_voting_pct", 0.2))))
    primacy_bonus     = max(0.0, min(0.2, float(data.get("primacy_bonus",     0.02))))
    # Pydantic Optional[List[str]] may pass null — fall back to [].
    candidate_order   = [str(n) for n in (data.get("candidate_order") or [])]
    primary_method    = str(data.get("method", "plurality"))
    cand_specs        = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ])[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, sincere_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    # ── Resolve candidate order for primacy ───────────────────────────────
    name_set = set(cand_names)
    ordered_names: list[str] = [n for n in candidate_order if n in name_set]
    if len(ordered_names) != len(cand_names):
        ordered_names = list(cand_names)
    first_listed = ordered_names[0]

    # ── Select affected voter subsets ─────────────────────────────────────
    all_ids       = [v["id"] for v in voters]
    rng           = _random.Random(seed)
    exp_count     = round(expressive_pct * num_voters)
    bullet_count  = round(bullet_pct     * num_voters)
    primacy_count = round(primacy_bonus  * num_voters)

    expressive_ids = set(rng.sample(all_ids, min(exp_count,     len(all_ids))))
    bullet_ids     = set(rng.sample(all_ids, min(bullet_count,  len(all_ids))))
    primacy_ids    = set(rng.sample(all_ids, min(primacy_count, len(all_ids))))

    # ── Build biased utilities ────────────────────────────────────────────
    biased_utilities: Dict[Any, Dict[str, float]] = _copy.deepcopy(sincere_utilities)

    for v in voters:
        vid = v["id"]
        u   = biased_utilities[vid]
        # Expressive: emotional attachment inflates ideal candidate utility ×10
        if vid in expressive_ids:
            ideal = max(u, key=lambda k: u[k])
            u[ideal] = u[ideal] * 10.0
        # Primacy: position bias nudges voter toward first-listed candidate
        if vid in primacy_ids:
            curr_max        = max(u.values())
            u[first_listed] = curr_max + 0.1

    # ── Fast winner computation (no strategic-vulnerability overhead) ──────
    from api.engine.utils.simulation_ranked_utils import (
        get_borda_winner as _borda,
        get_irv_winner   as _irv,
        get_schulze_winner as _schulze,
    )
    from api.engine.utils.simulation_score_utils import (
        get_star_voting_winner        as _star,
        get_majority_judgment_winner  as _mj,
    )

    def _compute_winners(utils: Dict[Any, Dict[str, float]]) -> Dict[str, Optional[str]]:
        rnk = [
            sorted(utils[v["id"]].keys(), key=lambda n: -utils[v["id"]][n])
            for v in voters
        ]
        sv = [
            {n: max(0, min(5, round(5 * val))) for n, val in utils[v["id"]].items()}
            for v in voters
        ]
        out: Dict[str, Optional[str]] = {}
        for mname, fn in [("plurality", get_plurality_winner),
                           ("borda",    _borda),
                           ("irv",      _irv),
                           ("schulze",  _schulze)]:
            try:
                out[mname] = fn(rnk)
            except Exception:
                out[mname] = None
        try:
            raw = _star(sv)
            out["star_voting"] = raw.get("winner") if isinstance(raw, dict) else raw
        except Exception:
            out["star_voting"] = None
        try:
            mj_utils = [dict(utils[v["id"]]) for v in voters]
            mj_raw   = _mj(mj_utils)
            out["majority_judgment"] = str(mj_raw["winner"]) if mj_raw.get("winner") else None
        except Exception:
            out["majority_judgment"] = None
        return out

    # ── Approval with bullet voting ───────────────────────────────────────
    def _approval_winner(utils: Dict[Any, Dict[str, float]], bids: set) -> str:
        tally: Counter = Counter()
        for v in voters:
            vid = v["id"]
            u   = utils[vid]
            if not u:
                continue
            if vid in bids:
                tally[max(u, key=lambda k: u[k])] += 1
            else:
                threshold = sum(u.values()) / len(u)
                for cname, val in u.items():
                    if val > threshold:
                        tally[cname] += 1
        return max(tally, key=tally.__getitem__) if tally else cand_names[0]

    sincere_winners  = _compute_winners(sincere_utilities)
    biased_winners   = _compute_winners(biased_utilities)

    # Approval computed separately for both runs
    sincere_winners["approval"] = _approval_winner(sincere_utilities, set())
    biased_winners["approval"]  = _approval_winner(biased_utilities,  bullet_ids)

    # ── Method sensitivity table ──────────────────────────────────────────
    TRACKED = ["plurality", "approval", "borda", "irv",
               "schulze", "star_voting", "majority_judgment"]
    method_sensitivity: Dict[str, Dict[str, Optional[str]]] = {
        m: {"sincere": sincere_winners.get(m), "biased": biased_winners.get(m)}
        for m in TRACKED
        if sincere_winners.get(m) or biased_winners.get(m)
    }

    # ── Headline comparison ───────────────────────────────────────────────
    sincere_winner = sincere_winners.get(primary_method) or cand_names[0]
    biased_winner  = biased_winners.get(primary_method)  or cand_names[0]
    winner_changed = sincere_winner != biased_winner

    # ── Pedagogical note ──────────────────────────────────────────────────
    changed_methods = [m for m, d in method_sensitivity.items()
                       if d["sincere"] != d["biased"]]
    if winner_changed:
        note = (
            f"Ces biais comportementaux changent le vainqueur de {sincere_winner}"
            f" à {biased_winner} sous la méthode '{primary_method}'. "
            f"{len(changed_methods)} méthode(s) affectée(s) : "
            f"{', '.join(changed_methods[:4])}."
        )
    else:
        if changed_methods:
            note = (
                f"Le vainqueur sincère ({sincere_winner}) est maintenu sous '{primary_method}', "
                f"mais {len(changed_methods)} autre(s) méthode(s) changent de vainqueur "
                f"sous ces biais : {', '.join(changed_methods[:4])}."
            )
        else:
            note = (
                f"Aucune méthode ne change de vainqueur malgré ces biais comportementaux. "
                f"L'électorat est suffisamment homogène pour résister aux distorsions."
            )

    return {
        "sincere_winner":   sincere_winner,
        "biased_winner":    biased_winner,
        "winner_changed":   winner_changed,
        "vote_breakdown": {
            "expressive_voters": exp_count,
            "bullet_voters":     bullet_count,
            "primacy_affected":  primacy_count,
            "first_listed":      first_listed,
            "candidate_order":   ordered_names,
        },
        "method_sensitivity":    method_sensitivity,
        "bullet_immune_methods": ["majority_judgment", "star_voting",
                                  "borda", "irv", "schulze"],
        "pedagogical_note":      note,
    }, 200


# ── Liquid Democracy ──────────────────────────────────────────────────────────

def _liquid_democracy_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /liquid-democracy — extracted for FastAPI v2."""
    num_voters       = max(2,  min(500, int(data.get("num_voters",            100))))
    ideology         = str(data.get("ideology",              "random"))
    seed             = int(data.get("seed",                   42))
    delegation_prob  = max(0.0, min(1.0, float(data.get("delegation_probability", 0.5))))
    strategy         = str(data.get("delegation_strategy",   "nearest"))
    max_chain        = max(1,   min(20,  int(data.get("max_chain_length",          5))))
    cand_specs       = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ])[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, sincere_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )
    all_ids: list[int] = [v["id"] for v in voters]

    # ── Voter ideology positions (for nearest-delegate lookup) ─────────────
    def _vpos(v: Dict[str, Any]) -> tuple[float, float]:
        return (
            round(2.0 * v["issue_positions"].get("economy",        0.5) - 1.0, 3),
            round(2.0 * v["issue_positions"].get("social_welfare", 0.5) - 1.0, 3),
        )

    voter_positions: Dict[int, tuple[float, float]] = {
        v["id"]: _vpos(v) for v in voters
    }

    rng = _random.Random(seed)

    # ── Delegate picker per strategy ──────────────────────────────────────
    def _pick_delegate(voter_id: int) -> int:
        others = [v for v in all_ids if v != voter_id]
        if not others:
            return voter_id
        if strategy == "nearest":
            vx, vy = voter_positions[voter_id]
            return min(others, key=lambda o: (voter_positions[o][0] - vx) ** 2
                                           + (voter_positions[o][1] - vy) ** 2)
        if strategy == "most_competent":
            return max(others, key=lambda o: max(sincere_utilities[o].values()))
        return rng.choice(others)  # "random"

    # ── Build delegation graph ────────────────────────────────────────────
    delegations: Dict[int, int] = {
        vid: _pick_delegate(vid)
        for vid in all_ids
        if rng.random() < delegation_prob
    }

    # ── Cycle detection (functional graph — each node has ≤1 outgoing edge) ─
    def _detect_cycles(delg: Dict[int, int]) -> set:
        in_cycle: set = set()
        visited:  set = set()
        for start in list(delg.keys()):
            if start in visited:
                continue
            path: list[int]      = []
            path_pos: Dict[int, int] = {}
            cur = start
            while cur not in visited and cur not in path_pos and cur in delg:
                path_pos[cur] = len(path)
                path.append(cur)
                cur = delg[cur]
            if cur in path_pos:
                for node in path[path_pos[cur]:]:
                    in_cycle.add(node)
            visited.update(path)
        return in_cycle

    in_cycle = _detect_cycles(delegations)

    # ── Resolve delegation chains ─────────────────────────────────────────
    effective:     Dict[int, int] = {}
    chain_lengths: Dict[int, int] = {}

    for vid in all_ids:
        if vid not in delegations or vid in in_cycle:
            effective[vid] = vid
            continue
        cur, steps = vid, 0
        while cur in delegations and cur not in in_cycle and steps < max_chain:
            cur = delegations[cur]
            steps += 1
        if cur not in delegations or cur in in_cycle:
            effective[vid] = cur
            chain_lengths[vid] = steps
        else:
            effective[vid] = vid   # max chain exhausted → vote directly

    # ── Voting weights ────────────────────────────────────────────────────
    weights: Counter = Counter(effective.values())

    # ── Liquid winner (weighted plurality) ────────────────────────────────
    liquid_tally: Counter = Counter()
    for vid, w in weights.items():
        choice = max(sincere_utilities[vid], key=lambda k: sincere_utilities[vid][k])
        liquid_tally[choice] += w
    liquid_winner: str = (
        max(liquid_tally, key=liquid_tally.__getitem__) if liquid_tally else cand_names[0]
    )

    # ── Direct winner (unweighted baseline) ──────────────────────────────
    direct_tally: Counter = Counter()
    for v in voters:
        choice = max(sincere_utilities[v["id"]], key=lambda k: sincere_utilities[v["id"]][k])
        direct_tally[choice] += 1
    direct_winner: str = (
        max(direct_tally, key=direct_tally.__getitem__) if direct_tally else cand_names[0]
    )

    winner_changed = liquid_winner != direct_winner

    # ── Statistics ────────────────────────────────────────────────────────
    def _gini(vals: List[Any]) -> float:
        n = len(vals)
        if n == 0:
            return 0.0
        s     = sorted(float(v) for v in vals)
        total = sum(s)
        if total == 0.0:
            return 0.0
        cumsum = sum((i + 1) * v for i, v in enumerate(s))
        return round(abs(2.0 * cumsum / (n * total) - (n + 1) / n), 4)

    all_w           = [weights.get(vid, 0) for vid in all_ids]
    gini            = _gini(all_w)
    lengths         = list(chain_lengths.values())
    direct_count    = sum(1 for vid in all_ids if effective[vid] == vid)
    delegator_count = sum(1 for vid in all_ids if effective[vid] != vid)

    chain_stats: Dict[str, Any] = {
        "mean": round(sum(lengths) / len(lengths), 2) if lengths else 0.0,
        "max":  max(lengths) if lengths else 0,
    }

    # ── Super voters ──────────────────────────────────────────────────────
    super_voters = [
        {
            "id":     vid,
            "weight": w,
            "x":      voter_positions[vid][0],
            "y":      voter_positions[vid][1],
            "choice": max(sincere_utilities[vid], key=lambda k: sincere_utilities[vid][k]),
        }
        for vid, w in sorted(weights.items(), key=lambda x: -x[1])[:10]
        if w >= 2
    ]

    # ── Delegation graph (raw edges for visualisation, ≤ 500) ─────────────
    delegation_graph_out = [
        {"from": d, "to": t} for d, t in delegations.items()
    ][:500]

    # ── Gini curve (11 steps 0 → 1) ──────────────────────────────────────
    gini_curve: list[Dict[str, Any]] = []
    for step in range(11):
        p = round(step / 10, 1)
        g_rng = _random.Random(seed)
        g_delg: Dict[int, int] = {
            vid: _pick_delegate(vid)
            for vid in all_ids
            if g_rng.random() < p
        }
        g_cycle    = _detect_cycles(g_delg)
        g_eff: Dict[int, int] = {}
        for vid in all_ids:
            if vid not in g_delg or vid in g_cycle:
                g_eff[vid] = vid
            else:
                cur, st = vid, 0
                while cur in g_delg and cur not in g_cycle and st < max_chain:
                    cur = g_delg[cur]
                    st += 1
                g_eff[vid] = cur if (cur not in g_delg or cur in g_cycle) else vid
        g_w = Counter(g_eff.values())
        gini_curve.append({"probability": p, "gini": _gini([g_w.get(v, 0) for v in all_ids])})

    # ── Pedagogical note ──────────────────────────────────────────────────
    total_w  = sum(weights.values())
    top3_w   = sum(w for _, w in sorted(weights.items(), key=lambda x: -x[1])[:3])
    top3_pct = round(100 * top3_w / total_w) if total_w else 0
    if winner_changed:
        note = (
            f"Avec {round(delegation_prob * 100)}% de délégation ({strategy}), "
            f"3 super-votants concentrent {top3_pct}% du poids électoral (Gini={gini}). "
            f"La Liquid Democracy change le vainqueur : {direct_winner} → {liquid_winner}."
        )
    else:
        note = (
            f"Avec {round(delegation_prob * 100)}% de délégation ({strategy}), "
            f"{top3_pct}% du poids va aux 3 premiers super-votants (Gini={gini}). "
            f"Le vainqueur reste {liquid_winner} malgré la concentration."
        )

    return {
        "weighted_results":   {c: int(liquid_tally.get(c, 0)) for c in cand_names},
        "direct_voters":      direct_count,
        "delegators":         delegator_count,
        "super_voters":       super_voters,
        "delegation_graph":   delegation_graph_out,
        "cycles_detected":    len(in_cycle),
        "cycle_voter_ids":    list(in_cycle),
        "chain_stats":        chain_stats,
        "gini_curve":         gini_curve,
        "comparison": {
            "liquid_winner":  liquid_winner,
            "direct_winner":  direct_winner,
            "winner_changed": winner_changed,
        },
        "gini_voting_weight": gini,
        "pedagogical_note":   note,
    }, 200


# ── Conviction Voting ─────────────────────────────────────────────────────────

_CV_LOCK_OPTIONS: list[int]    = [0, 7, 14, 28, 56, 112, 224]
_CV_MULTIPLIERS:  Dict[int, float] = {0: 0.1, 7: 1.0, 14: 2.0, 28: 3.0,
                                       56: 4.0, 112: 5.0, 224: 6.0}


def _conviction_voting_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /conviction-voting — extracted for FastAPI v2."""
    num_voters     = max(20, min(500, int(data.get("num_voters",   200))))
    ideology       = str(data.get("ideology",       "random"))
    seed           = int(data.get("seed",            42))
    cv_dist        = str(data.get("conviction_distribution", "uniform"))
    whale_pct      = max(0.05, min(0.5, float(data.get("whale_pct",       0.10))))
    small_lock_d   = int(data.get("small_lock_days", 224))
    small_lock_d   = small_lock_d if small_lock_d in _CV_LOCK_OPTIONS else 224
    proposals_in   = data.get("proposals", [
        {"name": "Proposition A", "x": -0.5},
        {"name": "Proposition B", "x":  0.5},
        {"name": "Proposition C", "x":  0.0},
    ])[:8]

    if len(proposals_in) < 2:
        return {"error": "At least 2 proposals required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    # ── Electorate ────────────────────────────────────────────────────────
    voters = [
        create_voter(issues, i, ideology_distribution=ideology)
        for i in range(num_voters)
    ]
    all_ids: list[int] = [v["id"] for v in voters]

    # ── Token distribution (Pareto a=1.16 — realistic crypto inequality) ──
    raw_tokens = _np.random.pareto(1.16, num_voters) + 1.0
    tokens_arr = raw_tokens / raw_tokens.mean() * 1000.0          # mean ≈ 1000
    voter_tokens: Dict[int, float] = {
        v["id"]: float(tokens_arr[i]) for i, v in enumerate(voters)
    }

    # ── Token rank (0 = smallest holder) ──────────────────────────────────
    tok_vals     = _np.array([voter_tokens[vid] for vid in all_ids])
    rank_arr     = _np.argsort(_np.argsort(tok_vals)) / max(1, len(all_ids) - 1)
    token_ranks: Dict[int, float] = {all_ids[i]: float(rank_arr[i]) for i in range(len(all_ids))}

    rng = _random.Random(seed + 1)

    # ── Assign conviction lock ────────────────────────────────────────────
    def _assign_lock(voter_id: int) -> int:
        rank = token_ranks[voter_id]
        if cv_dist == "uniform":
            return rng.choice(_CV_LOCK_OPTIONS)
        if cv_dist == "skewed":
            # Smaller holders lock longer (inverse relationship with token rank)
            lock_idx = min(6, round((1.0 - rank) * 6.0))
            return _CV_LOCK_OPTIONS[lock_idx]
        if cv_dist == "whale":
            # Top whale_pct% by tokens → no lock; rest → small_lock_d
            return 0 if rank >= (1.0 - whale_pct) else small_lock_d
        if cv_dist == "zero_lock":
            return 0
        return rng.choice(_CV_LOCK_OPTIONS)

    voter_lock:    Dict[int, int]   = {vid: _assign_lock(vid) for vid in all_ids}
    voter_mult:    Dict[int, float] = {vid: _CV_MULTIPLIERS[voter_lock[vid]] for vid in all_ids}
    voter_cv_w:    Dict[int, float] = {vid: voter_tokens[vid] * voter_mult[vid] for vid in all_ids}

    # ── Voter ideology → proposal choice ─────────────────────────────────
    prop_names: list[str]   = [p["name"] for p in proposals_in]
    prop_x:     Dict[str, float] = {p["name"]: float(p.get("x", 0.0)) for p in proposals_in}

    voter_ide: Dict[int, float] = {
        v["id"]: 2.0 * v["issue_positions"].get("economy", 0.5) - 1.0
        for v in voters
    }
    voter_choice: Dict[int, str] = {
        vid: min(prop_names, key=lambda pn: abs(voter_ide[vid] - prop_x[pn]))
        for vid in all_ids
    }

    # ── Tally ─────────────────────────────────────────────────────────────
    cv_tally:  Dict[str, float] = {p: 0.0 for p in prop_names}
    tok_tally: Dict[str, float] = {p: 0.0 for p in prop_names}

    for vid in all_ids:
        ch = voter_choice[vid]
        cv_tally[ch]  += voter_cv_w[vid]
        tok_tally[ch] += voter_tokens[vid]

    conviction_winner: str = max(cv_tally,  key=cv_tally.__getitem__)
    token_winner:      str = max(tok_tally, key=tok_tally.__getitem__)
    winner_changed         = conviction_winner != token_winner

    # ── Per-proposal stats ────────────────────────────────────────────────
    proposal_stats: list[Dict[str, Any]] = []
    for p in proposals_in:
        pn   = p["name"]
        supp = [vid for vid in all_ids if voter_choice[vid] == pn]
        proposal_stats.append({
            "name":                        pn,
            "conviction_score":            round(cv_tally[pn],  2),
            "token_score":                 round(tok_tally[pn], 2),
            "avg_conviction_of_supporters": round(
                sum(voter_mult[vid] for vid in supp) / len(supp), 3
            ) if supp else 0.0,
            "avg_tokens_of_supporters": round(
                sum(voter_tokens[vid] for vid in supp) / len(supp), 2
            ) if supp else 0.0,
        })

    # ── Gini + whale stats ────────────────────────────────────────────────
    def _gini(vals: List[Any]) -> float:
        n = len(vals)
        if n == 0:
            return 0.0
        s     = sorted(float(v) for v in vals)
        total = sum(s)
        if total == 0.0:
            return 0.0
        cumsum = sum((i + 1) * v for i, v in enumerate(s))
        return round(abs(2.0 * cumsum / (n * total) - (n + 1) / n), 4)

    all_tok = [voter_tokens[vid] for vid in all_ids]
    all_cvw = [voter_cv_w[vid]   for vid in all_ids]

    top_n          = max(1, round(whale_pct * num_voters))
    top_tok        = sorted(all_tok, reverse=True)[:top_n]
    top_cvw        = sorted(all_cvw, reverse=True)[:top_n]
    sum_tok        = sum(all_tok) or 1.0
    sum_cvw        = sum(all_cvw) or 1.0

    voter_stats: Dict[str, float] = {
        "gini_tokens":          _gini(all_tok),
        "gini_conviction":      _gini(all_cvw),
        "whale_pct_tokens":     round(sum(top_tok) / sum_tok, 4),
        "whale_pct_conviction": round(sum(top_cvw) / sum_cvw, 4),
    }

    # ── Voter scatter sample (max 300) ────────────────────────────────────
    voter_scatter: list[Dict[str, Any]] = [
        {
            "id":               vid,
            "tokens":           round(voter_tokens[vid], 1),
            "lock_days":        voter_lock[vid],
            "conviction_mult":  voter_mult[vid],
            "conviction_weight": round(voter_cv_w[vid], 1),
            "choice":           voter_choice[vid],
        }
        for vid in all_ids[:300]
    ]

    # ── Pedagogical note ──────────────────────────────────────────────────
    max_cv_vid  = max(all_ids, key=lambda v: voter_cv_w[v])
    max_tok_vid = max(all_ids, key=lambda v: voter_tokens[v])
    note = (
        f"Un votant avec {round(voter_tokens[max_cv_vid])} tokens "
        f"et {voter_lock[max_cv_vid]} jours de lock pèse "
        f"{round(voter_cv_w[max_cv_vid])} points de conviction. "
        f"La baleine principale ({round(voter_tokens[max_tok_vid])} tokens, "
        f"{voter_lock[max_tok_vid]} jours) pèse "
        f"{round(voter_cv_w[max_tok_vid])} points. "
    )
    if voter_stats["gini_conviction"] < voter_stats["gini_tokens"]:
        note += (
            f"La conviction réduit l'inégalité effective "
            f"(Gini tokens={voter_stats['gini_tokens']} → "
            f"conviction={voter_stats['gini_conviction']})."
        )
    else:
        note += (
            f"Dans ce scénario, la conviction n'atténue pas l'inégalité "
            f"(Gini tokens={voter_stats['gini_tokens']}, "
            f"conviction={voter_stats['gini_conviction']})."
        )

    return {
        "conviction_winner": conviction_winner,
        "token_winner":      token_winner,
        "winner_changed":    winner_changed,
        "proposals":         proposal_stats,
        "voter_scatter":     voter_scatter,
        "voter_stats":       voter_stats,
        "pedagogical_note":  note,
        "lock_options":      _CV_LOCK_OPTIONS,
        "multipliers":       {str(k): v for k, v in _CV_MULTIPLIERS.items()},
    }, 200


# ── NOTA (None Of The Above) ──────────────────────────────────────────────────

# How inclusive each method is: lower adjustment → fewer NOTA voters
# (method integrates more preference information → voter finds more to approve)
_NOTA_ADJ: Dict[str, float] = {
    "plurality":          1.00,
    "two_round":          1.00,
    "borda":              0.95,
    "irv":                0.95,
    "schulze":            0.90,
    "kemeny_young":       0.90,
    "coombs":             0.95,
    "bucklin":            0.95,
    "minimax":            0.90,
    "copeland":           0.92,
    "nanson":             0.92,
    "baldwin":            0.92,
    "approval":           0.50,   # most inclusive: approval of partial satisfaction
    "simple_score":       0.70,
    "star_voting":        0.70,
    "median_voting":      0.80,
    "mean_median_hybrid": 0.80,
    "variance_based":     0.80,
    "majority_judgment":  0.70,
    "quadratic":          0.75,
}

_NOTA_TRACKED = [
    "plurality", "approval", "borda", "irv", "schulze", "majority_judgment",
]


def _nota_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /nota — extracted for FastAPI v2 reuse (Phase 3 batch 3)."""

    num_voters     = max(50,  min(500, int(data.get("num_voters",     200))))
    ideology       = str(data.get("ideology",      "random"))
    seed           = int(data.get("seed",           42))
    nota_threshold = max(0.0, min(1.0, float(data.get("nota_threshold", 0.3))))
    nota_rule      = str(data.get("nota_rule",     "invalidate"))
    primary_method = str(data.get("method",        "plurality"))
    cand_specs     = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ])[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, sincere_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    # ── NOTA determination for a given method+threshold ───────────────────
    def _nota_pct(threshold: float, method: str = "plurality") -> float:
        adj           = _NOTA_ADJ.get(method, 1.0)
        eff_threshold = threshold * adj
        count = sum(
            1 for v in voters
            if max(sincere_utilities[v["id"]].values()) < eff_threshold
        )
        return round(count / num_voters, 4) if num_voters else 0.0

    # ── Winner with NOTA (plurality model for simplicity) ─────────────────
    def _winner_with_nota(threshold: float) -> tuple[Optional[str], float]:
        """Returns (sincere plurality winner or 'NOTA', nota_pct)."""
        tally: Counter = Counter()
        for v in voters:
            vid      = v["id"]
            max_util = max(sincere_utilities[vid].values())
            if max_util < threshold:
                tally["NOTA"] += 1
            else:
                choice = max(sincere_utilities[vid], key=lambda k: sincere_utilities[vid][k])
                tally[choice] += 1
        raw_winner = max(tally, key=tally.__getitem__) if tally else cand_names[0]
        np         = tally.get("NOTA", 0) / num_voters if num_voters else 0.0
        return raw_winner, round(np, 4)

    # ── Sincere winners per method (without NOTA) ─────────────────────────
    from api.engine.utils.simulation_ranked_utils import (
        get_borda_winner as _borda, get_irv_winner as _irv,
        get_schulze_winner as _schulze,
    )
    from api.engine.utils.simulation_score_utils import get_majority_judgment_winner as _mj

    def _sincere_winner(method: str) -> Optional[str]:
        rnk = [
            sorted(sincere_utilities[v["id"]].keys(),
                   key=lambda n: -sincere_utilities[v["id"]][n])
            for v in voters
        ]
        if method in ("plurality", "two_round"):
            return get_plurality_winner(rnk)
        if method == "borda":
            return _borda(rnk)
        if method == "irv":
            return _irv(rnk)
        if method == "schulze":
            return _schulze(rnk)
        if method == "approval":
            # sincere approval: approve above voter mean
            tally: Counter = Counter()
            for v in voters:
                u  = sincere_utilities[v["id"]]
                th = sum(u.values()) / len(u) if u else 0.5
                for cname, val in u.items():
                    if val > th:
                        tally[cname] += 1
            return max(tally, key=tally.__getitem__) if tally else cand_names[0]
        if method == "majority_judgment":
            mj_utils = [dict(sincere_utilities[v["id"]]) for v in voters]
            try:
                mj_raw = _mj(mj_utils)
                return str(mj_raw["winner"]) if mj_raw.get("winner") else None
            except Exception:
                return None
        return get_plurality_winner(rnk)

    # ── Main computation ──────────────────────────────────────────────────
    nota_pct_main = _nota_pct(nota_threshold, primary_method)
    raw_winner, _ = _winner_with_nota(nota_threshold)
    nota_wins_main = raw_winner == "NOTA"

    def _apply_nota_rule(nota_wins: bool, raw: Optional[str]) -> tuple[Optional[str], bool]:
        if not nota_wins:
            return raw, True
        if nota_rule == "winner_take_all":
            return "NOTA", True
        return None, False   # invalidate / runoff → null winner, invalid election

    final_winner, election_valid = _apply_nota_rule(nota_wins_main, raw_winner)

    # ── Nota curve (20 points: 0.00 → 0.95, step 0.05) ──────────────────
    nota_curve: list[Dict[str, Any]] = []
    sincere_w_primary = _sincere_winner(primary_method)
    for i in range(20):
        t          = round(i * 0.05, 2)
        np_t       = _nota_pct(t, primary_method)
        raw_t, _   = _winner_with_nota(t)
        nota_wins_t = raw_t == "NOTA"
        w_t, _     = _apply_nota_rule(nota_wins_t, sincere_w_primary if not nota_wins_t else None)
        nota_curve.append({
            "threshold": t,
            "nota_pct":  np_t,
            "nota_wins": nota_wins_t,
            "winner":    w_t,
        })

    # ── Method comparison ─────────────────────────────────────────────────
    method_comparison: Dict[str, Any] = {}
    for meth in _NOTA_TRACKED:
        np_m       = _nota_pct(nota_threshold, meth)
        nota_wins_m = np_m > 0.5
        sincere_m  = _sincere_winner(meth)
        w_m, v_m   = _apply_nota_rule(nota_wins_m, sincere_m)
        method_comparison[meth] = {
            "winner":         w_m,
            "nota_pct":       np_m,
            "election_valid": v_m,
        }

    # ── Pedagogical note ──────────────────────────────────────────────────
    most_inclusive = min(
        _NOTA_TRACKED,
        key=lambda m: method_comparison[m]["nota_pct"],
    )
    note = (
        f"Avec un seuil de {nota_threshold}, "
        f"{round(nota_pct_main * 100)}% de l'électorat voterait NOTA "
        f"sous la méthode '{primary_method}'. "
        f"La méthode '{most_inclusive}' génère seulement "
        f"{round(method_comparison[most_inclusive]['nota_pct'] * 100)}% de NOTA "
        f"— elle est plus inclusive car elle intègre davantage de préférences individuelles."
    )

    return {
        "nota_pct":          nota_pct_main,
        "election_valid":    election_valid,
        "winner":            final_winner,
        "nota_curve":        nota_curve,
        "method_comparison": method_comparison,
        "pedagogical_note":  note,
        "nota_rule":         nota_rule,
        "nota_threshold":    nota_threshold,
    }, 200


# ── Ballot Complexity ─────────────────────────────────────────────────────────

# Base error rate per voting method (empirically motivated)
_BALLOT_ERROR_BASE: Dict[str, float] = {
    "plurality":          0.010,
    "two_round":          0.012,
    "approval":           0.025,
    "irv":                0.040,
    "borda":              0.045,
    "star_voting":        0.035,
    "majority_judgment":  0.030,
    "schulze":            0.050,
    "kemeny_young":       0.060,
}

_DEFAULT_BALLOT_METHODS = [
    "plurality", "approval", "irv", "borda",
    "star_voting", "majority_judgment", "schulze",
]


def _ballot_complexity_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /ballot-complexity — extracted for FastAPI v2 reuse."""
    num_voters       = max(50, min(500, int(data.get("num_voters",              200))))
    ideology         = str(data.get("ideology",              "random"))
    seed             = int(data.get("seed",                   42))
    education_level  = max(0.0, min(1.0, float(data.get("education_level",     0.7))))
    ftv_pct          = max(0.0, min(1.0, float(data.get("first_time_voter_pct", 0.1))))
    # Pydantic Optional[List[str]]=None may pass null explicitly — fall back
    # to the server default in that case rather than indexing into None.
    methods_compare  = (data.get("methods_to_compare") or _DEFAULT_BALLOT_METHODS)[:8]
    cand_specs       = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ])[:8]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, sincere_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )
    n_cands = len(cand_names)

    # ── Null rate formula ─────────────────────────────────────────────────
    def _null_rate(method: str, n: int = n_cands) -> float:
        base = _BALLOT_ERROR_BASE.get(method, 0.03)
        rate = (base
                * (1.0 + 0.08 * max(0, n - 3))
                * (2.0 - education_level)
                * (1.0 + ftv_pct))
        return round(min(1.0, rate), 4)

    # ── Blank rate (intentional blank vote: max utility < 0.3) ───────────
    blank_rate_global = round(
        sum(1 for v in voters if max(sincere_utilities[v["id"]].values()) < 0.3)
        / num_voters, 4,
    )

    # ── Fast winner per method ────────────────────────────────────────────
    from api.engine.utils.simulation_ranked_utils import (
        get_borda_winner as _borda_w,
        get_irv_winner   as _irv_w,
        get_schulze_winner as _sch_w,
    )
    from api.engine.utils.simulation_score_utils import (
        get_star_voting_winner       as _star_w,
        get_majority_judgment_winner as _mj_w,
    )

    def _winner_for(method: str, vlist: list[Dict[str, Any]]) -> Optional[str]:
        if not vlist:
            return None
        rnk = [
            sorted(sincere_utilities[v["id"]].keys(),
                   key=lambda n: -sincere_utilities[v["id"]][n])
            for v in vlist
        ]
        sv = [
            {n: max(0, min(5, round(5 * sincere_utilities[v["id"]][n])))
             for n in cand_names}
            for v in vlist
        ]
        if method in ("plurality", "two_round"):
            return get_plurality_winner(rnk)
        if method == "borda":
            return _borda_w(rnk)
        if method == "irv":
            return _irv_w(rnk)
        if method == "schulze":
            return _sch_w(rnk)
        if method == "approval":
            tally: Counter = Counter()
            for v in vlist:
                u  = sincere_utilities[v["id"]]
                th = sum(u.values()) / len(u) if u else 0.5
                for cname, val in u.items():
                    if val > th:
                        tally[cname] += 1
            return max(tally, key=tally.__getitem__) if tally else cand_names[0]
        if method == "star_voting":
            try:
                raw = _star_w(sv)
                return raw.get("winner") if isinstance(raw, dict) else raw
            except Exception:
                return get_plurality_winner(rnk)
        if method == "majority_judgment":
            try:
                mj_u = [dict(sincere_utilities[v["id"]]) for v in vlist]
                raw  = _mj_w(mj_u)
                return str(raw["winner"]) if raw.get("winner") else None
            except Exception:
                return get_plurality_winner(rnk)
        return get_plurality_winner(rnk)

    # ── Per-method simulation ─────────────────────────────────────────────
    results: list[Dict[str, Any]] = []
    sincere_winners: Dict[str, Optional[str]] = {
        m: _winner_for(m, voters) for m in methods_compare
    }

    for i, method in enumerate(methods_compare):
        nr         = _null_rate(method)
        method_rng = _random.Random(seed + 1000 + i)
        valid_voters = [v for v in voters if method_rng.random() >= nr]
        valid_w      = _winner_for(method, valid_voters)
        results.append({
            "method":           method,
            "null_rate":        nr,
            "blank_rate":       blank_rate_global,
            "effective_voters": len(valid_voters),
            "winner":           valid_w,
            "winner_changed":   valid_w != sincere_winners[method],
        })

    # ── Candidate count curve (analytical) ───────────────────────────────
    candidate_count_curve: list[Dict[str, Any]] = [
        {
            "n_candidates": n,
            "null_rate_by_method": {
                m: _null_rate(m, n) for m in methods_compare
            },
        }
        for n in range(2, 11)
    ]

    # ── Most / least inclusive ────────────────────────────────────────────
    nr_map = {r["method"]: r["null_rate"] for r in results}
    most_inclusive  = min(nr_map, key=nr_map.__getitem__)
    least_inclusive = max(nr_map, key=nr_map.__getitem__)

    # ── Pedagogical note ──────────────────────────────────────────────────
    plurality_nr = nr_map.get("plurality", nr_map[methods_compare[0]])
    worst_nr     = nr_map[least_inclusive]
    note = (
        f"Avec {n_cands} candidats, {round(ftv_pct*100)}% de primo-votants "
        f"et un niveau d'éducation de {education_level:.1f}, "
        f"la méthode '{least_inclusive}' entraîne {round(worst_nr*100, 1)}% de bulletins nuls "
        f"contre {round(plurality_nr*100, 1)}% pour Plurality. "
        f"Ce n'est pas l'électeur qui échoue — c'est la conception du bulletin."
    )

    return {
        "results":                results,
        "candidate_count_curve":  candidate_count_curve,
        "most_inclusive_method":  most_inclusive,
        "least_inclusive_method": least_inclusive,
        "pedagogical_note":       note,
    }, 200


# ── Shy Voter Effect ──────────────────────────────────────────────────────────

def _shy_voter_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /shy-voter — extracted for FastAPI v2 reuse.

    Simulate the Bradley / Shy Tory effect: voters who intend to vote for a
    socially 'sensitive' candidate declare a more acceptable preference in polls
    (with probability social_desirability_factor) but vote sincerely in the booth.
    """
    num_voters     = max(50,  min(500, int(data.get("num_voters",                  300))))
    ideology       = str(data.get("ideology",                  "random"))
    seed           = int(data.get("seed",                       42))
    shy_idx        = max(0,   int(data.get("shy_candidate_idx",  0)))
    sdf            = max(0.0, min(1.0, float(data.get("social_desirability_factor", 0.4))))
    num_polls      = max(3,   min(30,  int(data.get("num_polls",                   10))))
    cand_specs     = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ])[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, sincere_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )
    shy_idx       = min(shy_idx, len(cand_names) - 1)
    shy_candidate = cand_names[shy_idx]
    all_ids       = [v["id"] for v in voters]

    # ── Sincere votes ─────────────────────────────────────────────────────
    sincere_votes: Dict[int, str] = {
        v["id"]: max(sincere_utilities[v["id"]], key=lambda k: sincere_utilities[v["id"]][k])
        for v in voters
    }
    real_counts = Counter(sincere_votes.values())
    real_results: Dict[str, float] = {
        c: round(real_counts.get(c, 0) / num_voters, 4) for c in cand_names
    }
    real_winner: str = max(real_results, key=real_results.__getitem__)

    # ── Second choices for shy voters ─────────────────────────────────────
    second_choices: Dict[int, str] = {}
    for v in voters:
        vid = v["id"]
        order = sorted(sincere_utilities[vid].keys(),
                       key=lambda k: -sincere_utilities[vid][k])
        sc = next((c for c in order if c != shy_candidate),
                  cand_names[(shy_idx + 1) % len(cand_names)])
        second_choices[vid] = sc

    # ── Declared votes (with shy masking) ────────────────────────────────
    decl_rng = _random.Random(seed + 1)
    declared: Dict[int, str] = {}
    for v in voters:
        vid = v["id"]
        s   = sincere_votes[vid]
        if s == shy_candidate and decl_rng.random() < sdf:
            declared[vid] = second_choices[vid]
        else:
            declared[vid] = s

    # ── Simulate polls ────────────────────────────────────────────────────
    poll_sample_size = min(1000, num_voters)
    poll_rng         = _random.Random(seed + 2)
    poll_results_out: list[Dict[str, Any]] = []

    for n in range(num_polls):
        sample    = [poll_rng.choice(all_ids) for _ in range(poll_sample_size)]
        dec_count = Counter(declared[vid] for vid in sample)
        predicted = {c: round(dec_count.get(c, 0) / poll_sample_size, 4) for c in cand_names}
        poll_results_out.append({
            "poll_n":    n + 1,
            "predicted": predicted,
            "real":      real_results,
        })

    # ── Average poll prediction + winner ─────────────────────────────────
    avg_pred: Dict[str, float] = {
        c: round(sum(pr["predicted"][c] for pr in poll_results_out) / num_polls, 4)
        for c in cand_names
    }
    poll_winner: str = max(avg_pred, key=avg_pred.__getitem__)
    polls_wrong       = poll_winner != real_winner

    systematic_error: Dict[str, float] = {
        c: round(avg_pred[c] - real_results[c], 4) for c in cand_names
    }

    # ── Social desirability curve (analytical → exactly monotone) ─────────
    real_shy_rate  = real_results.get(shy_candidate, 0.0)
    other_cands    = [c for c in cand_names if c != shy_candidate]
    other_total    = sum(real_results.get(c, 0) for c in other_cands) or 1.0

    curve: list[Dict[str, Any]] = []
    for step in range(11):
        f               = round(step / 10, 1)
        poll_shy        = real_shy_rate * (1.0 - f)
        poll_error_f    = round(real_shy_rate - poll_shy, 4)   # = real_shy_rate × f
        poll_others     = {
            c: real_results.get(c, 0) + real_shy_rate * f * (real_results.get(c, 0) / other_total)
            for c in other_cands
        }
        poll_f          = {shy_candidate: poll_shy, **poll_others}
        poll_win_f      = max(poll_f, key=poll_f.__getitem__)
        winner_wrong_f  = 1.0 if poll_win_f != real_winner else 0.0
        curve.append({
            "factor":           f,
            "poll_error":       poll_error_f,
            "winner_wrong_pct": winner_wrong_f,
        })

    # ── Pedagogical note ──────────────────────────────────────────────────
    shy_err = abs(systematic_error.get(shy_candidate, 0.0))
    note = (
        f"Avec un facteur de désirabilité sociale de {sdf}, "
        f"le candidat '{shy_candidate}' est sous-estimé de "
        f"{round(shy_err * 100, 1)}% en moyenne dans les sondages. "
    )
    if polls_wrong:
        note += f"Les sondages prédisaient '{poll_winner}' mais '{real_winner}' a gagné."
    else:
        note += f"Malgré le biais, les sondages prédisent correctement '{real_winner}'."

    return {
        "real_winner":               real_winner,
        "poll_winner":               poll_winner,
        "polls_wrong":               polls_wrong,
        "shy_candidate":             shy_candidate,
        "poll_results":              poll_results_out,
        "systematic_error":          systematic_error,
        "real_results":              real_results,
        "avg_poll_results":          avg_pred,
        "social_desirability_curve": curve,
        "pedagogical_note":          note,
    }, 200


# ── Electoral Fatigue ─────────────────────────────────────────────────────────

def _electoral_fatigue_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /electoral-fatigue — extracted for FastAPI v2 reuse.

    Simulate electoral fatigue across repeated elections.
    P(vote | election k) = max(engaged_pct, 1 - k × fatigue_rate)  [k = 0-based]
    Engaged voters (top engaged_pct by max_utility) always participate.
    As casual voters drop out, the residual electorate drifts ideologically
    toward the engaged (more partisan) voters.
    """
    num_voters     = max(50,  min(500,  int(data.get("num_voters",          200))))
    ideology       = str(data.get("ideology",          "random"))
    seed           = int(data.get("seed",               42))
    num_elections  = max(1,   min(12,   int(data.get("num_elections",         6))))
    fatigue_rate   = max(0.0, min(0.15, float(data.get("fatigue_rate",        0.07))))
    engaged_pct    = max(0.05, min(0.5, float(data.get("engaged_voter_pct",   0.2))))
    primary_method = str(data.get("method",            "plurality"))
    cand_specs     = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ])[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, sincere_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )
    all_ids: list[int] = [v["id"] for v in voters]

    # ── Voter ideology positions (1D economy axis) ────────────────────────
    voter_ideo: Dict[int, float] = {
        v["id"]: round(2.0 * v["issue_positions"].get("economy", 0.5) - 1.0, 3)
        for v in voters
    }
    full_mean_ideo = round(sum(voter_ideo.values()) / num_voters, 4)

    # ── Engaged voters = top engaged_pct by max_utility ──────────────────
    voter_max_util: Dict[int, float] = {
        v["id"]: max(sincere_utilities[v["id"]].values()) for v in voters
    }
    n_engaged      = max(1, round(engaged_pct * num_voters))
    engaged_ids: set = set(
        sorted(all_ids, key=lambda vid: -voter_max_util[vid])[:n_engaged]
    )
    partisan_threshold = 0.7  # "very partisan" label
    partisan_ids: set = {vid for vid, mu in voter_max_util.items() if mu > partisan_threshold}

    # ── Fast winner per method ────────────────────────────────────────────
    from api.engine.utils.simulation_ranked_utils import (
        get_borda_winner   as _bw,
        get_irv_winner     as _iw,
        get_schulze_winner as _sw,
    )

    def _fast_winner(vlist: list[Dict[str, Any]]) -> tuple[Optional[str], Dict[str, float]]:
        if not vlist:
            return cand_names[0], {c: 0.0 for c in cand_names}
        rnk = [
            sorted(sincere_utilities[v["id"]].keys(),
                   key=lambda n: -sincere_utilities[v["id"]][n])
            for v in vlist
        ]
        if primary_method == "borda":
            w: Optional[str] = _bw(rnk)
        elif primary_method == "irv":
            w = _iw(rnk)
        elif primary_method == "schulze":
            w = _sw(rnk)
        elif primary_method == "approval":
            tally: Counter = Counter()
            for v in vlist:
                u  = sincere_utilities[v["id"]]
                th = sum(u.values()) / len(u) if u else 0.5
                for cname, val in u.items():
                    if val > th:
                        tally[cname] += 1
            w = max(tally, key=tally.__getitem__) if tally else cand_names[0]
        else:
            w = get_plurality_winner(rnk)
        total  = len(vlist)
        fc     = Counter(r[0] for r in rnk)
        shares = {c: round(fc.get(c, 0) / total, 4) for c in cand_names}
        return w, shares

    # ── Simulate successive elections ─────────────────────────────────────
    rng_fat = _random.Random(seed + 500)
    elections_out: list[Dict[str, Any]] = []

    for k in range(num_elections):
        p_vote = max(engaged_pct, 1.0 - k * fatigue_rate)

        actual_voters = [
            v for v in voters
            if v["id"] in engaged_ids or rng_fat.random() < p_vote
        ]
        n_act   = len(actual_voters)
        turnout = round(n_act / num_voters, 4)
        winner, vote_shares = _fast_winner(actual_voters)

        if actual_voters:
            act_ids   = [v["id"] for v in actual_voters]
            mean_ideo = round(sum(voter_ideo[vid] for vid in act_ids) / n_act, 4)
            part_cnt  = sum(1 for vid in act_ids if vid in partisan_ids)
            part_pct  = round(part_cnt / n_act, 4)
        else:
            mean_ideo = 0.0
            part_pct  = 0.0

        elections_out.append({
            "election_n": k + 1,
            "turnout":    turnout,
            "winner":     winner,
            "voter_profile": {
                "mean_ideology_x": mean_ideo,
                "partisan_pct":    part_pct,
            },
            "vote_shares": vote_shares,
        })

    # ── Summary stats ─────────────────────────────────────────────────────
    winner_drift = [e["winner"] for e in elections_out]
    first_winner = winner_drift[0] if winner_drift else cand_names[0]
    winner_changed_at: Optional[int] = next(
        (e["election_n"] for e in elections_out if e["winner"] != first_winner),
        None,
    )

    first_ideo = elections_out[0]["voter_profile"]["mean_ideology_x"] if elections_out else 0.0
    last_ideo  = elections_out[-1]["voter_profile"]["mean_ideology_x"] if elections_out else 0.0
    ideology_drift    = round(last_ideo - first_ideo, 4)
    representation_gap = round(last_ideo - full_mean_ideo, 4)

    note = (
        f"Au bout de {num_elections} élections avec un taux de fatigue de "
        f"{round(fatigue_rate * 100)}%, la participation tombe à "
        f"{round(elections_out[-1]['turnout'] * 100, 1)}%. "
        f"La position idéologique moyenne des votants dérive de "
        f"{ideology_drift:+.3f} par rapport à la 1ère élection "
        f"(écart de représentation : {representation_gap:+.3f})."
    )

    return {
        "elections":             elections_out,
        "winner_drift":          winner_drift,
        "winner_changed_at":     winner_changed_at,
        "ideology_drift":        ideology_drift,
        "representation_gap":    representation_gap,
        "full_mean_ideology":    full_mean_ideo,
        "pedagogical_note":      note,
    }, 200


# ── Choice Overload ───────────────────────────────────────────────────────────

def _choice_overload_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /choice-overload — extracted for FastAPI v2 reuse."""
    num_voters         = max(50,  min(300, int(data.get("num_voters",         150))))
    ideology           = str(data.get("ideology",         "random"))
    seed               = int(data.get("seed",              42))
    cand_counts        = sorted({max(2, min(15, n)) for n in
                                 data.get("candidate_counts", [2, 3, 5, 7, 10])})[:8]
    overload_threshold = max(2,   min(12, int(data.get("overload_threshold",    5))))
    hw                 = data.get("heuristic_weights", {})
    h_not              = max(0.0, min(1.0, float(hw.get("notoriety",  0.20))))
    h_pri              = max(0.0, min(1.0, float(hw.get("primacy",    0.10))))
    h_par              = max(0.0, min(1.0, float(hw.get("partisan",   0.20))))
    total_h            = min(1.0, h_not + h_pri + h_par)
    # Pydantic Optional[List[str]] may pass null — fall back to the default.
    methods_req        = (data.get("methods") or ["plurality", "approval",
                                                   "borda", "majority_judgment"])[:5]

    if not cand_counts:
        return {"error": "candidate_counts must be non-empty"}, 400

    from api.engine.utils.simulation_score_utils import get_majority_judgment_winner as _mj_co
    from api.engine.utils.simulation_ranked_utils import (
        get_borda_winner   as _bw_co,
        get_irv_winner     as _iw_co,
        get_schulze_winner as _sw_co,
    )

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    # ── Fixed electorate (voters same across all N) ───────────────────────
    voters = [
        create_voter(issues, i, ideology_distribution=ideology)
        for i in range(num_voters)
    ]
    voter_ideo: Dict[int, float] = {
        v["id"]: 2.0 * v["issue_positions"].get("economy", 0.5) - 1.0
        for v in voters
    }

    def _quick_winner_co(
        method: str,
        v_list: list[Dict[str, Any]],
        rnk:    list[list[str]],
        utils:  Dict[Any, Dict[str, float]],
        voted:  Dict[int, str],
        is_h:   Dict[int, bool],
        cnames: list[str],
    ) -> Optional[str]:
        if not v_list:
            return cnames[0] if cnames else None
        if method == "plurality":
            t: Counter = Counter(voted[v["id"]] for v in v_list)
            return max(t, key=t.__getitem__) if t else cnames[0]
        if method == "borda":
            return _bw_co(rnk)
        if method == "irv":
            return _iw_co(rnk)
        if method == "schulze":
            return _sw_co(rnk)
        if method == "approval":
            t2: Counter = Counter()
            for v in v_list:
                vid = v["id"]
                if is_h[vid]:
                    t2[voted[vid]] += 1
                else:
                    u   = utils[vid]
                    th2 = sum(u.values()) / len(u) if u else 0.5
                    for cn, val in u.items():
                        if val > th2:
                            t2[cn] += 1
            return max(t2, key=t2.__getitem__) if t2 else cnames[0]
        if method == "majority_judgment":
            mj_u = [dict(utils[v["id"]]) for v in v_list]
            try:
                r = _mj_co(mj_u)
                return str(r["winner"]) if r.get("winner") else cnames[0]
            except Exception:
                return get_plurality_winner(rnk)
        return get_plurality_winner(rnk)

    # ── Main loop across N ────────────────────────────────────────────────
    results_by_n: list[Dict[str, Any]] = []
    regret_curve: list[Dict[str, Any]] = []
    sincere_match: Dict[str, int] = {m: 0 for m in methods_req}
    n_overload_cases = 0

    for n in cand_counts:
        # Deterministic candidates for this n
        c_rng   = _random.Random(seed + n * 1000)
        c_specs = [
            {
                "name": chr(65 + i) if i < 26 else f"C{i}",
                "x":    c_rng.uniform(-1, 1),
                "y":    c_rng.uniform(-1, 1),
            }
            for i in range(n)
        ]
        cands_n  = [
            _build_candidate_from_xy(
                i, str(c_specs[i]["name"]),
                max(-1.0, min(1.0, float(str(c_specs[i]["x"])))),
                max(-1.0, min(1.0, float(str(c_specs[i]["y"])))),
                issues,
            )
            for i in range(n)
        ]
        cnames_n = [c["name"] for c in cands_n]
        cideo_n  = {c["name"]: round(2.0 * float(c["ideology_position"]) - 1.0, 3)
                    for c in cands_n}

        # Utilities (deterministic)
        utils_n: Dict[Any, Dict[str, float]] = {
            v["id"]: {c["name"]: calculate_utility(v, c, issues)["utility"]
                      for c in cands_n}
            for v in voters
        }

        # Sincere votes (argmax utility)
        sinc_vote: Dict[int, str] = {
            v["id"]: max(utils_n[v["id"]], key=lambda k: utils_n[v["id"]][k])
            for v in voters
        }

        # Heuristic assignment
        h_rng  = _random.Random(seed + n * 5000 + 777)
        voted:  Dict[int, str]  = {}
        is_h:   Dict[int, bool] = {}

        for v in voters:
            vid = v["id"]
            if n > overload_threshold:
                r = h_rng.random()
                if r < h_not:
                    voted[vid], is_h[vid] = cnames_n[0], True
                elif r < h_not + h_pri:
                    voted[vid], is_h[vid] = cnames_n[0], True
                elif r < total_h:
                    partisan_cand = min(cnames_n,
                                       key=lambda c: abs(voter_ideo[vid] - cideo_n[c]))
                    voted[vid], is_h[vid] = partisan_cand, True
                else:
                    voted[vid], is_h[vid] = sinc_vote[vid], False
            else:
                voted[vid], is_h[vid] = sinc_vote[vid], False

        heuristic_pct = round(sum(is_h.values()) / num_voters, 4)

        # Voter regret
        regrets_n = [
            max(utils_n[v["id"]].values()) - utils_n[v["id"]].get(voted[v["id"]], 0)
            for v in voters
        ]
        mean_regret = round(sum(regrets_n) / len(regrets_n), 6) if regrets_n else 0.0

        # Rankings (heuristic choice first, rest sincere)
        h_rnk: list[list[str]] = []
        s_rnk: list[list[str]] = []
        for v in voters:
            vid      = v["id"]
            sorder   = sorted(utils_n[vid].keys(), key=lambda k: -utils_n[vid][k])
            hchoice  = voted[vid]
            s_rnk.append(sorder)
            if hchoice != sorder[0]:
                h_rnk.append([hchoice] + [c for c in sorder if c != hchoice])
            else:
                h_rnk.append(sorder)

        # Run methods (heuristic vs. sincere)
        winner_by_method:      Dict[str, Optional[str]] = {}
        sinc_winner_by_method: Dict[str, Optional[str]] = {}
        s_voted = {v["id"]: sinc_vote[v["id"]] for v in voters}
        s_is_h  = {v["id"]: False for v in voters}

        for meth in methods_req:
            winner_by_method[meth]      = _quick_winner_co(meth, voters, h_rnk, utils_n, voted,   is_h,   cnames_n)
            sinc_winner_by_method[meth] = _quick_winner_co(meth, voters, s_rnk, utils_n, s_voted, s_is_h, cnames_n)
            if n > overload_threshold:
                if winner_by_method[meth] == sinc_winner_by_method[meth]:
                    sincere_match[meth] += 1

        if n > overload_threshold:
            n_overload_cases += 1

        condorcet_w = get_condorcet_winner(s_rnk)

        results_by_n.append({
            "num_candidates":        n,
            "mean_voter_regret":     mean_regret,
            "heuristic_voters":      heuristic_pct,
            "winner_by_method":      winner_by_method,
            "condorcet_winner":      condorcet_w,
            "methods_elect_condorcet": {
                m: winner_by_method[m] == condorcet_w for m in methods_req
            },
        })
        regret_curve.append({"n_candidates": n, "regret": mean_regret})

    # ── Robustness ranking ────────────────────────────────────────────────
    if n_overload_cases > 0:
        match_rates = {m: sincere_match[m] / n_overload_cases for m in methods_req}
    else:
        match_rates = {m: 1.0 for m in methods_req}

    most_robust  = max(match_rates, key=match_rates.__getitem__)
    least_robust = min(match_rates, key=match_rates.__getitem__)

    # ── Pedagogical note ──────────────────────────────────────────────────
    over_regrets = [r["regret"] for r in regret_curve
                    if r["n_candidates"] > overload_threshold]
    avg_over_regret = round(sum(over_regrets) / len(over_regrets), 4) if over_regrets else 0.0
    note = (
        f"Au-delà de {overload_threshold} candidats, "
        f"{round(total_h * 100)}% des électeurs utilisent une heuristique "
        f"(notoriété, primauté ou partisane). "
        f"Le regret moyen de vote est de {round(avg_over_regret * 100, 1)} points d'utilité. "
        f"'{most_robust}' est la méthode la plus robuste à la surcharge cognitive."
    )

    return {
        "results_by_n":         results_by_n,
        "regret_curve":         regret_curve,
        "most_robust_method":   most_robust,
        "least_robust_method":  least_robust,
        "overload_threshold":   overload_threshold,
        "heuristic_weights":    {"notoriety": h_not, "primacy": h_pri, "partisan": h_par},
        "pedagogical_note":     note,
    }, 200


# ── Demographic Turnout ───────────────────────────────────────────────────────

_AGE_LABELS  = ["jeunes (18-34)", "adultes (35-64)", "seniors (65+)"]
_EDU_LABELS  = ["faible éducation", "éducation élevée"]


def _demographic_turnout_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /demographic-turnout — extracted for FastAPI v2."""
    num_voters        = max(50,  min(500, int(data.get("num_voters",         300))))
    seed              = int(data.get("seed",              42))
    primary_method    = str(data.get("method",           "plurality"))
    correct_flag      = bool(data.get("correct_for_turnout", True))
    cand_specs        = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ])[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    # Pydantic Optional dict may pass null — fall back to empty + use field defaults.
    dp       = data.get("demographic_profile") or {}
    age_dist = [float(x) for x in (dp.get("age_distribution")    or [0.25, 0.45, 0.30])][:3]
    to_age   = [float(x) for x in (dp.get("turnout_by_age")      or [0.55, 0.70, 0.85])][:3]
    ideo_age = [float(x) for x in (dp.get("ideology_by_age")     or [-0.10, 0.00,  0.15])][:3]
    edu_dist = [float(x) for x in (dp.get("education_distribution") or [0.40, 0.60])][:2]
    to_edu   = [float(x) for x in (dp.get("turnout_by_education")   or [1.00, 1.00])][:2]
    ideo_edu = [float(x) for x in (dp.get("ideology_by_education") or [ 0.05, -0.05])][:2]

    # Normalize distributions
    sum_a = sum(age_dist) or 1.0
    age_dist = [x / sum_a for x in age_dist]
    sum_e = sum(edu_dist) or 1.0
    edu_dist = [x / sum_e for x in edu_dist]

    _random.seed(seed)
    _np.random.seed(seed)
    issues   = DEFAULT_ISSUES
    cand_names = [str(s.get("name", f"C{i}")) for i, s in enumerate(cand_specs)]
    candidates = [
        _build_candidate_from_xy(
            i, cand_names[i],
            max(-1.0, min(1.0, float(s.get("x", 0.0)))),
            max(-1.0, min(1.0, float(s.get("y", 0.0)))),
            issues,
        )
        for i, s in enumerate(cand_specs)
    ]

    # ── Generate voters with demographic attributes ────────────────────────
    demo_rng     = _random.Random(seed)
    age_cumsum   = [sum(age_dist[:k+1]) for k in range(len(age_dist))]
    edu_cumsum   = [sum(edu_dist[:k+1]) for k in range(len(edu_dist))]

    def _pick_group(rng_val: float, cumsum: list[float]) -> int:
        for i, th in enumerate(cumsum):
            if rng_val < th:
                return i
        return len(cumsum) - 1

    raw_voters = [
        create_voter(issues, i, ideology_distribution="random")
        for i in range(num_voters)
    ]

    voter_demo: Dict[int, Dict[str, Any]] = {}
    for v in raw_voters:
        ag    = _pick_group(demo_rng.random(), age_cumsum)
        eg    = _pick_group(demo_rng.random(), edu_cumsum)
        base  = demo_rng.uniform(-0.5, 0.5)
        ideo  = max(-1.0, min(1.0, base + ideo_age[ag] + ideo_edu[eg]))
        p_v   = max(0.0, min(1.0, to_age[ag] * to_edu[eg]))
        voter_demo[v["id"]] = {"age": ag, "edu": eg, "ideology": ideo, "p_vote": p_v}
        v["issue_positions"]["economy"] = (ideo + 1.0) / 2.0   # remap to [0, 1]

    # Utilities (recomputed after ideology override)
    utils: Dict[Any, Dict[str, float]] = {
        v["id"]: {c["name"]: calculate_utility(v, c, issues)["utility"] for c in candidates}
        for v in raw_voters
    }

    # ── Determine effective voters ─────────────────────────────────────────
    t_rng      = _random.Random(seed + 100)
    voted_ids: set = {
        v["id"] for v in raw_voters
        if t_rng.random() < voter_demo[v["id"]]["p_vote"]
    }
    actual_voters = [v for v in raw_voters if v["id"] in voted_ids]
    n_actual  = len(actual_voters)

    # ── Fast winner ────────────────────────────────────────────────────────
    from api.engine.utils.simulation_ranked_utils import (
        get_borda_winner   as _b_dt,
        get_irv_winner     as _i_dt,
        get_schulze_winner as _s_dt,
    )

    def _winner(vlist: list[Dict[str, Any]]) -> tuple[str, Dict[str, float]]:
        if not vlist:
            return cand_names[0], {c: 0.0 for c in cand_names}
        rnk = [sorted(utils[v["id"]].keys(), key=lambda n: -utils[v["id"]][n]) for v in vlist]
        if primary_method == "borda":
            w: Optional[str] = _b_dt(rnk)
        elif primary_method == "irv":
            w = _i_dt(rnk)
        elif primary_method == "schulze":
            w = _s_dt(rnk)
        else:
            w = get_plurality_winner(rnk)
        total  = len(vlist)
        fc     = Counter(r[0] for r in rnk)
        shares = {c: round(fc.get(c, 0) / total, 4) for c in cand_names}
        return w or cand_names[0], shares

    biased_winner,    biased_shares    = _winner(actual_voters)
    corrected_winner, corrected_shares = _winner(raw_voters) if correct_flag else (biased_winner, biased_shares)
    winner_changed = biased_winner != corrected_winner

    # ── Ideology stats ─────────────────────────────────────────────────────
    full_mean = round(sum(voter_demo[v["id"]]["ideology"] for v in raw_voters)   / num_voters,  4)
    bias_mean = round(sum(voter_demo[v["id"]]["ideology"] for v in actual_voters) / n_actual,    4) if n_actual else 0.0
    ideo_drift = round(bias_mean - full_mean, 4)

    # ── Demographic breakdown (3 age × 2 edu groups) ─────────────────────
    grp_pop: Dict[tuple, int]   = {}
    grp_vot: Dict[tuple, int]   = {}
    grp_ideo: Dict[tuple, list] = {}
    for v in raw_voters:
        d   = voter_demo[v["id"]]
        key = (d["age"], d["edu"])
        grp_pop[key]  = grp_pop.get(key, 0) + 1
        if v["id"] in voted_ids:
            grp_vot[key]  = grp_vot.get(key, 0) + 1
            grp_ideo.setdefault(key, []).append(d["ideology"])

    breakdown: list[Dict[str, Any]] = []
    for ag in range(len(age_dist)):
        for eg in range(len(edu_dist)):
            key       = (ag, eg)
            pop_cnt   = grp_pop.get(key, 0)
            vot_cnt   = grp_vot.get(key, 0)
            ideo_vals = grp_ideo.get(key, [])
            breakdown.append({
                "group":          f"{_AGE_LABELS[ag]}, {_EDU_LABELS[eg]}",
                "population_pct": round(pop_cnt / num_voters,        4),
                "voter_pct":      round(vot_cnt / n_actual,          4) if n_actual else 0.0,
                "ideology_mean":  round(sum(ideo_vals) / len(ideo_vals), 4) if ideo_vals else 0.0,
            })

    overrep  = [d["group"] for d in breakdown if d["voter_pct"] > d["population_pct"] + 0.05]
    underrep = [d["group"] for d in breakdown if d["voter_pct"] < d["population_pct"] - 0.05]

    note = (
        f"Avec les taux de participation configurés, "
        f"l'électorat effectif ({round(n_actual/num_voters*100, 1)}% de participation) "
        f"est décalé de {ideo_drift:+.3f} sur l'axe idéologique par rapport à la population totale. "
    )
    if winner_changed:
        note += f"Si tous votaient, le résultat serait différent : '{biased_winner}' → '{corrected_winner}'."
    else:
        note += f"La méthode produit le même vainqueur ('{biased_winner}') malgré le biais de participation."

    # ── Per-method winners for both voter subsets ─────────────────────────
    try:
        bias_compare = compare_all_methods(actual_voters, candidates, issues)
        full_compare = compare_all_methods(raw_voters,    candidates, issues)
        biased_winners_by_method = {
            m: d.get("winner") for m, d in bias_compare.get("methods", {}).items()
        }
        corrected_winners_by_method = {
            m: d.get("winner") for m, d in full_compare.get("methods", {}).items()
        }
    except Exception:  # pylint: disable=broad-except
        biased_winners_by_method = {}
        corrected_winners_by_method = {}

    return {
        "biased_result": {
            "winner":         biased_winner,
            "vote_shares":    biased_shares,
            "actual_turnout": round(n_actual / num_voters, 4),
            "voter_profile": {
                "mean_age_group":       round(sum(voter_demo[v["id"]]["age"] for v in actual_voters) / n_actual, 4) if n_actual else 0.0,
                "mean_education_level": round(sum(voter_demo[v["id"]]["edu"] for v in actual_voters) / n_actual, 4) if n_actual else 0.0,
                "mean_ideology_x":      bias_mean,
            },
            "winners_by_method": biased_winners_by_method,
        },
        "corrected_result": {
            "winner":         corrected_winner,
            "vote_shares":    corrected_shares,
            "mean_ideology_x": full_mean,
            "winners_by_method": corrected_winners_by_method,
        },
        "winner_changed":      winner_changed,
        "representation_gap": {
            "ideology_drift":          ideo_drift,
            "overrepresented_groups":  overrep,
            "underrepresented_groups": underrep,
        },
        "demographic_breakdown": breakdown,
        "pedagogical_note":      note,
    }, 200


# ── Compulsory Voting ─────────────────────────────────────────────────────────

_COMPULSORY_BIAS = 0.15   # rightward participation bias in voluntary elections


def _compulsory_voting_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /compulsory-voting — extracted for FastAPI v2.

    Simulate voluntary vs. compulsory voting on the same electorate.
    Voluntary turnout is right-biased (empirical pattern: conservative voters
    participate more), while compulsory elections add reluctant left-leaning
    voters who may vote null, randomly, or sincerely.
    """
    num_voters   = max(50,  min(500, int(data.get("num_voters",          300))))
    ideology     = str(data.get("ideology",           "random"))
    seed         = int(data.get("seed",                42))
    vol_to       = max(0.30, min(0.90, float(data.get("voluntary_turnout",   0.65))))
    comp_to      = max(0.70, min(0.99, float(data.get("compulsory_turnout",  0.92))))
    rel_null     = max(0.00, min(0.20, float(data.get("reluctant_null_rate",  0.04))))
    rel_rnd      = max(0.00, min(1.00, float(data.get("reluctant_random_pct", 0.08))))
    primary_method = str(data.get("method", "plurality"))
    cand_specs   = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ])[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, sincere_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )
    all_ids: list[int] = [v["id"] for v in voters]

    voter_ideo:     Dict[int, float] = {
        v["id"]: round(2.0 * v["issue_positions"].get("economy", 0.5) - 1.0, 3)
        for v in voters
    }
    voter_max_util: Dict[int, float] = {
        v["id"]: max(sincere_utilities[v["id"]].values()) for v in voters
    }
    full_mean_ideo = round(sum(voter_ideo.values()) / num_voters, 4)

    # ── Participation scores (fixed per seed) ─────────────────────────────
    part_rng = _random.Random(seed)
    part_score: Dict[int, float] = {v["id"]: part_rng.random() for v in voters}

    # Voluntary: right-leaning voters have higher effective threshold
    # Compulsory: same bias, higher base threshold
    voluntary_ids:  set = {
        vid for vid, sc in part_score.items()
        if sc < vol_to + _COMPULSORY_BIAS * voter_ideo[vid]
    }
    compulsory_ids: set = {
        vid for vid, sc in part_score.items()
        if sc < comp_to + _COMPULSORY_BIAS * voter_ideo[vid]
    }
    reluctant_ids: set = compulsory_ids - voluntary_ids

    # ── Sincere votes ─────────────────────────────────────────────────────
    sincere_vote: Dict[int, str] = {
        v["id"]: max(sincere_utilities[v["id"]], key=lambda k: sincere_utilities[v["id"]][k])
        for v in voters
    }

    # ── Compulsory vote assignment ────────────────────────────────────────
    _NULL  = "__NULL__"
    noise_rng   = _random.Random(seed + 200)
    comp_vote:  Dict[int, str] = {}
    null_count  = 0
    rnd_count   = 0

    for vid in compulsory_ids:
        if vid in reluctant_ids:
            r = noise_rng.random()
            if r < rel_null:
                comp_vote[vid] = _NULL
                null_count += 1
            elif r < rel_null + rel_rnd:
                comp_vote[vid] = noise_rng.choice(cand_names)
                rnd_count += 1
            else:
                comp_vote[vid] = sincere_vote[vid]
        else:
            comp_vote[vid] = sincere_vote[vid]

    # ── Election runner (plurality) ───────────────────────────────────────
    def _run(vote_dict: Dict[int, str], voter_set: set) -> tuple[str, Dict[str, float], float]:
        tally: Counter = Counter()
        n_null = sum(1 for vid in voter_set if vote_dict.get(vid, _NULL) == _NULL)
        for vid in voter_set:
            v = vote_dict.get(vid, sincere_vote[vid])
            if v != _NULL:
                tally[v] += 1
        n_valid = len(voter_set) - n_null
        winner  = max(tally, key=tally.__getitem__) if tally else cand_names[0]
        shares  = {
            c: round(tally.get(c, 0) / n_valid, 4) if n_valid else 0.0
            for c in cand_names
        }
        return winner, shares, round(n_null / len(voter_set), 4) if voter_set else 0.0

    vol_vote = {vid: sincere_vote[vid] for vid in voluntary_ids}
    vol_winner,  vol_shares,  vol_null  = _run(vol_vote, voluntary_ids)
    comp_winner, comp_shares, comp_null = _run(comp_vote, compulsory_ids)
    winner_changed = vol_winner != comp_winner

    # ── Statistics ────────────────────────────────────────────────────────
    n_vol  = len(voluntary_ids)
    n_comp = len(compulsory_ids)
    n_rel  = len(reluctant_ids)

    vol_mean  = round(sum(voter_ideo[vid] for vid in voluntary_ids)  / n_vol,  4) if n_vol  else 0.0
    comp_mean = round(sum(voter_ideo[vid] for vid in compulsory_ids) / n_comp, 4) if n_comp else 0.0

    vol_drift  = abs(vol_mean  - full_mean_ideo)
    comp_drift = abs(comp_mean - full_mean_ideo)
    representation_improvement = round(max(0.0, vol_drift - comp_drift), 4)

    n_valid_comp = n_comp - null_count
    noise_effect     = round(rnd_count / n_valid_comp, 4)  if n_valid_comp else 0.0
    quality_degradation = noise_effect

    partisan_thr = 0.7
    vol_partisan = sum(1 for vid in voluntary_ids if voter_max_util[vid] > partisan_thr)

    note = (
        f"Le vote obligatoire augmente la participation de "
        f"{round(n_vol/num_voters*100, 1)}% à {round(n_comp/num_voters*100, 1)}%, "
        f"ajoutant {n_rel} électeurs réticents. "
        f"Représentativité améliorée de {representation_improvement:.3f}, "
        f"mais {round(quality_degradation*100, 1)}% des votes compulsoires sont du bruit aléatoire."
    )

    # ── Per-method winners for both voter subsets (for central matrix diff) ──
    try:
        vol_voters  = [v for v in voters if v["id"] in voluntary_ids]
        comp_voters = [v for v in voters if v["id"] in compulsory_ids]
        vol_compare  = compare_all_methods(vol_voters,  candidates, issues)
        comp_compare = compare_all_methods(comp_voters, candidates, issues)
        vol_winners_by_method = {
            m: d.get("winner") for m, d in vol_compare.get("methods", {}).items()
        }
        comp_winners_by_method = {
            m: d.get("winner") for m, d in comp_compare.get("methods", {}).items()
        }
    except Exception:  # pylint: disable=broad-except
        vol_winners_by_method = {}
        comp_winners_by_method = {}

    return {
        "voluntary": {
            "turnout":     round(n_vol  / num_voters, 4),
            "winner":      vol_winner,
            "vote_shares": vol_shares,
            "null_rate":   vol_null,
            "voter_profile": {
                "mean_ideology_x": vol_mean,
                "partisan_pct":    round(vol_partisan / n_vol, 4) if n_vol else 0.0,
            },
            "winners_by_method": vol_winners_by_method,
        },
        "compulsory": {
            "turnout":          round(n_comp / num_voters, 4),
            "winner":           comp_winner,
            "vote_shares":      comp_shares,
            "null_rate":        comp_null,
            "reluctant_count":  n_rel,
            "noise_effect":     noise_effect,
            "winners_by_method": comp_winners_by_method,
        },
        "winner_changed":             winner_changed,
        "representation_improvement": representation_improvement,
        "quality_degradation":        quality_degradation,
        "pedagogical_note":           note,
    }, 200


# ── Sortition (tirage au sort) ────────────────────────────────────────────────

import math as _math


def _sortition_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /sortition — extracted for FastAPI v2 reuse."""
    num_voters      = max(50,  min(500, int(data.get("num_voters",        300))))
    assembly_size   = max(5,   min(300, int(data.get("assembly_size",      50))))
    ideology        = str(data.get("ideology",          "random"))
    seed            = int(data.get("seed",               42))
    primary_method  = str(data.get("method",            "plurality"))
    num_sims        = max(5,   min(100, int(data.get("num_simulations",   20))))
    realistic_cands = bool(data.get("realistic_candidates", True))
    cand_specs      = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ])[:6]

    # Pydantic may pass null for the whole stratification object — guard.
    strat_cfg   = data.get("stratification") or {}
    age_dist_raw = strat_cfg.get("age_groups") or [0.25, 0.45, 0.30]
    gender_par  = bool(strat_cfg.get("gender_parity", True))
    edu_quota   = bool(strat_cfg.get("education_quota", True))

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, sincere_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )
    all_ids: list[int] = [v["id"] for v in voters]

    # ── Voter ideology + demographics ─────────────────────────────────────
    voter_ideo: Dict[int, float] = {
        v["id"]: round(2.0 * v["issue_positions"].get("economy", 0.5) - 1.0, 3)
        for v in voters
    }
    voter_max_util: Dict[int, float] = {
        v["id"]: max(sincere_utilities[v["id"]].values()) for v in voters
    }
    full_mean_ideo = round(sum(voter_ideo.values()) / num_voters, 4)

    # Demographics (for stratified sortition)
    d_rng = _random.Random(seed + 50)
    age_sum  = sum(age_dist_raw) or 1.0
    age_dist = [x / age_sum for x in age_dist_raw[:3]]
    age_cum  = [sum(age_dist[:k+1]) for k in range(len(age_dist))]

    def _age_group(r: float) -> int:
        for i, th in enumerate(age_cum):
            if r < th:
                return i
        return len(age_cum) - 1

    voter_age: Dict[int, int] = {v["id"]: _age_group(d_rng.random()) for v in voters}
    voter_edu: Dict[int, int] = {v["id"]: (0 if d_rng.random() < 0.40 else 1) for v in voters}
    voter_gen: Dict[int, int] = {v["id"]: (0 if d_rng.random() < 0.50 else 1) for v in voters}

    # ── Metric helpers ────────────────────────────────────────────────────
    def _representativity(asm: set) -> float:
        if not asm:
            return 0.0
        mean = sum(voter_ideo[vid] for vid in asm) / len(asm)
        return round(max(0.0, 1.0 - 2.0 * abs(mean - full_mean_ideo)), 4)

    def _diversity(asm: set) -> float:
        if not asm:
            return 0.0
        ideos = [voter_ideo[vid] for vid in asm]
        bins  = [-1.0, -0.5, 0.0, 0.5, 1.01]
        counts = [0] * 4
        for ideo in ideos:
            for i in range(4):
                if bins[i] <= ideo < bins[i + 1]:
                    counts[i] += 1
                    break
        n  = len(ideos)
        ps = [c / n for c in counts if c > 0]
        if len(ps) <= 1:
            return 0.0
        ent = -sum(p * _math.log(p) for p in ps)
        return round(ent / _math.log(4), 4)

    def _decision_regret(asm: set) -> float:
        if not asm:
            return 0.0
        asm_mean = sum(voter_ideo[vid] for vid in asm) / len(asm)
        return round(
            sum(abs(voter_ideo[vid] - asm_mean) for vid in all_ids) / num_voters, 4
        )

    def _gini_repr(asm: set) -> float:
        if not asm:
            return 0.0
        pop_s = sorted(voter_ideo.values())
        q     = max(1, num_voters // 4)
        bounds = [pop_s[0], pop_s[q], pop_s[2 * q], pop_s[3 * q], pop_s[-1] + 0.01]
        ideos  = [voter_ideo[vid] for vid in asm]
        n_asm  = len(ideos)
        ratios = []
        for i in range(4):
            af = sum(1 for x in ideos if bounds[i] <= x < bounds[i + 1]) / n_asm
            ratios.append(af / 0.25)
        s  = sorted(ratios)
        tot = sum(s) or 1.0
        cs  = sum((i + 1) * v for i, v in enumerate(s))
        return round(abs(2.0 * cs / (4 * tot) - (4 + 1) / 4), 4)

    def _asm_metrics(asm: set) -> Dict[str, Any]:
        n = len(asm)
        if n == 0:
            return {k: 0.0 for k in ("members_ideology_mean", "representativity",
                                      "diversity", "decision_regret", "gini_representation")}
        mean_ideo = round(sum(voter_ideo[vid] for vid in asm) / n, 4)
        return {
            "members_ideology_mean": mean_ideo,
            "representativity":      _representativity(asm),
            "diversity":             _diversity(asm),
            "decision_regret":       _decision_regret(asm),
            "gini_representation":   _gini_repr(asm),
            "demographic_profile": {
                "age":       round(sum(voter_age[vid] for vid in asm) / n, 4),
                "education": round(sum(voter_edu[vid] for vid in asm) / n, 4),
            },
        }

    # ── Assembly constructors ─────────────────────────────────────────────
    def _elected_asm(rng: _random.Random) -> set:
        cand_n = min(assembly_size * 3, num_voters)
        if realistic_cands:
            # Add noise so each MC run gets a slightly different candidate pool
            noisy_scores = {
                vid: abs(voter_ideo[vid]) + rng.uniform(0, 0.25)
                for vid in all_ids
            }
            pool_sorted = sorted(all_ids, key=lambda vid: -noisy_scores[vid])
            pool = set(pool_sorted[:cand_n])
        else:
            pool = set(rng.sample(all_ids, cand_n))

        tally: Counter = Counter()
        for vid in all_ids:
            closest = min(pool, key=lambda cid: abs(voter_ideo[vid] - voter_ideo[cid]))
            tally[closest] += 1

        elected = sorted(pool, key=lambda cid: -tally[cid])[:assembly_size]
        return set(elected)

    def _pure_asm(rng: _random.Random) -> set:
        return set(rng.sample(all_ids, min(assembly_size, num_voters)))

    def _stratified_asm(rng: _random.Random) -> set:
        age_targets = [max(1, round(p * assembly_size)) for p in age_dist]
        while sum(age_targets) > assembly_size:
            age_targets[age_targets.index(max(age_targets))] -= 1
        while sum(age_targets) < assembly_size:
            age_targets[age_targets.index(min(age_targets))] += 1

        result: list[int] = []
        for ag in range(len(age_dist)):
            n_ag = age_targets[ag]
            pool_ag = [vid for vid in all_ids if voter_age[vid] == ag]
            if not pool_ag:
                continue

            if edu_quota:
                n_low  = max(1, round(0.40 * n_ag))
                n_high = n_ag - n_low
                pool_low  = [vid for vid in pool_ag if voter_edu[vid] == 0]
                pool_high = [vid for vid in pool_ag if voter_edu[vid] == 1]
                result.extend(rng.sample(pool_low,  min(n_low,  len(pool_low))))
                result.extend(rng.sample(pool_high, min(n_high, len(pool_high))))
            else:
                result.extend(rng.sample(pool_ag, min(n_ag, len(pool_ag))))

        # Fill gap
        remaining = [vid for vid in all_ids if vid not in set(result)]
        while len(result) < assembly_size and remaining:
            pick = rng.choice(remaining)
            result.append(pick)
            remaining.remove(pick)
        return set(result[:assembly_size])

    # ── Main assembly run ─────────────────────────────────────────────────
    main_rng = _random.Random(seed + 100)
    elected_ids    = _elected_asm(_random.Random(seed))
    pure_ids       = _pure_asm(main_rng)
    stratified_ids = _stratified_asm(_random.Random(seed + 200))

    assemblies = {
        "elected":             _asm_metrics(elected_ids),
        "sortition_pure":      _asm_metrics(pure_ids),
        "sortition_stratified": _asm_metrics(stratified_ids),
    }

    # ── Winner by assembly ────────────────────────────────────────────────
    def _asm_winner(asm: set) -> Optional[str]:
        rnk = [
            sorted(sincere_utilities[vid].keys(), key=lambda k: -sincere_utilities[vid][k])
            for vid in asm
        ]
        return get_plurality_winner(rnk) if rnk else cand_names[0]

    winner_by_method = {
        "elected":             _asm_winner(elected_ids),
        "sortition_pure":      _asm_winner(pure_ids),
        "sortition_stratified": _asm_winner(stratified_ids),
    }
    consensus_possible = len(set(winner_by_method.values())) == 1

    # ── Monte Carlo variance ──────────────────────────────────────────────
    mc_elected:    list[float] = []
    mc_pure:       list[float] = []
    mc_stratified: list[float] = []

    for sim_i in range(num_sims):
        r = _random.Random(seed + 1000 + sim_i)
        def _mean_ideo(asm: set) -> float:
            return sum(voter_ideo[vid] for vid in asm) / len(asm) if asm else 0.0
        mc_elected.append(_mean_ideo(_elected_asm(r)))
        mc_pure.append(_mean_ideo(_pure_asm(_random.Random(seed + 2000 + sim_i))))
        mc_stratified.append(_mean_ideo(_stratified_asm(_random.Random(seed + 3000 + sim_i))))

    def _var(xs: list[float]) -> float:
        if len(xs) < 2:
            return 0.0
        return round(float(_np.var(xs)), 6)

    variance = {
        "elected":              _var(mc_elected),
        "sortition_pure":       _var(mc_pure),
        "sortition_stratified": _var(mc_stratified),
    }

    # ── Pedagogical note ──────────────────────────────────────────────────
    rep_elected = assemblies["elected"]["representativity"]
    rep_pure    = assemblies["sortition_pure"]["representativity"]
    note = (
        f"Avec {assembly_size} sièges et profil candidats "
        f"{'réaliste' if realistic_cands else 'neutre'}, "
        f"l'assemblée élue a une représentativité de {rep_elected:.2f} "
        f"contre {rep_pure:.2f} pour le tirage au sort pur. "
        f"{'Consensus atteint' if consensus_possible else 'Pas de consensus'} "
        f"entre les 3 modes de sélection."
    )

    return {
        "population": {
            "mean_ideology": full_mean_ideo,
            "gini_ideology": round(float(_np.std([voter_ideo[vid] for vid in all_ids])), 4),
            "demographics":  {
                "mean_age_group":       round(sum(voter_age.values()) / num_voters, 4),
                "mean_education_level": round(sum(voter_edu.values()) / num_voters, 4),
            },
        },
        "assemblies":         assemblies,
        "variance":           variance,
        "winner_by_method":   winner_by_method,
        "consensus_possible": consensus_possible,
        "pedagogical_note":   note,
    }, 200


# ── Party Dynamics ────────────────────────────────────────────────────────────

def _party_dynamics_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /party-dynamics — extracted for FastAPI v2.

    Simulate multi-election party system evolution (Duverger's Law).
    """
    import copy as _cp

    num_voters    = max(100, min(1000, int(data.get("num_voters",        500))))
    ideology      = str(data.get("ideology",                "random"))
    seed          = int(data.get("seed",                     42))
    num_elections = max(1,  min(30,  int(data.get("num_elections",       10))))
    method        = str(data.get("method",                  "plurality"))
    surv_thr      = max(0.01, min(0.20, float(data.get("survival_threshold",   0.05))))
    emerge_prob   = max(0.00, min(1.00, float(data.get("emergence_probability", 0.10))))
    hotelling_a   = max(0.00, min(1.00, float(data.get("hotelling_adaptation",  0.10))))
    tactical_on   = bool(data.get("tactical_voting", True))
    # Pydantic Optional may pass null — fall back to the server default.
    initial_pts   = (data.get("initial_parties") or [
        {"name": "A", "x": -0.8, "y":  0.0, "support_pct": 0.10},
        {"name": "B", "x": -0.3, "y":  0.0, "support_pct": 0.25},
        {"name": "C", "x":  0.1, "y":  0.0, "support_pct": 0.30},
        {"name": "D", "x":  0.5, "y":  0.0, "support_pct": 0.25},
        {"name": "E", "x":  0.9, "y":  0.0, "support_pct": 0.10},
    ])[:10]

    if len(initial_pts) < 2:
        return {"error": "At least 2 initial parties required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)

    # ── Voter ideology (fixed across all elections) ───────────────────────
    if ideology == "polarized":
        h = num_voters // 2
        voter_x = _np.clip(
            _np.concatenate([_np.random.normal(-0.6, 0.2, h),
                             _np.random.normal( 0.6, 0.2, num_voters - h)]),
            -1.0, 1.0,
        )
    elif ideology == "normal":
        voter_x = _np.clip(_np.random.normal(0, 0.3, num_voters), -1.0, 1.0)
    else:
        voter_x = _np.random.uniform(-1.0, 1.0, num_voters)

    voter_median = float(_np.median(voter_x))

    # ── Active parties (mutable state) ───────────────────────────────────
    active: list[Dict[str, Any]] = [
        {
            "name":        str(p.get("name", f"P{i}")),
            "x":           max(-1.0, min(1.0, float(p.get("x", 0.0)))),
            "y":           max(-1.0, min(1.0, float(p.get("y", 0.0)))),
            "poll":        max(0.0,  float(p.get("support_pct", 1 / len(initial_pts)))),
        }
        for i, p in enumerate(initial_pts)
    ]
    # Normalize polls
    poll_total = sum(p["poll"] for p in active) or 1.0
    for p in active:
        p["poll"] /= poll_total

    initial_positions: Dict[str, float] = {p["name"]: p["x"] for p in active}
    party_counter      = len(active)
    rng                = _random.Random(seed + 1)
    all_elections: list[Dict[str, Any]] = []
    n_eff_curve: list[float] = []
    tactical_methods = {"plurality", "two_round", "irv"}

    # ── Vote-share helper ─────────────────────────────────────────────────
    def _vote_shares(parties: list, polls: Dict[str, float]) -> Dict[str, float]:
        pxs = _np.array([p["x"] for p in parties])
        dists = _np.abs(voter_x[:, None] - pxs[None, :])   # (N, K)
        nearest = _np.argmin(dists, axis=1)

        apply_tac = tactical_on and method in tactical_methods
        if apply_tac:
            viable = _np.array([polls.get(p["name"], 0) >= 2 * surv_thr
                                 for p in parties])
            if viable.any() and not viable.all():
                masked = dists.copy()
                masked[:, ~viable] = 1e9
                tac_nearest = _np.argmin(masked, axis=1)
                mask = ~viable[nearest]
                nearest[mask] = tac_nearest[mask]

        counts = _np.bincount(nearest, minlength=len(parties))
        return {p["name"]: float(counts[i] / num_voters) for i, p in enumerate(parties)}

    # ── Gap finder for party emergence ────────────────────────────────────
    def _find_gap(pxs: list) -> float:
        cands = _np.linspace(-1.0, 1.0, 60)
        best_x, best_gap = 0.0, 0.0
        for cx in cands:
            g = min(abs(float(cx) - px) for px in pxs)
            if g > best_gap:
                best_gap, best_x = g, float(cx)
        return round(best_x, 2)

    # ── N_eff ─────────────────────────────────────────────────────────────
    def _n_eff(shares: Dict[str, float]) -> float:
        s = sum(v ** 2 for v in shares.values() if v > 0)
        return round(1.0 / s, 4) if s > 0 else 1.0

    # ── Simulation loop ───────────────────────────────────────────────────
    for k in range(num_elections):
        polls_dict = {p["name"]: p["poll"] for p in active}
        shares     = _vote_shares(active, polls_dict)
        n_eff      = _n_eff(shares)
        n_eff_curve.append(n_eff)

        winner = max(shares, key=shares.__getitem__) if shares else ""

        parties_snap = [
            {
                "name":     p["name"],
                "x":        round(p["x"], 4),
                "y":        round(p["y"], 4),
                "vote_pct": round(shares.get(p["name"], 0) * 100, 2),
                "seats":    round(shares.get(p["name"], 0) * 100),
                "survived": shares.get(p["name"], 0) >= surv_thr,
            }
            for p in active
        ]

        # Record before elimination
        all_elections.append({
            "election_n":        k + 1,
            "active_parties":    len(active),
            "parties":           parties_snap,
            "effective_parties": n_eff,
            "winner":            winner,
            "new_entrants":      [],   # filled in next iteration
            "eliminated":        [],   # filled below
        })

        # Eliminate
        eliminated = [p["name"] for p in active
                      if shares.get(p["name"], 0) < surv_thr]
        all_elections[-1]["eliminated"] = eliminated
        active = [p for p in active if shares.get(p["name"], 0) >= surv_thr]

        # Update polls
        for p in active:
            p["poll"] = shares.get(p["name"], 0)

        if not active:
            break

        # Hotelling adaptation
        for p in active:
            p["x"] = round(p["x"] + hotelling_a * (voter_median - p["x"]), 4)
            p["y"] = round(p["y"] + hotelling_a * (0.0 - p["y"]), 4)

        # Party emergence
        new_entrants: list[str] = []
        if emerge_prob > 0 and rng.random() < emerge_prob:
            gap_x = _find_gap([p["x"] for p in active])
            party_counter += 1
            new_name = f"Nouveau-{party_counter}"
            new_party: Dict[str, Any] = {
                "name": new_name, "x": gap_x, "y": 0.0, "poll": surv_thr * 1.5,
            }
            active.append(new_party)
            new_entrants.append(new_name)
            initial_positions[new_name] = gap_x

        if k + 1 < len(all_elections):
            all_elections[k + 1]["new_entrants"] = new_entrants
        else:
            # Mark on the NEXT election (we just finished election k)
            pass
        if new_entrants and k < num_elections - 1:
            all_elections[-1]["new_entrants"] = new_entrants

    # ── Summary ───────────────────────────────────────────────────────────
    n_eff_final = n_eff_curve[-1] if n_eff_curve else 1.0
    if n_eff_final < 2.5:
        final_system = "bipartite"
    elif n_eff_final < 4.0:
        final_system = "tripartite"
    else:
        final_system = "fragmented"

    duverger_confirmed = (method in ("plurality", "two_round")) and (n_eff_final < 2.5)

    convergence_speed: Optional[int] = None
    for i, nef in enumerate(n_eff_curve):
        if nef < 2.5:
            convergence_speed = i + 1
            break

    final_positions: Dict[str, float] = {p["name"]: p["x"] for p in active}
    ideology_drift = [
        {
            "party":     name,
            "initial_x": round(initial_positions[name], 4),
            "final_x":   round(final_positions.get(name, initial_positions[name]), 4),
        }
        for name in initial_positions
    ]

    note = (
        f"Avec la méthode '{method}' et {num_elections} élections, "
        f"le système passe de {len(initial_pts)} à {len(active)} partis. "
        f"Indice de Laakso-Taagepera final : {n_eff_final:.2f} "
        f"({'bipartisme' if final_system == 'bipartite' else 'multipartisme'}). "
        f"{'Loi de Duverger confirmée.' if duverger_confirmed else ''}"
    )

    return {
        "elections":               all_elections,
        "final_system":            final_system,
        "effective_parties_curve": n_eff_curve,
        "duverger_confirmed":      duverger_confirmed,
        "convergence_speed":       convergence_speed,
        "ideology_drift":          ideology_drift,
        "pedagogical_note":        note,
    }, 200


# ── Deliberation + Vote ───────────────────────────────────────────────────────

def _deliberation_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /deliberation — extracted for FastAPI v2 reuse.

    Simulate DeGroot-style deliberation before the vote.
    """
    import copy as _cpd

    num_voters     = max(50, min(500, int(data.get("num_voters",          200))))
    ideology       = str(data.get("ideology",               "random"))
    seed           = int(data.get("seed",                    42))
    delib_rounds   = max(1,  min(10,  int(data.get("deliberation_rounds",  5))))
    influence      = max(0.0, min(1.0, float(data.get("influence_weight",  0.3))))
    network_type   = str(data.get("network_type",           "random"))
    group_size     = max(3,  min(20,  int(data.get("group_size",           5))))
    arg_quality    = max(0.0, min(1.0, float(data.get("argument_quality",  0.5))))
    primary_method = str(data.get("method",                 "plurality"))
    cand_specs     = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.1},
    ])[:6]

    if len(cand_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES

    candidates, voters, sincere_utilities, cand_names = _build_base_electorate(
        cand_specs, num_voters, ideology, seed, issues
    )

    # ── Initial ideology (1D economy axis) ───────────────────────────────
    initial_ideo: _np.ndarray = _np.array([
        2.0 * v["issue_positions"].get("economy", 0.5) - 1.0
        for v in voters
    ])
    pop_median_init = float(_np.median(initial_ideo))

    # ── Helper functions ─────────────────────────────────────────────────
    def _win(utils: Dict[Any, Dict[str, float]]) -> Optional[str]:
        rnk = [sorted(utils[v["id"]], key=lambda k: -utils[v["id"]][k]) for v in voters]
        return get_plurality_winner(rnk) if rnk else cand_names[0]

    def _shares(utils: Dict[Any, Dict[str, float]]) -> Dict[str, float]:
        rnk = [sorted(utils[v["id"]], key=lambda k: -utils[v["id"]][k]) for v in voters]
        tally: Counter = Counter(r[0] for r in rnk if r)
        total = len(voters)
        return {c: round(tally.get(c, 0) / total, 4) for c in cand_names}

    def _regret(utils: Dict[Any, Dict[str, float]], winner: Optional[str]) -> float:
        if winner is None:
            return 0.0
        return round(
            sum(max(utils[v["id"]].values()) - utils[v["id"]].get(winner, 0)
                for v in voters) / len(voters), 4
        )

    def _cw(utils: Dict[Any, Dict[str, float]]) -> Optional[str]:
        rnk = [sorted(utils[v["id"]], key=lambda k: -utils[v["id"]][k]) for v in voters]
        return get_condorcet_winner(rnk)

    def _recalc_utils(ideo: _np.ndarray) -> Dict[Any, Dict[str, float]]:
        """Recompute utilities after ideology shift (economy axis only)."""
        out: Dict[Any, Dict[str, float]] = {}
        for i_v, v in enumerate(voters):
            orig = v["issue_positions"]["economy"]
            v["issue_positions"]["economy"] = float(_np.clip((ideo[i_v] + 1) / 2, 0, 1))
            out[v["id"]] = {
                c["name"]: calculate_utility(v, c, issues)["utility"]
                for c in candidates
            }
            v["issue_positions"]["economy"] = orig
        return out

    def _form_groups(ideo: _np.ndarray, rng: _random.Random) -> list:
        n   = len(ideo)
        idx = list(range(n))
        if network_type == "complete":
            return [idx]
        if network_type == "echo_chamber":
            sorted_idx = sorted(idx, key=lambda i: ideo[i])
            return [sorted_idx[i:i + group_size] for i in range(0, n, group_size)]
        if network_type == "bridge":
            sorted_idx = sorted(idx, key=lambda i: ideo[i])
            half       = n // 2
            left, right = sorted_idx[:half], sorted_idx[half:]
            rng.shuffle(left); rng.shuffle(right)
            g2     = max(1, group_size // 2)
            groups = []
            for k in range(max(len(left), len(right)) // g2):
                g = left[k * g2:(k + 1) * g2] + right[k * g2:(k + 1) * g2]
                if g:
                    groups.append(g)
            return groups or [idx]
        # random
        rng.shuffle(idx)
        return [idx[i:i + group_size] for i in range(0, n, group_size)]

    # ── Pre-deliberation ─────────────────────────────────────────────────
    pre_win    = _win(sincere_utilities)
    pre_shares = _shares(sincere_utilities)
    pre_cw     = _cw(sincere_utilities)
    pre_regret = _regret(sincere_utilities, pre_win)
    pre_var    = float(_np.var(initial_ideo))

    # ── Deliberation rounds ───────────────────────────────────────────────
    current_ideo  = initial_ideo.copy()
    current_utils = _cpd.deepcopy(sincere_utilities)
    rng_d         = _random.Random(seed + 100)
    per_round: list[Dict[str, Any]] = []

    for round_k in range(delib_rounds):
        groups  = _form_groups(current_ideo, rng_d)
        new_ideo = current_ideo.copy()

        for group in groups:
            if len(group) < 2:
                continue
            g_arr = current_ideo[group]

            if network_type == "echo_chamber":
                # Amplification: push group toward its own extreme
                g_mean  = float(g_arr.mean())
                g_std   = max(0.02, float(g_arr.std()))
                sign    = 1.0 if g_mean >= 0 else -1.0
                target  = float(_np.clip(g_mean + sign * g_std * 0.4, -1.0, 1.0))
            else:
                # Quality-weighted mean: high quality → bias toward median
                weights = _np.ones(len(group))
                if arg_quality > 0:
                    for ki, j in enumerate(group):
                        prox = max(0.0, 1.0 - abs(float(current_ideo[j]) - pop_median_init))
                        weights[ki] = (1.0 - arg_quality) + arg_quality * prox
                weights /= max(float(weights.sum()), 1e-9)
                target = float(_np.clip(_np.dot(weights, g_arr), -1.0, 1.0))

            for i in group:
                new_ideo[i] = float(_np.clip(
                    current_ideo[i] + influence * (target - current_ideo[i]),
                    -1.0, 1.0,
                ))

        current_ideo  = new_ideo
        current_utils = _recalc_utils(current_ideo)

        rnd_winner = _win(current_utils)
        per_round.append({
            "round":              round_k + 1,
            "variance":           round(float(_np.var(current_ideo)), 4),
            "mean_position":      round(float(_np.mean(current_ideo)), 4),
            "winner_if_voted_now": rnd_winner,
        })

    # ── Post-deliberation ─────────────────────────────────────────────────
    post_win    = _win(current_utils)
    post_shares = _shares(current_utils)
    post_cw     = _cw(current_utils)
    post_regret = _regret(current_utils, post_win)
    post_var    = float(_np.var(current_ideo))

    winner_changed    = pre_win != post_win
    opinion_shift     = round(float(_np.mean(_np.abs(current_ideo - initial_ideo))), 4)
    convergence_rate  = round(max(0.0, 1.0 - post_var / pre_var), 4) if pre_var > 1e-9 else 0.0
    polarization_chg  = round(post_var - pre_var, 4)
    regret_improv     = round((pre_regret - post_regret) / pre_regret * 100, 2) if pre_regret > 1e-9 else 0.0

    _NET_DESC: Dict[str, str] = {
        "echo_chamber": "Les chambres d'écho amplifient les clivages — les groupes homogènes se radicalisent.",
        "bridge":       "Les ponts entre les camps permettent une convergence progressive des opinions.",
        "complete":     "En réseau complet, la délibération converge rapidement vers le consensus de masse.",
        "random":       "Le réseau aléatoire produit une convergence modérée sans dynamique extrême.",
    }
    network_effect = _NET_DESC.get(network_type, "")

    poldir  = "augmente" if polarization_chg > 0 else "diminue"
    regdir  = "améliore" if regret_improv > 0 else "dégrade"
    note = (
        f"En réseau '{network_type}', {delib_rounds} rounds de délibération "
        f"{'changent' if winner_changed else 'ne changent pas'} le vainqueur. "
        f"La polarisation {poldir} de {abs(round(polarization_chg * 100, 1))}%. "
        f"Le regret bayésien se {regdir} de {abs(regret_improv):.1f}%."
    )

    return {
        "pre_deliberation": {
            "winner":            pre_win,
            "vote_shares":       pre_shares,
            "condorcet_winner":  pre_cw,
            "mean_regret":       pre_regret,
            "ideology_variance": round(pre_var, 4),
        },
        "post_deliberation": {
            "winner":            post_win,
            "vote_shares":       post_shares,
            "condorcet_winner":  post_cw,
            "mean_regret":       post_regret,
            "ideology_variance": round(post_var, 4),
        },
        "winner_changed":       winner_changed,
        "deliberation_effect": {
            "opinion_shift_mean": opinion_shift,
            "convergence_rate":   convergence_rate,
            "polarization_change": polarization_chg,
            "regret_improvement": regret_improv,
        },
        "per_round":      per_round,
        "network_effect": network_effect,
        "pedagogical_note": note,
    }, 200


# ── /api/election/power-indices ───────────────────────────────────────────────

import itertools as _it_pi  # noqa: E402

def _power_indices_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /power-indices — extracted for FastAPI v2."""
    raw_parties: List[Dict[str, Any]] = data.get("parties") or []
    majority_threshold: int = int(data.get("majority_threshold", 0))
    constraints_raw: List[Dict[str, str]] = data.get("coalition_constraints") or []
    calc_shapley: bool = bool(data.get("calculate_shapley", True))
    calc_banzhaf: bool = bool(data.get("calculate_banzhaf", True))

    if not raw_parties:
        return {"error": "parties required"}, 400

    # Normalise input
    parties: List[Dict[str, Any]] = []
    for p in raw_parties:
        name  = str(p.get("name", "?"))
        seats = max(0, int(p.get("seats", 0)))
        pariah = bool(p.get("pariah", False))
        parties.append({"name": name, "seats": seats, "pariah": pariah})

    total_seats = sum(p["seats"] for p in parties)
    if majority_threshold <= 0:
        majority_threshold = total_seats // 2 + 1

    names = [p["name"] for p in parties]
    n = len(names)
    seats_map: Dict[str, int] = {p["name"]: p["seats"] for p in parties}
    pariah_set: set = {p["name"] for p in parties if p["pariah"]}

    # Build forbidden pairs: explicit constraints + pariah rules
    forbidden: set = set()
    for c in constraints_raw:
        a, b = c.get("party_a", ""), c.get("party_b", "")
        if a in names and b in names:
            forbidden.add(frozenset([a, b]))
    # Pariah: cannot be in coalition with any other party
    for par in pariah_set:
        for other in names:
            if other != par:
                forbidden.add(frozenset([par, other]))

    def _coalition_valid(members: frozenset) -> bool:
        """Returns True if no forbidden pair is fully inside members."""
        for pair in forbidden:
            if pair.issubset(members):
                return False
        return True

    def _coalition_wins(members: frozenset) -> bool:
        return _coalition_valid(members) and sum(seats_map[m] for m in members) >= majority_threshold

    # ── Shapley-Shubik ────────────────────────────────────────────────────────
    pivot_counts: Dict[str, int] = {name: 0 for name in names}
    total_perms = 0

    if calc_shapley and n <= 10:
        for perm in _it_pi.permutations(names):
            total_perms += 1
            running: frozenset = frozenset()
            already_won = False
            for party in perm:
                new_coalition = running | {party}
                if _coalition_valid(new_coalition):
                    seats_so_far = sum(seats_map[m] for m in new_coalition)
                    if not already_won and seats_so_far >= majority_threshold:
                        pivot_counts[party] += 1
                        already_won = True
                running = new_coalition

    shapley: Dict[str, float] = {}
    if calc_shapley and total_perms > 0:
        for name in names:
            shapley[name] = round(pivot_counts[name] / total_perms, 6)
    else:
        for name in names:
            shapley[name] = 0.0

    # ── Banzhaf ───────────────────────────────────────────────────────────────
    critical_counts: Dict[str, int] = {name: 0 for name in names}
    viable_coalitions: List[Dict[str, Any]] = []

    if calc_banzhaf:
        for r in range(1, n + 1):
            for combo in _it_pi.combinations(names, r):
                coalition = frozenset(combo)
                if _coalition_wins(coalition):
                    # Track critical parties
                    is_minimal = True
                    for member in combo:
                        without = coalition - {member}
                        if not _coalition_wins(without):
                            critical_counts[member] += 1
                        else:
                            is_minimal = False  # member is superfluous
                    viable_coalitions.append({
                        "parties": sorted(combo),
                        "seats":   sum(seats_map[m] for m in combo),
                        "minimal": all(
                            not _coalition_wins(coalition - {m}) for m in combo
                        ),
                    })

        total_critical = sum(critical_counts.values())
        banzhaf: Dict[str, float] = {}
        for name in names:
            banzhaf[name] = (
                round(critical_counts[name] / total_critical, 6)
                if total_critical > 0 else 0.0
            )
    else:
        banzhaf = {name: 0.0 for name in names}

    # ── Build per-party output ────────────────────────────────────────────────
    party_results = []
    for p in parties:
        name = p["name"]
        seat_pct = p["seats"] / total_seats if total_seats > 0 else 0.0
        sh = shapley.get(name, 0.0)
        bz = banzhaf.get(name, 0.0)
        power_ratio = round(sh / seat_pct, 4) if seat_pct > 0 else 0.0
        party_results.append({
            "name":           name,
            "seats":          p["seats"],
            "seat_pct":       round(seat_pct, 4),
            "shapley_index":  sh,
            "banzhaf_index":  bz,
            "power_ratio":    power_ratio,
            "critical_count": critical_counts.get(name, 0),
            "pivot_count":    pivot_counts.get(name, 0),
            "is_pariah":      p["pariah"],
        })

    # ── Power surprises ───────────────────────────────────────────────────────
    surprises: List[str] = []
    for pr in party_results:
        ratio = pr["power_ratio"]
        if ratio > 1.5:
            surprises.append(
                f"{pr['name']} : {pr['seats']} sièges ({round(pr['seat_pct']*100)}%) "
                f"mais Shapley={round(pr['shapley_index']*100, 1)}% — "
                f"sur-puissant (×{ratio:.2f})"
            )
        elif ratio < 0.5 and pr["seats"] > 0 and not pr["is_pariah"]:
            surprises.append(
                f"{pr['name']} : {pr['seats']} sièges mais Shapley={round(pr['shapley_index']*100, 1)}% "
                f"— sous-puissant (ratio={ratio:.2f})"
            )
        elif pr["is_pariah"] and pr["seats"] > 0:
            surprises.append(
                f"{pr['name']} : {pr['seats']} sièges mais pouvoir=0 (paria, exclu de toutes les coalitions)"
            )

    # ── Pedagogical note ──────────────────────────────────────────────────────
    if party_results:
        top = max(party_results, key=lambda x: x["shapley_index"])
        parias_with_seats = [p for p in party_results if p["is_pariah"] and p["seats"] > 0]
        note = (
            f"Shapley-Shubik 1954 : le parti '{top['name']}' détient "
            f"{round(top['shapley_index']*100, 1)}% du pouvoir de coalition "
            f"pour {round(top['seat_pct']*100, 1)}% des sièges. "
        )
        if parias_with_seats:
            names_str = ", ".join(p["name"] for p in parias_with_seats)
            total_paria_seats = sum(p["seats"] for p in parias_with_seats)
            note += (
                f"Les partis '{names_str}' totalisent {total_paria_seats} sièges "
                f"mais ont un pouvoir réel de 0 (cordon sanitaire). "
            )
        note += (
            "Banzhaf (1965) : un parti est critique si son départ fait "
            "passer la coalition de gagnante à perdante."
        )
    else:
        note = "Aucun parti fourni."

    return {
        "total_seats":        total_seats,
        "majority_threshold": majority_threshold,
        "parties":            party_results,
        "viable_coalitions":  viable_coalitions[:50],
        "power_surprises":    surprises,
        "pedagogical_note":   note,
    }, 200


# ── Profile-simulate (Lab reshape P1) ─────────────────────────────────────────

_PROFILE_DEFAULT_CANDS = [
    {"name": "Alice", "x": -0.5, "y": -0.2},
    {"name": "Bob",   "x":  0.5, "y":  0.2},
    {"name": "Carol", "x":  0.0, "y":  0.3},
]


def _profile_simulate_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /profile-simulate (Lab reshape P1).

    Builds a preference profile from a user-chosen source (spatial / impartial /
    mallows / urn / handcrafted), applies the behaviour transform, runs every method
    via compare_all_methods(override_utilities=...), and returns winners + the
    profile's 2D embedding + the paradox/cycle rate (the robustness read-out).
    """
    source       = str(data.get("source", "spatial"))
    behavior     = str(data.get("behavior", "sincere"))
    dims         = max(1, min(3, int(data.get("dims", 2))))
    valence      = bool(data.get("valence", False))
    num_voters   = max(10, min(1000, int(data.get("num_voters", 300))))
    seed         = int(data.get("seed", 42))
    source_params: Dict[str, float] = {
        k: float(v) for k, v in (data.get("source_params") or {}).items()
    }
    cand_specs   = (data.get("candidates") or _PROFILE_DEFAULT_CANDS)[:8]
    handcrafted  = data.get("handcrafted_matrix")

    names_in = [str(c.get("name", f"C{i}")) for i, c in enumerate(cand_specs)]
    if len(names_in) < 2:
        return {"error": "At least 2 candidates required"}, 400
    if source == "handcrafted":
        if not handcrafted or len(handcrafted) < 1:
            return {"error": "handcrafted source requires a non-empty matrix"}, 400
        if any(len(row) != len(names_in) for row in handcrafted):
            return {"error": "each handcrafted row must match the candidate count"}, 400

    try:
        built = build_profile(
            source, cand_specs, num_voters, dims, valence, behavior,
            source_params, seed, handcrafted_matrix=handcrafted,
        )
    except ValueError as exc:
        return {"error": str(exc)}, 400

    matrix = built["matrix"]
    names  = built["names"]
    voters     = [{"id": vid} for vid in matrix]
    candidates = [{"name": n} for n in names]

    # ── Ballot projection (frontier FA-1) ──────────────────────────────────
    # The counting rules see the EXPRESSED ballot, not the true utilities.
    ballot_cfg  = data.get("ballot") or {}
    ballot_type = str(ballot_cfg.get("type", "full"))
    truncate_at = ballot_cfg.get("truncate_at")
    score_lv    = int(ballot_cfg.get("score_levels") or 6)
    try:
        projected = project_ballot(
            matrix, names, ballot_type,
            truncate_at=int(truncate_at) if truncate_at else None,
            score_levels=score_lv,
        )
    except ValueError as exc:
        return {"error": str(exc)}, 400

    compat = compatible_methods(ballot_type)
    result = compare_all_methods(voters, candidates, [], override_utilities=projected)
    raw_methods = result.get("methods", {})
    methods_out: Dict[str, Any] = {
        name: {"winner": md.get("winner")}
        for name, md in raw_methods.items()
        if name in compat
    }
    incompatible = sorted(set(raw_methods) - compat)

    # Headline demo: same counting rule, different ballot → different winner.
    winner_flips: List[str] = []
    if ballot_type != "full":
        full_run = compare_all_methods(voters, candidates, [], override_utilities=matrix)
        full_methods = full_run.get("methods", {})
        winner_flips = sorted(
            name for name in methods_out
            if full_methods.get(name, {}).get("winner") != methods_out[name]["winner"]
        )

    metrics = ballot_metrics(
        ballot_type, len(names),
        truncate_at=int(truncate_at) if truncate_at else None,
        score_levels=score_lv,
    )
    first_vid = next(iter(projected))
    sample_ballot = {n: round(float(v), 3) for n, v in projected[first_vid].items()}

    return {
        "methods":                methods_out,
        "condorcet_winner":       result.get("condorcet_winner"),
        "inter_method_agreement": _inter_method_agreement(methods_out),
        "cycle_rate":             cycle_rate(source, names, min(num_voters, 200), source_params, seed),
        "candidate_names":        names,
        "display_points":         built["display_points"],
        "candidate_points":       built["candidate_points"],
        "num_voters":             len(matrix),
        "ballot_type":            ballot_type,
        "ballot_expressiveness":  metrics["expressiveness"],
        "ballot_cognitive_load":  metrics["cognitive_load"],
        "sample_ballot":          sample_ballot,
        "winner_flips":           winner_flips,
        "incompatible_methods":   incompatible,
    }, 200


# ── Assembly (Lab reshape P3) ─────────────────────────────────────────────────

def _assembly_voters(n: int, seed: int, ideology: str) -> "_np.ndarray":
    """Deterministic 2D voter cloud matching the playground ideology presets."""
    rng = _np.random.default_rng(seed)
    if ideology == "polarized":
        left = rng.random(n) < 0.5
        cx = _np.where(left, -0.5, 0.5)
        cy = _np.where(left, -0.3, 0.3)
        pts = _np.column_stack([rng.normal(cx, 0.22), rng.normal(cy, 0.3)])
    elif ideology == "centrist":
        pts = rng.normal(0.0, 0.25, size=(n, 2))
    else:
        pts = rng.normal(0.0, 0.45, size=(n, 2))
    return _np.clip(pts, -1.0, 1.0)


def _minimal_winning_coalitions(
    seats: Dict[str, int], positions: Dict[str, tuple], majority: int
) -> List[Dict[str, Any]]:
    """Minimal winning coalitions (every member pivotal), with ideological span =
    max pairwise distance between member parties. Sorted by smallest span (the
    'governable' ones first), capped at 12."""
    names = [p for p, s in seats.items() if s > 0]
    out: List[Dict[str, Any]] = []
    for mask in range(1, 1 << len(names)):
        members = [names[i] for i in range(len(names)) if mask >> i & 1]
        total = sum(seats[m] for m in members)
        if total < majority:
            continue
        # minimal: removing any member must drop below majority
        if any(total - seats[m] >= majority for m in members):
            continue
        span = 0.0
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = positions[members[i]], positions[members[j]]
                span = max(span, math.hypot(a[0] - b[0], a[1] - b[1]))
        out.append({"parties": sorted(members), "seats": total, "span": round(span, 4)})
    out.sort(key=lambda c: (c["span"], -c["seats"]))
    return out[:12]


def _allocate_assembly(
    d2: "_np.ndarray",
    band_axis: "_np.ndarray",
    names: List[str],
    sincere_choice: "_np.ndarray",
    structure: str,
    seats_total: int,
    threshold: float,
    appt: str,
    desertion: bool,
) -> Dict[str, Any]:
    """Core votes→seats allocation, shared by /assembly and /assembly-scorecard.

    `band_axis` is the voter coordinate used to draw the equal-population
    single-member districts (x normally; the gerrymander probe re-runs with y —
    a different 'map' over the same voters).
    Returns {choice, votes, seats, district_seats, excluded, threshold_waived,
    wasted, assembly_size}.
    """
    num_voters = len(sincere_choice)
    choice = sincere_choice.copy()

    # Duverger (P4): voters iteratively abandon non-viable parties for the
    # nearest viable one (FPTP: district top-2; PR/MMP lists: above-threshold).
    if desertion:
        order_b = _np.argsort(band_axis, kind="stable")
        d_bands = _np.array_split(order_b, seats_total) if structure == "fptp" else []
        for _ in range(3):  # a few best-response rounds reach a near fixed point
            new_choice = choice.copy()
            if structure == "fptp":
                for band in d_bands:
                    if len(band) < 2:
                        continue
                    counts = _np.bincount(choice[band], minlength=len(names))
                    viable = [int(i) for i in counts.argsort()[-2:] if counts[i] > 0]
                    if len(viable) < 2:
                        continue
                    sub = d2[_np.ix_(band, viable)]
                    nearest_viable = _np.array(viable)[sub.argmin(axis=1)]
                    movers = ~_np.isin(choice[band], viable)
                    new_choice[band[movers]] = nearest_viable[movers]
            else:
                counts = _np.bincount(choice, minlength=len(names))
                viable = [i for i in range(len(names))
                          if counts[i] > 0 and counts[i] / num_voters >= threshold]
                if viable and len(viable) < len(names):
                    sub = d2[:, viable]
                    nearest_viable = _np.array(viable)[sub.argmin(axis=1)]
                    movers = ~_np.isin(choice, viable)
                    new_choice[movers] = nearest_viable[movers]
            if (new_choice == choice).all():
                break
            choice = new_choice

    votes = {n: int((choice == i).sum()) for i, n in enumerate(names)}
    vote_share = {n: votes[n] / num_voters for n in names}
    allocate = get_sainte_lague_winners if appt == "sainte_lague" else get_dhondt_winners

    def _pr_alloc(n_seats: int) -> tuple[Dict[str, int], List[str], bool]:
        """Threshold-filtered proportional allocation. Returns (seats, excluded, waived)."""
        eligible = {n: votes[n] for n in names if vote_share[n] >= threshold and votes[n] > 0}
        waived = False
        if not eligible:  # nobody passes → waive the threshold rather than fail
            eligible = {n: votes[n] for n in names if votes[n] > 0}
            waived = True
        alloc = allocate(eligible, n_seats)
        seats = {n: int(alloc.get(n, 0)) for n in names}
        excluded = [n for n in names if n not in eligible]
        return seats, excluded, waived

    district_seats = {n: 0 for n in names}
    excluded: List[str] = []
    threshold_waived = False
    wasted = 0

    if structure == "fptp":
        # One single-member district per seat: equal-population bands along band_axis.
        order = _np.argsort(band_axis, kind="stable")
        bands = _np.array_split(order, seats_total)
        seats = {n: 0 for n in names}
        for band in bands:
            if len(band) == 0:
                continue
            counts = _np.bincount(choice[band], minlength=len(names))
            win = int(counts.argmax())
            seats[names[win]] += 1
            wasted += int(len(band) - counts[win])  # votes for district losers
        assembly_size = seats_total
    elif structure == "mmp":
        n_districts = max(1, seats_total // 2)
        order = _np.argsort(band_axis, kind="stable")
        bands = _np.array_split(order, n_districts)
        for band in bands:
            if len(band) == 0:
                continue
            counts = _np.bincount(choice[band], minlength=len(names))
            district_seats[names[int(counts.argmax())]] += 1
        target, excluded, threshold_waived = _pr_alloc(seats_total)
        # Compensatory top-up; overhang (district wins beyond target) is kept.
        seats = {n: max(target[n], district_seats[n]) for n in names}
        assembly_size = sum(seats.values())
        wasted = sum(votes[n] for n in excluded)
    else:  # pr
        seats, excluded, threshold_waived = _pr_alloc(seats_total)
        assembly_size = seats_total
        wasted = sum(votes[n] for n in excluded)

    return {
        "choice":           choice,
        "votes":            votes,
        "seats":            seats,
        "district_seats":   district_seats,
        "excluded":         excluded,
        "threshold_waived": threshold_waived,
        "wasted":           wasted,
        "assembly_size":    assembly_size,
    }


def _assembly_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /assembly (Lab reshape P3).

    One shared electorate, party-level question: votes → seats under
    PR (national lists, threshold + apportionment), FPTP (one single-member
    district per seat, districts drawn as equal-population bands along the x
    axis — geography correlates with ideology, which is what makes wasted votes
    and the winner's bonus legible), or MMP (half district seats, half
    compensatory top-up; overhang seats are kept, so the assembly can slightly
    exceed the nominal size).
    """
    parties_in  = (data.get("parties") or [])[:8]
    num_voters  = max(10, min(1000, int(data.get("num_voters", 400))))
    ideology    = str(data.get("ideology", "random"))
    seed        = int(data.get("seed", 42))
    structure   = str(data.get("structure", "pr"))
    seats_total = max(10, min(500, int(data.get("seats", 100))))
    threshold   = max(0.0, min(0.15, float(data.get("threshold", 0.05))))
    appt        = str(data.get("apportionment", "dhondt"))

    if len(parties_in) < 2:
        return {"error": "At least 2 parties required"}, 400

    names     = [str(p.get("name", f"P{i}")) for i, p in enumerate(parties_in)]
    positions = {n: (float(p.get("x", 0.0)), float(p.get("y", 0.0)))
                 for n, p in zip(names, parties_in)}
    pts = _np.array([[positions[n][0], positions[n][1]] for n in names])

    voters = _assembly_voters(num_voters, seed, ideology)
    # Sincere party vote: nearest party in the plane.
    d2 = ((voters[:, None, :] - pts[None, :, :]) ** 2).sum(axis=2)
    sincere = d2.argmin(axis=1)

    alloc = _allocate_assembly(
        d2, voters[:, 0], names, sincere, structure, seats_total,
        threshold, appt, bool(data.get("strategic_desertion", False)),
    )
    votes            = alloc["votes"]
    vote_share       = {n: votes[n] / num_voters for n in names}
    seats            = alloc["seats"]
    district_seats   = alloc["district_seats"]
    excluded         = alloc["excluded"]
    threshold_waived = alloc["threshold_waived"]
    wasted           = alloc["wasted"]
    assembly_size    = alloc["assembly_size"]

    metrics = compute_proportionality_metrics(
        {n: float(votes[n]) for n in names}, seats
    )
    majority = assembly_size // 2 + 1

    return {
        "structure":      structure,
        "assembly_size":  assembly_size,
        "majority":       majority,
        "threshold_waived": threshold_waived,
        "parties": [
            {
                "name":           n,
                "x":              positions[n][0],
                "y":              positions[n][1],
                "votes":          votes[n],
                "vote_share":     round(vote_share[n], 4),
                "seats":          seats[n],
                "seat_share":     round(seats[n] / assembly_size, 4) if assembly_size else 0.0,
                "district_seats": district_seats[n],
                "excluded_by_threshold": n in excluded,
            }
            for n in names
        ],
        "gallagher_index":          metrics["gallagher_index"],
        "effective_parties_votes":  metrics["effective_parties_votes"],
        "effective_parties_seats":  metrics["effective_parties_seats"],
        "wasted_vote_share":        round(wasted / num_voters, 4),
        "coalitions": _minimal_winning_coalitions(seats, positions, majority),
    }, 200


# ── Assembly scorecard (Lab reshape P5) ───────────────────────────────────────

_SCORECARD_STRUCTURES = ("pr", "fptp", "mmp")
_SCORECARD_AXES = (
    "proportionality", "pluralism", "effective_votes",
    "minority_representation", "governability", "gerrymander_resistance",
)


def _assembly_scorecard_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /assembly-scorecard (Lab reshape P5).

    Monte-Carlo scorecard: re-rolls the electorate `replications` times and, for
    EACH structure (pr / fptp / mmp) at the requested knobs, scores six axes in
    [0, 1] (higher = better, orientations stated):
      proportionality          1 − Gallagher/0.2 (clamped)
      pluralism                ENP(seats) / ENP(votes) — vote diversity surviving into seats
      effective_votes          1 − wasted-vote share
      minority_representation  share of parties ≥3% votes holding ≥1 seat
      governability            1 / size of the smallest winning coalition
      gerrymander_resistance   1 − seat-share shift when districts are redrawn
                               along y instead of x (PR: immune → 1)
    Every number carries a band (mean, p10, p90 over the re-rolls).
    """
    parties_in   = (data.get("parties") or [])[:8]
    num_voters   = max(10, min(1000, int(data.get("num_voters", 400))))
    ideology     = str(data.get("ideology", "random"))
    seed         = int(data.get("seed", 42))
    seats_total  = max(10, min(500, int(data.get("seats", 100))))
    threshold    = max(0.0, min(0.15, float(data.get("threshold", 0.05))))
    appt         = str(data.get("apportionment", "dhondt"))
    desertion    = bool(data.get("strategic_desertion", False))
    replications = max(8, min(40, int(data.get("replications", 24))))

    if len(parties_in) < 2:
        return {"error": "At least 2 parties required"}, 400

    names     = [str(p.get("name", f"P{i}")) for i, p in enumerate(parties_in)]
    positions = {n: (float(p.get("x", 0.0)), float(p.get("y", 0.0)))
                 for n, p in zip(names, parties_in)}
    pts = _np.array([[positions[n][0], positions[n][1]] for n in names])

    acc: Dict[str, Dict[str, List[float]]] = {
        s: {a: [] for a in _SCORECARD_AXES} for s in _SCORECARD_STRUCTURES
    }

    for k in range(replications):
        voters = _assembly_voters(num_voters, seed + 101 * k, ideology)
        d2 = ((voters[:, None, :] - pts[None, :, :]) ** 2).sum(axis=2)
        sincere = d2.argmin(axis=1)

        for structure in _SCORECARD_STRUCTURES:
            a = _allocate_assembly(d2, voters[:, 0], names, sincere, structure,
                                   seats_total, threshold, appt, desertion)
            votes, seats = a["votes"], a["seats"]
            size = max(1, a["assembly_size"])

            metrics = compute_proportionality_metrics(
                {n: float(votes[n]) for n in names}, seats
            )
            g   = float(metrics["gallagher_index"] or 0.0)
            env = float(metrics["effective_parties_votes"] or 1.0)
            ens = float(metrics["effective_parties_seats"] or 1.0)

            proportionality = max(0.0, 1.0 - g / 0.2)
            pluralism = min(1.0, ens / env) if env > 0 else 1.0
            effective_votes = 1.0 - a["wasted"] / num_voters
            visible = [n for n in names if votes[n] / num_voters >= 0.03]
            minority = (sum(1 for n in visible if seats[n] > 0) / len(visible)) if visible else 1.0
            majority = size // 2 + 1
            coalitions = _minimal_winning_coalitions(seats, positions, majority)
            min_size = min((len(c["parties"]) for c in coalitions), default=len(names))
            governability = 1.0 / max(1, min_size)
            if structure == "pr":
                gerry = 1.0  # no districts → redistricting cannot move seats
            else:
                b = _allocate_assembly(d2, voters[:, 1], names, sincere, structure,
                                       seats_total, threshold, appt, desertion)
                size_b = max(1, b["assembly_size"])
                tv = 0.5 * sum(abs(seats[n] / size - b["seats"][n] / size_b) for n in names)
                gerry = max(0.0, 1.0 - tv)

            acc[structure]["proportionality"].append(proportionality)
            acc[structure]["pluralism"].append(pluralism)
            acc[structure]["effective_votes"].append(effective_votes)
            acc[structure]["minority_representation"].append(minority)
            acc[structure]["governability"].append(governability)
            acc[structure]["gerrymander_resistance"].append(gerry)

    def _band(xs: List[float]) -> Dict[str, float]:
        arr = _np.array(xs, dtype=float)
        return {
            "mean": round(float(arr.mean()), 4),
            "lo":   round(float(_np.percentile(arr, 10)), 4),
            "hi":   round(float(_np.percentile(arr, 90)), 4),
        }

    return {
        "replications": replications,
        "structures": {
            s: {a: _band(acc[s][a]) for a in _SCORECARD_AXES}
            for s in _SCORECARD_STRUCTURES
        },
    }, 200


# ── Temporal mode (frontier FA-3): democracy as a repeated game ───────────────

def _temporal_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Pure worker for /temporal (frontier FA-3).

    Runs N SEQUENTIAL elections on one starting electorate. Between rounds
    (stated, documented dynamics — knobs, not hidden assumptions):
      · parties ADAPT: myopic local search — each party tries 8 compass moves of
        `adaptation_step` and keeps the one maximising its own sincere support,
        others held fixed (vote-seeking Downsian dynamics);
      · voters ATTACH: each voter drifts `loyalty_drift` of the way toward the
        party they voted for (partisan identification → endogenous polarization).
    Tracked per round: positions, vote/seat shares, largest-party winner,
    ENP(votes/seats), Gallagher, polarization (vote-weighted dispersion of party
    positions), alternation (largest party changed), congruence gap (distance
    between the seat-weighted assembly position and the voter median).
    Reproducible by seed. The question it answers: is the system still good
    AFTER repeated play?
    """
    parties_in  = (data.get("parties") or [])[:8]
    num_voters  = max(10, min(1000, int(data.get("num_voters", 400))))
    ideology    = str(data.get("ideology", "random"))
    seed        = int(data.get("seed", 42))
    structure   = str(data.get("structure", "pr"))
    seats_total = max(10, min(500, int(data.get("seats", 100))))
    threshold   = max(0.0, min(0.15, float(data.get("threshold", 0.05))))
    appt        = str(data.get("apportionment", "dhondt"))
    desertion   = bool(data.get("strategic_desertion", False))
    rounds      = max(2, min(30, int(data.get("rounds", 20))))
    adapt_step  = max(0.0, min(0.2, float(data.get("adaptation_step", 0.06))))
    loyalty     = max(0.0, min(0.2, float(data.get("loyalty_drift", 0.05))))

    if len(parties_in) < 2:
        return {"error": "At least 2 parties required"}, 400

    names = [str(p.get("name", f"P{i}")) for i, p in enumerate(parties_in)]
    pts = _np.array(
        [[float(p.get("x", 0.0)), float(p.get("y", 0.0))] for p in parties_in],
        dtype=float,
    )
    voters = _assembly_voters(num_voters, seed, ideology)

    compass = _np.array(
        [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]],
        dtype=float,
    )
    compass /= _np.linalg.norm(compass, axis=1, keepdims=True)

    rounds_out: List[Dict[str, Any]] = []
    prev_winner: Optional[str] = None
    alternations = 0

    for r in range(rounds):
        d2 = ((voters[:, None, :] - pts[None, :, :]) ** 2).sum(axis=2)
        sincere = d2.argmin(axis=1)
        alloc = _allocate_assembly(
            d2, voters[:, 0], names, sincere, structure,
            seats_total, threshold, appt, desertion,
        )
        votes, seats = alloc["votes"], alloc["seats"]
        size = max(1, alloc["assembly_size"])
        shares = _np.array([votes[n] for n in names], dtype=float) / num_voters
        seat_shares = _np.array([seats[n] for n in names], dtype=float) / size

        metrics = compute_proportionality_metrics(
            {n: float(votes[n]) for n in names}, seats
        )
        # Vote-weighted dispersion of party positions (the polarization index).
        pbar = (shares[:, None] * pts).sum(axis=0) / max(1e-9, shares.sum())
        polarization = float(_np.sqrt((shares * ((pts - pbar) ** 2).sum(axis=1)).sum()))
        # Assembly position (seat-weighted) vs the voter median.
        assembly_pos = (seat_shares[:, None] * pts).sum(axis=0)
        median_pt = _np.median(voters, axis=0)
        congruence_gap = float(_np.linalg.norm(assembly_pos - median_pt))

        winner = names[int(_np.argmax([seats[n] for n in names]))]
        alternation = prev_winner is not None and winner != prev_winner
        if alternation:
            alternations += 1
        prev_winner = winner

        rounds_out.append({
            "round": r,
            "parties": [
                {"name": n, "x": round(float(pts[i, 0]), 4), "y": round(float(pts[i, 1]), 4),
                 "vote_share": round(float(shares[i]), 4), "seats": seats[n]}
                for i, n in enumerate(names)
            ],
            "winner":         winner,
            "enp_votes":      metrics["effective_parties_votes"],
            "enp_seats":      metrics["effective_parties_seats"],
            "gallagher":      metrics["gallagher_index"],
            "polarization":   round(polarization, 4),
            "alternation":    alternation,
            "congruence_gap": round(congruence_gap, 4),
        })

        if r == rounds - 1:
            break

        # ── Party adaptation: myopic vote-seeking local search ──────────────
        # Campaign resources follow EXPRESSED votes (stated convention): a
        # party starved by strategic desertion cannot reposition, while the
        # well-funded ones optimise freely — the second half of Duverger's
        # squeeze. Under PR with no threshold expressed = sincere, so all
        # parties adapt at full strength and the system sustains itself.
        if adapt_step > 0:
            expressed = _np.array([votes[n] for n in names], dtype=float)
            max_votes = expressed.max() or 1.0
            for i in range(len(names)):
                step_i = adapt_step * (expressed[i] / max_votes)
                if step_i <= 0:
                    continue
                others = _np.delete(_np.arange(len(names)), i)
                others_min = d2[:, others].min(axis=1)
                best_pos = pts[i].copy()
                best_support = int((d2[:, i] < others_min).sum())
                for step_dir in compass:
                    trial = _np.clip(pts[i] + step_i * step_dir, -1.0, 1.0)
                    trial_d2 = ((voters - trial) ** 2).sum(axis=1)
                    support = int((trial_d2 < others_min).sum())
                    if support > best_support:
                        best_support = support
                        best_pos = trial
                pts[i] = best_pos
                # keep d2 fresh for the next party's evaluation
                d2[:, i] = ((voters - pts[i]) ** 2).sum(axis=1)

        # ── Voter attachment: drift toward the party they VOTED for ─────────
        # The expressed vote (post-desertion), not the sincere favourite: a
        # deserter attaches to the viable party they chose — this realignment
        # is precisely how Duverger's squeeze compounds over repeated play.
        if loyalty > 0:
            voters = _np.clip(
                voters + loyalty * (pts[alloc["choice"]] - voters), -1.0, 1.0
            )

    first, last = rounds_out[0], rounds_out[-1]
    return {
        "rounds":               rounds_out,
        "alternation_rate":     round(alternations / max(1, rounds - 1), 4),
        "enp_votes_initial":    first["enp_votes"],
        "enp_votes_final":      last["enp_votes"],
        "polarization_initial": first["polarization"],
        "polarization_final":   last["polarization"],
    }, 200


