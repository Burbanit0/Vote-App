from itertools import permutations
from typing import Dict, List, Optional, Any

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
)
from .simulation_score_utils import (
    get_simple_score_winner,
    get_star_voting_winner,
    get_median_voting_winner,
    get_mean_median_hybrid_winner,
    get_variance_based_winner,
)

# Maximum number of voters sampled when computing strategic_vulnerability.
# Kept low because each call reruns the full election for every permutation.
_STRATEGIC_SAMPLE = 100


def compare_all_methods(voters: List[Dict], candidates: List[Dict], issues: List[str]) -> Dict[str, Any]:
    """
    Run every available voting method on the same population and return a
    structured comparison report.

    Returns:
        {
            "condorcet_winner": str | None,
            "methods": {
                "<method_name>": {
                    "winner": str | None,
                    "bayesian_regret": float | None,
                    "condorcet_consistent": bool | None,
                    "majority_satisfaction": float | None,
                    "strategic_vulnerability": float | None,
                },
                ...
            }
        }
    """
    if not voters or not candidates:
        return {"condorcet_winner": None, "methods": {}}

    # ------------------------------------------------------------------
    # 1. Pre-compute utilities for every (voter, candidate) pair.
    #    utilities[voter_id][candidate_name] = float
    # ------------------------------------------------------------------
    utilities: Dict[Any, Dict[str, float]] = {}
    for voter in voters:
        voter_utils = {}
        for c in candidates:
            voter_utils[c["name"]] = calculate_utility(voter, c, issues)["utility"]
        utilities[voter["id"]] = voter_utils

    # ------------------------------------------------------------------
    # 2. Build sincere rankings — each voter's candidates sorted by
    #    utility descending. Used by all ranked methods.
    # ------------------------------------------------------------------
    rankings: List[List[str]] = [
        sorted(utilities[v["id"]].keys(), key=lambda name: -utilities[v["id"]][name])
        for v in voters
    ]

    # ------------------------------------------------------------------
    # 3. Build score votes — utility mapped to integer 0-5.
    #    Used by score methods.
    # ------------------------------------------------------------------
    score_votes: List[Dict[str, int]] = [
        {
            name: max(0, min(5, round(5 * u_val)))
            for name, u_val in utilities[v["id"]].items()
        }
        for v in voters
    ]

    # ------------------------------------------------------------------
    # 4. Condorcet reference (used for condorcet_consistent metric).
    # ------------------------------------------------------------------
    condorcet_winner: Optional[str] = get_condorcet_winner(rankings)

    # ------------------------------------------------------------------
    # Metric helpers
    # ------------------------------------------------------------------

    def _bayesian_regret(winner_name: Optional[str]) -> Optional[float]:
        if not winner_name:
            return None
        total = sum(
            max(utilities[v["id"]].values()) - utilities[v["id"]].get(winner_name, 0)
            for v in voters
        )
        return round(total / len(voters), 6)

    def _majority_satisfaction(winner_name: Optional[str]) -> Optional[float]:
        if not winner_name:
            return None
        count = sum(
            1 for v in voters
            if all(
                utilities[v["id"]].get(winner_name, 0) > utilities[v["id"]].get(other, 0)
                for other in utilities[v["id"]]
                if other != winner_name
            )
        )
        return round(count / len(voters), 4)

    def _condorcet_consistent(winner_name: Optional[str]) -> Optional[bool]:
        if condorcet_winner is None:
            return None  # No Condorcet winner exists — criterion not applicable.
        return winner_name == condorcet_winner

    def _strategic_vulnerability_ranked(
        method_fn, winner_name: Optional[str]
    ) -> Optional[float]:
        """
        Proportion of sampled voters who can improve their outcome by
        submitting a non-sincere ranking.

        For each sampled voter, every permutation of their sincere ranking
        is tried. If any permutation changes the winner to a candidate the
        voter prefers over the current winner, the voter is counted as
        'vulnerable'.
        """
        if not winner_name:
            return None
        sample = voters[:_STRATEGIC_SAMPLE]
        vulnerable = 0
        for i, voter in enumerate(sample):
            u = utilities[voter["id"]]
            current_winner_u = u.get(winner_name, 0)
            sincere = rankings[i]
            # All rankings except this voter's.
            others = rankings[:i] + rankings[i + 1:]
            for perm in permutations(sincere):
                new_winner = method_fn(others + [list(perm)])
                if (
                    new_winner
                    and new_winner != winner_name
                    and u.get(new_winner, 0) > current_winner_u
                ):
                    vulnerable += 1
                    break
        return round(vulnerable / len(sample), 4)

    def _strategic_vulnerability_score(
        method_fn, winner_name: Optional[str]
    ) -> Optional[float]:
        """
        Proportion of sampled voters who can improve their outcome via
        bullet voting (give preferred candidate 5, everyone else 0).

        Each candidate is tried as the 'bullet' target in turn.
        """
        if not winner_name:
            return None
        sample = voters[:_STRATEGIC_SAMPLE]
        vulnerable = 0
        for i, voter in enumerate(sample):
            u = utilities[voter["id"]]
            current_winner_u = u.get(winner_name, 0)
            others = score_votes[:i] + score_votes[i + 1:]
            found = False
            for preferred in u:
                bullet = {name: (5 if name == preferred else 0) for name in u}
                result = method_fn(others + [bullet])
                new_winner = result.get("winner") if isinstance(result, dict) else result
                if (
                    new_winner
                    and new_winner != winner_name
                    and u.get(new_winner, 0) > current_winner_u
                ):
                    found = True
                    break
            if found:
                vulnerable += 1
        return round(vulnerable / len(sample), 4)

    def _build_metrics_ranked(method_fn, winner_name: Optional[str]) -> Dict:
        return {
            "winner": winner_name,
            "bayesian_regret": _bayesian_regret(winner_name),
            "condorcet_consistent": _condorcet_consistent(winner_name),
            "majority_satisfaction": _majority_satisfaction(winner_name),
            "strategic_vulnerability": _strategic_vulnerability_ranked(method_fn, winner_name),
        }

    def _build_metrics_score(method_fn, winner_name: Optional[str]) -> Dict:
        return {
            "winner": winner_name,
            "bayesian_regret": _bayesian_regret(winner_name),
            "condorcet_consistent": _condorcet_consistent(winner_name),
            "majority_satisfaction": _majority_satisfaction(winner_name),
            "strategic_vulnerability": _strategic_vulnerability_score(method_fn, winner_name),
        }

    # ------------------------------------------------------------------
    # Method registries
    # ------------------------------------------------------------------
    ranked_methods: Dict[str, Any] = {
        "plurality": get_plurality_winner,
        "two_round": get_two_round_winner,
        "borda": get_borda_winner,
        "approval": get_approval_winner,
        "irv": get_irv_winner,
        "coombs": get_coombs_winner,
        "bucklin": get_bucklin_winner,
        "minimax": get_minimax_winner,
        "schulze": get_schulze_winner,
        # Kemeny-Young is O(n!) per election call — keep sample small for large simulations.
        "kemeny_young": get_kemeny_young_winner,
    }

    score_methods: Dict[str, Any] = {
        "simple_score": get_simple_score_winner,
        "star_voting": get_star_voting_winner,
        "median_voting": get_median_voting_winner,
        "mean_median_hybrid": get_mean_median_hybrid_winner,
        "variance_based": get_variance_based_winner,
    }

    # ------------------------------------------------------------------
    # Run all methods
    # ------------------------------------------------------------------
    methods_result: Dict[str, Dict] = {}

    for name, fn in ranked_methods.items():
        winner = fn(rankings)
        methods_result[name] = _build_metrics_ranked(fn, winner)

    for name, fn in score_methods.items():
        result = fn(score_votes)
        winner = result.get("winner") if isinstance(result, dict) else result
        methods_result[name] = _build_metrics_score(fn, winner)

    return {
        "condorcet_winner": condorcet_winner,
        "methods": methods_result,
    }


def get_condorcet_matrix(
    voters: List[Dict],
    candidates: List[Dict],
    issues: List[str],
) -> Dict[str, Any]:
    """
    Build the full pairwise duel matrix for a population.

    For each ordered pair (A, B) returns the fraction of voters who prefer A
    over B, whether A wins the duel, and detects Condorcet cycles.

    Returns:
        {
            "candidates": [str, ...],
            "matrix": {
                "Alice": {
                    "Bob": {"pct_a": 0.58, "pct_b": 0.42, "winner": "Alice"},
                    ...
                }, ...
            },
            "condorcet_winner": str | None,
            "condorcet_cycles": [[str, str, str], ...]
        }
    """
    if not voters or not candidates:
        return {
            "candidates": [],
            "matrix": {},
            "condorcet_winner": None,
            "condorcet_cycles": [],
        }

    candidate_names = [c["name"] for c in candidates]
    n_voters = len(voters)

    # Pre-compute utilities once.
    utilities: Dict[Any, Dict[str, float]] = {
        voter["id"]: {
            c["name"]: calculate_utility(voter, c, issues)["utility"]
            for c in candidates
        }
        for voter in voters
    }

    # wins[A][B] = number of voters who strictly prefer A over B.
    wins: Dict[str, Dict[str, int]] = {
        a: {b: 0 for b in candidate_names if b != a}
        for a in candidate_names
    }
    for voter_utils in utilities.values():
        for a in candidate_names:
            for b in candidate_names:
                if a != b and voter_utils.get(a, 0) > voter_utils.get(b, 0):
                    wins[a][b] += 1

    # Build the matrix dict.
    matrix: Dict[str, Dict[str, Any]] = {}
    for a in candidate_names:
        matrix[a] = {}
        for b in candidate_names:
            if a == b:
                continue
            wins_a = wins[a][b]
            wins_b = wins[b][a]
            pct_a = round(wins_a / n_voters, 4)
            pct_b = round(wins_b / n_voters, 4)
            if wins_a > wins_b:
                duel_winner = a
            elif wins_b > wins_a:
                duel_winner = b
            else:
                duel_winner = "tie"
            matrix[a][b] = {"pct_a": pct_a, "pct_b": pct_b, "winner": duel_winner}

    # Condorcet winner: beats every other candidate head-to-head.
    condorcet_winner: Optional[str] = None
    for a in candidate_names:
        if all(matrix[a][b]["winner"] == a for b in candidate_names if b != a):
            condorcet_winner = a
            break

    # Condorcet cycles: find triples A > B > C > A.
    # Normalise each cycle to start with the lexicographically smallest name
    # to deduplicate rotations (A>B>C == B>C>A == C>A>B).
    seen: set = set()
    cycles: List[List[str]] = []
    for a in candidate_names:
        for b in candidate_names:
            if b == a or matrix[a][b]["winner"] != a:
                continue
            for c_name in candidate_names:
                if c_name == a or c_name == b:
                    continue
                if (
                    matrix[b][c_name]["winner"] == b
                    and matrix[c_name][a]["winner"] == c_name
                ):
                    raw = [a, b, c_name]
                    min_idx = raw.index(min(raw))
                    canonical = tuple(raw[min_idx:] + raw[:min_idx])
                    if canonical not in seen:
                        seen.add(canonical)
                        cycles.append(list(canonical))

    return {
        "candidates": candidate_names,
        "matrix": matrix,
        "condorcet_winner": condorcet_winner,
        "condorcet_cycles": cycles,
    }
