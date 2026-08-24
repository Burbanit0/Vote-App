"""Anonymity: shuffling the ballots must never change the winner.

Anonymity is the axiom that a voting rule treats voters symmetrically — the
result depends on WHICH ballots were cast, never on the ORDER they were counted
in. A rule that fails it elects a different candidate depending on the order the
ballot box happens to be emptied, which no election could defend.

Thirteen of the twenty-six rules in this module used to fail it:

    get_plurality_winner([["C", "A", "B"], ["A", "B", "C"]])  ->  "C"
    get_plurality_winner([["A", "B", "C"], ["C", "A", "B"]])  ->  "A"

The cause was uniform: `max(counter.items(), key=lambda x: x[1])` returns the
first maximal element in the Counter's ITERATION order, which is insertion order
— the order candidates first appear across the ballots. Two variants of the same
mistake: `Counter.most_common(2)` picking the two-round runoff field, and a
`for cand in candidates` scan returning the first Schulze-condition candidate
from a first-seen list.

WHY NOTHING CAUGHT IT. The engine-parity harness detects exactly this — its
`strict_winner()` shuffles the ballots and checks the winner holds. But on a
mismatch it DISCARDS the scenario as an unusable tie rather than reporting it,
so the filter written to keep the parity fixture clean was quietly absorbing an
axiom violation. This file asserts the property directly, so it cannot be
filtered away again.

The fix is the tie-break convention this codebase already used in
get_evaluative_winner and get_maximin_winner:  min(names, key=lambda c: (-v, c))
— alphabetical. No deterministic tie-break can be both anonymous and neutral
(that is a theorem), and alphabetical is the standard, documented choice.
"""

import random

import pytest

from api.engine.utils import simulation_ranked_utils as ranked

# Every public rule in the module, discovered rather than listed, so a rule added
# later is covered without anyone remembering to add it here.
RULE_NAMES = sorted(
    name
    for name in dir(ranked)
    if name.startswith("get_") and name.endswith("_winner")
)


def _ballot_sets(rng: random.Random, candidates: list[str]) -> list[list[list[str]]]:
    """A spread of small profiles: the sizes where exact ties are common."""
    return [
        [rng.sample(candidates, len(candidates)) for _ in range(n)]
        for n in (2, 3, 4, 5, 6, 7)
    ]


def test_the_rule_list_is_not_empty():
    """A discovery bug that silently found no rules would make every test below
    pass vacuously."""
    assert len(RULE_NAMES) >= 20


@pytest.mark.parametrize("rule_name", RULE_NAMES)
def test_shuffling_the_ballots_never_changes_the_winner(rule_name):
    rule = getattr(ranked, rule_name)
    rng = random.Random(20260824)
    candidates = ["A", "B", "C"]

    for ballots in _ballot_sets(rng, candidates):
        expected = rule(ballots)
        for _ in range(40):
            shuffled = ballots[:]
            rng.shuffle(shuffled)
            assert rule(shuffled) == expected, (
                f"{rule_name} is not anonymous: the same ballots counted in a "
                f"different order elect {rule(shuffled)!r} instead of "
                f"{expected!r}.\n  ballots:  {ballots}\n  shuffled: {shuffled}"
            )


@pytest.mark.parametrize("rule_name", RULE_NAMES)
def test_relabelling_the_voters_never_changes_the_winner(rule_name):
    """The same property stated the other way round: duplicating the profile
    (each ballot twice) scales every count identically, so the winner must hold.
    Catches a tie-break that reads a raw count rather than a comparison."""
    rule = getattr(ranked, rule_name)
    rng = random.Random(99)
    candidates = ["A", "B", "C"]

    for ballots in _ballot_sets(rng, candidates):
        doubled = [b[:] for b in ballots for _ in range(2)]
        rng.shuffle(doubled)
        assert rule(doubled) == rule(ballots), (
            f"{rule_name} changed its winner when every ballot was cast twice"
        )


def test_the_documented_plurality_regression():
    """The concrete case from the bug report, pinned so the exact profile that
    exposed this cannot regress silently."""
    assert ranked.get_plurality_winner([["C", "A", "B"], ["A", "B", "C"]]) == "A"
    assert ranked.get_plurality_winner([["A", "B", "C"], ["C", "A", "B"]]) == "A"


def test_ties_break_alphabetically_not_by_appearance():
    """A perfect two-way tie resolves to the alphabetically first candidate,
    whichever order the ballots arrive in — the convention, stated once."""
    tied = [["B", "A", "C"], ["A", "B", "C"]]
    assert ranked.get_plurality_winner(tied) == "A"
    assert ranked.get_plurality_winner(list(reversed(tied))) == "A"
    assert ranked.get_borda_winner(tied) == "A"
    assert ranked.get_approval_winner(tied) == "A"
