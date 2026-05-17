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

import eventlet
from eventlet import tpool
import numpy as _np
from flask import Blueprint, Response, current_app, jsonify, request

from app.constants import DEFAULT_ISSUES, ECONOMY_ISSUES, ENV_ISSUES, SOCIAL_ISSUES
from app.utils.simulation_voting_utils import calculate_utility, create_candidate, create_voter
from app.utils.simulation_metrics      import compare_all_methods
from app.utils.simulation_ranked_utils import (
    get_plurality_winner,
    get_condorcet_winner,
    get_irv_winner,
    get_approval_winner_sincere,
    get_borda_winner,
    get_schulze_winner,
)
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
@sim_limiter.limit("20 per minute")
def simulate() -> tuple[Response, int]:
    """
    POST /api/election/simulate

    Unified simulation that chains all Vote Lab models in logical order.
    """
    data = request.get_json() or {}
    try:
        with eventlet.Timeout(120):
            body, status = tpool.execute(_simulate_worker, data)
        return jsonify(body), status
    except eventlet.timeout.Timeout:
        current_app.logger.warning("simulate() timed out after 120s")
        return jsonify({"error": "Simulation timed out"}), 503
    except Exception as exc:
        current_app.logger.exception("simulate() crashed")
        return jsonify({"error": f"Internal error: {exc}"}), 500


def _simulate_worker(data: Dict[str, Any]) -> tuple[Dict[str, Any], int]:
    """Run simulation in a real OS thread so eventlet greenlets stay responsive."""

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
        return {"error": "At least 2 candidates required"}, 400

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

    return {
        "config":                data,
        "voters_snapshot":       voters_snapshot,
        "candidates":            candidates_out,
        "methods":               methods_out,
        "condorcet_winner":      condorcet_winner,
        "blank_rate":            round(blank_pct, 4),
        "campaign_trajectory":   campaign_trajectory,
        "inter_method_agreement": _inter_method_agreement(methods_out),
        "condorcet_exists":      condorcet_winner is not None,
    }, 200


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
@sim_limiter.limit("20 per minute")
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


@election_bp.route("/interpret", methods=["POST"])
def interpret() -> tuple[Response, int]:
    """
    POST /api/election/interpret

    Deterministic text interpretation of a /simulate result.
    No new simulation — pure rule-based analysis.

    Body: { ...ElectionResult, lang: 'fr' | 'en' }
    """
    data = request.get_json() or {}
    lang = str(data.get("lang", "fr")) if str(data.get("lang", "fr")) in ("fr", "en") else "fr"
    T    = _T[lang]

    methods_raw        = data.get("methods", {}) or {}
    condorcet_winner   = data.get("condorcet_winner")
    condorcet_exists   = bool(data.get("condorcet_exists", condorcet_winner is not None))
    inter_agreement    = float(data.get("inter_method_agreement", 0.0))
    blank_rate         = float(data.get("blank_rate", 0.0))
    blank_rule         = str((data.get("config") or {}).get("blank_vote", {}).get("rule", "symbolic"))

    if not methods_raw:
        return jsonify({"error": "No methods data provided"}), 400

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

    return jsonify({
        "headline":           headline,
        "condorcet_analysis": condorcet_analysis,
        "divergence_reason":  divergence_reason,
        "method_groups":      method_groups,
        "best_by_regret":     best_by_regret,
        "worst_by_regret":    worst_by_regret,
        "blank_analysis":     blank_analysis,
        "pedagogical_note":   pedagogical_note,
        "key_facts":          key_facts,
    }), 200


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


@election_bp.route("/simulate-pipeline", methods=["POST"])
def simulate_pipeline() -> tuple[Response, int]:
    """
    POST /api/election/simulate-pipeline

    Runs the election simulation and returns intermediate voter snapshots for
    each model stage, enabling step-by-step animation in the frontend.

    Steps returned (only active models generate a step):
      base        — always
      campaign    — if campaign.enabled
      contagion   — if blank_vote.contagion.enabled AND blank_vote.enabled
      information — if information_model.enabled
      results     — always (final winners)
    """
    import copy

    data = request.get_json() or {}

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
        return jsonify({"error": "At least 2 candidates required"}), 400

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

    return jsonify({
        "steps":      steps,
        "candidates": cands_out,
        "num_steps":  len(steps),
    }), 200


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


@election_bp.route("/coalition", methods=["POST"])
@sim_limiter.limit("20 per minute")
def coalition() -> tuple[Response, int]:
    """
    POST /api/election/coalition

    Compute D'Hondt seat allocation from election vote shares, then
    form a minimal government coalition per winning method, returning:
      - per-method seat allocation + coalition
      - coalition_spread per method (ideological variance of coalition)
      - pedagogical summary comparing coalition centrism across methods
    """
    data = request.get_json() or {}

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
        return jsonify({"error": "At least 2 candidates required"}), 400

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

    return jsonify({
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
    }), 200


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


@election_bp.route("/districts", methods=["POST"])
@sim_limiter.limit("10 per minute")
def districts() -> tuple[Response, int]:
    """
    POST /api/election/districts

    Simulate N districts with locally shifted ideology distributions.
    Each district elects its winner by FPTP (plurality).
    National parliament:
      - FPTP:         sum of district wins
      - Proportional: D'Hondt on aggregated national vote shares
    Also computes national Condorcet winner from all voters pooled.
    """
    data = request.get_json() or {}

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
        return jsonify({"error": "At least 2 candidates required"}), 400

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

    return jsonify({
        "districts":              district_results,
        "parliament_fptp":        parliament_fptp,
        "parliament_proportional": parliament_proportional,
        "national_vote_share":    national_vote_share,
        "distortion":             distortion,
        "condorcet_winner_national": condorcet_national,
        "fptp_winner":            fptp_winner,
        "proportional_winner":    proportional_winner,
        "num_districts":          num_districts,
    }), 200


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


@election_bp.route("/primary", methods=["POST"])
@sim_limiter.limit("15 per minute")
def primary() -> tuple[Response, int]:
    """
    POST /api/election/primary

    Two-round system:
      Round 1 — each party holds an internal primary among its partisan voters.
               The primary winner becomes that party's general-election candidate.
      Round 2 — general election among one candidate per party.

    Also computes what would have happened if party centres (not primary winners)
    had run directly ("without_primaries_winner").
    """
    data = request.get_json() or {}

    parties_raw        = data.get("parties", [])
    general_num_voters = max(50, min(2000, int(data.get("general_num_voters", 500))))
    general_ideology   = str(data.get("general_ideology", "random"))
    primary_method     = str(data.get("primary_method", "plurality"))
    general_method     = str(data.get("general_method",  "plurality"))
    seed               = int(data.get("seed", 42))

    if len(parties_raw) < 2:
        return jsonify({"error": "At least 2 parties required"}), 400

    for p in parties_raw:
        if len(p.get("primary_candidates", [])) < 2:
            return jsonify({"error": f"Party '{p.get('name')}' needs at least 2 primary candidates"}), 400

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

    return jsonify({
        "primaries":              primaries_out,
        "general_ballot":         [c["name"] for c in general_ballot_cands],
        "general_winner":         general_winner_name,
        "general_runner_up":      general_runner_up,
        "general_vote_shares":    gen_vote_shares,
        "median_voter_distance":  median_voter_distance,
        "without_primaries_winner": no_primary_winner,
    }), 200


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


@election_bp.route("/adaptive", methods=["POST"])
@sim_limiter.limit("10 per minute")
def adaptive() -> tuple[Response, int]:
    """
    POST /api/election/adaptive

    Simulate N rounds of adaptive voting:
      Round 0 — sincere vote (no polls yet)
      Round k — strategic voters whose 1st choice polls below
                strategic_threshold switch to their best viable alternative.

    Supports: plurality, irv, borda, schulze, approval.
    Tracks convergence (winner stable for 2 consecutive rounds).
    """
    data = request.get_json() or {}

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
        return jsonify({"error": "At least 2 candidates required"}), 400

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

    return jsonify({
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
    }), 200


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


@election_bp.route("/historical-replay", methods=["POST"])
@sim_limiter.limit("10 per minute")
def historical_replay() -> tuple[Response, int]:
    """
    POST /api/election/historical-replay

    Simulate a historical election scenario day by day with optional
    candidate position overrides. Returns per-day vote shares and winners.
    """
    data        = request.get_json() or {}
    scenario_id = str(data.get("scenario_id", "france2002"))
    overrides   = data.get("overrides", [])
    num_days    = max(1, min(60, int(data.get("num_days", 30))))
    seed        = int(data.get("seed", 42))

    cfg = _REPLAY_SCENARIOS.get(scenario_id)
    if not cfg:
        return jsonify({"error": f"Unknown scenario: {scenario_id}"}), 400

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

    return jsonify({
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
    }), 200


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


@election_bp.route("/jury", methods=["POST"])
@sim_limiter.limit("10 per minute")
def jury() -> tuple[Response, int]:
    """
    POST /api/election/jury

    Simulate the Condorcet Jury Theorem: voters with individual
    competence p > 0.5 aggregate collectively toward the "truth".

    Returns:
      - Per-method accuracy from Monte Carlo
      - Theoretical majority-rule accuracy (Condorcet formula)
      - Pre-computed competence curve (20 points × 5 methods) for the chart
    """
    data              = request.get_json() or {}
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

    return jsonify({
        "theoretical_accuracy": round(theoretical, 4),
        "methods":              methods_out,
        "best_method":          best_method,
        "worst_method":         worst_method,
        "voter_competence":     voter_competence,
        "num_voters":           num_voters,
        "competence_curve":     curve_points,
        "pedagogical_note":     note_fr,
        "pedagogical_note_en":  note_en,
    }), 200
