"""Golden-fixture generator for the client⇄backend voting-engine parity test.

The Playground computes winners client-side (voter-app/src/lib/playgroundVoting.ts);
this repo's authoritative engine is the (tested) Python backend. To guarantee the
two agree, we run the backend rules on a set of seeded ranking profiles and dump
the winners; a Vitest test then asserts the TS client returns the same winner.

Run from anywhere:  PYTHONHASHSEED=0 python fast_api_voter/scripts/gen_engine_parity.py
Re-run whenever a ranked rule changes on either side — CI enforces it
(scripts/check_engine_parity_drift.sh regenerates and fails on any diff).

Voter counts are ODD so every pairwise majority is strict — that removes the
tie-break ambiguity that would otherwise make Condorcet methods diverge for
reasons unrelated to the algorithm.
"""

from __future__ import annotations

import itertools
import json
import os
import random
import sys

# Reproducibility: `random.Random(SEED)` alone is NOT enough. The engine iterates
# sets/dicts of candidate names, so Python's per-process string-hash randomisation
# changes tie-detection order, which changes how many times strict_winner() re-rolls,
# which shifts the whole RNG stream — three runs used to give three different
# fixtures. That made "just re-run the generator" produce a 200 kB spurious diff,
# so nobody re-ran it, so the parity test drifted against a frozen snapshot.
# PYTHONHASHSEED is read at interpreter start-up, so it cannot be set from here —
# refuse to run rather than silently emit a fixture nobody else can reproduce.
if os.environ.get("PYTHONHASHSEED") != "0":
    sys.exit(
        "PYTHONHASHSEED=0 is required for a reproducible fixture. Run:"
        "\n  PYTHONHASHSEED=0 python fast_api_voter/scripts/gen_engine_parity.py"
        "\nor just ./scripts/check_engine_parity_drift.sh, which sets it for you."
    )

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from api.engine.utils.simulation_ranked_utils import (  # noqa: E402
    get_anti_plurality_winner,
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
from api.engine.utils.simulation_score_utils import (  # noqa: E402
    get_simple_score_winner,
    get_star_voting_winner,
    get_cumulative_winner,
    get_maximin_score_winner,
    get_nash_winner,
)

# Client Rule id → backend winner fn. Only the purely ordinal rules both engines
# share (score/approval/STAR/MJ take cardinal ballots; random_ballot is a lottery).
RULES = {
    "plurality": get_plurality_winner,
    "two_round": get_two_round_winner,
    "borda": get_borda_winner,
    "irv": get_irv_winner,
    "coombs": get_coombs_winner,
    # The client's "condorcet" rule is labelled "Condorcet (Copeland)" in
    # RULE_LABELS and always resolves to a winner (Copeland's method, which
    # elects the Condorcet winner when one exists but doesn't return None
    # otherwise) -- get_condorcet_winner is the wrong backend twin: it's the
    # strict criterion (Optional[str], often None). Every scenario here that
    # used to compare against it happened to have a real Condorcet winner
    # (where the two functions necessarily agree), so this was masked until
    # an exhaustive small-profile comparison checked cases with none too
    # (Lot 4.3, PLAN_SOLIDITE_TECHNIQUE.md).
    "condorcet": get_copeland_winner,
    "minimax": get_minimax_winner,
    "schulze": get_schulze_winner,
    "bucklin": get_bucklin_winner,
    "nanson": get_nanson_winner,
    "baldwin": get_baldwin_winner,
    "ranked_pairs": get_ranked_pairs_winner,
    "kemeny": get_kemeny_young_winner,
    "black": get_black_winner,
    "anti_plurality": get_anti_plurality_winner,
    "dowdall": get_dowdall_winner,
    "raynaud": get_raynaud_winner,
    "benham": get_benham_winner,
    "river": get_river_winner,
    "smith_irv": get_smith_irv_winner,
    "split_cycle": get_split_cycle_winner,
}

# Cardinal rules that take the SAME per-voter score vector on both engines (so a
# shared score matrix is a fair comparison). Approval is excluded — the two engines
# derive the approval ballot differently (rankings/utility-threshold vs scores), a
# modelling choice, not an algorithm. Majority judgment is excluded — its grade
# quantisation differs (client round(s·5) vs backend threshold buckets).
CARDINAL = {
    "score": lambda b: get_simple_score_winner(b)["winner"],
    "star": lambda b: get_star_voting_winner(b)["winner"],
    "cumulative": get_cumulative_winner,
    "maximin": get_maximin_score_winner,
    "nash": get_nash_winner,
}

NAMES = ["A", "B", "C", "D", "E"]
SEED = 20260628
OUT = os.path.abspath(
    os.path.join(ROOT, "..", "voter-app", "src", "lib", "__fixtures__", "engineParity.json")
)


def strict_winner(fn, ballots, cands, rng):
    """The winner only if it is UNAMBIGUOUS — i.e. invariant to relabeling the
    candidates. A voting rule is neutral, so a strict winner can't depend on
    candidate order; if any random relabeling changes it, the result was decided
    by a tie-break (a convention, not the algorithm) → return None and skip it,
    so the parity test stays a pure algorithmic-correctness check."""
    base = fn(ballots)
    if base is None:
        return None
    for _ in range(200):
        shuffled = cands[:]
        rng.shuffle(shuffled)
        relabel = dict(zip(cands, shuffled))  # old name -> new name
        inv = {v: k for k, v in relabel.items()}
        rows = [[relabel[c] for c in b] for b in ballots]
        rng.shuffle(rows)  # ballot order too — neutrality AND anonymity, so any
        w = fn(rows)  # insertion-order tie-break shows up as an unstable winner
        if w is None or inv[w] != base:
            return None
    return base


def strict_winner_cardinal(fn, ballots, cands, rng):
    """As strict_winner, for score ballots (per-voter {candidate: score} dicts):
    keep the winner only if it survives relabeling the candidates and shuffling
    the voters, so it isn't a tie-break artefact."""
    base = fn(ballots)
    if base is None:
        return None
    for _ in range(200):
        shuffled = cands[:]
        rng.shuffle(shuffled)
        relabel = dict(zip(cands, shuffled))
        inv = {v: k for k, v in relabel.items()}
        rows = [{relabel[c]: v for c, v in b.items()} for b in ballots]
        rng.shuffle(rows)
        w = fn(rows)
        if w is None or inv[w] != base:
            return None
    return base


def generate_exhaustive_scenarios() -> list[dict]:
    """Every possible ordinal profile for n<=3 candidates and m<=5 voters --
    an exhaustive proof of parity over that whole bounded domain, not a
    sample of it (Lot 4.3, PLAN_SOLIDITE_TECHNIQUE.md). Anonymity (already
    established by test_anonymity.py) means only the MULTISET of ballots
    matters, so `combinations_with_replacement` over the n! ballot types
    enumerates the space without redundant voter-relabellings -- 481 profiles
    total (20 for n=2, 461 for n=3), fully deterministic (itertools order,
    no dict/set iteration), no PYTHONHASHSEED dependency.

    Unlike the random scenarios above, winners here are RAW -- not run
    through strict_winner's relabel-robustness filter. That filter exists to
    stop "no comparable winner" ballast, but on a handful of large random
    profiles it also silently skips every tied/degenerate case, which is
    exactly where 4 of the 5 real bugs this exhaustive check found were
    hiding (a fifth, `condorcet`, was a wrong function mapping -- see RULES
    above). n=4 (an additional 98,280 profiles, ~60MB of JSON) was also
    verified this way as a one-time pass during development -- 0 mismatches
    after the fixes below -- but isn't committed here: regenerating it on
    every PR would be slow for a domain size a smaller committed slice
    already exercises the same bug CLASS on.
    """
    scenarios = []
    for n in (2, 3):
        cands = NAMES[:n]
        ballot_types = list(itertools.permutations(cands))
        k = len(ballot_types)
        for m in range(1, 6):
            for combo in itertools.combinations_with_replacement(range(k), m):
                ballots = [list(ballot_types[i]) for i in combo]
                winners = {rule: fn(ballots) for rule, fn in RULES.items()}
                scenarios.append({"candidates": cands, "ballots": ballots, "winners": winners})
    return scenarios


def main() -> None:
    rng = random.Random(SEED)
    scenarios = []
    for m in (3, 4, 5):
        cands = NAMES[:m]
        for n in (21, 31, 41, 51, 61):
            for _ in range(4):  # 4 profiles per (m, n) → 60 scenarios
                ballots = [rng.sample(cands, m) for _ in range(n)]
                winners = {rule: strict_winner(fn, ballots, cands, rng) for rule, fn in RULES.items()}
                scenarios.append({"candidates": cands, "ballots": ballots, "winners": winners})

    cardinal_scenarios = []
    for m in (3, 4, 5):
        cands = NAMES[:m]
        for n in (21, 31, 41, 51, 61):
            for _ in range(4):
                score_ballots = [{c: rng.randint(0, 5) for c in cands} for _ in range(n)]
                winners = {
                    rule: strict_winner_cardinal(fn, score_ballots, cands, rng)
                    for rule, fn in CARDINAL.items()
                }
                matrix = [[b[c] for c in cands] for b in score_ballots]
                cardinal_scenarios.append(
                    {"candidates": cands, "scores": matrix, "winners": winners}
                )

    exhaustive_scenarios = generate_exhaustive_scenarios()

    payload = {
        "_generatedBy": "fast_api_voter/scripts/gen_engine_parity.py",
        "_seed": SEED,
        "_note": "Authoritative winners from the Python backend. Asserted by playgroundVoting.parity.test.ts.",
        "scenarios": scenarios,
        "cardinalScenarios": cardinal_scenarios,
        "exhaustiveScenarios": exhaustive_scenarios,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=0)
        f.write("\n")
    print(
        f"wrote {len(scenarios)} ordinal + {len(cardinal_scenarios)} cardinal + "
        f"{len(exhaustive_scenarios)} exhaustive (n<=3) scenarios -> {OUT}"
    )


if __name__ == "__main__":
    main()
