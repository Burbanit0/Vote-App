"""EXP-029 (Stage 2c): read the model's leaders' moves against Laver and Sergenti's four leader rules (ADR-040).

Finished experiment script (see archive/README.md): not imported, not type-checked, not collected by CI. CPU only. From the runs
of EXP-028 (`<model-runs-dir>/stage2b-scenario-8y-p100-seed{1..10}/run/<id>/{events,snapshots}.jsonl`):

    python scripts/archive/classify_model_leaders_against_rules.py <model-runs-dir>

What it can and cannot read. In this profile `parties.leader_rule` is `sticker` and no party platform moves, so there is no
rule-driven move to compare with. What the model's leaders do is `shifts` on their own `agent_turn` (a dimension and a delta).
Each shifted dimension is read against what a rule would have done from the leader's own position at the latest snapshot at or
before the turn (a snapshot every fourth tick, so an approximation):
  sticker     no move: the share of turns with no shift;
  aggregator  moves toward the centroid of its supporters: share of shifted dimensions whose sign points toward the centroid of
              the leader's own party (and, for comparison, of the whole electorate);
  hunter      keeps its heading: for a leader with two moves on the same dimension, share with the same sign. The rule's
              condition (its poll share rose) is not read;
  explorer    probes five positions and takes the best: not identifiable from one logged move, so not classified.
A chance level is 0.5 for a sign test; a two-sided exact binomial p is printed (scipy-free).
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path


def binom_p(k: int, n: int) -> float:
    """Two-sided exact binomial test against 0.5."""
    if n == 0:
        return float("nan")
    pk = [math.comb(n, i) / 2**n for i in range(n + 1)]
    return min(1.0, sum(p for p in pk if p <= pk[k] + 1e-12))


def centroid(rows: list[list[float]]) -> list[float]:
    return [sum(r[d] for r in rows) / len(rows) for d in range(len(rows[0]))]


def read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main(base: Path) -> None:
    turns = Counter()
    moved = Counter()
    dims = {"party": [0, 0], "electorate": [0, 0]}
    by_role = defaultdict(lambda: {"party": [0, 0], "electorate": [0, 0]})
    persist = [0, 0]
    sizes = []
    for seed in range(1, 11):
        run_id = f"stage2b-scenario-8y-p100-seed{seed}"
        d = base / run_id / "run" / run_id
        events = read(d / "events.jsonl")
        snaps = defaultdict(dict)
        for s in read(d / "snapshots.jsonl"):
            snaps[s["tick"]][s["citizen_id"]] = s
        ticks = sorted(snaps)
        last_move: dict[tuple[int, int], float] = {}
        for e in sorted(
            (x for x in events if x["event_type"] == "agent_turn"),
            key=lambda x: (x["tick"], x["event_id"]),
        ):
            role = e["payload"].get("role")
            if role not in ("president", "nominee"):
                continue
            turns[role] += 1
            shifts = e["payload"].get("shifts") or []
            if not shifts:
                continue
            moved[role] += 1
            t = max(x for x in ticks if x <= e["tick"])
            me = snaps[t].get(e["citizen_id"])
            if me is None:
                continue
            electorate = centroid([s["issue_positions"] for s in snaps[t].values()])
            mine = [
                s["issue_positions"]
                for s in snaps[t].values()
                if s["party_affiliation"] == me["party_affiliation"]
            ]
            party = centroid(mine) if len(mine) > 1 else None
            for sh in shifts:
                dim, delta = sh["dimension"], sh["delta"]
                sizes.append(abs(delta))
                for name, target in (("party", party), ("electorate", electorate)):
                    if target is None or target[dim] == me["issue_positions"][dim]:
                        continue
                    hit = (target[dim] - me["issue_positions"][dim]) * delta > 0
                    for tally in (dims[name], by_role[role][name]):
                        tally[0] += hit
                        tally[1] += 1
                key = (e["citizen_id"], dim)
                if key in last_move:
                    persist[1] += 1
                    persist[0] += last_move[key] * delta > 0
                last_move[key] = delta
    print("turns by role:", dict(turns), "turns with a shift:", dict(moved))
    for role in turns:
        print(
            f" {role}: no move {1 - moved[role] / turns[role]:.1%} (sticker-like), moved {moved[role] / turns[role]:.1%}"
        )
    if sizes:
        print(
            f"shift size: median {sorted(sizes)[len(sizes) // 2]:.3f}, max {max(sizes):.3f}, shifted dimensions {len(sizes)}"
        )
    for name in ("party", "electorate"):
        k, n = dims[name]
        print(
            f"aggregator, toward the {name}'s centroid: {k}/{n} = {k / n:.1%} (p {binom_p(k, n):.3g})"
            if n
            else f"{name}: no data"
        )
        for role, tallies in by_role.items():
            k, n = tallies[name]
            print(
                f"   {role}: {k}/{n}"
                + (f" = {k / n:.1%} (p {binom_p(k, n):.3g})" if n else "")
            )
    k, n = persist
    print(
        f"hunter heading: same sign as the leader's previous move on that dimension {k}/{n}"
        + (f" = {k / n:.1%} (p {binom_p(k, n):.3g})" if n else "")
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]).expanduser())
