"""EXP-029 (Stage 2c): read the model's leaders' moves against Laver and Sergenti's four leader rules (ADR-040).

Finished experiment script (see archive/README.md): not imported, not type-checked, not collected by CI. CPU only. From the runs
of EXP-028 (`<model-runs-dir>/stage2b-scenario-8y-p100-seed{1..10}/run/<id>/{events,snapshots}.jsonl`):

    python scripts/archive/classify_model_leaders_against_rules.py <model-runs-dir>

What it can and cannot read. In this profile `parties.leader_rule` is `sticker` and no party platform moves, so there is no
rule-driven move to compare with. What the model's leaders do is `shifts` on their own `agent_turn`: the kernel's step toward
the targets the model named (`agents.steps_toward`, at most 0.3 a dimension), applied to the leader's *stated* position (a
nominee's pledge, a president's `revealed`), not to the sincere one. The stated position is replayed here from the journal
the way `run_frames` does: candidacy (own position at the latest snapshot at or before it), `campaign_positioning`,
`mandate_pledge_declared`, then each turn's shifts, clamped to 0..1. Each shifted dimension is read from there:
  sticker     no move: the share of turns with no shift (the model restated the value it was shown, or the kernel dropped a
              step under half the shown precision);
  aggregator  the sign points toward the centroid of the leader's party without the leader (two members at least), and, for
              comparison, toward the electorate's median (what the prompts show as `public median`) and centroid; a dimension
              where the target is within 0.02 of the leader's value is skipped. Two baselines: the hit rate expected from the
              sign mix alone, and from a same-size random group of citizens in place of the party;
  hunter      for a leader with two shifts on the same dimension in the same campaign or term, share with the same sign
              (the rule's own condition, its poll share, is not read);
  explorer    probes five positions and takes the best: not identifiable from one logged move, so not classified.
Sincere positions and parties come from the latest snapshot (every fourth tick) at or before the turn, so up to three ticks old.
"""

from __future__ import annotations

import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

MIN_GAP = 0.02


def binom_p(k: int, n: int) -> float:
    """Two-sided exact binomial test against 0.5, summing the terms no likelier than the observed one (relative tolerance)."""
    if n == 0:
        return float("nan")
    pk = [math.comb(n, i) / 2**n for i in range(n + 1)]
    return min(1.0, sum(p for p in pk if p <= pk[k] * (1 + 1e-9)))


def read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def shifted(base: list[float], shifts: list[dict]) -> list[float]:
    out = list(base)
    for s in shifts:
        out[s["dimension"]] = min(1.0, max(0.0, out[s["dimension"]] + s["delta"]))
    return out


def median(values: list[float]) -> float:
    v = sorted(values)
    return v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2


def pct(k: int, n: int) -> str:
    return f"{k}/{n} = {k / n:.1%} (p {binom_p(k, n):.2g})" if n else "no data"


def main(base: Path) -> None:
    rng = random.Random(0)
    turns, moved, unreadable = Counter(), Counter(), Counter()
    norms: dict[str, list[float]] = defaultdict(list)
    sizes: list[float] = []
    hits = {
        r: {t: [0, 0] for t in ("median", "centroid", "party")}
        for r in ("nominee", "president")
    }
    signs = {
        r: {t: [0, 0, 0, 0] for t in ("median", "centroid", "party")} for r in hits
    }  # target up&delta up, target up, delta up, n
    null_party = {r: [0.0, 0] for r in hits}
    persist = {r: [0, 0] for r in hits}
    for seed in range(1, 11):
        run_id = f"stage2b-scenario-8y-p100-seed{seed}"
        d = base / run_id / "run" / run_id
        snaps = defaultdict(dict)
        for s in read(d / "snapshots.jsonl"):
            snaps[s["tick"]][s["citizen_id"]] = s
        ticks = sorted(snaps)
        stated: dict[int, list[float]] = {}
        term: Counter = Counter()
        last: dict[tuple, float] = {}
        for e in read(d / "events.jsonl"):
            kind, cid, p = e["event_type"], e.get("citizen_id"), e.get("payload") or {}
            sincere = snaps[max(t for t in ticks if t <= e["tick"])]
            if kind == "candidacy_declared":
                stated[cid] = list(sincere[cid]["issue_positions"])
                term[cid] += 1
            elif kind == "campaign_positioning":
                stated[cid] = shifted(
                    list(sincere[cid]["issue_positions"]), p["shifts"]
                )
            elif kind == "mandate_pledge_declared":
                stated[cid] = [float(v) for v in p["pledged_platform"]]
                term[cid] += 1
            elif kind == "representative_response":
                if cid in stated:
                    stated[cid] = shifted(stated[cid], p["shifts"])
            elif kind == "agent_turn" and p.get("role") in ("president", "nominee"):
                role = p["role"]
                if cid not in stated:
                    unreadable[role] += 1
                    continue
                turns[role] += 1
                shifts = p.get("shifts") or []
                own = stated[cid]
                if shifts:
                    moved[role] += 1
                    norms[role].append(math.sqrt(sum(s["delta"] ** 2 for s in shifts)))
                    peers = [s for c, s in sincere.items() if c != cid]
                    mates = [
                        s["issue_positions"]
                        for s in peers
                        if s["party_affiliation"] == sincere[cid]["party_affiliation"]
                    ]
                    allpos = [s["issue_positions"] for s in peers]
                    for sh in shifts:
                        dim, delta = sh["dimension"], sh["delta"]
                        sizes.append(abs(delta))
                        targets = {
                            "median": median([x[dim] for x in allpos]),
                            "centroid": sum(x[dim] for x in allpos) / len(allpos),
                        }
                        if len(mates) >= 2:
                            targets["party"] = sum(x[dim] for x in mates) / len(mates)
                            draw = [rng.sample(allpos, len(mates)) for _ in range(20)]
                            rate = (
                                sum(
                                    (sum(x[dim] for x in g) / len(g) - own[dim]) * delta
                                    > 0
                                    for g in draw
                                )
                                / 20
                            )
                            if abs(targets["party"] - own[dim]) >= MIN_GAP:
                                null_party[role][0] += rate
                                null_party[role][1] += 1
                        for name, target in targets.items():
                            if abs(target - own[dim]) < MIN_GAP:
                                continue
                            hits[role][name][0] += (target - own[dim]) * delta > 0
                            hits[role][name][1] += 1
                            sg = signs[role][name]
                            sg[0] += (target > own[dim]) and delta > 0
                            sg[1] += target > own[dim]
                            sg[2] += delta > 0
                            sg[3] += 1
                        key = (role, cid, dim, term[cid])
                        if key in last:
                            persist[role][1] += 1
                            persist[role][0] += last[key] * delta > 0
                        last[key] = delta
                    stated[cid] = shifted(own, shifts)
    print(
        "readable turns:",
        dict(turns),
        "with a shift:",
        dict(moved),
        "unreadable (no stated position yet):",
        dict(unreadable),
    )
    for role in ("nominee", "president"):
        print(
            f"\n{role}: no shift {1 - moved[role] / turns[role]:.1%} of {turns[role]} turns; a turn that moves has a Euclidean step of "
            f"median {sorted(norms[role])[len(norms[role]) // 2]:.3f}, mean {sum(norms[role]) / len(norms[role]):.3f}"
        )
        for name in ("median", "centroid", "party"):
            k, n = hits[role][name]
            tu, tn, du, n2 = signs[role][name]
            chance = (
                (tu * du / n2 + (n2 - tu) * (n2 - du) / n2) / n2 if n2 else float("nan")
            )
            print(
                f"  toward the electorate's {name:9s}: {pct(k, n)}; chance from the sign mix {chance:.3f}"
            )
        k, n = persist[role]
        print(f"  same-sign repeat on a dimension in one campaign or term: {pct(k, n)}")
        v, c = null_party[role]
        print(
            f"  random same-size group in place of the party: expected hit rate {v / c:.3f} over {c} dimensions"
            if c
            else ""
        )
    allsizes = sorted(sizes)
    print(
        f"\nshifted dimensions {len(sizes)}: median {allsizes[len(allsizes) // 2]:.3f}, at the 0.3 cap {sum(s >= 0.2995 for s in sizes)} ({sum(s >= 0.2995 for s in sizes) / len(sizes):.0%})"
    )
    print(f"president turns per run-year: {turns['president'] / 10 / 8:.1f}")


if __name__ == "__main__":
    main(Path(sys.argv[1]).expanduser())
