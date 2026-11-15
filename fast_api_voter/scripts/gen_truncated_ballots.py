#!/usr/bin/env python3
"""Generate voter-app/src/lib/__fixtures__/truncatedBallots.json: what the BACKEND does with a
truncated ballot and with equal ranks, so the client's tests can set the two side by side
(docs/spec/truncated-ballots.md; PLAN_GLOBAL_2026-11.md, Phase 3).

This records what each engine does TODAY. It is not a convention and it changes no behaviour: the
client's own answers are pinned in voter-app/src/lib/truncatedBallots.test.ts, and the backend's
in api/tests/test_truncated_ballots_as_is.py, which also checks this file is in step.

Three experiments, all on the 21 ordinal rules the two engines share:
  truncated    60 fixed profiles of 5-9 ballots over A-D, each ballot ranking 1 to 4 of them;
  equalRanks   voters exactly equidistant from two candidates, run through the backend's own
               profile construction (`rankings_from_utilities`, the per-voter lot of #662),
               with the candidates listed as given and reversed;
  scores       a truncated SCORE ballot (the backend's `project_ballot`, "rank_truncated":
               the top k scored, the rest 0), for the five score rules.

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
    SCORE_RULES,
    rankings_from_utilities,
)
from api.engine.utils.profile_engine import project_ballot  # noqa: E402

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

#: Six voters' true utilities for the score experiment (A-D), projected to a 2-place truncated ballot.
SCORE_UTILITIES: List[List[float]] = [
    [0.9, 0.2, 0.6, 0.1], [0.1, 0.8, 0.7, 0.3], [0.5, 0.4, 0.9, 0.2],
    [0.3, 0.9, 0.2, 0.6], [0.8, 0.1, 0.3, 0.7], [0.2, 0.3, 0.8, 0.9],
]
SCORE_TRUNCATE_AT = 2


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


def ordinal_winner(rule: str, ballots: List[List[str]]) -> Optional[str]:
    return RANKED_RULES[ORDINAL[rule]]([list(b) for b in ballots])


def equal_rank_winners(order: List[str]) -> Dict[str, Optional[str]]:
    utilities = {
        i: {n: -math.hypot(v[0] - EQUAL_CANDIDATES[n][0], v[1] - EQUAL_CANDIDATES[n][1]) for n in order}
        for i, v in enumerate(EQUAL_VOTERS)
    }
    rankings = rankings_from_utilities(utilities, [{"id": i} for i in range(len(EQUAL_VOTERS))])
    return {rule: ordinal_winner(rule, rankings) for rule in ORDINAL}


def truncated_score_matrix() -> Dict[str, Any]:
    matrix = {i: dict(zip(NAMES, row)) for i, row in enumerate(SCORE_UTILITIES)}
    projected = project_ballot(matrix, NAMES, "rank_truncated", truncate_at=SCORE_TRUNCATE_AT)
    ballots = [[projected[i][n] for n in NAMES] for i in range(len(SCORE_UTILITIES))]
    winners: Dict[str, Optional[str]] = {}
    for rule, key in SCORED.items():
        result = SCORE_RULES[key]([dict(zip(NAMES, row)) for row in ballots])
        winners[rule] = result["winner"] if isinstance(result, dict) else result
    return {"ballots": ballots, "truncateAt": SCORE_TRUNCATE_AT, "backend": winners}


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
        "equalRanks": {
            "candidates": {n: list(xy) for n, xy in EQUAL_CANDIDATES.items()},
            "voters": [list(v) for v in EQUAL_VOTERS],
            "listings": LISTINGS,
            "backend": {label: equal_rank_winners(order) for label, order in LISTINGS.items()},
        },
        "scores": truncated_score_matrix(),
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
          f"{len(EQUAL_VOTERS)} equal-rank voters x 2 listings, 1 score matrix -> {OUT}")


if __name__ == "__main__":
    main()
