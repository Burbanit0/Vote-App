"""
arrow_criteria.py
Empirical verification of Arrow's impossibility theorem criteria for each
ranked voting method.

Arrow (1951) proved that no ranked voting rule can simultaneously satisfy
all desirable criteria when there are 3+ candidates. This module checks
each criterion empirically on a simulated population and measures how
frequently each one is violated.
"""
from typing import Callable, Dict, List, Optional, Any
import math

from .simulation_voting_utils import calculate_utility
from .simulation_ranked_utils import (
    get_condorcet_winner,
    get_plurality_winner,
    get_two_round_winner,
    get_borda_winner,
    get_approval_winner,
    get_irv_winner,
    get_coombs_winner,
    get_kemeny_young_winner,
    get_bucklin_winner,
    get_minimax_winner,
    get_schulze_winner,
    get_positional_score_winner,
)

# ── Method registry ────────────────────────────────────────────────────────

RANKED_METHODS: Dict[str, Callable[..., Any]] = {
    "plurality":        get_plurality_winner,
    "two_round":        get_two_round_winner,
    "borda":            get_borda_winner,
    "approval":         get_approval_winner,
    "irv":              get_irv_winner,
    "coombs":           get_coombs_winner,
    "bucklin":          get_bucklin_winner,
    "minimax":          get_minimax_winner,
    "schulze":          get_schulze_winner,
    "kemeny_young":     get_kemeny_young_winner,
    "condorcet":        get_condorcet_winner,
    "positional_score": get_positional_score_winner,
}

# ── Internal helpers ───────────────────────────────────────────────────────

def _get_condorcet_loser(rankings: List[List[str]]) -> Optional[str]:
    """Return the Condorcet loser (loses every pairwise duel), or None."""
    if not rankings:
        return None
    candidates = {c for r in rankings for c in r}
    for c in candidates:
        loses_to_all = True
        for other in candidates:
            if other == c:
                continue
            c_preferred = sum(
                1 for r in rankings
                if c in r and other in r and r.index(c) < r.index(other)
            )
            other_preferred = sum(
                1 for r in rankings
                if c in r and other in r and r.index(other) < r.index(c)
            )
            if c_preferred >= other_preferred:
                loses_to_all = False
                break
        if loses_to_all:
            return c
    return None


def _remove_candidate(
    rankings: List[List[str]], candidate: str
) -> List[List[str]]:
    """Return rankings with the given candidate removed from every ballot."""
    return [[c for c in r if c != candidate] for r in rankings]


def _reverse_rankings(rankings: List[List[str]]) -> List[List[str]]:
    """Return rankings with every ballot reversed (1st↔last)."""
    return [list(reversed(r)) for r in rankings]


def _promote_to_first(
    rankings: List[List[str]], candidate: str, fraction: float = 0.05
) -> List[List[str]]:
    """
    In `fraction` of ballots where `candidate` is ranked 2nd,
    move them to 1st place. Returns a new list (originals unchanged).
    """
    eligible = [i for i, r in enumerate(rankings) if len(r) >= 2 and r[1] == candidate]
    n_to_modify = max(1, math.floor(len(eligible) * fraction))
    to_modify = set(eligible[:n_to_modify])

    modified = []
    for i, r in enumerate(rankings):
        if i in to_modify:
            # swap 1st and 2nd
            new_r = [r[1], r[0]] + r[2:]
            modified.append(new_r)
        else:
            modified.append(r)
    return modified


# ── Criterion checks ───────────────────────────────────────────────────────

def check_condorcet_winner_criterion(
    rankings: List[List[str]], winner: Optional[str]
) -> bool:
    """
    True if: whenever a Condorcet winner exists, this method elects it.
    Vacuously True when no Condorcet winner exists.
    """
    condorcet = get_condorcet_winner(rankings)
    if condorcet is None:
        return True
    return winner == condorcet


def check_condorcet_loser_criterion(
    rankings: List[List[str]], winner: Optional[str]
) -> bool:
    """
    True if: the method never elects the Condorcet loser.
    Vacuously True when no Condorcet loser exists.
    """
    loser = _get_condorcet_loser(rankings)
    if loser is None:
        return True
    return winner != loser


def check_monotonicity(
    rankings: List[List[str]],
    winner: Optional[str],
    method_fn: Callable[..., Any],
) -> Optional[bool]:
    """
    True if: promoting the winner in some ballots cannot cause them to lose.

    Test: take voters who rank the winner 2nd, move the winner to 1st in
    5% of those ballots, re-run the election, verify the winner still wins.
    Returns None if the winner has no 2nd-place votes to promote.
    """
    if winner is None:
        return None
    eligible = [r for r in rankings if len(r) >= 2 and r[1] == winner]
    if not eligible:
        return None  # cannot test

    modified = _promote_to_first(rankings, winner, fraction=0.05)
    new_winner = method_fn(modified)
    return bool(new_winner == winner)


def check_iia(
    rankings: List[List[str]],
    candidate_names: List[str],
    winner: Optional[str],
    method_fn: Callable[..., Any],
) -> Dict[str, Any]:
    """
    Independence of Irrelevant Alternatives.

    True if: removing a non-winning candidate does not change the winner.
    Returns {satisfied, violation_rate, violations}.
    """
    if winner is None:
        return {"satisfied": None, "violation_rate": None, "violations": []}

    non_winners = [c for c in candidate_names if c != winner]
    if not non_winners:
        return {"satisfied": True, "violation_rate": 0.0, "violations": []}

    violations = []
    for removed in non_winners:
        trimmed = _remove_candidate(rankings, removed)
        # Filter out empty/trivial ballots
        trimmed = [r for r in trimmed if r]
        if len(trimmed) < 2:
            continue
        new_winner = method_fn(trimmed)
        if new_winner != winner:
            violations.append(removed)

    violation_rate = len(violations) / len(non_winners) if non_winners else 0.0
    return {
        "satisfied": len(violations) == 0,
        "violation_rate": round(violation_rate, 4),
        "violations": violations,
    }


def check_majority_criterion(
    rankings: List[List[str]], winner: Optional[str]
) -> bool:
    """
    True if: any candidate ranked first by >50% of voters wins.
    Vacuously True when no such candidate exists.
    """
    if not rankings:
        return True

    first_choice_counts: Dict[str, int] = {}
    for r in rankings:
        if r:
            first_choice_counts[r[0]] = first_choice_counts.get(r[0], 0) + 1

    majority_threshold = len(rankings) / 2
    for candidate, count in first_choice_counts.items():
        if count > majority_threshold:
            return winner == candidate
    return True  # vacuously satisfied


def check_reversal_symmetry(
    rankings: List[List[str]],
    winner: Optional[str],
    method_fn: Callable[..., Any],
) -> Optional[bool]:
    """
    True if: reversing all rankings does not elect the original winner.
    (If A wins normally, A should not win when all preferences are flipped.)
    """
    if winner is None:
        return None
    reversed_rankings = _reverse_rankings(rankings)
    reversed_winner = method_fn(reversed_rankings)
    return bool(reversed_winner != winner)


# ── Main function ──────────────────────────────────────────────────────────

def check_all_criteria(
    voters: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    issues: List[str],
) -> Dict[str, Any]:
    """
    Run all 6 Arrow criteria checks for every ranked voting method.

    Returns a dict keyed by method name, each value containing the 6
    criterion results plus a summary across all methods.
    """
    if not voters or not candidates:
        return {"summary": {}, "methods": {}}

    candidate_names = [c["name"] for c in candidates]

    # Pre-compute sincere rankings from utilities.
    utilities = {
        v["id"]: {
            c["name"]: calculate_utility(v, c, issues)["utility"]
            for c in candidates
        }
        for v in voters
    }
    rankings: List[List[str]] = [
        sorted(candidate_names, key=lambda n: -utilities[v["id"]][n])
        for v in voters
    ]

    method_results: Dict[str, Any] = {}
    satisfaction_counts: Dict[str, int] = {}

    for method_name, method_fn in RANKED_METHODS.items():
        winner = method_fn(rankings)

        # --- run every check ---
        cw   = check_condorcet_winner_criterion(rankings, winner)
        cl   = check_condorcet_loser_criterion(rankings, winner)
        mono = check_monotonicity(rankings, winner, method_fn)
        iia  = check_iia(rankings, candidate_names, winner, method_fn)
        maj  = check_majority_criterion(rankings, winner)
        rev  = check_reversal_symmetry(rankings, winner, method_fn)

        criteria: Dict[str, Any] = {
            "winner":              winner,
            "condorcet_winner":    cw,
            "condorcet_loser":     cl,
            "monotonicity":        mono,
            "iia":                 iia["satisfied"],
            "iia_violation_rate":  iia["violation_rate"],
            "majority":            maj,
            "reversal_symmetry":   rev,
        }
        method_results[method_name] = criteria

        # Count satisfied criteria (skip None and the float rate field)
        count = sum(
            1 for k, v in criteria.items()
            if k not in ("winner", "iia_violation_rate") and v is True
        )
        satisfaction_counts[method_name] = count

    # --- summary ---
    if satisfaction_counts:
        ranked_by_score = sorted(satisfaction_counts, key=lambda m: satisfaction_counts[m])
        summary = {
            "most_criteria_satisfied":  ranked_by_score[-1],
            "least_criteria_satisfied": ranked_by_score[0],
            "criteria_satisfaction_count": satisfaction_counts,
        }
    else:
        summary = {}

    return {"methods": method_results, "summary": summary}
