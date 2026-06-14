"""
api.domain.election._electorate — shared electorate-construction helpers,
extracted from the workers.py monolith so worker clusters can be split into
their own modules without importing back into workers.py (no cycles).

Pure builders: spec -> (candidates, voters, true utilities, names), the
method-comparison wrapper, and a lightweight winners-only snapshot.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional  # noqa: F401

from api.engine.utils.simulation_voting_utils import calculate_utility, create_voter
from api.engine.utils.simulation_metrics import compare_all_methods
from api.engine.utils.blank_vote_rules import BlankVoteRule, apply_blank_rule
from ._helpers import (
    build_candidate_from_xy as _build_candidate_from_xy,
    inter_method_agreement as _inter_method_agreement,
)


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
