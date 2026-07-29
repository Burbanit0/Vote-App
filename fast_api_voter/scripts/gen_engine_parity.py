"""Golden-fixture generator for the client⇄backend voting-engine parity test.

The Playground computes winners client-side (voter-app/src/lib/playgroundVoting.ts);
this repo's authoritative engine is the (tested) Python backend. To guarantee the
two agree, we run the backend rules on a set of seeded ranking profiles and dump
the winners; a Vitest test then asserts the TS client returns the same winner.

Run from anywhere:  python fast_api_voter/scripts/gen_engine_parity.py
Re-run whenever a ranked rule changes on either side.

Voter counts are ODD so every pairwise majority is strict — that removes the
tie-break ambiguity that would otherwise make Condorcet methods diverge for
reasons unrelated to the algorithm.
"""

from __future__ import annotations

import json
import os
import random
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from api.engine.utils.simulation_ranked_utils import (  # noqa: E402
    get_anti_plurality_winner,
    get_baldwin_winner,
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
    get_schulze_winner,
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
    "condorcet": get_condorcet_winner,
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

    payload = {
        "_generatedBy": "fast_api_voter/scripts/gen_engine_parity.py",
        "_seed": SEED,
        "_note": "Authoritative winners from the Python backend. Asserted by playgroundVoting.parity.test.ts.",
        "scenarios": scenarios,
        "cardinalScenarios": cardinal_scenarios,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=0)
        f.write("\n")
    print(f"wrote {len(scenarios)} ordinal + {len(cardinal_scenarios)} cardinal scenarios -> {OUT}")


if __name__ == "__main__":
    main()
