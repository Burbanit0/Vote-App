"""Unit tests for Kemeny-Young: the ranking that most agrees with the
electorate's pairwise preferences wins, and its first-place candidate is the
winner. Exact up to `_KY_EXACT_CAP` candidates by DP over candidate subsets
(it enumerated all m! orderings until that got too slow to allow a cap wide
enough for the 8 candidates every request schema admits); KwikSort
approximation above the cap, which only polity reaches.
No dedicated test file existed before (PR #157's mutation-testing baseline
found 21 surviving mutants here)."""

import itertools
import random

from api.engine.utils.simulation_ranked_utils import (
    get_kemeny_young_winner, get_condorcet_winner, kemeny_used_approximation,
    _pairwise_wins, _kwik_sort, _kemeny_exact_winner, _KY_EXACT_CAP,
)
from api.engine.utils.simulation_metrics import compare_all_methods
from api.engine.utils.tie_lot import draw


def test_kemeny_young_elects_the_condorcet_winner_when_one_exists():
    ballots = (
        [["A", "B", "C"]] * 4
        + [["B", "A", "C"]] * 3
        + [["C", "A", "B"]] * 2
    )  # A beats B (6-3) and C (7-2) head-to-head.
    assert get_condorcet_winner(ballots) == "A"
    assert get_kemeny_young_winner(ballots) == "A"


def test_kemeny_young_resolves_a_top_cycle_via_the_best_agreeing_ranking():
    ballots = (
        [["A", "B", "C"]] * 6
        + [["B", "C", "A"]] * 4
        + [["C", "A", "B"]] * 3
    )
    assert get_condorcet_winner(ballots) is None
    assert get_kemeny_young_winner(ballots) == "A"


def test_kemeny_young_uses_the_exact_path_under_the_candidate_cap():
    ballots = (
        [["A", "B", "C"]] * 4
        + [["B", "A", "C"]] * 3
        + [["C", "A", "B"]] * 2
    )
    assert kemeny_used_approximation(ballots) is False


def test_kemeny_young_uses_the_approximation_path_over_the_candidate_cap():
    # 11 candidates. These profiles used 7, which was above the old cap of 6 but
    # is under the current one -- exact Kemeny is now DP over subsets rather than
    # m! enumeration, so the cap could go to 10 and cover every input any request
    # schema allows. Left at 7 they would assert nothing about KwikSort.
    ballots = [list("ABCDEFGHIJK")] * 3 + [list("KJIHGFEDCBA")] * 2
    assert kemeny_used_approximation(ballots) is True


def test_kemeny_young_single_and_empty():
    assert get_kemeny_young_winner([]) is None
    assert get_kemeny_young_winner([["A"]]) == "A"
    # Ballots that rank nobody: `votes` is non-empty so the first guard passes,
    # but no candidate exists. Without the empty-candidate guard the DP indexes
    # `candidates[-1]` on an empty list and raises.
    assert get_kemeny_young_winner([[], []]) is None
    assert kemeny_used_approximation([]) is False
    assert kemeny_used_approximation([[], []]) is False


def test_kemeny_young_approximation_path_actually_runs_kwiksort():
    """kemeny_used_approximation() only checks the candidate-count predicate --
    it never calls get_kemeny_young_winner, so it doesn't exercise _kwik_sort
    itself. This test drives the real approximation path (the >_KY_EXACT_CAP
    branch in get_kemeny_young_winner) end to end, which a
    coordinated seven-way sweep found had zero coverage in the non-benchmark
    suite despite the predicate having its own test above."""
    ballots = [list("ABCDEFGHIJK")] * 3 + [list("KJIHGFEDCBA")] * 2  # 11 > cap
    assert kemeny_used_approximation(ballots) is True

    # 3 ballots A>...>K against 2 ballots K>...>A: A wins every pairwise duel
    # 3-2, so it is the Condorcet winner and Kemeny-Young, being
    # Condorcet-consistent, must elect it. `assert winner in "ABCDEFG"` used to
    # stand here -- a substring test that passes for any single letter, which is
    # how _kwik_sort shipped returning the ranking upside down (this profile
    # returned "K", the unanimous last place).
    assert get_kemeny_young_winner(ballots) == "A"


def test_kemeny_young_approximation_is_condorcet_consistent_and_deterministic():
    """Above the exact cap the winner still has to be the Condorcet winner when
    one exists (a theorem, not a heuristic), and it must not move between
    identical calls -- _kwik_sort used to pick its pivot from the global
    `random` module, so a seeded caller got different answers."""
    ballots = [list("ABCDEFGHIJK")] * 5 + [list("BACDEFGHIJK")] * 4  # A beats all
    assert kemeny_used_approximation(ballots) is True
    assert {get_kemeny_young_winner(ballots) for _ in range(25)} == {"A"}


def test_compare_all_methods_registers_kemeny_young():
    names = ["A", "B", "C"]
    matrix = {
        i: {n: float(u) for n, u in zip(names, utils)}
        for i, utils in enumerate(
            [(1.0, 0.5, 0.0)] * 4 + [(0.0, 1.0, 0.5)] * 3 + [(0.5, 0.0, 1.0)] * 2
        )
    }
    res = compare_all_methods(
        [{"id": vid} for vid in matrix],
        [{"name": n} for n in names],
        [],
        override_utilities=matrix,
    )
    assert "kemeny_young" in res["methods"]
    assert res["methods"]["kemeny_young"]["winner"] in names


def test_the_documented_hash_order_regression_now_gets_the_exact_answer():
    """The pinned counterexample for the PYTHONHASHSEED bug, per the repo's
    "a discovered violation gets pinned, not left to the random search" rule.

    These 9 ballots over 7 candidates returned four different winners -- C, A, D
    and G -- across orderings of the same candidate list, because the list was
    `list(cand_set)` and KwikSort's pivot is `candidates[len(candidates) // 2]`.
    Sorting the list settled that on C.

    C was still the wrong answer. 7 candidates is now under the cap, so this
    profile gets exact Kemeny, and the true optimum is D -- which is also the
    winner a plurality of candidate orderings used to produce (2352 of the 5040).
    KwikSort's answer was reproducible, then correct.
    """
    votes = [
        list(b) for b in (
            "ECGDBFA", "EAFDGBC", "DGAECBF", "FCEDGBA", "GACDEFB",
            "FGCDBEA", "ADCBEGF", "ABCFEGD", "DGABFCE",
        )
    ]
    assert kemeny_used_approximation(votes) is False
    assert get_kemeny_young_winner(votes) == "D"
    pw = _pairwise_wins(votes)
    assert _kwik_sort(sorted(pw), pw)[0] == "C", "the approximation's old answer"


def test_exact_kemeny_agrees_with_brute_force_across_the_whole_cap_range():
    """The DP replaced `max(permutations(...))`, so it has to elect what the
    enumeration found optimal. Where several candidates head an optimal ranking
    the DP draws among them by lot (it used to take the lexicographically
    smallest optimal ranking), so the check is that its winner is one of them,
    and exactly the one when there is only one.

    7 and 8 are the interesting widths: both are inside every request schema's
    limit and both used to be answered by KwikSort, so that is the band where
    the winner actually changed. 9 and 10 are covered too because the cap
    reaches them, even though only polity can.
    """
    rng = random.Random(21)
    # Up to the cap, not to 8: 9 and 10 are the widths the cap raise newly made
    # exact, and 10! = 3.6M orderings is still ~1s of brute force per profile,
    # so they get one profile each rather than four.
    for m in range(2, _KY_EXACT_CAP + 1):
        names = sorted([f"C{i:02d}" for i in range(m)])
        for kind in range(1 if m > 8 else 4):
            nb = rng.randint(1, 8)
            if kind == 0:     # truncated
                votes = [rng.sample(names, rng.randint(1, m)) for _ in range(nb)]
            elif kind == 1:   # complete
                votes = [rng.sample(names, m) for _ in range(nb)]
            elif kind == 2:   # mirrored, so optima tie and the tie-break decides
                half = [rng.sample(names, m) for _ in range(nb)]
                votes = half + [list(reversed(b)) for b in half]
            else:             # unanimous
                votes = [rng.sample(names, m)] * nb
            pw = _pairwise_wins(votes)
            candidates = sorted(pw)
            if len(candidates) < 2:
                continue

            def score(ranking: tuple[str, ...], pw: dict = pw) -> int:
                return sum(
                    pw[ranking[i]][ranking[j]]
                    for i, j in itertools.combinations(range(len(ranking)), 2)
                )

            best, leaders = -1, set()
            for ranking in itertools.permutations(candidates):
                s = score(ranking)
                if s > best:
                    best, leaders = s, {ranking[0]}
                elif s == best:
                    leaders.add(ranking[0])
            assert get_kemeny_young_winner(votes) in leaders
            if len(leaders) == 1:
                assert get_kemeny_young_winner(votes) == next(iter(leaders))


def test_a_ballot_ranking_neither_candidate_does_not_vote_in_their_duel():
    """Kemeny used to build its own duel counts instead of the module's shared
    `_pairwise_wins`, and the copy differed on exactly one case: for a pair the
    ballot ranked NEITHER of, both positions defaulted to `len(ranking)`, so the
    `<` was False and the `else` credited a full win to whichever candidate came
    second in the candidate list.

    Pinned counterexample: B is the Kemeny winner, and the old counter elected A.
    Only one ballot ranks A alone, and it used to cast a vote in the B-vs-C,
    B-vs-D and C-vs-D duels it says nothing about.
    """
    votes = [["A"], ["B", "A"], ["D", "B", "C", "A"]]
    assert get_kemeny_young_winner(votes) == "B"

    # The invariant the old counter broke: a pair's duel draws exactly as many
    # votes as there are ballots ranking at least ONE of the two. A ballot
    # ranking one of them does count (the ranked candidate beats the omitted
    # one); a ballot ranking neither does not. The old counter gave every duel
    # `len(votes)` votes regardless, so C-vs-D below drew 3 instead of 1.
    pw = _pairwise_wins(votes)
    for a, b in itertools.combinations(sorted(pw), 2):
        involved = sum(1 for ballot in votes if a in ballot or b in ballot)
        assert pw[a][b] + pw[b][a] == involved, f"{a} vs {b}"
    assert pw["C"]["D"] + pw["D"]["C"] == 1, "only the third ballot ranks C or D"


def test_the_winner_never_depends_on_candidate_discovery_order():
    """Guards determinism at every hash seed, on both paths.

    One profile cannot do that: whether set order disagrees with sorted order on
    a given profile depends on the interpreter's hash seed, and on ~1 seed in 3
    they agree -- including seed 0, the one this repo's own tooling pins. An
    earlier single-profile version of this test passed with the bug restored.
    Nothing pins PYTHONHASHSEED for pytest, so one profile is a coin flip.

    Sweeping removes the luck. Both paths are covered because both read the
    candidate order: above the cap it is KwikSort's pivot, and below it the DP's
    tie-break between equally optimal rankings.
    """
    rng = random.Random(11)
    for names in (list("ABCDEFG"), [f"C{i:02d}" for i in range(11)]):
        for _ in range(60):
            votes = [rng.sample(names, len(names)) for _ in range(9)]
            winner = get_kemeny_young_winner(votes)
            pw = _pairwise_wins(votes)
            assert winner == (
                _kwik_sort(sorted(pw), pw)[0] if len(names) > _KY_EXACT_CAP
                else _kemeny_exact_winner(sorted(pw), pw)
            )
            # Same candidate set either way, so the answer must not move when the
            # ballots arrive in a different order.
            assert winner == get_kemeny_young_winner(list(reversed(votes)))


# Three equally good rankings: each pair is a 2-1 majority around a cycle, so A>B>C, B>C>A and
# C>A>B all score 5 and every candidate heads one. The lot draws among all three, over their
# names, never the name-smallest (A) or the first listed.
CYCLE = [["A", "B", "C"], ["B", "C", "A"], ["C", "A", "B"]]


def test_equally_good_rankings_are_drawn_by_lot_among_every_candidate_that_heads_one():
    drawn = [get_kemeny_young_winner(CYCLE, seed=s) for s in range(32)]
    assert drawn == [draw(["A", "B", "C"], s) for s in range(32)]
    assert set(drawn) == {"A", "B", "C"}  # not always A, the name-smallest
    assert drawn[0] == "C"  # seed 0, as a literal: the client's test pins the same winner


def test_only_the_candidates_that_head_an_optimal_ranking_are_drawn_among():
    """Ann and Cat tie for first and Zed trails: two leaders out of three. The lot is over
    those two names, not over all three, so Zed can never win, and the draw is the same as for
    any other two-way tie of Ann and Cat."""
    votes = [["Ann", "Cat", "Zed"]] * 3 + [["Cat", "Ann", "Zed"]] * 3
    drawn = [get_kemeny_young_winner(votes, seed=s) for s in range(32)]
    assert drawn == [draw(["Ann", "Cat"], s) for s in range(32)]
    assert set(drawn) == {"Ann", "Cat"}
    assert get_kemeny_young_winner(votes) == "Cat"  # seed 0


def test_the_draw_does_not_follow_the_order_the_ballots_arrive_in():
    for seed in range(8):
        expected = get_kemeny_young_winner(CYCLE, seed=seed)
        assert get_kemeny_young_winner(list(reversed(CYCLE)), seed=seed) == expected
        assert get_kemeny_young_winner(CYCLE[1:] + CYCLE[:1], seed=seed) == expected


def test_a_unique_optimum_is_not_drawn():
    """One optimal ranking, one head: the seed cannot move it."""
    votes = [["A", "B", "C"]] * 3 + [["B", "A", "C"]]
    assert {get_kemeny_young_winner(votes, seed=s) for s in range(16)} == {"A"}
