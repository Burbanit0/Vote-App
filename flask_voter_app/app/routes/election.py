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

import random as _random
from collections import Counter
from typing import Any, Dict, Optional

import numpy as _np
from flask import Blueprint, Response, jsonify, request

from app.constants import DEFAULT_ISSUES, ECONOMY_ISSUES, ENV_ISSUES, SOCIAL_ISSUES
from app.utils.simulation_voting_utils import calculate_utility, create_candidate, create_voter
from app.utils.simulation_metrics      import compare_all_methods
from app.utils.blank_vote_rules        import BlankVoteRule, apply_blank_rule
from app.utils.blank_contagion         import simulate_blank_contagion
from app.utils.campaign_dynamics       import simulate_campaign
from app.utils.information_model       import apply_information_asymmetry
from app.extensions import sim_limiter

election_bp = Blueprint("election", __name__, url_prefix="/api/election")

_PARTY_CYCLE = ["Green", "Liberal", "Conservative", "Independent"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_candidate_from_xy(
    i: int, name: str, x: float, y: float, issues: list[str]
) -> Dict[str, Any]:
    """Build a candidate dict from explicit 2D ideological position."""
    econ_pos = (x + 1) / 2
    soc_pos  = (y + 1) / 2
    env_pos  = 1.0 - econ_pos

    policies = {
        issue: (
            econ_pos if issue in ECONOMY_ISSUES else
            env_pos  if issue in ENV_ISSUES      else
            soc_pos  if issue in SOCIAL_ISSUES   else
            (econ_pos + soc_pos) / 2
        )
        for issue in issues
    }
    return {
        "id":               i,
        "name":             name,
        "party":            _PARTY_CYCLE[i % len(_PARTY_CYCLE)],
        "party_lean":       x,
        "ideology_position": econ_pos,
        "policies":         policies,
        "charisma":         0.7,
        "scandals":         0,
        "campaign_funds":   500_000,
        "experience":       10,
        "popularity":       0.6,
    }


def _inter_method_agreement(methods_data: Dict[str, Any]) -> float:
    """Fraction of voting methods that agree on the same winner."""
    winners = [md.get("winner") for md in methods_data.values() if md.get("winner")]
    if not winners:
        return 0.0
    most_common = Counter(winners).most_common(1)[0][1]
    return round(most_common / len(winners), 4)


# ── Endpoint ──────────────────────────────────────────────────────────────────

@election_bp.route("/simulate", methods=["POST"])
def simulate() -> tuple[Response, int]:
    """
    POST /api/election/simulate

    Unified simulation that chains all Vote Lab models in logical order.
    """
    data = request.get_json() or {}

    # ── Parse params ──────────────────────────────────────────────────────
    num_voters   = max(10, min(1000, int(data.get("num_voters",  300))))
    ideology     = str(data.get("ideology",   "random"))
    seed         = int(data.get("seed",        42))
    cand_specs   = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ])[:6]

    blank_cfg       = data.get("blank_vote", {}) or {}
    blank_enabled   = bool(blank_cfg.get("enabled", False))
    blank_rule_str  = str(blank_cfg.get("rule", "symbolic"))
    contagion_cfg   = blank_cfg.get("contagion", {}) or {}
    contagion_on    = bool(contagion_cfg.get("enabled", False))

    info_cfg        = data.get("information_model", {}) or {}
    info_enabled    = bool(info_cfg.get("enabled", False))

    campaign_cfg    = data.get("campaign", {}) or {}
    campaign_on     = bool(campaign_cfg.get("enabled", False))
    num_days        = max(7, min(60, int(campaign_cfg.get("num_days",       30))))
    polling_effect  = max(0.0, min(1.0, float(campaign_cfg.get("polling_effect", 0.3))))

    if len(cand_specs) < 2:
        return jsonify({"error": "At least 2 candidates required"}), 400

    # ── Seed both PRNGs ───────────────────────────────────────────────────
    _random.seed(seed)
    _np.random.seed(seed)

    issues     = DEFAULT_ISSUES
    cand_names = [str(s.get("name", f"C{i}")) for i, s in enumerate(cand_specs)]

    # ── 1. Build candidates ───────────────────────────────────────────────
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

    # ── 2. Build electorate ───────────────────────────────────────────────
    voters = [
        create_voter(issues, i, ideology_distribution=ideology)
        for i in range(num_voters)
    ]

    # ── 3. Compute true utilities ─────────────────────────────────────────
    true_utilities: Dict[Any, Dict[str, float]] = {
        v["id"]: {
            c["name"]: calculate_utility(v, c, issues)["utility"]
            for c in candidates
        }
        for v in voters
    }

    # ── 4. Campaign dynamics (optional) ───────────────────────────────────
    campaign_trajectory: Optional[Dict[str, Any]] = None
    if campaign_on:
        camp = simulate_campaign(
            num_candidates=len(candidates),
            num_voters=num_voters,
            num_days=num_days,
            events=[],
            seed=seed,
        )
        campaign_trajectory = camp
        # Map campaign candidate order → our candidate names
        camp_cands = camp.get("candidates", [])
        # Get final-day vote shares (%) and normalise to [0, 1]
        final_shares: Dict[str, float] = {}
        for camp_idx, camp_name in enumerate(camp_cands):
            if camp_idx < len(cand_names):
                our_name = cand_names[camp_idx]
                shares_list = camp.get("daily_scores", {}).get(camp_name, [50.0])
                final_shares[our_name] = shares_list[-1] / 100.0

        # Apply polling-bandwagon effect: blend true utility toward poll share
        for v in voters:
            for c_name in cand_names:
                share = final_shares.get(c_name, 1.0 / len(cand_names))
                u     = true_utilities[v["id"]][c_name]
                # Weighted blend: more polling_effect → more "pulled" by polling share
                blended = u * (1.0 - polling_effect * 0.4) + share * (polling_effect * 0.4)
                true_utilities[v["id"]][c_name] = max(0.0, min(1.0, blended))

    # ── 5. Blank-vote contagion (optional) ────────────────────────────────
    if contagion_on and blank_enabled:
        beta    = max(0.0, min(1.0, float(contagion_cfg.get("beta",  0.15))))
        gamma   = max(0.0, min(1.0, float(contagion_cfg.get("gamma", 0.10))))
        net_map = {"random": "random", "watts_strogatz": "small-world", "block": "clustered"}
        net     = net_map.get(str(contagion_cfg.get("network", "random")), "random")

        contagion_result = simulate_blank_contagion(
            num_voters=num_voters,
            initial_blank_rate=0.05,
            contagion_rate=beta,
            recovery_rate=gamma,
            num_rounds=10,
            network_type=net,
            seed=seed,
        )
        final_blank_rate = contagion_result.get("final_blank_rate", 0.05)
        # Lower blank_threshold for voters proportionally to contagion spread
        threshold_reduction = final_blank_rate * 0.4
        for v in voters:
            v["blank_threshold"] = max(0.05, v["blank_threshold"] - threshold_reduction)

    # ── 6. Information model (optional) ───────────────────────────────────
    effective_utilities = true_utilities
    if info_enabled:
        # Build bias dict keyed by str(candidate_idx)
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
        true_list = [
            [true_utilities[v["id"]][c["name"]] for c in candidates]
            for v in voters
        ]
        perceived_list = apply_information_asymmetry(
            true_list, media_bias, voter_segments, seed=seed
        )
        effective_utilities = {
            v["id"]: {c["name"]: perceived_list[idx][j] for j, c in enumerate(candidates)}
            for idx, v in enumerate(voters)
        }

    # ── 7. Run all voting methods ─────────────────────────────────────────
    result = compare_all_methods(
        voters,
        candidates,
        issues,
        blank_vote=blank_enabled,
        override_utilities=effective_utilities,
    )

    condorcet_winner = result.get("condorcet_winner")
    blank_pct        = result.get("blank_pct") or 0.0
    methods_data     = result.get("methods", {})

    # ── 8. Apply constitutional blank-vote rule ───────────────────────────
    try:
        blank_rule = BlankVoteRule(blank_rule_str)
    except ValueError:
        blank_rule = BlankVoteRule.SYMBOLIC

    methods_out: Dict[str, Any] = {}
    for method_name, md in methods_data.items():
        winner = md.get("winner")
        entry: Dict[str, Any] = {
            "winner":               winner,
            "bayesian_regret":      md.get("bayesian_regret"),
            "majority_satisfaction": md.get("majority_satisfaction"),
            "condorcet_consistent": md.get("condorcet_consistent"),
        }
        if blank_enabled:
            rule_result            = apply_blank_rule(winner=winner, blank_pct=blank_pct, rule=blank_rule)
            entry["winner_with_blank"]  = rule_result.get("winner")
            entry["blank_triggered"]    = rule_result.get("blank_triggered", False)
        methods_out[method_name] = entry

    # ── 9. Build voter snapshot for ideology map ──────────────────────────
    voters_snapshot = [
        {
            "id": v["id"],
            "x":  round(2.0 * v["issue_positions"].get("economy",       0.5) - 1.0, 3),
            "y":  round(2.0 * v["issue_positions"].get("social_welfare", 0.5) - 1.0, 3),
            "blank_threshold_final": round(v["blank_threshold"], 4),
        }
        for v in voters
    ]

    candidates_out = [
        {
            "name":  c["name"],
            "x":     round(2.0 * c["ideology_position"] - 1.0, 3),
            "y":     round(2.0 * c["policies"].get("social_welfare", 0.5) - 1.0, 3),
            "party": c["party"],
        }
        for c in candidates
    ]

    return jsonify({
        "config":                data,
        "voters_snapshot":       voters_snapshot,
        "candidates":            candidates_out,
        "methods":               methods_out,
        "condorcet_winner":      condorcet_winner,
        "blank_rate":            round(blank_pct, 4),
        "campaign_trajectory":   campaign_trajectory,
        "inter_method_agreement": _inter_method_agreement(methods_out),
        "condorcet_exists":      condorcet_winner is not None,
    }), 200


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

@election_bp.route("/divergence", methods=["POST"])
def divergence() -> tuple[Response, int]:
    """
    POST /api/election/divergence

    Runs the same electorate twice — without and with blank vote — to isolate
    the effect of blank-vote rules on inter-method agreement.

    Campaign is intentionally skipped so we measure only the blank-vote effect.
    """
    data = request.get_json() or {}

    num_voters  = max(10, min(500, int(data.get("num_voters", 200))))
    ideology    = str(data.get("ideology", "random"))
    seed        = int(data.get("seed", 42))
    cand_specs  = data.get("candidates", [
        {"name": "Alice", "x": -0.5, "y": -0.2},
        {"name": "Bob",   "x":  0.5, "y":  0.2},
        {"name": "Carol", "x":  0.0, "y":  0.3},
    ])[:6]

    blank_cfg      = data.get("blank_vote", {}) or {}
    blank_rule_str = str(blank_cfg.get("rule", "symbolic"))
    contagion_cfg  = blank_cfg.get("contagion", {}) or {}
    contagion_on   = bool(contagion_cfg.get("enabled", False))

    if len(cand_specs) < 2:
        return jsonify({"error": "At least 2 candidates required"}), 400

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

    return jsonify({
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
    }), 200


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
    from app.utils.simulation_ranked_utils import (
        get_condorcet_winner,
        get_plurality_winner, get_two_round_winner, get_borda_winner,
        get_approval_winner, get_irv_winner, get_coombs_winner,
        get_bucklin_winner, get_minimax_winner, get_schulze_winner,
    )
    from app.utils.simulation_score_utils import (
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


@election_bp.route("/campaign-sensitivity", methods=["POST"])
def campaign_sensitivity() -> tuple[Response, int]:
    """
    POST /api/election/campaign-sensitivity

    Runs the same electorate at multiple campaign "snapshots" to measure how
    the polling effect changes which method elects which winner over time.

    Body:
        ...ElectionConfig fields...
        snapshot_days: [0, 7, 14, 21, 28, "final"]   (optional)
    """
    import copy

    data = request.get_json() or {}

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
        return jsonify({"error": "At least 2 candidates required"}), 400

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

    return jsonify({
        "snapshots":           snapshots,
        "method_stability":    method_stability,
        "most_stable_method":  most_stable,
        "least_stable_method": least_stable,
    }), 200


# ── Combined effects (2³ factorial) ──────────────────────────────────────────

@election_bp.route("/combined-effects", methods=["POST"])
def combined_effects() -> tuple[Response, int]:
    """
    POST /api/election/combined-effects

    2×2×2 factorial analysis: runs the same electorate under all 8 combinations
    of blank-vote / campaign / information-model ON-OFF to isolate and compare
    each factor's contribution to method divergence.
    """
    import copy
    from app.utils.simulation_ranked_utils import get_condorcet_winner

    data = request.get_json() or {}

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
        return jsonify({"error": "At least 2 candidates required"}), 400

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

    return jsonify({
        "base_winner":                base_winner,
        "combinations":               combinations,
        "factor_deltas":              {k: round(v * 100, 1) for k, v in factor_deltas.items()},
        "most_disruptive_factor":     most_disruptive,
        "least_disruptive_factor":    least_disruptive,
        "max_disruption_combination": max_disrup_combo,
    }), 200
