"""ADR-030, stage 2: read a schema_order_live_ab.sh run and apply its pre-registered criteria.

Usage (from fast_api_voter/): python scripts/schema_order_live_report.py <out dir>

Each measure is pooled per arm over its seeds. The candidate passes a measure when it lies within the range of
the two controls (ctl-a, ctl-b: the same code twice, so their difference is live noise), widened to half and
twice the controls when they agree exactly, and to an absolute floor for measures the controls put at zero.
Fallbacks and retries are failures, so only an excess fails them.
The candidate WIRE_ORDER ships only if every measure passes.
"""
from __future__ import annotations

import collections
import glob
import json
import os
import sys
from typing import Any

ARMS = ("ctl-a", "ctl-b", "new")
FLOOR = {"recalls per run": 1.0, "fallbacks": 5.0, "retry rate": 0.02, "forum mind-shift rate": 0.02}
"""How far above zero a measure may go when both controls put it at zero."""
LOWER_IS_BETTER = {"fallbacks", "retry rate"}
"""Failures, not behaviour: only an excess fails them (2026-10-20: the first table had fewer retries than both
controls, and a two-sided range called that a failure)."""


def _jsonl(path: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()] if os.path.exists(path) else []


def runs(out: str, arm: str) -> list[dict[str, Any]]:
    loaded = []
    for digest in sorted(glob.glob(os.path.join(out, arm, "sweep-*", "run", "*", "digest.json"))):
        run = os.path.dirname(digest)
        loaded.append({"digest": json.load(open(digest, encoding="utf-8")), "events": _jsonl(os.path.join(run, "events.jsonl")),
                       "calls": _jsonl(os.path.join(run, "llm_calls.jsonl"))})
    return loaded


def _act(event: dict[str, Any]) -> Any:
    return event["act"] if event.get("act") is not None else (event.get("payload") or {}).get("act")


def _content(call: dict[str, Any]) -> Any:
    try:
        return json.loads(call.get("content") or "")
    except ValueError:
        return None


def measures(rs: list[dict[str, Any]]) -> dict[str, float]:
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
        "pressure 'nothing' share": sum(a == 0 for a in acts) / len(acts) if acts else 0.0,
        "forum mind-shift rate": sum(j.get("shift_issue", -1) != -1 for j in forum) / len(forum) if forum else 0.0,
        "fallbacks": float(sum(r["digest"].get("llm_fallbacks") or 0 for r in rs)),
        "retry rate": sum(1 for c in decisions if c.get("attempt")) / len(decisions) if decisions else 0.0,
    }


def verdict(name: str, controls: list[float], candidate: float) -> tuple[float, float, bool]:
    low, high = min(controls), max(controls)
    if low == high:
        low, high = low / 2, high * 2
    high = max(high, FLOOR.get(name, 0.0))
    if name in LOWER_IS_BETTER:
        low = 0.0
    return low, high, low <= candidate <= high


def main(out: str) -> int:
    per_arm = {arm: runs(out, arm) for arm in ARMS}
    missing = [arm for arm, rs in per_arm.items() if not rs or any(r["digest"].get("outcome") != "completed" for r in rs)]
    if missing:
        print(f"incomplete arms: {', '.join(missing)}")
        return 1
    values = {arm: measures(rs) for arm, rs in per_arm.items()}
    print("| measure | ctl-a | ctl-b | new | allowed | passes |\n| --- | ---: | ---: | ---: | --- | --- |")
    passed = True
    for name in values["new"]:
        low, high, ok = verdict(name, [values["ctl-a"][name], values["ctl-b"][name]], values["new"][name])
        passed &= ok
        print(f"| {name} | {values['ctl-a'][name]:.3g} | {values['ctl-b'][name]:.3g} | {values['new'][name]:.3g} | "
              f"[{low:.3g}, {high:.3g}] | {'yes' if ok else '**no**'} |")
    print(f"\n{'PASS: the candidate WIRE_ORDER may ship' if passed else 'FAIL: keep the current WIRE_ORDER'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
