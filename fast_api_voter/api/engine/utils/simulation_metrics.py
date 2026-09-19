from itertools import permutations
from math import factorial
import random
from typing import Any, Callable, Dict, List, Optional

from .simulation_voting_utils import calculate_utility
from .simulation_ranked_utils import (
    get_condorcet_winner,
    kemeny_used_approximation,
    random_ballot_probabilities,
)
from .simulation_score_utils import (
    get_evaluative_winner,
)
from .method_registry import RANKED_RULES, SCORE_RULES
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



def bayesian_regret(
    utilities: Dict[Any, Dict[str, float]],
    voters: List[Dict[str, Any]],
    winner: Optional[str],
    ndigits: int = 6,
) -> Optional[float]:
    """Mean utility a voter loses by the election choosing `winner` instead of
    that voter's own favourite. 0 means every voter got their best candidate.

    `None` winner (no result to score) gives `None`. A candidate missing from a
    voter's row counts as utility 0, the same convention the callers' own
    `.get(winner, 0)` used. `max()` on an empty row would raise and take every
    method's regret with it, not just that voter's contribution -- atheris found
    exactly that shape in the since-deleted calculate_bayesian_regret -- but no
    caller can produce one: each builds a utility per candidate for every voter.
    """
    if not winner:
        return None
    total = sum(
        max(utilities[v["id"]].values()) - utilities[v["id"]].get(winner, 0) for v in voters
    )
    return round(total / len(voters), ndigits)


def compare_all_methods(
    voters: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    issues: List[str],
    blank_vote: bool = False,
    blank_candidate_name: str = "Blank",
    override_utilities: Optional[Dict[Any, Dict[str, float]]] = None,
    compute_strategic: bool = False,
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
        utilities = {
            voter["id"]: {
                c["name"]: calculate_utility(voter, c, issues)["utility"] for c in candidates
            }
            for voter in voters
        }

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
        return bayesian_regret(utilities, voters, winner_name)

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
            # `list(permutations(sincere))` materialised the whole factorial
            # BEFORE sampling it down, so the cap ran after the explosion it
            # names: 8 candidates built 40,320 tuples (~4.9 MB) to keep 100, and
            # that ran once per (sampled voter x ranked method) -- 330 times per
            # call. Below the cap the enumeration is exhaustive and cheaper than
            # sampling, so it stays; above it, k shuffles draw the same k
            # samples with no enumeration and stay O(k x n) at any width.
            if factorial(len(sincere)) <= _MAX_STRATEGIC_PERMS:
                perms = [list(p) for p in permutations(sincere)]
            else:
                # A generator of our own, seeded per voter -- not the process-wide
                # one, which left identical requests with different numbers per
                # process above the cap. Per voter, every rule is also probed
                # with the same manipulations, so their numbers compare.
                rng = random.Random(i)
                perms = [rng.sample(sincere, len(sincere))
                         for _ in range(_MAX_STRATEGIC_PERMS)]
            ballots = list(rankings)
            for perm in perms:
                # One ballot differs per iteration; reuse the list rather than
                # rebuilding `others + [perm]` 33,000 times per call.
                ballots[i] = perm
                new_winner = method_fn(ballots)
                if (
                    new_winner
                    and new_winner != winner_name
                    and u.get(new_winner, 0) > current_winner_u
                ):
                    vulnerable += 1
                    break
        return round(vulnerable / len(sample), 4)

    def _strategic_vulnerability_score(
        method_fn: Callable[..., Any], winner_name: Optional[str],
        ballots: List[Dict[str, Any]],
    ) -> Optional[float]:
        """
        Proportion of sampled voters who can improve their outcome via
        bullet voting (give preferred candidate 5, everyone else 0).

        Each candidate is tried as the 'bullet' target in turn, against
        `ballots` -- the ones the rule grades (5 is the top grade on either scale).
        """
        if not winner_name:
            return None
        sample = voters[:_STRATEGIC_SAMPLE]
        vulnerable = 0
        for i, voter in enumerate(sample):
            u = utilities[voter["id"]]
            current_winner_u = u.get(winner_name, 0)
            others = ballots[:i] + ballots[i + 1:]
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
        method_fn: Callable[..., Any], winner_name: Optional[str],
        ballots: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            "winner": winner_name,
            "bayesian_regret": _bayesian_regret(winner_name),
            "condorcet_consistent": _condorcet_consistent(winner_name),
            "majority_satisfaction": _majority_satisfaction(winner_name),
            "strategic_vulnerability":
                _strategic_vulnerability_score(method_fn, winner_name, ballots)
                if compute_strategic else None,
        }

    # ------------------------------------------------------------------
    # Run all methods
    # ------------------------------------------------------------------
    methods_result: Dict[str, Dict[str, Any]] = {}

    for name, fn in RANKED_RULES.items():
        winner = fn(rankings)
        entry = _build_metrics_ranked(fn, winner)
        if name == "kemeny_young":
            # Informative on the polity path only. Every request schema caps
            # candidates at 8, and a blank rule splices in at most one more, so
            # over HTTP this is now always True -- the approximation begins
            # above `_KY_EXACT_CAP` = 10. Kept because polity has no such cap
            # (`max_candidates_hard_cap` is 20) and it rides out through the
            # v1 envelope, which is `extra="allow"`.
            entry["kemeny_exact"] = not kemeny_used_approximation(rankings)
        methods_result[name] = entry

    for name, fn in SCORE_RULES.items():
        if name == "majority_judgment":
            continue   # reads raw utilities, not 0-5 ballots -- run just below
        raw = fn(score_votes)
        winner = raw.get("winner") if isinstance(raw, dict) else raw
        methods_result[name] = _build_metrics_score(fn, winner, score_votes)

    # ── Majority Judgment — uses raw float utilities, not 0-5 scaled ──────────
    mj_utility_scores: List[Dict[str, float]] = [
        utilities[v["id"]].copy() for v in voters
    ]
    mj_raw: Dict[str, Any]   = SCORE_RULES["majority_judgment"](mj_utility_scores)
    mj_winner: Optional[str] = str(mj_raw["winner"]) if mj_raw.get("winner") else None
    # The real rule on the ballots it grades: a stub here pinned MJ/EV at 0.0.
    mj_entry = _build_metrics_score(
        SCORE_RULES["majority_judgment"], mj_winner, mj_utility_scores,
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
        get_evaluative_winner, ev_winner, mj_utility_scores,
    )
    ev_entry["ev_scores"]       = ev_raw.get("scores", {})
    ev_entry["ev_distribution"] = ev_raw.get("distribution", {})
    methods_result["evaluative"] = ev_entry

    # ── Quadratic Voting — uses raw float utilities, not 0-5 scaled ──────────
    qv_utilities: List[Dict[str, float]] = [
        utilities[v["id"]].copy() for v in voters
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

    # ── Random ballot / random dictator (Gibbard, 1977) ──────────────────────
    # The realised winner is a lottery; we report the most-probable winner but
    # weight regret and majority-satisfaction by each candidate's win probability
    # (P = first-preference share). It is provably strategyproof, so its
    # strategic_vulnerability is exactly 0.
    rb_probs = random_ballot_probabilities(rankings)
    if rb_probs:
        rb_winner = min(rb_probs, key=lambda c: (-rb_probs[c], c))
        rb_regret = round(
            sum(p * (_bayesian_regret(c) or 0.0) for c, p in rb_probs.items()), 6
        )
        rb_majsat = round(
            sum(p * (_majority_satisfaction(c) or 0.0) for c, p in rb_probs.items()), 4
        )
        methods_result["random_ballot"] = {
            "winner":                rb_winner,
            "bayesian_regret":       rb_regret,
            "condorcet_consistent":  _condorcet_consistent(rb_winner),
            "majority_satisfaction": rb_majsat,
            "strategic_vulnerability": 0.0,   # strategyproof (Gibbard, 1977)
            "rb_probabilities":      {c: round(p, 4) for c, p in rb_probs.items()},
        }

    output: Dict[str, Any] = {
        "condorcet_winner": condorcet_winner,
        "methods": methods_result,
    }
    if blank_vote:
        output["blank_pct"] = blank_pct
    return output


#: `compare_all_methods_mc`'s narrower rule set (why narrower: its docstring),
#: looked up in the registry. These tuples set the Monte-Carlo table's order.
_MC_RANKED = (
    "plurality", "two_round", "borda", "approval", "irv",
    "coombs", "bucklin", "minimax", "schulze",
)
_MC_SCORE = (
    "simple_score", "star_voting", "median_voting",
    "mean_median_hybrid", "variance_based",
)


def compare_all_methods_mc(
    voters: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    issues: List[str],
) -> Dict[str, Any]:
    """
    Lightweight version of compare_all_methods optimised for Monte Carlo runs.

    Returns winner, bayesian_regret, majority_satisfaction and
    condorcet_consistent for a deliberately narrower 14-rule set.

    It originally existed to skip strategic_vulnerability, which is off by
    default now -- but the 14-rule set is the reason it survives. Measured at
    MonteCarloRequest's own ceiling (num_runs=500, num_voters=1000, 8
    candidates): this 82 ms/run -> 41 s, `compare_all_methods` 168 ms/run ->
    84 s, against WORKER_TIMEOUT_SECONDS = 180. worker_dispatch.py records that
    budget as calibrated against this exact request at 34 s, and that a 90 s
    timeout already failed for real in CI, so a 2.1x margin on the documented
    maximum is not enough. The tally is pure Python, so the inner
    ThreadPoolExecutor does not recover it.

    The cost of keeping it is real and should be said out loud: /monte-carlo and
    the Socket.IO stream report 14 of the engine's 34 rules, so a rule added to
    the registry never reaches them. Closing that wants a method
    allow-list on the engine (or a lower num_runs cap), not a second registry --
    but a 2x regression on a documented-max request is the wrong way to pay for
    it.
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
        return bayesian_regret(utilities, voters, winner)

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

    methods_result_mc: Dict[str, Dict[str, Any]] = {}

    for name in _MC_RANKED:
        winner = RANKED_RULES[name](rankings)
        methods_result_mc[name] = {
            "winner":                winner,
            "bayesian_regret":       _regret(winner),
            "majority_satisfaction": _satisfaction(winner),
            "condorcet_consistent":  (winner == condorcet_winner) if condorcet_winner else None,
        }

    for name in _MC_SCORE:
        raw_mc = SCORE_RULES[name](score_votes)
        winner = raw_mc.get("winner") if isinstance(raw_mc, dict) else raw_mc
        methods_result_mc[name] = {
            "winner":                winner,
            "bayesian_regret":       _regret(winner),
            "majority_satisfaction": _satisfaction(winner),
            "condorcet_consistent":  (winner == condorcet_winner) if condorcet_winner else None,
        }

    return {"condorcet_winner": condorcet_winner, "methods": methods_result_mc}


