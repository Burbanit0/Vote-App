"""
simulation_compare.py — Method-comparison endpoints.

Serves SimulationComparePage (/simulation/compare) tabs:
Winner Matrix, Metrics, Strategic Impact, Condorcet Matrix,
Arrow Criteria, Sensitivity.

All endpoints use the spatial utility pipeline.
"""
from typing import Any, Dict, Optional

from flask import Blueprint, Response, request, jsonify

import random as _rng

import numpy as _np

from app.utils.simulation_voting_utils import calculate_utility, compute_strategic_plurality_vote, create_candidate, create_voter
from app.utils.simulation_ranked_utils import get_plurality_winner
from app.utils.simulation_metrics import compare_all_methods, compare_all_methods_mc, get_condorcet_matrix
from app.utils.arrow_criteria import check_all_criteria
from app.utils.blank_vote_rules import BlankVoteRule, apply_blank_rule
from app.utils.information_model import apply_information_asymmetry, compute_information_gap
from app.routes.simulation_helpers import (
    _parse_candidate_configs, _build_population,
    _PRESET_TO_DISTRIBUTION, _SCENARIO_METHODS,
    _build_scenario_candidates, _build_scenario_voters,
)
from app.constants import DEFAULT_ISSUES, ECONOMY_ISSUES, ENV_ISSUES, SOCIAL_ISSUES

simulation_compare_bp = Blueprint("simulation_compare", __name__, url_prefix="/simulations")


@simulation_compare_bp.route("/compare", methods=["POST"])
def compare_methods() -> tuple[Response, int]:
    """
    Run compare_all_methods on a fresh population and return per-method metrics.

    Body: {
        "num_voters":             int,
        "ideology_distribution":  str,               // default "random"
        "candidates":             [str|dict, ...],
        "blank_vote":             bool,              // default false
        "blank_rule":             str,               // "symbolic" | ...
        "information_model": {                        // optional
            "enabled":        bool,
            "media_bias":     {"0": float, ...},     // candidate_idx → [-1, 1]
            "voter_segments": {"low_info": float, "medium_info": float, "high_info": float}
        }
    }

    When information_model.enabled=true, utilities are distorted before
    voting.  The response includes:
        information_model.sincere_winner   — plurality winner on TRUE utilities
        information_model.perceived_winner — plurality winner on PERCEIVED utilities
        information_model.information_gap  — mean absolute utility distortion
    """
    data = request.get_json() or {}
    num_voters            = int(data.get("num_voters", 500))
    ideology_distribution = data.get("ideology_distribution", "random")
    raw_candidates        = data.get("candidates", ["Alice", "Bob", "Charlie"])
    blank_vote            = bool(data.get("blank_vote", False))
    blank_rule_str        = data.get("blank_rule", BlankVoteRule.SYMBOLIC.value)
    info_cfg              = data.get("information_model", {}) or {}
    info_enabled          = bool(info_cfg.get("enabled", False))

    candidate_configs = _parse_candidate_configs(raw_candidates)
    if len(candidate_configs) < 2:
        return jsonify({"error": "At least 2 candidates required"}), 400

    try:
        blank_rule = BlankVoteRule(blank_rule_str)
    except ValueError:
        return jsonify({"error": f"Unknown blank_rule '{blank_rule_str}'"}), 400

    try:
        voters, candidates, issues = _build_population(
            candidate_configs, num_voters, ideology_distribution
        )

        # ── Compute true utilities once ────────────────────────────────────
        true_utils_dict: Dict[Any, Dict[str, float]] = {
            v["id"]: {c["name"]: calculate_utility(v, c, issues)["utility"] for c in candidates}
            for v in voters
        }

        if info_enabled:
            # ── Build true utility matrix [voter_idx][cand_idx] ───────────
            candidate_names = [c["name"] for c in candidates]
            voter_ids       = [v["id"] for v in voters]
            true_matrix     = [
                [true_utils_dict[vid][cn] for cn in candidate_names]
                for vid in voter_ids
            ]

            media_bias    = info_cfg.get("media_bias", {})
            voter_segs    = info_cfg.get("voter_segments", {
                "low_info": 0.3, "medium_info": 0.5, "high_info": 0.2,
            })

            # ── Apply information asymmetry ────────────────────────────────
            perc_matrix = apply_information_asymmetry(
                true_matrix, media_bias, voter_segs,
            )
            perc_dict: Dict[Any, Dict[str, float]] = {
                vid: {cn: perc_matrix[i][j] for j, cn in enumerate(candidate_names)}
                for i, vid in enumerate(voter_ids)
            }

            # ── Sincere result (true utilities) ────────────────────────────
            sincere_sim = compare_all_methods(
                voters, candidates, issues,
                blank_vote=blank_vote,
                override_utilities=true_utils_dict,
            )
            sincere_winner = sincere_sim["methods"].get("plurality", {}).get("winner")
            sincere_condorcet = sincere_sim.get("condorcet_winner")

            # ── Perceived result (distorted utilities) ─────────────────────
            result = compare_all_methods(
                voters, candidates, issues,
                blank_vote=blank_vote,
                override_utilities=perc_dict,
            )
            perceived_winner = result["methods"].get("plurality", {}).get("winner")

            gap = compute_information_gap(true_matrix, perc_matrix)

            result["information_model"] = {
                "enabled":                True,
                "sincere_winner":         sincere_winner,
                "perceived_winner":       perceived_winner,
                "information_gap":        gap,
                "sincere_condorcet_winner": sincere_condorcet,
                "winners_differ":         sincere_winner != perceived_winner,
            }
        else:
            result = compare_all_methods(
                voters, candidates, issues,
                blank_vote=blank_vote,
                override_utilities=true_utils_dict,
            )
            result["information_model"] = {"enabled": False}

        if blank_vote:
            blank_pct = result.get("blank_pct", 0.0)
            for method_data in result["methods"].values():
                winner = method_data.get("winner")
                rule_result = apply_blank_rule(
                    winner=winner,
                    blank_pct=blank_pct,
                    rule=blank_rule,
                )
                method_data["blank_rule_applied"] = rule_result

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@simulation_compare_bp.route("/strategic-impact", methods=["POST"])
def strategic_impact() -> tuple[Response, int]:
    """
    Measure how bayesian_regret per method changes as the proportion of
    strategic voters increases.

    Body: {
        "num_voters": int,
        "ideology_distribution": str,
        "candidates": [str, ...] | [dict, ...],
        "strategic_percentages": [0, 10, 20, 30, 40, 50]
    }
    """
    data = request.get_json() or {}
    num_voters = int(data.get("num_voters", 500))
    ideology_distribution = data.get("ideology_distribution", "random")
    raw_candidates = data.get("candidates", ["Alice", "Bob", "Charlie"])
    strategic_percentages = data.get("strategic_percentages", [0, 10, 20, 30, 40, 50])

    candidate_configs = _parse_candidate_configs(raw_candidates)
    if len(candidate_configs) < 2:
        return jsonify({"error": "At least 2 candidates required"}), 400

    try:
        voters, candidates, issues = _build_population(candidate_configs, num_voters, ideology_distribution)

        utilities = {
            voter["id"]: {c["name"]: calculate_utility(voter, c, issues)["utility"] for c in candidates}
            for voter in voters
        }
        sincere = compare_all_methods(voters, candidates, issues)
        sorted_voters = sorted(voters, key=lambda v: -v.get("strategic_propensity", 0))

        results = []
        for pct in strategic_percentages:
            n_strategic = int(len(voters) * pct / 100)
            poll_standings: Dict[str, float] = {}
            for voter in voters:
                u = utilities[voter["id"]]
                first_choice: str = max(u, key=lambda k: u[k])
                poll_standings[first_choice] = poll_standings.get(first_choice, 0.0) + 1.0

            plurality_votes = []
            for i, voter in enumerate(sorted_voters):
                u = utilities[voter["id"]]
                choice: Optional[str]
                if i < n_strategic:
                    choice = compute_strategic_plurality_vote(voter, candidates, issues, poll_standings)
                else:
                    choice = max(u, key=lambda k: u[k])
                plurality_votes.append([choice] if choice else list(u.keys()))

            plurality_winner = get_plurality_winner(plurality_votes)
            if plurality_winner:
                total = sum(
                    max(utilities[v["id"]].values()) - utilities[v["id"]].get(plurality_winner, 0)
                    for v in voters
                )
                plurality_regret = round(total / len(voters), 6)
            else:
                plurality_regret = None

            methods_regret = {
                method: (
                    plurality_regret if method == "plurality"
                    else method_data["bayesian_regret"]
                )
                for method, method_data in sincere["methods"].items()
            }
            results.append({"strategic_pct": pct, "methods": methods_regret})

        return jsonify({"results": results}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@simulation_compare_bp.route("/condorcet-matrix", methods=["POST"])
def condorcet_matrix_route() -> tuple[Response, int]:
    """
    Build the full pairwise duel matrix for a fresh population.

    Body: { "num_voters": int, "ideology_distribution": str, "candidates": [...] }
    """
    data = request.get_json() or {}
    num_voters = int(data.get("num_voters", 500))
    ideology_distribution = data.get("ideology_distribution", "random")
    raw_candidates = data.get("candidates", ["Alice", "Bob", "Charlie"])

    candidate_configs = _parse_candidate_configs(raw_candidates)
    if len(candidate_configs) < 2:
        return jsonify({"error": "At least 2 candidates required"}), 400

    try:
        voters, candidates, issues = _build_population(candidate_configs, num_voters, ideology_distribution)
        result = get_condorcet_matrix(voters, candidates, issues)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@simulation_compare_bp.route("/sensitivity", methods=["POST"])
def sensitivity_analysis() -> tuple[Response, int]:
    """
    Vary one parameter and observe how winners and Bayesian regret change
    across all voting methods.

    Body: {
        "base_config": { "num_voters": int, "candidates": [...], "ideology_distribution": str },
        "variable": "ideology_distribution" | "num_voters" | "strategic_pct",
        "values": [value, ...]
    }
    """
    data = request.get_json() or {}
    base = data.get("base_config", {})
    variable = data.get("variable", "ideology_distribution")
    values = data.get("values", [])

    if not values:
        return jsonify({"error": "No values provided"}), 400

    base_num_voters = int(base.get("num_voters", 500))
    base_ideology = base.get("ideology_distribution", "random")
    raw_candidates = base.get("candidates", ["Alice", "Bob", "Charlie"])
    candidate_configs = _parse_candidate_configs(raw_candidates)

    if len(candidate_configs) < 2:
        return jsonify({"error": "At least 2 candidates required"}), 400

    results = []
    for value in values:
        try:
            if variable == "ideology_distribution":
                num_voters = base_num_voters
                ideology = str(value)
            elif variable == "num_voters":
                num_voters = max(10, int(value))
                ideology = base_ideology
            else:
                num_voters = base_num_voters
                ideology = base_ideology

            voters, candidates, issues = _build_population(candidate_configs, num_voters, ideology)
            comparison = compare_all_methods(voters, candidates, issues)
            winners = {m: d["winner"] for m, d in comparison["methods"].items()}
            regrets = {m: d["bayesian_regret"] for m, d in comparison["methods"].items()}

            if variable == "strategic_pct":
                pct = float(value)
                utilities = {
                    voter["id"]: {c["name"]: calculate_utility(voter, c, issues)["utility"] for c in candidates}
                    for voter in voters
                }
                sorted_voters = sorted(voters, key=lambda v: -v.get("strategic_propensity", 0))
                n_strategic = int(len(voters) * pct / 100)
                poll_standings_s: Dict[str, float] = {}
                for voter in voters:
                    u = utilities[voter["id"]]
                    top: str = max(u, key=lambda k: u[k])
                    poll_standings_s[top] = poll_standings_s.get(top, 0.0) + 1.0

                plurality_votes = []
                for i, voter in enumerate(sorted_voters):
                    u = utilities[voter["id"]]
                    choice = (
                        compute_strategic_plurality_vote(voter, candidates, issues, poll_standings_s)
                        if i < n_strategic else max(u, key=lambda k: u[k])
                    )
                    plurality_votes.append([choice] if choice else list(u.keys()))

                plurality_winner = get_plurality_winner(plurality_votes)
                winners["plurality"] = plurality_winner
                if plurality_winner:
                    total = sum(
                        max(utilities[v["id"]].values()) - utilities[v["id"]].get(plurality_winner, 0)
                        for v in voters
                    )
                    regrets["plurality"] = round(total / len(voters), 6)

            results.append({
                "value": value,
                "condorcet_winner": comparison["condorcet_winner"],
                "winners_by_method": winners,
                "regret_by_method": regrets,
            })

        except Exception as exc:
            results.append({
                "value": value,
                "condorcet_winner": None,
                "winners_by_method": {},
                "regret_by_method": {},
                "error": str(exc),
            })

    return jsonify({"variable": variable, "values": values, "results": results}), 200


@simulation_compare_bp.route("/arrow-criteria", methods=["POST"])
def arrow_criteria_route() -> tuple[Response, int]:
    """
    Empirically verify Arrow's impossibility theorem criteria.

    Body: { "num_voters": int, "ideology_distribution": str, "candidates": [...] }
    """
    data = request.get_json() or {}
    num_voters = int(data.get("num_voters", 300))
    ideology_distribution = data.get("ideology_distribution", "random")
    raw_candidates = data.get("candidates", ["Alice", "Bob", "Charlie"])

    candidate_configs = _parse_candidate_configs(raw_candidates)
    if len(candidate_configs) < 2:
        return jsonify({"error": "At least 2 candidates required"}), 400

    try:
        voters, candidates, issues = _build_population(candidate_configs, num_voters, ideology_distribution)
        result = check_all_criteria(voters, candidates, issues)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── /simulations/scenario ─────────────────────────────────────────────────

@simulation_compare_bp.route("/scenario", methods=["POST"])
def run_scenario() -> tuple[Response, int]:
    """
    Run a citizen-configured scenario through voting methods with and without blank vote.

    Body: {
        "candidates": [
            { "name": str, "ideology": float [-1,1],
              "positions": {"economy": float, "environment": float, "social": float},
              "is_blank": bool }
        ],
        "electorate": {
            "num_voters": int,
            "ideology_preset": "polarized"|"centrist"|"left"|"right"|"random",
            "dissatisfaction_rate": float [0,1]
        },
        "blank_rule": str,
        "methods": [str, ...]
    }
    """
    data = request.get_json() or {}
    candidates_raw    = data.get("candidates", [])
    electorate        = data.get("electorate", {})
    blank_rule_str    = data.get("blank_rule", BlankVoteRule.SYMBOLIC.value)
    requested_methods = data.get("methods", _SCENARIO_METHODS)

    num_voters           = max(10, int(electorate.get("num_voters", 500)))
    ideology_preset      = electorate.get("ideology_preset", "random")
    dissatisfaction_rate = max(0.0, min(1.0, float(electorate.get("dissatisfaction_rate", 0.2))))
    ideology_dist        = _PRESET_TO_DISTRIBUTION.get(ideology_preset, "random")

    try:
        blank_rule = BlankVoteRule(blank_rule_str)
    except ValueError:
        return jsonify({"error": f"Unknown blank_rule '{blank_rule_str}'"}), 400

    # Build candidates from 3 user-defined issue positions
    issues = DEFAULT_ISSUES
    real_candidates = []

    for i, c in enumerate(candidates_raw):
        if c.get("is_blank"):
            continue  # blank placeholder — handled via blank_vote flag
        ideology  = max(-1.0, min(1.0, float(c.get("ideology", 0.0))))
        pos       = (ideology + 1) / 2  # [-1, 1] → [0, 1]
        positions = c.get("positions", {})
        eco_pos   = max(0.0, min(1.0, float(positions.get("economy",     pos))))
        env_pos   = max(0.0, min(1.0, float(positions.get("environment", 1 - pos))))
        soc_pos   = max(0.0, min(1.0, float(positions.get("social",      1 - pos))))

        policies = {
            iss: eco_pos if iss in ECONOMY_ISSUES
                 else env_pos if iss in ENV_ISSUES
                 else soc_pos if iss in SOCIAL_ISSUES
                 else 0.5
            for iss in issues
        }
        real_candidates.append({
            "id": i, "name": c.get("name", f"Candidate {i + 1}"),
            "party": "Independent", "party_lean": ideology,
            "ideology_position": pos, "policies": policies,
            "charisma": 0.7, "scandals": 0,
            "campaign_funds": 500_000, "experience": 10, "popularity": 0.6,
        })

    if len(real_candidates) < 2:
        return jsonify({"error": "At least 2 real candidates required"}), 400

    voters = [
        create_voter(issues, i, ideology_distribution=ideology_dist)
        for i in range(num_voters)
    ]
    if dissatisfaction_rate > 0:
        for voter in voters:
            extra = dissatisfaction_rate * _rng.betavariate(2, 2)
            voter["blank_threshold"] = min(0.95, voter["blank_threshold"] + extra)

    try:
        result_no_blank   = compare_all_methods(voters, real_candidates, issues, blank_vote=False)
        result_with_blank = compare_all_methods(voters, real_candidates, issues, blank_vote=True)
    except Exception as e:
        return jsonify({"error": f"Simulation failed: {e}"}), 500

    blank_pct = result_with_blank.get("blank_pct", 0.0)
    for method_data in result_with_blank["methods"].values():
        method_data["blank_rule_applied"] = apply_blank_rule(
            winner=method_data.get("winner"), blank_pct=blank_pct, rule=blank_rule,
        )

    def _filter(result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "condorcet_winner": result.get("condorcet_winner"),
            "methods": {m: result["methods"][m] for m in requested_methods if m in result["methods"]},
        }

    return jsonify({
        "without_blank": _filter(result_no_blank),
        "with_blank":    {**_filter(result_with_blank), "blank_pct": blank_pct},
    }), 200


# ── /simulations/manipulability ──────────────────────────────────────────────

_MANIPULABILITY_METHODS = [
    "plurality", "borda", "irv", "two_round", "approval",
    "schulze", "coombs", "bucklin", "minimax",
]


@simulation_compare_bp.route("/manipulability", methods=["GET"])
def manipulability_analysis() -> tuple[Response, int]:
    """
    Estimate the Gibbard-Satterthwaite manipulability index for multiple
    voting methods on a synthetic population.

    Query params:
        num_candidates : int  (2–8,  default 4)
        num_voters     : int  (50–2000, default 500)
        methods        : str  comma-separated method keys or "all" (default)
        num_trials     : int  voters sampled per method (default 200)
        ideology       : str  ideology_distribution (default "random")

    Response (200):
    {
        "num_candidates": 4,
        "num_voters":     500,
        "results": [
            {
                "method":               "plurality",
                "manipulability_rate":  28.5,   // % of sampled voters
                "average_gain":         1.2,    // average rank improvement
                "num_manipulators":     57,
                "num_sampled":          200,
                "examples":             [...]
            },
            ...
        ]   // sorted by manipulability_rate descending
    }
    """
    try:
        num_candidates  = max(2, min(8,    int(request.args.get("num_candidates", 4))))
        num_voters      = max(50, min(2000, int(request.args.get("num_voters",     500))))
        num_trials_arg  = max(10, min(500,  int(request.args.get("num_trials",     200))))
        ideology_dist   = request.args.get("ideology", "random")
        methods_arg     = request.args.get("methods", "all")
    except (TypeError, ValueError) as e:
        return jsonify({"error": f"Invalid query parameter: {e}"}), 400

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
        return jsonify({"error": f"Population build failed: {exc}"}), 500

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
    if methods_arg.strip().lower() == "all":
        target_methods = _MANIPULABILITY_METHODS
    else:
        target_methods = [m.strip() for m in methods_arg.split(",") if m.strip()]
        if not target_methods:
            return jsonify({"error": "No valid methods specified"}), 400

    # ── Compute manipulability per method ──────────────────────────────────
    from app.utils.gibbard_satterthwaite import compute_manipulability_index

    results = []
    for method in target_methods:
        try:
            result = compute_manipulability_index(method, rankings, num_trials=num_trials_arg)
            results.append(result)
        except Exception as exc:
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

    return jsonify({
        "num_candidates": num_candidates,
        "num_voters":     num_voters,
        "ideology":       ideology_dist,
        "num_trials":     num_trials_arg,
        "results":        results,
    }), 200


# ── Vote-steps (step-by-step counting animation) ──────────────────────────────

_VOTE_STEPS_METHODS = {"irv", "borda", "plurality", "schulze", "approval"}
_PARTY_CYCLE_STEPS  = ["Green", "Conservative", "Liberal", "Independent"]


def _irv_steps(rankings: list, n_voters: int) -> list:
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

    rounds: list        = []
    active: set         = {c for r in rankings for c in r}
    last_eliminated     = None
    last_transfers      = None

    while True:
        counts: Counter = Counter()
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
            rounds.append({"round": rnum, "scores": scores,
                           "eliminated": last_eliminated, "transfers": last_transfers})
            rounds.append({"round": rnum + 1, "winner": winner})
            break

        # Find eliminated (lowest first-choice count, alphabetical tiebreak)
        min_c = min(counts.get(c, 0) for c in active)
        eliminated = next(c for c in sorted(active) if counts.get(c, 0) == min_c)

        # Compute vote transfers from eliminated candidate
        transfers: Counter = Counter()
        for r in rankings:
            active_r = [c for c in r if c in active]
            if active_r and active_r[0] == eliminated:
                rest = [c for c in active_r[1:] if c != eliminated]
                if rest:
                    transfers[rest[0]] += 1
        transfer_pct = {c: round(v / n_voters, 4) for c, v in transfers.items()} if transfers else None

        rounds.append({"round": rnum, "scores": scores,
                       "eliminated": last_eliminated, "transfers": last_transfers})
        active.remove(eliminated)
        last_eliminated = eliminated
        last_transfers  = transfer_pct

    return rounds


def _borda_steps(rankings: list) -> tuple:
    """Return (steps_list, winner) for Borda animation (one step per rank)."""
    from collections import defaultdict

    all_candidates = sorted({c for r in rankings for c in r})
    n = max((len(r) for r in rankings), default=0)
    cumulative: dict = {c: 0 for c in all_candidates}
    steps: list = []

    for rank_idx in range(n):
        points = n - 1 - rank_idx
        for r in rankings:
            if rank_idx < len(r):
                cumulative[r[rank_idx]] += points
        steps.append({
            "rank":           rank_idx + 1,
            "points_awarded": points,
            "tally":          dict(cumulative),
        })

    winner = max(cumulative, key=cumulative.get) if cumulative else None
    return steps, winner


def _schulze_matrices(rankings: list, candidate_names: list) -> tuple:
    """Return (duel_pct, path_pct, winner) for Schulze animation."""
    from collections import defaultdict
    from itertools import combinations, permutations

    n       = len(rankings) or 1
    cands   = candidate_names

    pref: dict = {c1: {c2: 0 for c2 in cands if c2 != c1} for c1 in cands}
    for c1, c2 in combinations(cands, 2):
        for r in rankings:
            try:
                p1, p2 = r.index(c1), r.index(c2)
                if p1 < p2:
                    pref[c1][c2] += 1
                else:
                    pref[c2][c1] += 1
            except ValueError:
                pass

    duel_pct = {c1: {c2: round(pref[c1][c2] / n, 4) for c2 in cands if c2 != c1} for c1 in cands}

    # Strongest-path (Floyd-Warshall style)
    strength: dict = {c1: {c2: pref[c1][c2] for c2 in cands if c2 != c1} for c1 in cands}
    for c1, c2, c3 in permutations(cands, 3):
        strength[c1][c2] = max(strength[c1][c2], min(strength[c1][c3], strength[c3][c2]))

    path_pct = {c1: {c2: round(strength[c1][c2] / n, 4) for c2 in cands if c2 != c1} for c1 in cands}

    wins: dict = {c: 0 for c in cands}
    for c1, c2 in combinations(cands, 2):
        if strength[c1][c2] > strength[c2][c1]:
            wins[c1] += 1
        elif strength[c2][c1] > strength[c1][c2]:
            wins[c2] += 1
    winner = max(wins, key=wins.get) if any(wins.values()) else (cands[0] if cands else None)
    return duel_pct, path_pct, winner


@simulation_compare_bp.route("/vote-steps", methods=["POST"])
def vote_steps() -> tuple[Response, int]:
    """
    POST /simulations/vote-steps

    Returns per-step intermediate data for animating how a single method
    counts the same set of ballots.

    Body:
        method    str   irv | borda | plurality | schulze | approval
        num_voters int
        candidates [str]
        ideology   str
        seed       int
    """
    from collections import Counter

    data          = request.get_json() or {}
    method        = str(data.get("method",    "plurality")).lower()
    num_voters    = max(10, min(500, int(data.get("num_voters", 100))))
    raw_cands     = [str(c) for c in data.get("candidates", ["Alice", "Bob", "Charlie"])][:8]
    ideology      = str(data.get("ideology",  "random"))
    seed          = int(data.get("seed",       42))

    if len(raw_cands) < 2:
        return jsonify({"error": "At least 2 candidates required"}), 400
    if method not in _VOTE_STEPS_METHODS:
        return jsonify({"error": f"method must be one of: {', '.join(sorted(_VOTE_STEPS_METHODS))}"}), 400

    _rng.seed(seed)
    _np.random.seed(seed)

    issues     = DEFAULT_ISSUES
    candidates = [
        {
            "id": i, "name": name,
            "party": _PARTY_CYCLE_STEPS[i % len(_PARTY_CYCLE_STEPS)],
            "party_lean": 0.0, "ideology_position": 0.5,
            "policies": {iss: 0.5 for iss in issues},
            "charisma": 0.7, "scandals": 0,
            "campaign_funds": 500_000, "experience": 10, "popularity": 0.6,
        }
        for i, name in enumerate(raw_cands)
    ]
    # Override with proper create_candidate for realistic utilities
    candidates = [
        create_candidate(issues, i, name, _PARTY_CYCLE_STEPS[i % len(_PARTY_CYCLE_STEPS)])
        for i, name in enumerate(raw_cands)
    ]
    voters = [create_voter(issues, i, ideology_distribution=ideology) for i in range(num_voters)]

    cand_names = [c["name"] for c in candidates]
    utilities: Dict[Any, Dict[str, float]] = {
        v["id"]: {c["name"]: calculate_utility(v, c, issues)["utility"] for c in candidates}
        for v in voters
    }
    rankings = [sorted(cand_names, key=lambda n, vid=v["id"]: -utilities[vid][n]) for v in voters]

    if method == "irv":
        return jsonify({"method": "irv", "rounds": _irv_steps(rankings, num_voters)}), 200

    if method == "borda":
        steps, winner = _borda_steps(rankings)
        return jsonify({"method": "borda", "num_candidates": len(cand_names),
                        "steps": steps, "winner": winner}), 200

    if method == "plurality":
        fc = Counter(r[0] for r in rankings if r)
        pct = {c: round(fc.get(c, 0) / num_voters, 4) for c in cand_names}
        winner = max(pct, key=pct.get) if pct else None
        return jsonify({"method": "plurality", "first_choices": pct, "winner": winner}), 200

    if method == "schulze":
        duel, path, winner = _schulze_matrices(rankings, cand_names)
        return jsonify({"method": "schulze", "duel_matrix": duel,
                        "path_matrix": path, "winner": winner}), 200

    # approval
    approval: Counter = Counter()
    threshold = 0.5
    for v in voters:
        u = utilities[v["id"]]
        for cname, score in u.items():
            if score >= threshold:
                approval[cname] += 1
    approval_pct = {c: round(approval.get(c, 0) / num_voters, 4) for c in cand_names}
    winner = max(approval_pct, key=approval_pct.get) if approval_pct else None
    return jsonify({"method": "approval", "threshold_used": threshold,
                    "approval_scores": approval_pct, "winner": winner}), 200


# ── Ideology map ──────────────────────────────────────────────────────────────

_IDEOLOGY_MAP_PARTIES = ["Green", "Liberal", "Conservative", "Independent"]


def _build_map_candidate(
    i: int,
    name: str,
    x: float,  # economy axis [-1, 1]
    y: float,  # social axis  [-1, 1]
    issues: list,
) -> Dict[str, Any]:
    """
    Build a candidate dict from explicit 2D ideological coordinates.

    X maps to economy dimension: -1 = far left, +1 = far right.
    Y maps to social dimension:  -1 = very liberal, +1 = very conservative.
    All issue positions derived deterministically (no noise) for stable
    real-time drag behaviour.
    """
    econ_pos = (x + 1) / 2          # [0, 1]
    soc_pos  = (y + 1) / 2          # [0, 1]
    env_pos  = 1.0 - econ_pos        # left = more environment spending

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
        "party":            _IDEOLOGY_MAP_PARTIES[i % len(_IDEOLOGY_MAP_PARTIES)],
        "party_lean":       x,          # already in [-1, 1]
        "ideology_position": econ_pos,
        "policies":         policies,
        "charisma":         0.7,
        "scandals":         0,
        "campaign_funds":   500_000,
        "experience":       10,
        "popularity":       0.6,
    }


@simulation_compare_bp.route("/ideology-map", methods=["POST"])
def ideology_map() -> tuple[Response, int]:
    """
    POST /simulations/ideology-map

    Compute 2D ideological map: voters coloured by which method's winner
    they prefer (method_a vs method_b).  Candidates are passed with explicit
    (x, y) positions so the client can drag them and call this endpoint to
    re-colour the voter dots without regenerating the electorate.

    Body:
        num_voters  int               [50, 500]
        candidates  [{name, x, y}]    x/y in [-1, 1]
        ideology    str               voter distribution
        seed        int               fixes the electorate
        method_a    str
        method_b    str
    """
    data         = request.get_json() or {}
    num_voters   = max(10, min(500, int(data.get("num_voters",  200))))
    candidate_specs = data.get("candidates", [])
    ideology     = str(data.get("ideology",   "random"))
    seed         = int(data.get("seed",        42))
    method_a     = str(data.get("method_a",   "plurality"))
    method_b     = str(data.get("method_b",   "schulze"))

    if len(candidate_specs) < 2:
        return jsonify({"error": "At least 2 candidates required"}), 400

    # Seed both PRNGs so the electorate is deterministic
    _rng.seed(seed)
    _np.random.seed(seed)

    issues = DEFAULT_ISSUES

    # Build candidates from explicit positions (no randomness in policy values)
    candidates: list[Dict[str, Any]] = []
    for i, spec in enumerate(candidate_specs[:8]):
        x    = max(-1.0, min(1.0, float(spec.get("x", 0.0))))
        y    = max(-1.0, min(1.0, float(spec.get("y", 0.0))))
        name = str(spec.get("name", f"Candidate {i + 1}"))
        candidates.append(_build_map_candidate(i, name, x, y, issues))

    # Build fixed electorate (seed controls this)
    voters = [create_voter(issues, i, ideology_distribution=ideology) for i in range(num_voters)]

    # Lightweight method comparison
    result          = compare_all_methods_mc(voters, candidates, issues)
    condorcet_winner = result.get("condorcet_winner")
    methods_data    = result.get("methods", {})

    winner_a: Optional[str] = (methods_data.get(method_a) or {}).get("winner")
    winner_b: Optional[str] = (methods_data.get(method_b) or {}).get("winner")

    # Pre-compute all voter utilities in one pass
    voter_utils: list[Dict[str, float]] = [
        {c["name"]: calculate_utility(voter, c, issues)["utility"] for c in candidates}
        for voter in voters
    ]

    # Build voter data for the map
    voter_data: list[Dict[str, Any]] = []
    prefers_a_count = 0

    for voter, utils in zip(voters, voter_utils):
        util_a = utils.get(winner_a, 0.0) if winner_a else 0.0
        util_b = utils.get(winner_b, 0.0) if winner_b else 0.0
        prefers_a = util_a >= util_b
        if prefers_a:
            prefers_a_count += 1

        # Map voter issue positions to 2D coordinates
        ip      = voter.get("issue_positions", {})
        voter_x = round(2.0 * ip.get("economy",        0.5) - 1.0, 3)
        voter_y = round(2.0 * ip.get("social_welfare",  0.5) - 1.0, 3)

        voter_data.append({
            "id":              voter["id"],
            "x":               voter_x,
            "y":               voter_y,
            "utility_winner_a": round(util_a, 4),
            "utility_winner_b": round(util_b, 4),
            "prefers_a":       prefers_a,
        })

    pct_a = round(prefers_a_count / num_voters, 4)
    pct_b = round(1.0 - pct_a, 4)

    return jsonify({
        "voters":     voter_data,
        "candidates": [
            {
                "name":  c["name"],
                "x":     round(2.0 * c["ideology_position"] - 1.0, 3),
                "y":     round(2.0 * c["policies"].get("social_welfare", 0.5) - 1.0, 3),
                "party": c["party"],
            }
            for c in candidates
        ],
        "winner_a":             winner_a,
        "winner_b":             winner_b,
        "method_a":             method_a,
        "method_b":             method_b,
        "condorcet_winner":     condorcet_winner,
        "pct_better_off_with_a": pct_a,
        "pct_better_off_with_b": pct_b,
    }), 200

