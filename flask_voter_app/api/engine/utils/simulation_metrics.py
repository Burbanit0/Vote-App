from itertools import permutations
import random
from typing import Any, Callable, Dict, List, Optional

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
    get_copeland_winner,
    get_nanson_winner,
    get_baldwin_winner,
)
from .simulation_score_utils import (
    get_simple_score_winner,
    get_star_voting_winner,
    get_median_voting_winner,
    get_mean_median_hybrid_winner,
    get_variance_based_winner,
    get_majority_judgment_winner,
    get_evaluative_winner,
)
from .quadratic_voting import apply_quadratic_voting

# Maximum number of voters sampled when computing strategic_vulnerability.
# Kept low because each call reruns the full election for every permutation.
_STRATEGIC_SAMPLE = 15
_MAX_STRATEGIC_PERMS = 100


def _insert_blank(
    sorted_names: List[str],
    voter_utils: Dict[str, float],
    blank_threshold: float,
    blank_name: str,
) -> List[str]:  # noqa: E501
    """
    Insert the blank candidate into an already-sorted ranking.

    Blank is placed immediately after all candidates whose utility exceeds
    the voter's blank_threshold.  Candidates below the threshold are ranked
    after blank — expressing "I'd accept these over nothing, but barely."

    Example: threshold=0.5, utils={A:0.7, B:0.4, C:0.2}
             sorted = [A, B, C]  →  [A, Blank, B, C]
    """
    pos = sum(1 for n in sorted_names if voter_utils[n] > blank_threshold)
    return sorted_names[:pos] + [blank_name] + sorted_names[pos:]


def compare_all_methods(
    voters: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    issues: List[str],
    blank_vote: bool = False,
    blank_candidate_name: str = "Blank",
    override_utilities: Optional[Dict[Any, Dict[str, float]]] = None,
    compute_strategic: bool = True,
) -> Dict[str, Any]:
    """
    Run every available voting method on the same population and return a
    structured comparison report.

    When blank_vote=True, each voter's ranking includes a "Blank" candidate
    inserted at the position determined by their blank_threshold field.
    Score-based methods run on real candidates only (blank is rank-based
    by nature — it has no scorable platform).

    Returns:
        {
            "condorcet_winner": str | None,
            "blank_pct":        float | None,   # only when blank_vote=True
            "methods": {
                "<method_name>": {
                    "winner": str | None,
                    "bayesian_regret": float | None,
                    "condorcet_consistent": bool | None,
                    "majority_satisfaction": float | None,
                    "strategic_vulnerability": float | None,
                }, ...
            }
        }
    """
    if not voters or not candidates:
        return {"condorcet_winner": None, "methods": {}}

    # ------------------------------------------------------------------
    # 1. Pre-compute utilities for every (voter, candidate) pair.
    #    utilities[voter_id][candidate_name] = float
    #    When override_utilities is provided (e.g. from the information
    #    asymmetry model), skip calculate_utility() and use it directly.
    # ------------------------------------------------------------------
    if override_utilities is not None:
        utilities: Dict[Any, Dict[str, float]] = override_utilities
    else:
        utilities = {}
        for voter in voters:
            voter_utils = {}
            for c in candidates:
                voter_utils[c["name"]] = calculate_utility(voter, c, issues)["utility"]
            utilities[voter["id"]] = voter_utils

    # ------------------------------------------------------------------
    # 2. Build sincere rankings — each voter's candidates sorted by
    #    utility descending. Used by all ranked methods.
    #    When blank_vote=True, the blank candidate is spliced in at the
    #    position corresponding to each voter's blank_threshold.
    # ------------------------------------------------------------------
    candidate_names = [c["name"] for c in candidates]

    if blank_vote:
        rankings: List[List[str]] = [
            _insert_blank(
                sorted(candidate_names, key=lambda n: -utilities[v["id"]][n]),
                utilities[v["id"]],
                v.get("blank_threshold", 0.375),
                blank_candidate_name,
            )
            for v in voters
        ]
        blank_pct = round(
            sum(1 for r in rankings if r and r[0] == blank_candidate_name) / len(voters),
            4,
        )
    else:
        rankings = [
            sorted(utilities[v["id"]].keys(), key=lambda name: -utilities[v["id"]][name])
            for v in voters
        ]
        blank_pct = None

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
        method_fn: Callable[..., Optional[str]], winner_name: Optional[str]
    ) -> Optional[float]:
        """
        Proportion of sampled voters who can improve their outcome by
        submitting a non-sincere ranking.

        For each sampled voter, up to 200 random permutations of their
        sincere ranking are tried. If any permutation changes the winner
        to a candidate the voter prefers over the current winner, the
        voter is counted as 'vulnerable'.
        """
        if not winner_name:
            return None
        sample = voters[:_STRATEGIC_SAMPLE]
        vulnerable = 0
        for i, voter in enumerate(sample):
            u = utilities[voter["id"]]
            current_winner_u = u.get(winner_name, 0)
            sincere = rankings[i]
            others = rankings[:i] + rankings[i + 1:]
            # Cap permutations to avoid factorial explosion
            perms = list(permutations(sincere))
            if len(perms) > _MAX_STRATEGIC_PERMS:
                perms = random.sample(perms, _MAX_STRATEGIC_PERMS)
            for perm in perms:
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
        method_fn: Callable[..., Any], winner_name: Optional[str]
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

    def _build_metrics_ranked(
        method_fn: Callable[..., Optional[str]], winner_name: Optional[str]
    ) -> Dict[str, Any]:
        return {
            "winner": winner_name,
            "bayesian_regret": _bayesian_regret(winner_name),
            "condorcet_consistent": _condorcet_consistent(winner_name),
            "majority_satisfaction": _majority_satisfaction(winner_name),
            # strategic_vulnerability re-runs the method while perturbing every
            # sampled voter's ballot — the dominant cost. Callers that only need
            # winners (e.g. the playground) pass compute_strategic=False.
            "strategic_vulnerability":
                _strategic_vulnerability_ranked(method_fn, winner_name)
                if compute_strategic else None,
        }

    def _build_metrics_score(
        method_fn: Callable[..., Any], winner_name: Optional[str]
    ) -> Dict[str, Any]:
        return {
            "winner": winner_name,
            "bayesian_regret": _bayesian_regret(winner_name),
            "condorcet_consistent": _condorcet_consistent(winner_name),
            "majority_satisfaction": _majority_satisfaction(winner_name),
            "strategic_vulnerability":
                _strategic_vulnerability_score(method_fn, winner_name)
                if compute_strategic else None,
        }

    # ------------------------------------------------------------------
    # Method registries
    # ------------------------------------------------------------------
    ranked_methods: Dict[str, Callable[..., Optional[str]]] = {
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
        "copeland":     get_copeland_winner,
        "nanson":       get_nanson_winner,
        "baldwin":      get_baldwin_winner,
    }

    score_methods: Dict[str, Callable[..., Any]] = {
        "simple_score": get_simple_score_winner,
        "star_voting": get_star_voting_winner,
        "median_voting": get_median_voting_winner,
        "mean_median_hybrid": get_mean_median_hybrid_winner,
        "variance_based": get_variance_based_winner,
    }

    # ------------------------------------------------------------------
    # Run all methods
    # ------------------------------------------------------------------
    methods_result: Dict[str, Dict[str, Any]] = {}

    for name, fn in ranked_methods.items():
        winner = fn(rankings)
        entry = _build_metrics_ranked(fn, winner)
        if name == "kemeny_young":
            entry["kemeny_exact"] = not getattr(fn, "was_approx", False)
        methods_result[name] = entry

    for name, fn in score_methods.items():
        raw = fn(score_votes)
        winner = raw.get("winner") if isinstance(raw, dict) else raw
        methods_result[name] = _build_metrics_score(fn, winner)

    # ── Majority Judgment — uses raw float utilities, not 0-5 scaled ──────────
    mj_utility_scores: List[Dict[str, float]] = [
        dict(utilities[v["id"]]) for v in voters
    ]
    mj_raw: Dict[str, Any]   = get_majority_judgment_winner(mj_utility_scores)
    mj_winner: Optional[str] = str(mj_raw["winner"]) if mj_raw.get("winner") else None
    mj_entry = _build_metrics_score(
        lambda sv: {"winner": mj_winner},
        mj_winner,
    )
    mj_entry["mj_grades"]             = mj_raw.get("grades", {})
    mj_entry["mj_medians"]            = mj_raw.get("medians", {})
    mj_entry["mj_scores"]             = mj_raw.get("scores", {})
    mj_entry["mj_grade_distributions"] = mj_raw.get("grade_distributions", {})
    methods_result["majority_judgment"] = mj_entry

    # ── Evaluative voting (+1 / 0 / −1) — uses raw float utilities ───────────
    ev_raw: Dict[str, Any]    = get_evaluative_winner(mj_utility_scores)
    ev_winner: Optional[str]  = str(ev_raw["winner"]) if ev_raw.get("winner") else None
    ev_entry = _build_metrics_score(
        lambda sv: {"winner": ev_winner},
        ev_winner,
    )
    ev_entry["ev_scores"]       = ev_raw.get("scores", {})
    ev_entry["ev_distribution"] = ev_raw.get("distribution", {})
    methods_result["evaluative"] = ev_entry

    # ── Quadratic Voting — uses raw float utilities, not 0-5 scaled ──────────
    qv_utilities: List[Dict[str, float]] = [
        dict(utilities[v["id"]]) for v in voters
    ]
    qv_result = apply_quadratic_voting(qv_utilities, budget=100)
    qv_winner: Optional[str] = qv_result.get("winner")
    methods_result["quadratic"] = {
        "winner":                qv_winner,
        "bayesian_regret":       _bayesian_regret(qv_winner),
        "condorcet_consistent":  _condorcet_consistent(qv_winner),
        "majority_satisfaction": _majority_satisfaction(qv_winner),
        "strategic_vulnerability": None,   # QV strategic behaviour is complex
        "qv_scores":             qv_result.get("scores"),
        "qv_credits_used":       qv_result.get("total_credits_used"),
        "qv_credit_distribution": qv_result.get("credit_distribution"),
    }

    output: Dict[str, Any] = {
        "condorcet_winner": condorcet_winner,
        "methods": methods_result,
    }
    if blank_vote:
        output["blank_pct"] = blank_pct
    return output


def compare_all_methods_mc(
    voters: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    issues: List[str],
) -> Dict[str, Any]:
    """
    Lightweight version of compare_all_methods optimised for Monte Carlo runs.

    Skips strategic_vulnerability (permutation search) which is O(n! × voters)
    and would make 500-run MC unfeasibly slow. Returns winner, bayesian_regret,
    majority_satisfaction, and condorcet_consistent for every method.
    """
    if not voters or not candidates:
        return {"condorcet_winner": None, "methods": {}}

    candidate_names = [c["name"] for c in candidates]

    utilities: Dict[Any, Dict[str, float]] = {
        voter["id"]: {
            c["name"]: calculate_utility(voter, c, issues)["utility"]
            for c in candidates
        }
        for voter in voters
    }

    rankings: List[List[str]] = [
        sorted(candidate_names, key=lambda name: -utilities[v["id"]][name])
        for v in voters
    ]
    score_votes: List[Dict[str, int]] = [
        {
            name: max(0, min(5, round(5 * utilities[v["id"]][name])))
            for name in candidate_names
        }
        for v in voters
    ]

    condorcet_winner: Optional[str] = get_condorcet_winner(rankings)

    def _regret(winner: Optional[str]) -> Optional[float]:
        if not winner:
            return None
        return round(
            sum(
                max(utilities[v["id"]].values()) - utilities[v["id"]].get(winner, 0)
                for v in voters
            ) / len(voters),
            6,
        )

    def _satisfaction(winner: Optional[str]) -> Optional[float]:
        if not winner:
            return None
        return round(
            sum(
                1 for v in voters
                if all(
                    utilities[v["id"]].get(winner, 0) > utilities[v["id"]].get(other, 0)
                    for other in candidate_names if other != winner
                )
            ) / len(voters),
            4,
        )

    ranked_methods_mc: Dict[str, Callable[..., Optional[str]]] = {
        "plurality":        get_plurality_winner,
        "two_round":        get_two_round_winner,
        "borda":            get_borda_winner,
        "approval":         get_approval_winner,
        "irv":              get_irv_winner,
        "coombs":           get_coombs_winner,
        "bucklin":          get_bucklin_winner,
        "minimax":          get_minimax_winner,
        "schulze":          get_schulze_winner,
    }
    score_methods_mc: Dict[str, Callable[..., Any]] = {
        "simple_score":       get_simple_score_winner,
        "star_voting":        get_star_voting_winner,
        "median_voting":      get_median_voting_winner,
        "mean_median_hybrid": get_mean_median_hybrid_winner,
        "variance_based":     get_variance_based_winner,
    }

    methods_result_mc: Dict[str, Dict[str, Any]] = {}

    for name, fn in ranked_methods_mc.items():
        winner = fn(rankings)
        methods_result_mc[name] = {
            "winner":                winner,
            "bayesian_regret":       _regret(winner),
            "majority_satisfaction": _satisfaction(winner),
            "condorcet_consistent":  (winner == condorcet_winner) if condorcet_winner else None,
        }

    for name, fn in score_methods_mc.items():
        raw_mc = fn(score_votes)
        winner = raw_mc.get("winner") if isinstance(raw_mc, dict) else raw_mc
        methods_result_mc[name] = {
            "winner":                winner,
            "bayesian_regret":       _regret(winner),
            "majority_satisfaction": _satisfaction(winner),
            "condorcet_consistent":  (winner == condorcet_winner) if condorcet_winner else None,
        }

    return {"condorcet_winner": condorcet_winner, "methods": methods_result_mc}


def get_condorcet_matrix(
    voters: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
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
    seen: set[tuple[str, ...]] = set()
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
