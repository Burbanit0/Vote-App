"""Tests for api/engine/utils/method_registry.py.

Nine workers used to carry their own `{name: winner_fn}` table ending in
`.get(method, get_plurality_winner)`. The default was the bug: an unlisted name
— or a typo — returned plurality's winner under the requested method's name.
`/adaptive` answered identically for `kemeny_young`, `minimax`, `star_voting`
and the literal string `not_a_method`.
"""
import pytest

from api.domain.election.workers_behavioral import (
    _NOTA_TRACKED,
    _ballot_complexity_worker,
    _nota_worker,
)
from api.domain.election.workers_mechanisms import _adaptive_worker
from api.engine.utils.method_registry import (
    RANKED_RULES,
    SCORE_RULES,
    UnknownMethod,
    rule_winner,
    supported,
)

# 3 ballots A>B>C against 2 ballots C>B>A: A wins every duel 3-2.
RANKED = [list("ABC")] * 3 + [list("CBA")] * 2
SCORES = [{"A": 5, "B": 3, "C": 0}] * 3 + [{"A": 0, "B": 3, "C": 5}] * 2


def test_a_name_no_rule_answers_to_raises_instead_of_defaulting():
    with pytest.raises(UnknownMethod) as exc:
        rule_winner("not_a_method", RANKED)
    # The message has to name the alternatives: the caller mistyped something.
    assert "not_a_method" in str(exc.value)
    assert "plurality" in str(exc.value)


def test_a_rule_asked_without_the_ballots_it_needs_raises():
    """Both directions: a score rule handed only rankings, and a ranked rule
    handed nothing. Silently returning None here would read as "nobody won"."""
    with pytest.raises(UnknownMethod, match="score rule"):
        rule_winner("star_voting", RANKED)
    with pytest.raises(UnknownMethod, match="ranked rule"):
        rule_winner("borda", scores=SCORES)


@pytest.mark.parametrize("method", sorted(RANKED_RULES))
def test_every_ranked_rule_returns_a_real_candidate(method):
    assert rule_winner(method, RANKED) in {"A", "B", "C"}


@pytest.mark.parametrize(
    "method",
    ["plurality", "borda", "irv", "two_round", "condorcet", "black", "schulze",
     "minimax", "copeland", "ranked_pairs", "kemeny_young", "bucklin", "coombs",
     "baldwin", "nanson", "dowdall"],
)
def test_the_condorcet_family_elects_the_condorcet_winner(method):
    """A beats B and C 3-2 in this profile and leads on first preferences, so
    every rule here elects A. Approval and anti-plurality are deliberately left
    out: approve-top-2 makes B the most-approved (5 of 10 approvals), and
    anti-plurality elects the candidate least often ranked last, which is also
    B — they are different rules, not wrong answers."""
    assert rule_winner(method, RANKED) == "A"


def test_approval_and_anti_plurality_legitimately_disagree_here():
    assert rule_winner("approval", RANKED) == "B"
    assert rule_winner("anti_plurality", RANKED) == "B"


@pytest.mark.parametrize("method", sorted(SCORE_RULES))
def test_every_score_rule_returns_a_name_for_score_ballots(method):
    winner = rule_winner(method, scores=SCORES)
    assert winner in {"A", "B", "C"}, method


def test_supported_lists_both_families():
    names = supported()
    assert "plurality" in names and "star_voting" in names
    assert names == sorted(names)
    assert supported(score=False) == sorted(RANKED_RULES)


def test_two_round_is_its_own_rule_not_plurality():
    """Both /nota and /ballot-complexity mapped `two_round` to
    get_plurality_winner. The rules differ exactly when nobody holds a majority:
    here A leads on first preferences 4-3-3 but loses the runoff to B 6-4."""
    profile = [list("ABC")] * 4 + [list("BCA")] * 3 + [list("CBA")] * 3
    assert rule_winner("plurality", profile) == "A"
    assert rule_winner("two_round", profile) == "B"


class TestWorkersRejectUnknownMethods:
    CANDIDATES = [
        {"name": "Alice", "x": -0.5, "y": 0.0},
        {"name": "Bob", "x": 0.4, "y": 0.0},
        {"name": "Carol", "x": 0.6, "y": 0.1},
    ]

    def test_adaptive_400s_instead_of_answering_as_plurality(self):
        base = {"candidates": self.CANDIDATES, "num_voters": 300, "seed": 7,
                "ideology": "polarized"}
        body, status = _adaptive_worker({**base, "method": "kemeny_young"})
        assert status == 400
        assert "kemeny_young" in body["error"]
        # …and the methods it does support still work, with different answers.
        plurality, _ = _adaptive_worker({**base, "method": "plurality"})
        borda, _ = _adaptive_worker({**base, "method": "borda"})
        assert plurality["final_winner"] != borda["final_winner"]

    def test_ballot_complexity_runs_two_round_as_two_round(self):
        """The ranked path through the registry. two_round and plurality differ
        when nobody holds a majority, which is the whole point of the panel --
        both used to call get_plurality_winner."""
        body, status = _ballot_complexity_worker({
            "candidates": self.CANDIDATES, "num_voters": 300, "seed": 3,
            "ideology": "polarized",
            "methods_to_compare": ["plurality", "two_round", "borda", "schulze"],
        })
        assert status == 200
        by_method = {r["method"]: r["winner"] for r in body["results"]}
        assert set(by_method) == {"plurality", "two_round", "borda", "schulze"}
        assert all(w in {"Alice", "Bob", "Carol"} for w in by_method.values())

    def test_ballot_complexity_400s_on_an_unsupported_name(self):
        body, status = _ballot_complexity_worker({
            "candidates": self.CANDIDATES, "num_voters": 300, "seed": 3,
            "methods_to_compare": ["plurality", "kemeny_young"],
        })
        assert status == 400
        assert "kemeny_young" in body["error"]

    def test_nota_400s_on_an_unsupported_name(self):
        body, status = _nota_worker({
            "candidates": self.CANDIDATES, "num_voters": 200, "seed": 5,
            "method": "kemeny_young",
        })
        assert status == 400
        assert "kemeny_young" in body["error"]

    def test_the_methods_each_worker_does_support_still_answer(self):
        """The guard rejects names, not work: every tracked method still runs."""
        body, status = _nota_worker({
            "candidates": self.CANDIDATES, "num_voters": 200, "seed": 5, "method": "borda",
        })
        assert status == 200
        assert set(body["method_comparison"]) == set(_NOTA_TRACKED)
