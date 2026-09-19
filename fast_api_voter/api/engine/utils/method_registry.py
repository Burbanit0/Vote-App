"""
Look a voting rule up by the name an API request uses.

Every surface that lets a caller name a method used to carry its own
`{"plurality": get_plurality_winner, ...}` table ending in
`.get(method, get_plurality_winner)` — nine of them at the last count. The
default is the dangerous part: an unlisted name, or a typo, returned plurality's
winner *under the requested method's name*, so `/adaptive` answered identically
for `kemeny_young`, `minimax`, `star_voting` and the literal string
`not_a_method`, and nothing failed.

`rule_winner` raises `UnknownMethod` instead. A worker that catches it turns a
bad name into a 400 naming what it supports, rather than a confident wrong
answer.

Ranked rules take `rankings` (a list of candidate-name lists, best first) and
return the winner's name, or None when the rule elects nobody (an exact tie IRV
cannot break). Score rules take 0-5 `scores` (one dict per voter); some return
the name and some a `{"winner": ..., "details": ...}` report, so this module
unwraps the dict shape and both kinds end up with one signature.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from .simulation_ranked_utils import (
    get_anti_plurality_winner,
    get_approval_winner,
    get_approval_winner_sincere,
    get_baldwin_winner,
    get_benham_winner,
    get_black_winner,
    get_borda_winner,
    get_bucklin_winner,
    get_coombs_winner,
    get_copeland_winner,
    get_dowdall_winner,
    get_irv_winner,
    get_kemeny_young_winner,
    get_minimax_winner,
    get_nanson_winner,
    get_plurality_winner,
    get_ranked_pairs_winner,
    get_raynaud_winner,
    get_river_winner,
    get_schulze_winner,
    get_smith_irv_winner,
    get_split_cycle_winner,
    get_two_round_winner,
)
from .simulation_score_utils import (
    get_cumulative_winner,
    get_majority_judgment_winner,
    get_maximin_score_winner,
    get_mean_median_hybrid_winner,
    get_median_voting_winner,
    get_nash_winner,
    get_simple_score_winner,
    get_star_voting_winner,
    get_variance_based_winner,
)


class UnknownMethod(ValueError):
    """A method name no rule answers to."""


#: Every rule a name resolves to, in the order `compare_all_methods` reports
#: them -- which is why these two dicts are not alphabetical, and why
#: `test_compare_all_methods_reports_in_the_registry_order` pins it. The order
#: is load-bearing: `/interpret` takes the best and worst method by regret with
#: min/max over a list where many rules tie, so the first-listed of the tied
#: ones wins; re-alphabetising these dicts flips its default answer from
#: plurality to baldwin. (compare_all_methods also reports evaluative, quadratic
#: and random_ballot, which are not name-resolvable rules -- see the test.)
#:
#: This used to be one of three tables: `compare_all_methods` and
#: `compare_all_methods_mc` each kept their own. They had drifted apart both
#: ways -- five ranked rules the engine reported were unknown here, so a caller
#: asking this registry for `split_cycle` got UnknownMethod for a rule
#: `/simulate` reports, and this held `condorcet`, which nothing reported. That
#: one is the Condorcet *criterion* (`get_condorcet_winner` returns None when a
#: cycle leaves no Condorcet winner), not a rule; `compare_all_methods` reports
#: it separately as `condorcet_winner`, and no request can name it here.
RANKED_RULES: Dict[str, Callable[..., Optional[str]]] = {
    "plurality":      get_plurality_winner,
    "two_round":      get_two_round_winner,
    "borda":          get_borda_winner,
    "approval":       get_approval_winner,
    "irv":            get_irv_winner,
    "coombs":         get_coombs_winner,
    "bucklin":        get_bucklin_winner,
    "minimax":        get_minimax_winner,
    "schulze":        get_schulze_winner,
    # The costliest rule here: exact by DP over candidate subsets, O(2^m · m²)
    # in the CANDIDATE count, KwikSort above `_KY_EXACT_CAP`. ~4 ms at 8
    # candidates / 1000 voters, most of it the shared `_pairwise_wins` build.
    "kemeny_young":   get_kemeny_young_winner,
    "copeland":       get_copeland_winner,
    "nanson":         get_nanson_winner,
    "baldwin":        get_baldwin_winner,
    "ranked_pairs":   get_ranked_pairs_winner,
    "black":          get_black_winner,
    "anti_plurality": get_anti_plurality_winner,
    "dowdall":        get_dowdall_winner,
    "raynaud":        get_raynaud_winner,
    "benham":         get_benham_winner,
    "river":          get_river_winner,
    "smith_irv":      get_smith_irv_winner,
    "split_cycle":    get_split_cycle_winner,
}

SCORE_RULES: Dict[str, Callable[..., Any]] = {
    "simple_score":       get_simple_score_winner,
    "star_voting":        get_star_voting_winner,
    "median_voting":      get_median_voting_winner,
    "mean_median_hybrid": get_mean_median_hybrid_winner,
    "variance_based":     get_variance_based_winner,
    "cumulative":         get_cumulative_winner,
    "maximin":            get_maximin_score_winner,
    "nash":               get_nash_winner,
    # Grades on the raw utilities, not the 0-5 ballots the rules above read, so
    # `compare_all_methods` and `winner_from_utilities` both call it separately.
    "majority_judgment":  get_majority_judgment_winner,
}


def supported(*, ranked: bool = True, score: bool = True) -> List[str]:
    """The names `rule_winner` answers to, for an error message or a schema."""
    names = (list(RANKED_RULES) if ranked else []) + (list(SCORE_RULES) if score else [])
    return sorted(names)


def rule_winner(
    method: str,
    rankings: Optional[List[List[str]]] = None,
    scores: Optional[Sequence[Mapping[str, float]]] = None,
) -> Optional[str]:
    """The winner under `method`, or None if the rule elects nobody.

    Raises `UnknownMethod` for a name no rule answers to, and for a rule whose
    ballots the caller did not pass (a score rule needs `scores`).
    """
    if method in RANKED_RULES:
        if rankings is None:
            raise UnknownMethod(f"{method!r} is a ranked rule but no rankings were given")
        return RANKED_RULES[method](rankings)
    if method in SCORE_RULES:
        if scores is None:
            raise UnknownMethod(f"{method!r} is a score rule but no score ballots were given")
        result = SCORE_RULES[method](scores)
        winner = result.get("winner") if isinstance(result, dict) else result
        return str(winner) if winner else None
    raise UnknownMethod(f"unknown voting method {method!r} -- supported: {', '.join(supported())}")


#: The rules a voter -> candidate -> utility map can express. Ranked rules read
#: the rankings it induces; `approval` and `majority_judgment` read the
#: utilities themselves, which is why neither is a plain registry lookup.
UTILITY_METHODS: tuple[str, ...] = (
    "plurality", "borda", "irv", "schulze", "two_round",
    "approval", "majority_judgment", "star_voting",
)


def rankings_from_utilities(
    utilities: Mapping[Any, Mapping[str, float]], voters: Sequence[Mapping[str, Any]]
) -> List[List[str]]:
    """Each voter's candidates, their favourite first."""
    return [
        sorted(utilities[v["id"]].keys(), key=lambda n: -utilities[v["id"]][n])
        for v in voters
    ]


def winner_from_utilities(
    method: str,
    utilities: Mapping[Any, Mapping[str, float]],
    voters: Sequence[Mapping[str, Any]],
) -> Optional[str]:
    """The winner under `method`, read off a voter -> candidate -> utility map.

    Five dispatchers each rebuilt this: rankings from the utilities, 0-5 score
    ballots from the same, an if-chain over method names, and a silent
    `get_plurality_winner` at the end -- so /adaptive, /nota, /ballot-complexity
    and /electoral-fatigue all reported plurality's winner under whatever name
    was asked for. This is that, once, and it raises `UnknownMethod` instead.

    `voters` is the subset that actually voted (panels drop voters a ballot's
    complexity turned away, or who did not turn out), so every rule reads those
    voters' utilities alone.

    Returns None when the rule elects nobody -- an exact tie, or an approval
    round where no candidate cleared any voter's own mean.
    """
    if method not in UTILITY_METHODS:
        raise UnknownMethod(
            f"{method!r} cannot be read off a utility matrix -- "
            f"supported: {', '.join(UTILITY_METHODS)}"
        )
    if method == "approval":
        # Sincere approval: approve above your own mean. A ranking cannot
        # express where a voter's mean falls, so this reads the utilities --
        # and it is the engine's own helper, so these panels tie-break the same
        # way /adaptive does.
        return get_approval_winner_sincere({v["id"]: utilities[v["id"]] for v in voters})
    if method == "majority_judgment":
        # Also utility-native: MJ grades on the raw values, not a 0-5 rounding.
        raw = SCORE_RULES[method]([dict(utilities[v["id"]]) for v in voters])
        return str(raw["winner"]) if raw.get("winner") else None
    if method in SCORE_RULES:
        scores = [
            {n: max(0, min(5, round(5 * val))) for n, val in utilities[v["id"]].items()}
            for v in voters
        ]
        return rule_winner(method, scores=scores)
    return rule_winner(method, rankings_from_utilities(utilities, voters))
