"""The ranked rules draw an exact tie by the seeded lot (tie_lot.py), never by name or by the
listing order (#926; LISTING_ORDER_TIES.md). The client engine draws the same way over the same
names: playgroundVoting.parity.test.ts pins that against the fixture generated from these rules.

Each rule gets a profile where Ann and Cat tie exactly at the end and Zed trails: whatever the
rule's own steps (counts, rounds, duels, locks), it is left with the two of them and has to
draw. Ann is listed first AND first by name; the lot draws Cat (seed 0), so a listing-order or a
name tie-break fails here.
"""
import pytest

from api.engine.utils.method_registry import RANKED_RULES, rule_winner, winner_from_utilities
from api.engine.utils.tie_lot import draw

TIED = ["Ann", "Cat"]
# Mirror twins: every ballot of one kind has its mirror, so the rule cannot tell Ann from Cat.
BALLOTS = [["Ann", "Cat", "Zed"]] * 3 + [["Cat", "Ann", "Zed"]] * 3

# Kemeny-Young picks the optimal RANKING, and among equally good rankings the name-smallest
# (an ordering tie, not an aggregate one): not drawn yet, a #926 follow-up.
DRAWN = sorted(set(RANKED_RULES) - {"kemeny_young"})


def test_the_drawn_rules_are_every_ranked_rule_but_kemeny():
    assert len(DRAWN) == len(RANKED_RULES) - 1 == 21


@pytest.mark.parametrize("rule", DRAWN)
def test_a_tie_at_the_end_is_drawn_by_lot_not_by_name_or_listing(rule):
    fn = RANKED_RULES[rule]
    assert fn(BALLOTS) == draw(TIED, 0) == "Cat"
    # Nor does the order of the ballots (the voters) reach the draw.
    assert fn(list(reversed(BALLOTS))) == "Cat"


@pytest.mark.parametrize("rule", DRAWN)
def test_the_request_seed_reaches_the_ranked_rules_lot(rule):
    fn = RANKED_RULES[rule]
    drawn = {s: fn(BALLOTS, seed=s) for s in range(16)}
    assert all(w == draw(TIED, s) for s, w in drawn.items())
    assert set(drawn.values()) == set(TIED)  # both are elected under some seed


def test_rule_winner_and_winner_from_utilities_thread_the_seed_to_a_ranked_rule():
    for s in range(8):
        assert rule_winner("plurality", BALLOTS, seed=s) == draw(TIED, s)
    utilities = {
        v: ({"Ann": 1.0, "Cat": 0.5, "Zed": 0.0} if v % 2 else {"Ann": 0.5, "Cat": 1.0, "Zed": 0.0})
        for v in range(6)
    }
    voters = [{"id": v} for v in utilities]
    for method in ("plurality", "borda", "irv", "schulze", "two_round", "approval"):
        for s in range(4):
            assert winner_from_utilities(method, utilities, voters, seed=s) in TIED
    assert {winner_from_utilities("plurality", utilities, voters, seed=s) for s in range(16)} == set(TIED)


def test_a_full_tie_in_irv_and_coombs_is_drawn_not_no_winner():
    """25-25: every candidate is tied for last. IRV and Coombs used to return None."""
    profile = [["Bob", "Alice"]] * 25 + [["Alice", "Bob"]] * 25
    for rule in ("irv", "coombs"):
        assert RANKED_RULES[rule](profile) == draw(["Alice", "Bob"], 0)
        assert {RANKED_RULES[rule](profile, seed=s) for s in range(16)} == {"Alice", "Bob"}


def test_two_round_draws_its_finalists_and_the_runoff():
    """Three candidates level on first choices: the lot picks the first finalist, then the
    second among the rest; a runoff tied on the second round is drawn between the two."""
    ballots = [["Ann", "Cat", "Zed"], ["Cat", "Zed", "Ann"], ["Zed", "Ann", "Cat"]] * 2
    winners = {s: RANKED_RULES["two_round"](ballots, seed=s) for s in range(32)}
    assert set(winners.values()) == {"Ann", "Cat", "Zed"}  # every one can be drawn into it
    for s in range(8):
        assert winners[s] == RANKED_RULES["two_round"](list(reversed(ballots)), seed=s)


def test_compare_all_methods_draws_a_ranked_tie_with_the_request_seed():
    """The report's ranked rules draw an exact tie with the request's seed (as its score rules
    do), so a tie is drawn per request rather than always the same way."""
    from api.engine.utils.simulation_metrics import compare_all_methods

    # Every voter's twin has Ann's and Cat's utilities swapped, so the two tie exactly; Zed trails.
    rows = [(0.9, 0.6, 0.1), (0.6, 0.9, 0.1), (0.8, 0.5, 0.2), (0.5, 0.8, 0.2)]
    util = {v: dict(zip(("Ann", "Cat", "Zed"), row)) for v, row in enumerate(rows)}
    winners = {}
    for seed in range(12):
        report = compare_all_methods(
            [{"id": v} for v in util], [{"name": n} for n in ("Ann", "Cat", "Zed")], [],
            override_utilities=util, seed=seed,
        )["methods"]
        for rule in ("plurality", "borda", "irv", "schulze", "two_round"):
            assert report[rule]["winner"] == draw(TIED, seed), (rule, seed)
        winners[seed] = report["plurality"]["winner"]
    assert set(winners.values()) == set(TIED)
