"""Tests for api/engine/utils/method_registry.py.

Nine workers used to carry their own `{name: winner_fn}` table ending in
`.get(method, get_plurality_winner)`. The default was the bug: an unlisted name
— or a typo — returned plurality's winner under the requested method's name.
`/adaptive` answered identically for `kemeny_young`, `minimax`, `star_voting`
and the literal string `not_a_method`.
"""
import pytest

from api.domain.election.workers_behavioral import (
    BIAS_TRACKED,
    _NOTA_TRACKED,
    _ballot_complexity_worker,
    _behavioral_biases_worker,
    _electoral_fatigue_worker,
    _nota_worker,
)
from api.domain.election.workers_mechanisms import _adaptive_worker
from api.engine.utils.method_registry import (
    RANKED_RULES,
    SCORE_RULES,
    UTILITY_METHODS,
    UnknownMethod,
    rule_winner,
    supported,
    winner_from_utilities,
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
    ["plurality", "borda", "irv", "two_round", "black", "schulze",
     "minimax", "copeland", "ranked_pairs", "kemeny_young", "bucklin", "coombs",
     "baldwin", "nanson", "dowdall",
     # Registered alongside the rest once the registry became the one table;
     # all five are Condorcet methods, so they must elect A here too.
     "raynaud", "benham", "river", "smith_irv", "split_cycle"],
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

    def test_electoral_fatigue_400s_on_an_unsupported_name(self):
        """The fourth endpoint of the family: it ran `else: get_plurality_winner`
        over every election in the series, so a whole fatigue curve was
        plurality's under another rule's name."""
        base = {"candidates": self.CANDIDATES, "num_voters": 200, "seed": 3,
                "ideology": "polarized"}
        body, status = _electoral_fatigue_worker({**base, "method": "kemeny_young"})
        assert status == 400
        assert "kemeny_young" in body["error"]
        assert "plurality" in body["error"]  # names what it does support

        # …and the rules it does support give genuinely different curves, which
        # is what the silent plurality fallback was hiding. star_voting is one of
        # the three the old `else:` branch swallowed outright.
        curves = {}
        for method in ("plurality", "borda", "star_voting"):
            panel, status = _electoral_fatigue_worker({**base, "method": method})
            assert status == 200, method
            curves[method] = panel["winner_drift"]
        assert curves["borda"] != curves["plurality"]
        assert curves["star_voting"] != curves["plurality"]

    def test_behavioral_biases_400s_instead_of_naming_the_first_candidate(self):
        """The worst of the four fallbacks: `_compute_winners` only builds the
        tracked names, so `sincere_winners.get(method) or cand_names[0]` handed
        back whoever was first in the candidate list -- no votes involved -- and
        the pedagogical note asserted the winner held "sous la méthode
        'not_a_method'"."""
        base = {"candidates": self.CANDIDATES, "num_voters": 200, "seed": 5}
        for bad in ("not_a_method", "kemeny_young", "two_round"):
            body, status = _behavioral_biases_worker({**base, "method": bad})
            assert status == 400, bad
            assert bad in body["error"]

        ok, status = _behavioral_biases_worker({**base, "method": "borda"})
        assert status == 200
        # Every tracked rule still gets its sincere/biased pair, plus approval,
        # which this panel models separately through bullet voting.
        assert set(ok["method_sensitivity"]) == set(BIAS_TRACKED) | {"approval"}

    def test_the_methods_each_worker_does_support_still_answer(self):
        """The guard rejects names, not work: every tracked method still runs."""
        body, status = _nota_worker({
            "candidates": self.CANDIDATES, "num_voters": 200, "seed": 5, "method": "borda",
        })
        assert status == 200
        assert set(body["method_comparison"]) == set(_NOTA_TRACKED)


def test_schema_method_literals_match_workers():
    """The request schemas enumerate each panel's methods so a bad name is a 422
    at the contract boundary, not a 400 from inside the worker (Schemathesis
    reads that 400 as a broken contract, and it was one). The worker guard stays
    as the defence for direct calls -- these are two copies of one list, so this
    fails if either drifts."""
    from typing import get_args

    from api.domain.election.workers_behavioral import (
        BALLOT_METHODS, BIAS_TRACKED, CO_METHODS, _NOTA_TRACKED,
    )
    from api.domain.election.workers import PRIMARY_METHODS
    from api.domain.election.workers_advanced import DT_METHODS, PD_METHODS
    from api.domain.election.workers_dynamics import HOTELLING_METHODS
    from api.domain.election.workers_mechanisms import ADAPTIVE_METHODS
    from api.schemas import perturbers

    for literal, worker_tuple in (
        (perturbers.AdaptiveMethod,       ADAPTIVE_METHODS),
        (perturbers.BiasMethod,           BIAS_TRACKED),
        (perturbers.NotaMethod,           _NOTA_TRACKED),
        (perturbers.BallotMethod,         BALLOT_METHODS),
        (perturbers.FatigueMethod,        UTILITY_METHODS),
        (perturbers.ChoiceOverloadMethod, CO_METHODS),
        (perturbers.HotellingMethod,          HOTELLING_METHODS),
        (perturbers.DemographicTurnoutMethod, DT_METHODS),
        (perturbers.PrimaryMethod,            PRIMARY_METHODS),
        (perturbers.PartyDynamicsMethod,      PD_METHODS),
    ):
        assert set(get_args(literal)) == set(worker_tuple), literal

    # _co_winner tallies these three itself and hands every other name to
    # rule_winner as a ranked rule. A score rule added here (star_voting is the
    # obvious one) would pass both schema and guard and then raise inside the
    # worker -- a 500, since nothing catches UnknownMethod.
    self_tallied = {"plurality", "approval", "majority_judgment"}
    assert set(CO_METHODS) - self_tallied <= set(RANKED_RULES)


def test_theory_method_literals_match_workers():
    """The theory endpoints' Literals and the tuples their workers guard with are
    two copies of one list; this fails if either drifts."""
    from typing import get_args

    from api.domain.theory.workers import (
        _VIOLATIONS, IIA_METHODS, MA_METHODS, MT_RULES,
    )
    from api.schemas import theory

    for literal, worker_names in (
        (theory.ArrowMethod,        tuple(_VIOLATIONS)),
        (theory.IIAMethod,          IIA_METHODS),
        (theory.ManipulationMethod, MA_METHODS),
        (theory.TyrannyRule,        MT_RULES),
    ):
        assert set(get_args(literal)) == set(worker_names), literal


def test_every_panel_method_is_one_winner_from_utilities_can_answer():
    """Each guard is a subset of UTILITY_METHODS, so a name the request accepts
    can never reach UnknownMethod inside a worker."""
    from api.domain.election.workers_behavioral import (
        BALLOT_METHODS, BIAS_TRACKED, _NOTA_TRACKED,
    )

    for guard in (BALLOT_METHODS, BIAS_TRACKED, _NOTA_TRACKED):
        assert set(guard) <= set(UTILITY_METHODS), sorted(set(guard) - set(UTILITY_METHODS))


def test_winner_from_utilities_refuses_a_rule_a_utility_matrix_cannot_express():
    """The docstring promised this and did not do it: kemeny_young used to come
    back with a confident winner, and a score rule would have been handed raw
    0..1 utilities as if they were 0-5 ballots."""
    utilities = {1: {"A": 0.9, "B": 0.1}, 2: {"A": 0.2, "B": 0.8}}
    voters = [{"id": 1}, {"id": 2}]
    for method in ("kemeny_young", "minimax", "copeland", "nash", "not_a_method"):
        with pytest.raises(UnknownMethod):
            winner_from_utilities(method, utilities, voters)


def test_sincere_approval_agrees_with_the_engine_on_ties():
    """Four panels had their own copy of the tally, which broke ties by Counter
    insertion order -- so the same electorate could elect Bob here and Alice on
    /adaptive. Both now call the engine helper, which breaks ties lexicographically
    and returns None when nobody clears their own mean."""
    voters = [{"id": 1}, {"id": 2}]
    tied = {1: {"Bob": 0.9, "Alice": 0.1}, 2: {"Bob": 0.1, "Alice": 0.9}}
    assert winner_from_utilities("approval", tied, voters) == "Alice"

    flat = {1: {"Bob": 0.5, "Alice": 0.5}, 2: {"Bob": 0.5, "Alice": 0.5}}
    assert winner_from_utilities("approval", flat, voters) is None


def test_the_registry_answers_every_rule_the_engine_reports():
    """The registry and `compare_all_methods` used to keep separate tables, and
    they drifted both ways: the engine reported `split_cycle`, `river`,
    `raynaud`, `benham` and `smith_irv` while `rule_winner` raised UnknownMethod
    for all five. The engine reads the registry now; this fails if a rule is
    added to one without the other.

    Three reports are not registry rules and say why here rather than silently:
    evaluative reads raw utilities through a +1/0/-1 threshold, quadratic spends
    a credit budget, and random_ballot is a lottery reported by its most
    probable winner."""
    from api.engine.utils.simulation_metrics import compare_all_methods

    names = ["A", "B", "C"]
    utils = {
        i: {n: float(u) for n, u in zip(names, row)}
        for i, row in enumerate([(1.0, 0.5, 0.0)] * 4 + [(0.0, 1.0, 0.5)] * 3)
    }
    reported = set(compare_all_methods(
        [{"id": v} for v in utils], [{"name": n} for n in names], [],
        override_utilities=utils,
    )["methods"])
    not_registry_rules = {"evaluative", "quadratic", "random_ballot"}
    assert reported - not_registry_rules == set(RANKED_RULES) | set(SCORE_RULES)
    assert not_registry_rules <= reported


def test_each_name_resolves_to_the_rule_of_that_name():
    """A copy-paste swap -- `"raynaud": get_benham_winner` -- is lint-clean,
    and no behavioural test in this file catches it: the profiles here elect the
    same candidate under most Condorcet methods, so two of them trading places
    changes nothing observed while every compare_all_methods surface reports the
    wrong rule under both names. The functions follow `get_<name>_winner`, so
    say that. One documented exception."""
    exceptions = {"maximin": "get_maximin_score_winner"}
    for name, fn in {**RANKED_RULES, **SCORE_RULES}.items():
        assert fn.__name__ == exceptions.get(name, f"get_{name}_winner"), name


def test_compare_all_methods_reports_in_the_registry_order():
    """The key order is load-bearing, and no other test holds it: the snapshot
    serializer sorts keys and the drift test above compares sets.
    `_interpret_best_worst_by_regret` takes min/max by regret over a dict where
    many rules tie, so the first-listed tied rule wins -- measured on the default
    seed-42 /simulate, this order answers (plurality, approval) and the same
    dicts alphabetised answer (baldwin, anti_plurality)."""
    from api.engine.utils.simulation_metrics import compare_all_methods

    names = ["A", "B", "C"]
    utils = {i: {n: float(u) for n, u in zip(names, (1.0, 0.5, 0.0))} for i in range(5)}
    reported = list(compare_all_methods(
        [{"id": v} for v in utils], [{"name": n} for n in names], [],
        override_utilities=utils,
    )["methods"])
    assert reported == [
        "plurality", "two_round", "borda", "approval", "irv", "coombs",
        "bucklin", "minimax", "schulze", "kemeny_young", "copeland", "nanson",
        "baldwin", "ranked_pairs", "black", "anti_plurality", "dowdall",
        "raynaud", "benham", "river", "smith_irv", "split_cycle",
        "simple_score", "star_voting", "median_voting", "mean_median_hybrid",
        "variance_based", "cumulative", "maximin", "nash", "majority_judgment",
        "evaluative", "quadratic", "random_ballot",
    ]
