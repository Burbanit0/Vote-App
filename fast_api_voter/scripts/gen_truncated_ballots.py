#!/usr/bin/env python3
"""Generate voter-app/src/lib/__fixtures__/truncatedBallots.json: what the BACKEND does with a
truncated ballot and with equal ranks, so the client's tests can set the two side by side
(docs/spec/truncated-ballots.md; PLAN_GLOBAL_2026-11.md, Phase 3).

This records what each engine does TODAY. It is not a convention and it changes no behaviour: the
client's own answers are pinned in voter-app/src/lib/truncatedBallots.test.ts, the backend's
readings in api/tests/test_truncated_ballots_as_is.py, and api/tests/test_truncated_ballots_fixture.py
checks this file is in step.

Six experiments:
  truncated    60 fixed profiles of 5-9 ballots over A-D, each ballot ranking 1 to 4 of them
               (the 21 ordinal rules the two engines share);
  probes       two small profiles on which no rule is decided by a lot, so each reading is one
               winner and not a draw: "duel" (a candidate a ballot leaves out, in a duel and in
               Borda-type points) and "field" (a candidate no ballot ranks);
  equalRanks   voters exactly equidistant from two candidates, run through the backend's own
               profile construction (`rankings_from_utilities`, the per-voter lot of #662),
               with the candidates listed as given and reversed (the 21 ordinal rules);
  scores       a truncated SCORE ballot (the backend's `project_ballot`, "rank_truncated":
               the top k scored, the rest 0), for the five score rules, on a matrix whose
               winners are the same under every seed;
  shared       the same 9 voters' 0-5 grades, in full and cut to their top 1 and top 2, read as
               a majority-judgment ballot and as a 0/1 approval ballot: the two rules each
               engine derives its own way from utility, so the ballots are shared as in the
               parity harness (0/1, and multiples of 0.2);
  scoreTies    two candidates with identical score columns, the candidates listed as given and
               reversed, for the seven non-ordinal rules.

Run (from the repo root, the seed pinned as for the parity fixture):
    PYTHONHASHSEED=0 python fast_api_voter/scripts/gen_truncated_ballots.py
    PYTHONHASHSEED=0 python fast_api_voter/scripts/gen_truncated_ballots.py --check   # drift check
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if os.environ.get("PYTHONHASHSEED") != "0":
    sys.exit(
        "PYTHONHASHSEED=0 is required for a reproducible fixture. Run:\n"
        "  PYTHONHASHSEED=0 python fast_api_voter/scripts/gen_truncated_ballots.py"
    )

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.engine.utils.method_registry import (  # noqa: E402
    RANKED_RULES,
    rankings_from_utilities,
    rule_winner,
)
from api.engine.utils.profile_engine import project_ballot  # noqa: E402
from api.engine.utils.simulation_ranked_utils import get_approval_winner_sincere  # noqa: E402

OUT = ROOT.parent / "voter-app" / "src" / "lib" / "__fixtures__" / "truncatedBallots.json"

SEED = 926
NAMES = ["A", "B", "C", "D"]
PROFILES = 60

#: client rule id -> the backend registry's key (the client's "condorcet" is Copeland's method).
ORDINAL: Dict[str, str] = {
    "plurality": "plurality",
    "two_round": "two_round",
    "borda": "borda",
    "irv": "irv",
    "coombs": "coombs",
    "condorcet": "copeland",
    "minimax": "minimax",
    "schulze": "schulze",
    "bucklin": "bucklin",
    "nanson": "nanson",
    "baldwin": "baldwin",
    "ranked_pairs": "ranked_pairs",
    "kemeny": "kemeny_young",
    "black": "black",
    "anti_plurality": "anti_plurality",
    "dowdall": "dowdall",
    "raynaud": "raynaud",
    "benham": "benham",
    "river": "river",
    "smith_irv": "smith_irv",
    "split_cycle": "split_cycle",
}

#: client rule id -> the backend score rule's key.
SCORED: Dict[str, str] = {
    "score": "simple_score",
    "star": "star_voting",
    "cumulative": "cumulative",
    "maximin": "maximin",
    "nash": "nash",
}

#: Two candidates on the x axis, two on the y axis: a voter at (0, y) is exactly as near to A as to
#: B, one at (x, 0) exactly as near to C as to D.
EQUAL_CANDIDATES: Dict[str, Tuple[float, float]] = {
    "A": (-0.5, 0.0),
    "B": (0.5, 0.0),
    "C": (0.0, 0.6),
    "D": (0.0, -0.6),
}
EQUAL_VOTERS: List[Tuple[float, float]] = [
    (0.0, 0.0), (0.0, 0.0), (0.0, 0.2), (0.0, -0.2), (0.3, 0.0),
    (-0.3, 0.0), (-0.4, 0.1), (0.4, -0.1), (0.1, 0.3),
]
LISTINGS: Dict[str, List[str]] = {"listed": ["A", "B", "C", "D"], "reversed": ["D", "C", "B", "A"]}

#: Seven voters' true utilities for the score experiment (A-D), projected to a 2-place truncated
#: ballot. Found by a seeded search: every one of the five rules elects the same candidate under
#: every seed 0-11 (no lot decides), and the rules do not all elect the same one.
SCORE_UTILITIES: List[List[float]] = [
    [0.9, 0.8, 0.2, 0.7], [0.4, 0.9, 0.6, 0.0], [0.1, 0.2, 0.6, 0.0], [0.0, 0.6, 0.8, 0.4],
    [0.1, 0.8, 0.9, 0.3], [0.3, 0.7, 0.9, 0.4], [0.0, 0.4, 0.3, 0.6],
]
SCORE_TRUNCATE_AT = 2

#: Nine voters' 0-5 grades (multiples of 0.2: both engines read these identically) for the shared
#: approval / majority-judgment experiment. Found by a seeded search: under every seed 0-11 both
#: rules elect C on the full ballots, D on the top-1 ballots and B on the top-2 ballots.
SHARED_GRADES: List[List[float]] = [
    [0.0, 0.8, 0.6, 0.4], [0.4, 0.2, 0.0, 1.0], [1.0, 0.8, 0.6, 0.0], [0.4, 0.6, 1.0, 0.0],
    [0.0, 0.4, 0.2, 0.8], [0.0, 0.4, 0.8, 1.0], [0.6, 0.0, 1.0, 0.2], [0.0, 0.8, 0.6, 1.0],
    [1.0, 0.8, 0.0, 0.6],
]
#: How many places a shared ballot keeps (4 = the full ballot).
SHARED_KEEP = [4, 1, 2]
#: A grade at or above this is an approval.
APPROVAL_GRADE = 0.6

#: Six voters who grade A and B identically (columns A and B equal), above C and D.
TIE_GRADES: List[List[float]] = [
    [1.0, 1.0, 0.2, 0.0], [0.8, 0.8, 0.0, 0.4], [0.6, 0.6, 0.4, 0.2],
    [1.0, 1.0, 0.0, 0.2], [0.8, 0.8, 0.2, 0.0], [0.6, 0.6, 0.0, 0.4],
]

#: Two probe profiles (see the docstring); the seeds a rule is asked under.
PROBES: Dict[str, List[List[str]]] = {
    "duel": [["A"], ["A"], ["A"], ["B", "C"], ["B", "C"]],
    "field": [["D", "B"], ["C", "D"], ["B", "C"]],
}
SEEDS = range(12)


def short_profiles() -> List[List[List[str]]]:
    rng = random.Random(SEED)
    profiles: List[List[List[str]]] = []
    for _ in range(PROFILES):
        ballots = []
        for _ in range(rng.randint(5, 9)):
            order = rng.sample(NAMES, len(NAMES))
            ballots.append(order[: rng.choice([1, 1, 2, 2, 3, 4])])
        profiles.append(ballots)
    return profiles


def ordinal_winner(rule: str, ballots: List[List[str]], seed: int = 0) -> Optional[str]:
    return RANKED_RULES[ORDINAL[rule]]([list(b) for b in ballots], seed=seed)


def equal_rank_winners(order: List[str]) -> Dict[str, Optional[str]]:
    utilities = {
        i: {n: -math.hypot(v[0] - EQUAL_CANDIDATES[n][0], v[1] - EQUAL_CANDIDATES[n][1]) for n in order}
        for i, v in enumerate(EQUAL_VOTERS)
    }
    rankings = rankings_from_utilities(utilities, [{"id": i} for i in range(len(EQUAL_VOTERS))])
    return {rule: ordinal_winner(rule, rankings) for rule in ORDINAL}


def _row(ballot: Dict[str, float], order: List[str]) -> List[float]:
    return [ballot[n] for n in order]


def _stable(label: str, winner_at: Any) -> str:
    """The winner a rule gives under every seed in SEEDS; exit if a lot decides it."""
    winners = {winner_at(seed) for seed in SEEDS}
    if len(winners) != 1 or None in winners:
        sys.exit(f"{label}: no one winner under every seed ({sorted(map(str, winners))}).")
    return str(winners.pop())


def truncated_score_matrix() -> Dict[str, Any]:
    matrix = {i: dict(zip(NAMES, row)) for i, row in enumerate(SCORE_UTILITIES)}
    projected = project_ballot(matrix, NAMES, "rank_truncated", truncate_at=SCORE_TRUNCATE_AT)
    ballots = [_row(projected[i], NAMES) for i in range(len(SCORE_UTILITIES))]
    dicts = [dict(zip(NAMES, row)) for row in ballots]
    winners = {
        rule: _stable(rule, lambda seed, key=key: rule_winner(key, scores=dicts, seed=seed))
        for rule, key in SCORED.items()
    }
    return {"ballots": ballots, "truncateAt": SCORE_TRUNCATE_AT, "backend": winners}


def _keep_top(row: List[float], places: int) -> List[float]:
    """The voter's `places` best grades; every other candidate gets 0."""
    kept = set(sorted(range(len(row)), key=lambda i: -row[i])[:places])
    return [g if i in kept else 0.0 for i, g in enumerate(row)]


def _approvals(row: List[float]) -> List[float]:
    return [1.0 if g >= APPROVAL_GRADE else 0.0 for g in row]


def _grade_winners(grades: List[List[float]], order: List[str]) -> Dict[str, str]:
    """Majority judgment on the grades, approval on the 0/1 ballots they imply, under every seed."""
    ballots = [dict(zip(order, row)) for row in grades]
    approvals = {i: dict(zip(order, _approvals(row))) for i, row in enumerate(grades)}
    return {
        "majority_judgment": _stable(
            "majority_judgment",
            lambda seed: rule_winner("majority_judgment", scores=ballots, seed=seed),
        ),
        "approval": _stable("approval", lambda seed: get_approval_winner_sincere(approvals, seed=seed)),
    }


def shared_grade_ballots() -> Dict[str, Any]:
    cases = []
    for places in SHARED_KEEP:
        grades = [_keep_top(row, places) for row in SHARED_GRADES]
        cases.append({"places": places, "grades": grades, "backend": _grade_winners(grades, NAMES)})
    return {"approvalGrade": APPROVAL_GRADE, "cases": cases}


def score_ties() -> Dict[str, Any]:
    """A and B graded identically by everyone, the candidates listed as given and reversed. The
    winner here is a lot's draw (at seed 0), so this is a measure of the lot, not of a reading."""
    out: Dict[str, Any] = {}
    for label, order in LISTINGS.items():
        grades = [[row[NAMES.index(n)] for n in order] for row in TIE_GRADES]
        dicts = [dict(zip(order, row)) for row in grades]
        approvals = {i: dict(zip(order, _approvals(row))) for i, row in enumerate(grades)}
        winners = {rule: rule_winner(key, scores=dicts) for rule, key in SCORED.items()}
        winners["majority_judgment"] = rule_winner("majority_judgment", scores=dicts)
        winners["approval"] = get_approval_winner_sincere(approvals)
        out[label] = winners
    return {"grades": TIE_GRADES, "listings": LISTINGS, "backend": out}


def probes() -> Dict[str, Any]:
    """`duel`: one winner per rule, the same under every seed. `field`: the set of winners a rule
    gives across the seeds (a lot decides some, which is why it is a set)."""
    out: Dict[str, Any] = {}
    for label, ballots in PROBES.items():
        if label == "duel":
            backend: Dict[str, Any] = {
                rule: _stable(rule, lambda seed, rule=rule: ordinal_winner(rule, ballots, seed))
                for rule in ORDINAL
            }
        else:
            backend = {
                rule: sorted({str(ordinal_winner(rule, ballots, seed)) for seed in SEEDS})
                for rule in ORDINAL
            }
        out[label] = {"ballots": ballots, "backend": backend}
    return out


def build() -> Dict[str, Any]:
    profiles = short_profiles()
    return {
        "_generatedBy": "fast_api_voter/scripts/gen_truncated_ballots.py (PYTHONHASHSEED=0)",
        "_seed": SEED,
        "candidates": NAMES,
        "truncated": {
            "profiles": profiles,
            "backend": {rule: [ordinal_winner(rule, p) for p in profiles] for rule in ORDINAL},
        },
        "probes": probes(),
        "equalRanks": {
            "candidates": {n: list(xy) for n, xy in EQUAL_CANDIDATES.items()},
            "voters": [list(v) for v in EQUAL_VOTERS],
            "listings": LISTINGS,
            "backend": {label: equal_rank_winners(order) for label, order in LISTINGS.items()},
        },
        "scores": truncated_score_matrix(),
        "shared": shared_grade_ballots(),
        "scoreTies": score_ties(),
    }


def render() -> str:
    return json.dumps(build(), indent=1, sort_keys=True) + "\n"


def main() -> None:
    if "--check" in sys.argv[1:]:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != render():
            sys.exit(f"{OUT} is out of step with the backend: regenerate it with this script.")
        print("truncatedBallots.json is in step with the backend.")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(), encoding="utf-8")
    print(f"wrote {PROFILES} short-ballot profiles x {len(ORDINAL)} rules, "
          f"{len(EQUAL_VOTERS)} equal-rank voters x 2 listings, the probes, the score and "
          f"shared-grade ballots -> {OUT}")


if __name__ == "__main__":
    main()
