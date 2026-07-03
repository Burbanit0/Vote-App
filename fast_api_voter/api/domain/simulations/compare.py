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
from typing import Any, Dict, List, Optional, Tuple


import random as _rng

import numpy as _np

from api.engine.utils.simulation_voting_utils import calculate_utility, compute_strategic_plurality_vote, create_candidate, create_voter
from api.engine.utils.simulation_ranked_utils import get_plurality_winner
from api.engine.utils.simulation_metrics import compare_all_methods, compare_all_methods_mc, get_condorcet_matrix
from api.engine.utils.arrow_criteria import check_all_criteria
from api.engine.utils.blank_vote_rules import BlankVoteRule, apply_blank_rule
from api.engine.utils.information_model import apply_information_asymmetry, compute_information_gap
from api.domain.simulations.helpers import (
    _parse_candidate_configs, _build_population,
    _PRESET_TO_DISTRIBUTION, _SCENARIO_METHODS,
)
from api.engine.constants import DEFAULT_ISSUES, ECONOMY_ISSUES, ENV_ISSUES, SOCIAL_ISSUES



# ── /simulations/compare ────────────────────────────────────────────────────

def _compare_methods_worker(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Run compare_all_methods on a fresh population and return per-method metrics.

    When information_model.enabled=true, utilities are distorted before voting
    and the response includes sincere vs perceived winners + information_gap.
    """
    num_voters            = int(data.get("num_voters", 500))
    ideology_distribution = data.get("ideology_distribution", "random")
    raw_candidates        = data.get("candidates", ["Alice", "Bob", "Charlie"])
    blank_vote            = bool(data.get("blank_vote", False))
    blank_rule_str        = data.get("blank_rule", BlankVoteRule.SYMBOLIC.value)
    info_cfg              = data.get("information_model", {}) or {}
    info_enabled          = bool(info_cfg.get("enabled", False))

    candidate_configs = _parse_candidate_configs(raw_candidates)
    if len(candidate_configs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    try:
        blank_rule = BlankVoteRule(blank_rule_str)
    except ValueError:
        return {"error": f"Unknown blank_rule '{blank_rule_str}'"}, 400

    try:
        voters, candidates, issues = _build_population(
            candidate_configs, num_voters, ideology_distribution
        )

        # ── Compute true utilities once ────────────────────────────────────
        true_utils_dict: Dict[Any, Dict[str, float]] = {
            v["id"]: {str(c["name"]): calculate_utility(v, c, issues)["utility"] for c in candidates}
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

        return result, 200
    except Exception as e:
        return {"error": str(e)}, 500




# ── /simulations/strategic-impact ───────────────────────────────────────────

def _strategic_impact_worker(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Measure how bayesian_regret per method changes as the proportion of
    strategic voters increases.
    """
    num_voters = int(data.get("num_voters", 500))
    ideology_distribution = data.get("ideology_distribution", "random")
    raw_candidates = data.get("candidates", ["Alice", "Bob", "Charlie"])
    strategic_percentages = data.get("strategic_percentages", [0, 10, 20, 30, 40, 50])

    candidate_configs = _parse_candidate_configs(raw_candidates)
    if len(candidate_configs) < 2:
        return {"error": "At least 2 candidates required"}, 400

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

        return {"results": results}, 200
    except Exception as e:
        return {"error": str(e)}, 500




# ── /simulations/condorcet-matrix ───────────────────────────────────────────

def _condorcet_matrix_worker(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """Build the full pairwise duel matrix for a fresh population."""
    num_voters = int(data.get("num_voters", 500))
    ideology_distribution = data.get("ideology_distribution", "random")
    raw_candidates = data.get("candidates", ["Alice", "Bob", "Charlie"])

    candidate_configs = _parse_candidate_configs(raw_candidates)
    if len(candidate_configs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    try:
        voters, candidates, issues = _build_population(candidate_configs, num_voters, ideology_distribution)
        result = get_condorcet_matrix(voters, candidates, issues)
        return result, 200
    except Exception as e:
        return {"error": str(e)}, 500




# ── /simulations/sensitivity ────────────────────────────────────────────────

def _sensitivity_worker(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Vary one parameter and observe how winners and Bayesian regret change
    across all voting methods.
    """
    base = data.get("base_config", {})
    variable = data.get("variable", "ideology_distribution")
    values = data.get("values", [])

    if not values:
        return {"error": "No values provided"}, 400

    base_num_voters = int(base.get("num_voters", 500))
    base_ideology = base.get("ideology_distribution", "random")
    raw_candidates = base.get("candidates", ["Alice", "Bob", "Charlie"])
    candidate_configs = _parse_candidate_configs(raw_candidates)

    if len(candidate_configs) < 2:
        return {"error": "At least 2 candidates required"}, 400

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

    return {"variable": variable, "values": values, "results": results}, 200




# ── /simulations/arrow-criteria ─────────────────────────────────────────────

def _arrow_criteria_worker(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """Empirically verify Arrow's impossibility theorem criteria."""
    num_voters = int(data.get("num_voters", 300))
    ideology_distribution = data.get("ideology_distribution", "random")
    raw_candidates = data.get("candidates", ["Alice", "Bob", "Charlie"])

    candidate_configs = _parse_candidate_configs(raw_candidates)
    if len(candidate_configs) < 2:
        return {"error": "At least 2 candidates required"}, 400

    try:
        voters, candidates, issues = _build_population(candidate_configs, num_voters, ideology_distribution)
        result = check_all_criteria(voters, candidates, issues)
        return result, 200
    except Exception as e:
        return {"error": str(e)}, 500




# ── /simulations/scenario ─────────────────────────────────────────────────

def _scenario_worker(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """Run a citizen-configured scenario through voting methods with and without blank vote."""
    candidates_raw    = data.get("candidates") or []
    electorate        = data.get("electorate") or {}
    blank_rule_str    = data.get("blank_rule") or BlankVoteRule.SYMBOLIC.value
    requested_methods = data.get("methods") or _SCENARIO_METHODS

    num_voters           = max(10, int(electorate.get("num_voters", 500)))
    ideology_preset      = electorate.get("ideology_preset", "random")
    dissatisfaction_rate = max(0.0, min(1.0, float(electorate.get("dissatisfaction_rate", 0.2))))
    ideology_dist        = _PRESET_TO_DISTRIBUTION.get(ideology_preset, "random")

    try:
        blank_rule = BlankVoteRule(blank_rule_str)
    except ValueError:
        return {"error": f"Unknown blank_rule '{blank_rule_str}'"}, 400

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
        return {"error": "At least 2 real candidates required"}, 400

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
        return {"error": f"Simulation failed: {e}"}, 500

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

    return {
        "without_blank": _filter(result_no_blank),
        "with_blank":    {**_filter(result_with_blank), "blank_pct": blank_pct},
    }, 200




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
        return {"error": f"Population build failed: {exc}"}, 500

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
_PARTY_CYCLE_STEPS  = ["Green", "Conservative", "Liberal", "Independent"]


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
    active: set[str]             = {c for r in rankings for c in r}
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
            rounds.append({"round": rnum, "scores": scores,
                           "eliminated": last_eliminated, "transfers": last_transfers})
            rounds.append({"round": rnum + 1, "winner": winner})
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
    all_candidates = sorted({c for r in rankings for c in r})
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
            "tally":          dict(cumulative),
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

_IDEOLOGY_MAP_PARTIES = ["Green", "Liberal", "Conservative", "Independent"]


def _build_map_candidate(
    i: int,
    name: str,
    x: float,  # economy axis [-1, 1]
    y: float,  # social axis  [-1, 1]
    issues: list[str],
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


def _ideology_map_worker(data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Compute 2D ideological map: voters coloured by which method's winner
    they prefer (method_a vs method_b). Candidates carry explicit (x, y)
    positions so the client can drag them and re-colour without regenerating
    the electorate.
    """
    num_voters   = max(10, min(500, int(data.get("num_voters",  200))))
    candidate_specs = data.get("candidates", [])
    ideology     = str(data.get("ideology",   "random"))
    seed         = int(data.get("seed",        42))
    method_a     = str(data.get("method_a",   "plurality"))
    method_b     = str(data.get("method_b",   "schulze"))

    if len(candidate_specs) < 2:
        return {"error": "At least 2 candidates required"}, 400

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

    return {
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
    }, 200


