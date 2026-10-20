"""ADR-030, stage 2: read a schema_order_live_ab.sh run and apply its pre-registered criteria.

Usage (from fast_api_voter/): python scripts/schema_order_live_report.py <out dir>

The test is by seed. Each seed has two runs, started together on one server: the control code (ctl) and the
candidate (new), from worktrees that differ only in WIRE_ORDER. If the candidate's order changes nothing, the two
runs of a seed are exchangeable, so the difference new - ctl is as likely to be d as -d. The exact sign-flip test
asks: of the 2^k ways to flip the signs of the seeds' differences, how many give a mean at least as far from zero
as the observed one (two-sided, for behaviour) or at least as high (one-sided, for fallbacks and retries)? That
share is the p-value. Two runs of the same code are NOT exchangeable with a third that differs: with the same
seed and the same bytes they replay the same first hundred-odd events (2026-10-20, 8-year A/B), which is why
there is one control, not two.

Holm at ALPHA across the measures that can be tested. A measure equal in every run is "same" and left out. A
measure whose smallest reachable p (2^-k over the seeds where the two runs differ, twice that two-sided) is too
large for Holm to ever reject it, alongside the measures with smaller ones, is "cannot tell" and also left out
(testable). Both conditions are unchanged by any sign flip, so leaving the measure out keeps the test exact. The verdict, written before the run that uses it (ADR-030, "The 8-year A/B and the second gate"):
- FAIL: a share (pressure inaction, forum mind-shift) at 0 or 1, or gone (no such decision at all), where the
  control shows a mix, which needs no test (the motif-first order took pressure inaction to 0%); or fallbacks
  or retries significantly higher.
- CHANGED: a behaviour measure significantly different, either way. Not a rejection: the order is chosen to
  change decisions; the owner reads what changed before it ships.
- No verdict: a behaviour measure that varies could not be tested (too few seeds).
- PASS: none of these, naming the failure measures it could not tell (fallbacks are sparse).
Exit 0 on PASS, 2 on CHANGED, 1 on FAIL or no verdict.
"""

from __future__ import annotations

import collections
import glob
import itertools
import json
import os
import re
import sys
from typing import Any

ARMS = ("ctl", "new")
ALPHA = 0.05
MEASURES = (
    "elections per run",
    "recalls per run",
    "office occupancy",
    "pressure 'nothing' share",
    "forum mind-shift rate",
    "fallbacks",
    "retry rate",
)
FAILURES = {"fallbacks", "retry rate"}
"""Only an excess counts: fewer retries or fallbacks than the control is never a failure."""
SHARES = {"pressure 'nothing' share", "forum mind-shift rate"}
"""Shares that must not collapse to 0 or 1, or vanish, where the control shows a mix."""
_RUN = re.compile(r"^(sweep-.+)-seed(\d+)$")


def _jsonl(path: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()] if os.path.exists(path) else []


def runs(out: str, arm: str) -> dict[tuple[str, int], dict[str, Any]]:
    """(sweep, seed) -> the arm's run, the sweep being e.g. "sweep-8y-p100", so seed10 pairs with seed10."""
    loaded = {}
    for digest in sorted(glob.glob(os.path.join(out, arm, "sweep-*", "run", "*", "digest.json"))):
        run = os.path.dirname(digest)
        match = _RUN.match(os.path.basename(run))
        if match is None:
            print(f"not a sweep run, left out: {run}")
            continue
        loaded[(match.group(1), int(match.group(2)))] = {
            "digest": json.load(open(digest, encoding="utf-8")),
            "events": _jsonl(os.path.join(run, "events.jsonl")),
            "calls": _jsonl(os.path.join(run, "llm_calls.jsonl")),
        }
    return loaded


def _act(event: dict[str, Any]) -> Any:
    return event["act"] if event.get("act") is not None else (event.get("payload") or {}).get("act")


def _content(call: dict[str, Any]) -> Any:
    try:
        return json.loads(call.get("content") or "")
    except ValueError:
        return None


def measures(rs: list[dict[str, Any]]) -> dict[str, float | None]:
    """None for a share with nothing to be a share of (no pressure actions, no forum posts)."""
    events = [e for r in rs for e in r["events"]]
    kinds = collections.Counter(e["event_type"] for e in events)
    acts = [_act(e) for e in events if e["event_type"] == "pressure_action"]
    decisions = [c for r in rs for c in r["calls"] if c.get("kind") == "decision"]
    forum = [j for c in decisions if c.get("decision_type") == "forum_post" and not c.get("attempt")
             for j in [_content(c)] if isinstance(j, dict)]
    n = len(rs) or 1
    return {
        "elections per run": kinds["elected"] / n,
        "recalls per run": kinds["recalled"] / n,
        "office occupancy": sum(r["digest"].get("office_occupancy") or 0 for r in rs) / n,
        "pressure 'nothing' share": sum(a == 0 for a in acts) / len(acts) if acts else None,
        "forum mind-shift rate": sum(j.get("shift_issue", -1) != -1 for j in forum) / len(forum) if forum else None,
        "fallbacks": float(sum(r["digest"].get("llm_fallbacks") or 0 for r in rs)),
        "retry rate": sum(1 for c in decisions if c.get("attempt")) / len(decisions) if decisions else 0.0,
    }


def sign_flip_p(diffs: list[float], one_sided: bool) -> tuple[float, float]:
    """(mean difference, exact p) over every sign flip of the seeds' new - ctl differences.
    ponytail: enumerates all 2^k flips, fine to ~20 seeds; sample them if a run ever has more."""
    observed = sum(diffs) / len(diffs)
    moving = [d for d in diffs if d != 0]  # a zero difference is the same under either sign
    eps = 1e-12 * max(1.0, abs(observed))
    hits = 0
    for signs in itertools.product((1, -1), repeat=len(moving)):
        flipped = sum(s * d for s, d in zip(signs, moving)) / len(diffs)
        hits += flipped >= observed - eps if one_sided else abs(flipped) >= abs(observed) - eps
    return observed, hits / 2 ** len(moving)


def smallest_p(diffs: list[float], one_sided: bool) -> float:
    """The smallest p the test can give these seeds, whatever their values: only the all-same-sign flips reach
    the extreme, one of them one-sided, two (all plus, all minus) two-sided."""
    return (1 if one_sided else 2) / 2.0 ** sum(d != 0 for d in diffs)


def holm(pvalues: dict[str, float], alpha: float = ALPHA) -> set[str]:
    """The measures Holm rejects: the i-th smallest p against alpha / (m - i), stopping at the first that holds."""
    rejected: set[str] = set()
    for i, (name, p) in enumerate(sorted(pvalues.items(), key=lambda item: item[1])):
        if p >= alpha / (len(pvalues) - i):
            break
        rejected.add(name)
    return rejected


def testable(diffs: dict[str, list[float]]) -> tuple[set[str], set[str]]:
    """(the measures Holm tests, those it cannot tell). The family is the largest set of the measures with the
    smallest reachable p-values that Holm could reject in full if every p came out at that value: a measure with
    a larger reachable p only raises the bar for the others, so the family is always such a prefix. Which
    measures it holds depends only on which seeds differ, never on the signs, so the test stays exact."""
    varying = {name for name, ds in diffs.items() if any(ds)}
    best = {name: smallest_p(diffs[name], name in FAILURES) for name in varying}
    for cut in sorted(set(best.values()), reverse=True):
        family = {name for name, p in best.items() if p <= cut}
        if holm({name: best[name] for name in family}) == family:
            return family, varying - family
    return set(), varying


def collapsed(name: str, pooled: dict[str, dict[str, float | None]]) -> bool:
    """A share at 0 or 1, or with nothing left to be a share of, where the control's is a mix."""
    ctl, new = pooled["ctl"][name], pooled["new"][name]
    return name in SHARES and ctl is not None and 0.0 < ctl < 1.0 and (new is None or new in (0.0, 1.0))


def _diff(ctl: float | None, new: float | None) -> float:
    """A seed where either run has no such decision cannot vote on the share."""
    return 0.0 if ctl is None or new is None else new - ctl


def main(out: str) -> int:
    per_arm = {arm: runs(out, arm) for arm in ARMS}
    incomplete = [arm for arm, rs in per_arm.items()
                  if not rs or any(r["digest"].get("outcome") != "completed" for r in rs.values())]
    if incomplete:
        print(f"incomplete arms: {', '.join(incomplete)}")
        return 1
    sweeps = {sweep for rs in per_arm.values() for sweep, _ in rs}
    if len(sweeps) > 1:
        print(f"more than one sweep in {out}: {sorted(sweeps)}; pair one sweep size per out dir")
        return 1
    keys = sorted(set(per_arm["ctl"]) & set(per_arm["new"]))
    unpaired = sorted(set(per_arm["ctl"]) ^ set(per_arm["new"]))
    if unpaired:
        print(f"seeds missing from an arm, left out: {[seed for _, seed in unpaired]}")
    pooled = {arm: measures([per_arm[arm][k] for k in keys]) for arm in ARMS}
    per_seed = {arm: [measures([per_arm[arm][k]]) for k in keys] for arm in ARMS}
    diffs = {name: [_diff(ctl[name], new[name]) for ctl, new in zip(per_seed["ctl"], per_seed["new"])]
             for name in MEASURES}
    family, cannot_tell = testable(diffs)
    tests = {name: sign_flip_p(diffs[name], name in FAILURES) for name in family}
    rejected = holm({name: p for name, (_, p) in tests.items()})
    print(f"{len(keys)} paired seeds {[seed for _, seed in keys]}; exact sign-flip test by seed, Holm across the "
          f"{len(family)} measures it can test, at {ALPHA}\n")
    print("| measure | ctl | new | new − ctl, mean per seed | p | result |\n| --- | ---: | ---: | ---: | ---: | --- |")
    failed = changed = False
    for name in MEASURES:
        effect = sum(diffs[name]) / len(diffs[name]) if diffs[name] else 0.0  # the tested statistic, as in sign_flip_p
        p = f"{tests[name][1]:.3g}{' (one-sided)' if name in FAILURES else ''}" if name in tests else "–"
        result = "same" if not any(diffs[name]) else "cannot tell" if name in cannot_tell else "no difference"
        if collapsed(name, pooled):
            result, failed = "**collapsed**", True
        elif name in rejected and name in FAILURES:
            result, failed = "**worse**", True
        elif name in rejected:
            result, changed = "**changed**", True
        fmt = {arm: "–" if pooled[arm][name] is None else f"{pooled[arm][name]:.3g}" for arm in ARMS}
        print(f"| {name} | {fmt['ctl']} | {fmt['new']} | {effect:+.3g} | {p} | {result} |")
    untold = f" Cannot tell: {', '.join(sorted(cannot_tell))}." if cannot_tell else ""
    if failed:
        print("\nFAIL: keep the current WIRE_ORDER")
        return 1
    if not keys:
        print("\nno verdict: no seed has a run in both arms")
        return 1
    if changed:
        print(f"\nCHANGED: the candidate moves a behaviour measure; the owner reads what changed before it ships.{untold}")
        return 2
    if cannot_tell - FAILURES:
        print(f"\nno verdict: {len(keys)} paired seeds are too few to test every behaviour measure.{untold}")
        return 1
    print(f"\nPASS: the candidate WIRE_ORDER may ship.{untold}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
