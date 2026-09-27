"""Systematic axiomatic tests (Lot 4.1, PLAN_SOLIDITE_TECHNIQUE.md).

For each of the 21 "locked" ordinal voting methods (the parity set shared
with the frontend engine — see CLAUDE.md's dual-engine section and
scripts/gen_engine_parity.py's own RULES dict, which this file's method
registry mirrors), verify which of 7 classic social-choice criteria it
satisfies and which it's known to violate.

A test asserting a method VIOLATES a criterion is as valuable as one
asserting it satisfies one (test_anonymity.py already established this
precedent for anonymity): it documents real voting theory *and* detects an
implementation that accidentally became more "well-behaved" than its
algorithm actually guarantees — which would be a correctness regression
worth investigating, not a bug in this test.

**Methodology.** The satisfies/violates split below is NOT taken from
memory — every cell was empirically discovered by fuzzing each method
against each criterion (thousands of random profiles per method, more for
lower-incidence criteria like monotonicity) and inspecting any discovered
counterexample by hand before trusting it. Two examples of that
verification catching something real: (1) minimax is Condorcet-consistent
for WINNERS but the fuzzer found it can still elect a literal Condorcet
LOSER (confirmed: a candidate who loses every single pairwise contest) — a
genuine, if under-cited, property of the Simpson-Kramer method, not a bug.
(2) An initial low-sample exploration (~100-240 random profiles per
method/criterion) wrongly classified ranked_pairs, river, and smith_irv as
satisfying clone independence, and nanson as satisfying monotonicity — all
four are degenerate-tie failures (an exact pairwise-margin or first-place-
vote tie that a tie-breaking convention resolves differently once a clone
or promotion disturbs it) rare enough that only Hypothesis's shrinking
search over the full test suite surfaced them. This is the exercise's
methodology working as intended: an under-sampled classification looked
clean until a more thorough search found the counterexample, so the
`@given`-based property tests below (not the exploration script) are the
source of truth for every "satisfies" claim. smith_irv's story didn't end
there: cross-checking the whole engine against the independent
`pref_voting` library (Lot 4.2) found that its clone-independence failure
was itself downstream of a genuine bug in `_smith_set`/`get_smith_irv_winner`
(a Smith-set tie-handling error, and recomputing the Smith set every
elimination round instead of once) -- fixing that bug made every found
clone-independence counterexample stop reproducing, so smith_irv moved back
to the "satisfies" side once the underlying algorithm was corrected.

**A known, now-largely-closed gap in this file's own methodology.** Every
random-search helper in this file (`_profiles4`, and every inline
`cands = [...]` fixture in the "can be violated" fallback tests) fixes the
CANDIDATE COUNT at exactly 4 -- only the ballot count varies, and the
Hypothesis property tests cap at 200 fixed examples. Lot 4.4 ported this
matrix's satisfies/violates split to the client engine using fast-check
(n in [3,6] candidates, wider than 4, and a bigger/differently-shaped
search than 200 fixed Hypothesis examples), and its non-deterministic
exploration turned up five real counterexamples during development, all
hand-verified against this backend and corrected here, not treated as
frontend-only findings:

- `baldwin` fails clone independence, but only at n=6
  (`test_clone_independence_baldwin_can_be_violated`) -- a candidate count
  this file's own fixtures (capped at 4) never generate.
- `irv`, `coombs`, `benham`, and `raynaud` each elect a Condorcet loser in
  specific profiles (`test_condorcet_loser_{irv,coombs,benham,raynaud}_
  can_be_violated`) that needed no new candidate count -- just a specific
  ballot combination the fixed 200-example Hypothesis run never sampled.

Neither kind of miss was ever a false signal: a property test that passes
200 times answers a true, narrower question than "for all profiles",
which is the only promise `@given` can make given a finite budget. A
broader or differently-shaped search can always find something a
narrower one didn't.

Given how much the Condorcet loser criterion alone had drifted (4 of 21
methods misclassified), the rest of this file was re-swept once, directly
in Python rather than via the client engine, at higher volume (~15,000-
24,000 trials per method/criterion, n in {3,4} for Condorcet winner/loser/
majority/Pareto, n in {3,4,5,6} for clone independence/monotonicity) to
check whether the other five criteria had similar gaps. They didn't:
Condorcet winner, Pareto, and monotonicity's classifications matched this
file's existing sets exactly, and clone independence's did too aside from
`baldwin` above. Majority had one more real, very rare miss: `dowdall`
(`test_majority_criterion_dowdall_can_be_violated`) can tie a majority
winner's score exactly and lose the alphabetical tie-break -- the same
family of failure as Borda's already-known majority weakness, just rarer
(an exact score tie, not just "second choices are weak"), which is exactly
why 200 fixed Hypothesis examples never hit it either.

This higher-volume Python re-sweep is reasonably thorough but still not
exhaustive proof the way Lot 4.3's small-profile check is -- it's a bigger
random search, not a different kind of guarantee. Whether a search wider
still (more trials, or candidate counts beyond 6) would find a seventh gap
is consequently still an open question, named as follow-up rather than
chased further here (matches the participation/reversal-symmetry deferral
below: there's a point where a widening search is its own open-ended
project, not a bounded fix).

**Scope.** 7 of the 8 criteria the plan names are covered here:
Condorcet winner, Condorcet loser, majority, unanimity, Pareto, clone
independence, monotonicity. Participation and reversal symmetry are
deliberately NOT included yet — fuzzing found real signal for both, but
also visible tie-driven noise (a profile with an exact score tie can make
two structurally different outcomes compare equal, which isn't a genuine
axiom violation), and disentangling "genuine violation" from "coincidental
tie" for every borderline cell needs a more careful pass than this PR's
budget covers. Documented as a named follow-up rather than shipped with a
guessed or possibly-flaky classification.

**Cardinal methods** (score, STAR, cumulative, maximin, nash — the other 5
of the 26 "locked" methods) are out of scope for this file: most of these
criteria are defined over preference orderings, and cardinal-ballot
analogues would need their own careful theoretical treatment rather than a
mechanical reuse of the ranking-based checks here.
"""
from __future__ import annotations

import itertools
import random
from typing import Any, Callable, Optional

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from api.engine.utils.simulation_ranked_utils import (
    get_anti_plurality_winner,
    get_baldwin_winner,
    get_benham_winner,
    get_black_winner,
    get_borda_winner,
    get_bucklin_winner,
    get_condorcet_winner,
    get_coombs_winner,
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

Rankings = list[list[str]]
MethodFn = Callable[[Rankings], Optional[str]]

# Mirrors scripts/gen_engine_parity.py's RULES — the 21 ordinal methods in
# the parity-locked set (CLAUDE.md).
METHODS: dict[str, MethodFn] = {
    "plurality":      get_plurality_winner,
    "two_round":      get_two_round_winner,
    "borda":          get_borda_winner,
    "irv":            get_irv_winner,
    "coombs":         get_coombs_winner,
    "condorcet":      get_condorcet_winner,
    "minimax":        get_minimax_winner,
    "schulze":        get_schulze_winner,
    "bucklin":        get_bucklin_winner,
    "nanson":         get_nanson_winner,
    "baldwin":        get_baldwin_winner,
    "ranked_pairs":   get_ranked_pairs_winner,
    "kemeny":         get_kemeny_young_winner,
    "black":          get_black_winner,
    "anti_plurality": get_anti_plurality_winner,
    "dowdall":        get_dowdall_winner,
    "raynaud":        get_raynaud_winner,
    "benham":         get_benham_winner,
    "river":          get_river_winner,
    "smith_irv":      get_smith_irv_winner,
    "split_cycle":    get_split_cycle_winner,
}


def test_the_method_registry_is_not_stale():
    """A discovery bug that silently dropped a method would make every
    matrix test below pass vacuously for it."""
    assert len(METHODS) == 21


# ── Pairwise helpers (ground truth, independent of any method under test) ──

def _condorcet_winner(rankings: Rankings) -> Optional[str]:
    cands = {c for r in rankings for c in r}
    for c in cands:
        if all(
            sum(1 for r in rankings if r.index(c) < r.index(o))
            > sum(1 for r in rankings if r.index(o) < r.index(c))
            for o in cands if o != c
        ):
            return c
    return None


def _condorcet_loser(rankings: Rankings) -> Optional[str]:
    cands = {c for r in rankings for c in r}
    for c in cands:
        if all(
            sum(1 for r in rankings if r.index(c) < r.index(o))
            < sum(1 for r in rankings if r.index(o) < r.index(c))
            for o in cands if o != c
        ):
            return c
    return None


_CANDS4 = ["A", "B", "C", "D"]
_profiles4 = st.lists(st.permutations(_CANDS4), min_size=3, max_size=12)


# ── 1. Condorcet winner criterion ───────────────────────────────────────────
# "If a Condorcet winner exists, the method must elect them."

CONDORCET_WINNER_SATISFIES = {
    "condorcet", "minimax", "schulze", "nanson", "baldwin", "ranked_pairs",
    "kemeny", "black", "raynaud", "benham", "river", "smith_irv", "split_cycle",
}
CONDORCET_WINNER_VIOLATES = {
    "plurality":      (11, ["A", "B", "C"]),
    "two_round":      (6, ["A", "B", "C", "D"]),
    "borda":          (2, ["A", "B", "C", "D"]),
    "irv":            (9, ["A", "B", "C"]),
    "coombs":         (1, ["A", "B", "C", "D"]),
    "bucklin":        (8, ["A", "B", "C"]),
    "anti_plurality": (20, ["A", "B", "C"]),
    "dowdall":        (10, ["A", "B", "C"]),
}
assert CONDORCET_WINNER_SATISFIES | CONDORCET_WINNER_VIOLATES.keys() == METHODS.keys()


@pytest.mark.parametrize("method_name", sorted(CONDORCET_WINNER_SATISFIES))
@settings(max_examples=200, deadline=None, derandomize=True, suppress_health_check=[HealthCheck.too_slow])
@given(rankings=_profiles4)
def test_condorcet_winner_criterion_satisfied(method_name, rankings):
    cw = _condorcet_winner(rankings)
    if cw is None:
        return
    fn = METHODS[method_name]
    assert fn(rankings) == cw, (
        f"{method_name} should always elect the Condorcet winner ({cw!r}) "
        f"but elected {fn(rankings)!r}"
    )


@pytest.mark.parametrize("method_name", sorted(CONDORCET_WINNER_VIOLATES))
def test_condorcet_winner_criterion_can_be_violated(method_name):
    """A method here is one for which real fuzzing found a profile with a
    Condorcet winner it does not elect — random search for a fresh
    counterexample, since the exact discovered one wasn't pinned (only its
    existence and approximate frequency were recorded during exploration)."""
    fn = METHODS[method_name]
    rng = random.Random(f"cw-{method_name}")
    cands = ["A", "B", "C", "D"]
    for _ in range(20_000):
        n = rng.choice([3, 5, 7, 9])
        rankings = [rng.sample(cands, len(cands)) for _ in range(n)]
        cw = _condorcet_winner(rankings)
        if cw is None:
            continue
        if fn(rankings) != cw:
            return  # found a genuine violation — the method is not Condorcet
    pytest.fail(
        f"{method_name} was expected to sometimes violate the Condorcet "
        f"winner criterion (seen during exploration) but 20000 random "
        f"profiles found no counterexample — investigate before trusting "
        f"this classification"
    )


# ── 2. Condorcet loser criterion ────────────────────────────────────────────
# "The method must never elect the Condorcet loser."

CONDORCET_LOSER_SATISFIES = METHODS.keys() - {
    "plurality", "minimax", "bucklin", "anti_plurality", "dowdall",
    "irv", "coombs", "raynaud", "benham",
}
CONDORCET_LOSER_VIOLATES = {
    "plurality", "minimax", "bucklin", "anti_plurality", "dowdall",
    "irv", "coombs", "raynaud", "benham",
}


@pytest.mark.parametrize("method_name", sorted(CONDORCET_LOSER_SATISFIES))
@settings(max_examples=200, deadline=None, derandomize=True, suppress_health_check=[HealthCheck.too_slow])
@given(rankings=_profiles4)
def test_condorcet_loser_criterion_satisfied(method_name, rankings):
    cl = _condorcet_loser(rankings)
    if cl is None:
        return
    fn = METHODS[method_name]
    assert fn(rankings) != cl, (
        f"{method_name} elected the Condorcet loser {cl!r} — a candidate "
        f"who loses every pairwise contest"
    )


def test_condorcet_loser_irv_can_be_violated():
    """Pinned counterexample (found by fast-check on the client engine, Lot
    4.4, PLAN_SOLIDITE_TECHNIQUE.md; hand-verified against this backend
    too): a 3-candidate, 7-ballot profile where C loses both of its pairwise
    contests (a genuine Condorcet loser) but wins under IRV anyway. A and B
    tie for fewest first-preferences and are eliminated TOGETHER, leaving C
    — who nobody's second choice could rescue A or B ahead of — as the sole
    survivor. This needed exactly 3 candidates to show up, a candidate count
    this file's own `_profiles4`/`cands` fixtures never generate (both are
    hardcoded to exactly 4) — a real, named gap in this file's own
    methodology, not just an IRV quirk. See the module docstring."""
    rankings = [
        ["C", "B", "A"], ["C", "A", "B"], ["A", "B", "C"], ["C", "A", "B"],
        ["B", "A", "C"], ["B", "A", "C"], ["A", "B", "C"],
    ]
    assert _condorcet_loser(rankings) == "C"
    assert get_irv_winner(rankings) == "C"


def test_condorcet_loser_coombs_can_be_violated():
    """Pinned counterexample (found by fast-check on the client engine, Lot
    4.4, PLAN_SOLIDITE_TECHNIQUE.md; hand-verified against this backend
    too): unlike the irv/baldwin findings above, this one needed no new
    candidate count -- 4 candidates, exactly what `_profiles4` already
    covers -- just an 11-ballot profile Hypothesis's 200 fixed examples
    happened not to sample. `test_condorcet_loser_criterion_satisfied`
    passed for coombs many times before this; it wasn't wrong to trust that
    the same way the shrinking-driven finds above were, it just hadn't been
    asked this particular question yet. Property-based testing narrows the
    odds of a bug surviving, not to zero."""
    rankings = [
        ["B", "D", "C", "A"], ["A", "D", "C", "B"], ["B", "C", "D", "A"],
        ["D", "A", "C", "B"], ["B", "D", "A", "C"], ["C", "B", "D", "A"],
        ["A", "D", "C", "B"], ["A", "B", "C", "D"], ["D", "A", "B", "C"],
        ["A", "B", "C", "D"], ["C", "D", "B", "A"],
    ]
    assert _condorcet_loser(rankings) == "C"
    assert get_coombs_winner(rankings) == "C"


def test_condorcet_loser_benham_can_be_violated():
    """Pinned counterexample (found by fast-check, Lot 4.4; hand-verified
    against this backend), same class as the coombs finding above: a
    6-ballot, 4-candidate profile Hypothesis's fixed 200 examples never
    sampled."""
    rankings = [
        ["C", "A", "D", "B"], ["B", "D", "A", "C"], ["D", "C", "A", "B"],
        ["C", "A", "D", "B"], ["B", "C", "D", "A"], ["D", "C", "A", "B"],
    ]
    assert _condorcet_loser(rankings) == "B"
    assert get_benham_winner(rankings) == "B"


def test_condorcet_loser_raynaud_can_be_violated():
    """Pinned counterexample (found by fast-check, Lot 4.4; hand-verified
    against this backend), same class as the coombs/benham findings above."""
    rankings = [["D", "B", "A", "C"], ["B", "C", "D", "A"], ["C", "A", "D", "B"]]
    assert _condorcet_loser(rankings) == "A"
    assert get_raynaud_winner(rankings) == "A"


@pytest.mark.parametrize(
    "method_name",
    sorted(CONDORCET_LOSER_VIOLATES - {"irv", "coombs", "benham", "raynaud"}),
)
def test_condorcet_loser_criterion_can_be_violated(method_name):
    """minimax's case is the interesting one: it IS Condorcet-consistent
    for winners, but that does not imply it avoids the Condorcet loser —
    verified by hand (see the module docstring) before trusting this."""
    fn = METHODS[method_name]
    rng = random.Random(f"cl-{method_name}")
    cands = ["A", "B", "C", "D"]
    for _ in range(20_000):
        n = rng.choice([3, 5, 7, 9])
        rankings = [rng.sample(cands, len(cands)) for _ in range(n)]
        cl = _condorcet_loser(rankings)
        if cl is None:
            continue
        if fn(rankings) == cl:
            return
    pytest.fail(
        f"{method_name} was expected to sometimes elect the Condorcet "
        f"loser (seen during exploration) but 20000 random profiles found "
        f"no counterexample — investigate before trusting this classification"
    )


# ── 3. Majority criterion ───────────────────────────────────────────────────
# "A candidate ranked first by a strict majority of voters must win."

MAJORITY_VIOLATES = {"borda", "anti_plurality", "dowdall"}
MAJORITY_SATISFIES = METHODS.keys() - MAJORITY_VIOLATES


def _majority_first_choice(rankings: Rankings) -> Optional[str]:
    counts: dict[str, int] = {}
    for r in rankings:
        counts[r[0]] = counts.get(r[0], 0) + 1
    for c, n in counts.items():
        if n * 2 > len(rankings):
            return c
    return None


@pytest.mark.parametrize("method_name", sorted(MAJORITY_SATISFIES))
@settings(max_examples=200, deadline=None, derandomize=True, suppress_health_check=[HealthCheck.too_slow])
@given(rankings=_profiles4)
def test_majority_criterion_satisfied(method_name, rankings):
    maj = _majority_first_choice(rankings)
    if maj is None:
        return
    fn = METHODS[method_name]
    assert fn(rankings) == maj, (
        f"{method_name} did not elect {maj!r}, who a strict majority of "
        f"voters ranked first"
    )


def test_majority_criterion_dowdall_can_be_violated():
    """Pinned counterexample (found by fast-check on the client engine, Lot
    4.4, PLAN_SOLIDITE_TECHNIQUE.md; hand-verified against this backend
    too): B has an outright majority of first-place votes (5 of 9 ballots),
    but ties A exactly on Dowdall score (19/3 each, verified in exact
    fractions) and loses the alphabetical tie-break. Same family as Borda's
    already-known majority failure -- both are positional scoring rules
    that weigh every rank, not just first place, so a "thin" majority can
    be outweighed by a rival's strength elsewhere. Needed an exact score
    tie to show up, rare enough (2 in ~6500 random trials during
    exploration) that this file's existing 20000-trial generic search
    (fixed at 4 candidates and voter counts {3,5,7,9}, like every other
    fallback here) might not reliably re-find it -- pinned instead."""
    rankings = [
        ["A", "C", "B"], ["B", "A", "C"], ["A", "C", "B"], ["B", "A", "C"],
        ["A", "C", "B"], ["B", "A", "C"], ["A", "C", "B"], ["B", "A", "C"],
        ["B", "C", "A"],
    ]
    assert _majority_first_choice(rankings) == "B"
    assert get_dowdall_winner(rankings) == "A"


@pytest.mark.parametrize("method_name", sorted(MAJORITY_VIOLATES - {"dowdall"}))
def test_majority_criterion_can_be_violated(method_name):
    """Borda's classic weakness: a majority's first choice can still lose
    if the majority's second choices are weak relative to a broadly-liked
    runner-up (a textbook Borda criticism). Anti-plurality only tallies
    last-place votes, so it doesn't look at first-place support at all."""
    fn = METHODS[method_name]
    rng = random.Random(f"maj-{method_name}")
    cands = ["A", "B", "C", "D"]
    for _ in range(20_000):
        n = rng.choice([3, 5, 7, 9])
        rankings = [rng.sample(cands, len(cands)) for _ in range(n)]
        maj = _majority_first_choice(rankings)
        if maj is None:
            continue
        if fn(rankings) != maj:
            return
    pytest.fail(
        f"{method_name} was expected to sometimes fail the majority "
        f"criterion but 20000 random profiles found no counterexample"
    )


# ── 4. Unanimity ─────────────────────────────────────────────────────────────
# "If every voter ranks the same candidate first, that candidate must win."
# Constructed directly rather than via random sampling: full agreement is
# rare among random permutations, so this needs a hand-built profile to get
# reliable coverage for every method rather than depending on luck.

@pytest.mark.parametrize("method_name", sorted(METHODS))
def test_unanimity(method_name):
    fn = METHODS[method_name]
    rankings = [
        ["B", "A", "C", "D"],
        ["B", "C", "A", "D"],
        ["B", "D", "C", "A"],
        ["B", "A", "D", "C"],
        ["B", "C", "D", "A"],
    ]
    assert fn(rankings) == "B", (
        f"{method_name} did not elect 'B', who every voter ranked first"
    )


# ── 5. Pareto efficiency ────────────────────────────────────────────────────
# "If every voter ranks A above B, B must never win."

PARETO_VIOLATES = {"anti_plurality"}
PARETO_SATISFIES = METHODS.keys() - PARETO_VIOLATES


def _pareto_dominated(rankings: Rankings) -> set[str]:
    """Candidates ranked below some other candidate on every single ballot."""
    cands = list({c for r in rankings for c in r})
    dominated = set()
    for b in cands:
        if any(
            all(r.index(a) < r.index(b) for r in rankings)
            for a in cands if a != b
        ):
            dominated.add(b)
    return dominated


@pytest.mark.parametrize("method_name", sorted(PARETO_SATISFIES))
@settings(max_examples=200, deadline=None, derandomize=True, suppress_health_check=[HealthCheck.too_slow])
@given(rankings=_profiles4)
def test_pareto_efficiency_satisfied(method_name, rankings):
    dominated = _pareto_dominated(rankings)
    if not dominated:
        return
    fn = METHODS[method_name]
    winner = fn(rankings)
    assert winner not in dominated, (
        f"{method_name} elected {winner!r}, who every voter ranked below "
        f"some other candidate"
    )


def test_pareto_efficiency_anti_plurality_can_be_violated():
    """Pinned counterexample (found and hand-verified during exploration,
    see the module docstring): C is preferred to A on every single ballot,
    yet anti-plurality (which only tallies LAST-place votes, ignoring
    first-place preferences entirely) elects A anyway."""
    rankings = [
        ["B", "C", "A", "D"],
        ["C", "A", "D", "B"],
        ["C", "B", "A", "D"],
    ]
    assert all(r.index("C") < r.index("A") for r in rankings)
    assert get_anti_plurality_winner(rankings) == "A"


# ── 6. Clone independence ───────────────────────────────────────────────────
# "Adding a clone of a non-winning candidate (inserted immediately adjacent
# to it on every ballot) must not change the winner; a clone of the winner
# must not hand victory to a third candidate."

CLONE_INDEPENDENCE_VIOLATES = {
    "borda", "coombs", "bucklin", "nanson", "kemeny", "black",
    "anti_plurality", "dowdall", "split_cycle",
    "ranked_pairs", "river", "baldwin",
}
CLONE_INDEPENDENCE_SATISFIES = METHODS.keys() - CLONE_INDEPENDENCE_VIOLATES


def _clone_after(rankings: Rankings, target: str, clone_name: str) -> Rankings:
    out = []
    for r in rankings:
        i = r.index(target)
        out.append(r[: i + 1] + [clone_name] + r[i + 1 :])
    return out


@pytest.mark.parametrize("method_name", sorted(CLONE_INDEPENDENCE_SATISFIES))
@settings(max_examples=100, deadline=None, derandomize=True, suppress_health_check=[HealthCheck.too_slow])
@given(rankings=_profiles4)
def test_clone_independence_satisfied(method_name, rankings):
    fn = METHODS[method_name]
    winner = fn(rankings)
    if winner is None:
        return
    for target in ["A", "B", "C", "D"]:
        cloned = _clone_after(rankings, target, "A*" if target != "A" else "AA")
        clone_name = "A*" if target != "A" else "AA"
        new_winner = fn(cloned)
        if target == winner:
            assert new_winner in (winner, clone_name), (
                f"{method_name}: cloning the winner {winner!r} handed "
                f"victory to third party {new_winner!r}"
            )
        else:
            assert new_winner == winner, (
                f"{method_name}: cloning non-winner {target!r} changed the "
                f"winner from {winner!r} to {new_winner!r}"
            )


def test_clone_independence_borda_can_be_violated():
    """Borda is the textbook example of clone vulnerability: adding a
    near-identical candidate splits the "middle-rank" points a rival would
    otherwise get, flipping the result — the classic argument against using
    Borda count in contexts where similar candidates can enter (see
    THEORY.md and any Borda-count criticism in the social choice
    literature)."""
    rankings = [
        ["B", "C", "A"], ["C", "A", "B"], ["C", "B", "A"], ["B", "C", "A"],
        ["A", "B", "C"], ["A", "B", "C"], ["A", "B", "C"],
    ]
    assert get_borda_winner(rankings) == "B"
    cloned = [
        ["B", "C", "A", "A*"], ["C", "A", "A*", "B"], ["C", "B", "A", "A*"],
        ["B", "C", "A", "A*"], ["A", "A*", "B", "C"], ["A", "A*", "B", "C"],
        ["A", "A*", "B", "C"],
    ]
    assert get_borda_winner(cloned) == "A"


def test_clone_independence_ranked_pairs_can_be_violated():
    """Pinned counterexample (found by Hypothesis shrinking, hand-verified):
    a 3-voter Condorcet cycle where all three pairwise margins are exactly
    tied at 2-1 — a degenerate case the textbook clone-independence proof for
    Tideman's ranked-pairs method doesn't cover, since that proof assumes
    generic (non-tied) margins. With a three-way tie, which edge gets locked
    in first is a tie-breaking convention, and cloning a candidate disturbs
    that tie-break: original winner B, cloning non-winner C flips it to A."""
    rankings = [["A", "C", "B", "D"], ["B", "A", "C", "D"], ["C", "B", "A", "D"]]
    assert get_ranked_pairs_winner(rankings) == "B"
    cloned = _clone_after(rankings, "C", "A*")
    assert get_ranked_pairs_winner(cloned) == "A"


def test_clone_independence_river_can_be_violated():
    """River is a ranked-pairs variant and shares its tie-breaking
    convention, so it fails on the exact same degenerate tied-cycle profile
    as test_clone_independence_ranked_pairs_can_be_violated above."""
    rankings = [["A", "C", "B", "D"], ["B", "A", "C", "D"], ["C", "B", "A", "D"]]
    assert get_river_winner(rankings) == "B"
    cloned = _clone_after(rankings, "C", "A*")
    assert get_river_winner(cloned) == "A"


def test_clone_independence_baldwin_can_be_violated():
    """Pinned counterexample (found by fast-check on the client engine, Lot
    4.4, PLAN_SOLIDITE_TECHNIQUE.md; hand-verified against this backend
    too): a 6-candidate, 9-ballot profile where cloning non-winner D changes
    the winner from C to D. This needed 6 candidates to show up — this
    file's own clone-independence fixtures (`_profiles4`'s 4 and this
    section's generic search's 3) never generate that many, so nothing here
    could have found it. Baldwin was classified as clone-independent by Lot
    4.1/4.2 on exactly that narrower search; this is a real correction, not
    a new bug introduced since. See the module docstring."""
    rankings = [
        ["A", "B", "D", "E", "C", "F"], ["C", "F", "D", "B", "A", "E"],
        ["D", "A", "C", "F", "E", "B"], ["A", "C", "E", "D", "F", "B"],
        ["C", "D", "E", "B", "F", "A"], ["C", "F", "D", "B", "E", "A"],
        ["D", "B", "A", "C", "F", "E"], ["D", "B", "A", "E", "F", "C"],
        ["B", "A", "C", "E", "F", "D"],
    ]
    assert get_baldwin_winner(rankings) == "C"
    cloned = _clone_after(rankings, "D", "G")
    assert get_baldwin_winner(cloned) == "D"


@pytest.mark.parametrize(
    "method_name",
    sorted(CLONE_INDEPENDENCE_VIOLATES - {"borda", "ranked_pairs", "river", "baldwin"}),
)
def test_clone_independence_can_be_violated(method_name):
    fn = METHODS[method_name]
    rng = random.Random(f"clone-{method_name}")
    cands = ["A", "B", "C"]
    for _ in range(3_000):
        n = rng.choice([3, 5, 7, 9])
        rankings = [rng.sample(cands, len(cands)) for _ in range(n)]
        winner = fn(rankings)
        if winner is None:
            continue
        for target in cands:
            clone_name = f"{target}*"
            cloned = _clone_after(rankings, target, clone_name)
            new_winner = fn(cloned)
            if target == winner:
                if new_winner not in (winner, clone_name):
                    return
            elif new_winner != winner:
                return
    pytest.fail(
        f"{method_name} was expected to sometimes fail clone independence "
        f"but 3000 random profiles found no counterexample"
    )


# ── 7. Monotonicity ──────────────────────────────────────────────────────────
# "Ranking the winner higher on some ballot (with everyone else's relative
# order unchanged) must never cause them to lose."

MONOTONICITY_VIOLATES = {
    "two_round", "irv", "coombs", "baldwin", "raynaud", "benham", "smith_irv",
    "nanson",
}
MONOTONICITY_SATISFIES = METHODS.keys() - MONOTONICITY_VIOLATES


def _promote_to_first(rankings: Rankings, ballot_index: int, candidate: str) -> Rankings:
    r = rankings[ballot_index]
    new_r = [candidate] + [c for c in r if c != candidate]
    return rankings[:ballot_index] + [new_r] + rankings[ballot_index + 1 :]


@pytest.mark.parametrize("method_name", sorted(MONOTONICITY_SATISFIES))
@settings(max_examples=150, deadline=None, derandomize=True, suppress_health_check=[HealthCheck.too_slow])
@given(rankings=_profiles4)
def test_monotonicity_satisfied(method_name, rankings):
    fn = METHODS[method_name]
    winner = fn(rankings)
    if winner is None:
        return
    for i, r in enumerate(rankings):
        if r[0] == winner:
            continue
        modified = _promote_to_first(rankings, i, winner)
        new_winner = fn(modified)
        assert new_winner == winner, (
            f"{method_name}: promoting winner {winner!r} to 1st place on "
            f"one ballot changed the outcome to {new_winner!r}"
        )
        break  # one promotion per profile is enough signal


def test_monotonicity_smith_irv_can_be_violated():
    """Pinned counterexample (found and hand-verified during exploration,
    see the module docstring): Smith-IRV inherits IRV's classic
    non-monotonicity in some cases despite the Smith-set restriction —
    promoting the winner to 1st place on one more ballot flips the winner
    to someone else entirely."""
    rankings = [
        ["D", "A", "C", "B"], ["C", "A", "D", "B"], ["D", "B", "C", "A"],
        ["B", "C", "A", "D"], ["A", "D", "C", "B"], ["D", "C", "B", "A"],
        ["B", "C", "A", "D"], ["A", "D", "C", "B"], ["B", "A", "D", "C"],
    ]
    assert get_smith_irv_winner(rankings) == "A"
    modified = _promote_to_first(rankings, 0, "A")
    assert get_smith_irv_winner(modified) == "B"


def test_monotonicity_nanson_can_be_violated():
    """Pinned counterexample (found by Hypothesis shrinking, hand-verified
    with a standalone script): an 8-ballot profile where Nanson elects D,
    but promoting D to first place on one more ballot (with everyone else's
    relative order unchanged) flips the winner to B. Nanson eliminates every
    below-average-Borda-score candidate each round rather than just the
    single lowest (Baldwin's rule) — that wider per-round cut doesn't make
    it monotone; both methods can fail this criterion."""
    rankings = [
        ["C", "D", "B", "A"], ["C", "A", "D", "B"], ["B", "D", "A", "C"],
        ["D", "C", "B", "A"], ["B", "D", "A", "C"], ["C", "A", "B", "D"],
        ["D", "A", "C", "B"], ["B", "A", "D", "C"],
    ]
    assert get_nanson_winner(rankings) == "D"
    modified = _promote_to_first(rankings, 0, "D")
    assert get_nanson_winner(modified) == "B"


@pytest.mark.parametrize(
    "method_name",
    sorted(MONOTONICITY_VIOLATES - {"smith_irv", "nanson"}),
)
def test_monotonicity_can_be_violated(method_name):
    fn = METHODS[method_name]
    rng = random.Random(f"mono-{method_name}")
    cands = ["A", "B", "C", "D"]
    for _ in range(20_000):
        n = rng.choice([9, 11, 13, 15])
        rankings = [rng.sample(cands, len(cands)) for _ in range(n)]
        winner = fn(rankings)
        if winner is None:
            continue
        for i, r in enumerate(rankings):
            if r[0] == winner:
                continue
            modified = _promote_to_first(rankings, i, winner)
            if fn(modified) != winner:
                return
            break
    pytest.fail(
        f"{method_name} was expected to sometimes fail monotonicity but "
        f"20000 random profiles found no counterexample"
    )
