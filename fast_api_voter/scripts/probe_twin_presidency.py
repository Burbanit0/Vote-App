"""D9's evidence: why the deterministic twin cannot hold a president, and what would.

D9 (plan-polity-build-order.md) records that all three Stage 4 calibrations ran on a twin
whose presidents are recalled after a median of two ticks (OBS-015), so nothing qualified. It
names the options: accept the verdicts; or make the twin's presidency last -- through the
pressure weights, the recall floor, or a pressure rule calibrated against the LLM path's --
and re-run all three under a new pre-registration.

This probe measures those options instead of arguing them. It is exploratory: it adopts
nothing and pre-registers nothing, and choosing between the options stays the owner's.

1. **Each knob D9 names, alone,** on the calibrations' own twin (population 100, seeds 1-10,
   8 years): how many presidencies end inside the run, how long they last, how many are
   recalled, and how many reach a full 16-tick term. Twenty is the most possible -- two terms
   per seed -- which the run with both pressure channels off reaches, checking the measure.
2. **What the twin's citizens do under pressure,** against the LLM runs it stands in for
   (the p500 batch's completed seeds, read and never written).

A presidency's end is counted from the journal: a recall, or the successor's `elected` at the
next election (the engine journals no term-end event). The last presidency of a run ends with
the run and is not counted as finished.

Usage (from fast_api_voter/):
    python scripts/probe_twin_presidency.py [--llm-runs DIR]   # writes probe_twin_presidency_results.md
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import statistics
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.codebook import PressureAct  # noqa: E402
from api.domain.polity.config import PolityConfig  # noqa: E402
from twin_runs import POPULATION, SEEDS, run_twin, twin_config  # noqa: E402

YEARS = 8
FULL_TERM_TICKS = 16
RESULTS = Path(__file__).resolve().parent / "probe_twin_presidency_results.md"

Tweak = Callable[[PolityConfig], PolityConfig]


def spans(events: Sequence[dict[str, Any]]) -> list[tuple[int, str]]:
    """(length in ticks, how it ended) for each presidency, the run's last one included."""
    out: list[tuple[int, str]] = []
    start: int | None = None
    for event in events:
        tick, kind = int(event["tick"]), event.get("event_type")
        if kind == "elected":
            if start is not None:
                out.append((tick - start, "election"))
            start = tick
        elif kind == "recalled" and start is not None:
            out.append((tick - start, "recalled"))
            start = None
    if start is not None and events:
        out.append((int(events[-1]["tick"]) - start, "run_end"))
    return out


def section(field: str, **changes: Any) -> Tweak:
    return lambda c: dataclasses.replace(c, **{field: dataclasses.replace(getattr(c, field), **changes)})


def together(*tweaks: Tweak) -> Tweak:
    def apply(config: PolityConfig) -> PolityConfig:
        for tweak in tweaks:
            config = tweak(config)
        return config
    return apply


# A pressure channel is two keys that must agree: the menu's switch and the section's own.
MOBILIZATION_OFF = together(section("pressure_menu", mobilization_enabled=False), section("street_pressure", enabled=False))
PETITION_OFF = together(section("pressure_menu", petition_enabled=False), section("petition", enabled=False))

KNOBS: list[tuple[str, str, Tweak]] = [
    ("shipped", "—", lambda c: c),
    ("recall floor 0.10", "the recall floor", section("legitimacy", recall_floor=0.10)),
    ("recall floor 0.05", "the recall floor", section("legitimacy", recall_floor=0.05)),
    ("street decay 0.50", "a pressure weight", section("street_pressure", decay=0.50)),
    ("street decay 0.00", "a pressure weight", section("street_pressure", decay=0.0)),
    ("legitimacy decay 0.8", "a pressure weight", section("legitimacy", decay=0.8)),
    ("legitimacy decay 0.5", "a pressure weight", section("legitimacy", decay=0.5)),
    ("petition channel off", "which channel", PETITION_OFF),
    ("mobilization channel off", "which channel", MOBILIZATION_OFF),
    ("both channels off", "the check", together(MOBILIZATION_OFF, PETITION_OFF)),
]


def knob_row(tweak: Tweak) -> dict[str, Any]:
    finished: list[tuple[int, str]] = []
    for seed in SEEDS:
        events = run_twin(tweak(twin_config(seed=seed, years=YEARS)))
        finished += [span for span in spans(events) if span[1] != "run_end"]
    lengths = [length for length, _ in finished]
    return {
        "ended": len(finished),
        "median": statistics.median(lengths) if lengths else None,
        "recalled": sum(1 for _, how in finished if how == "recalled"),
        "full_terms": sum(1 for length in lengths if length >= FULL_TERM_TICKS),
    }


def act_counts(events: Sequence[dict[str, Any]]) -> Counter[str]:
    return Counter(
        PressureAct(int(e["payload"]["act"])).name
        for e in events
        if e.get("event_type") == "pressure_action" and "act" in (e.get("payload") or {})
    )


def ticks_of(events: Sequence[dict[str, Any]]) -> int:
    return len({int(e["tick"]) for e in events})


def act_row(label: str, counts: Counter[str], ticks: int, population: int) -> str:
    consulted = sum(counts.values())
    mobilize = counts["MOBILIZE"]
    return (f"| {label} | {consulted:,} | {mobilize:,} ({100 * mobilize / consulted:.1f}%) "
            f"| {100 * mobilize / ticks / population:.2f}% | {counts['WAIT_FOR_ELECTION']:,} "
            f"| {counts['SIGN_PETITION']:,} |")


def llm_runs(root: Path) -> list[tuple[str, Path]]:
    found = []
    for journal in sorted(root.glob("*/run/*/events.jsonl")):
        if (journal.parent / "digest.json").is_file() and (journal.parent / "digest.json").stat().st_size > 0:
            found.append((journal.parent.name, journal))
    return found


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--llm-runs", type=Path, default=None,
                        help="a seed-sweep directory holding completed LLM runs (read only)")
    args = parser.parse_args(argv)

    lines = [
        "# Why the twin cannot hold a president (D9's evidence)",
        "",
        "Generated by `scripts/probe_twin_presidency.py`. Exploratory: nothing here is adopted or "
        "pre-registered, and choosing between D9's options stays the owner's.",
        "",
        f"The twin is the Stage 4 calibrations' own: population {POPULATION}, seeds "
        f"{SEEDS[0]}-{SEEDS[-1]}, {YEARS} years. A full term is {FULL_TERM_TICKS} ticks, and "
        f"{2 * len(SEEDS)} is the most possible (two per seed).",
        "",
        "## 1. Each knob D9 names, alone",
        "",
        "| setting | D9's option | presidencies ended | median ticks | recalled | full terms |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for name, option, tweak in KNOBS:
        row = knob_row(tweak)
        share = f"{row['recalled']} ({100 * row['recalled'] / row['ended']:.0f}%)" if row["ended"] else "—"
        median = f"{row['median']:g}" if row["median"] is not None else "—"
        lines.append(f"| {name} | {option} | {row['ended']} | {median} | {share} | {row['full_terms']} |")
        print(name, row, flush=True)

    lines += [
        "",
        "## 2. What citizens do under pressure: the twin against the LLM path",
        "",
        "Every consulted citizen's `pressure_action`. *Mobilizing* is the share of the whole "
        "population mobilizing per tick, the rate `street_pressure` accumulates.",
        "",
        "| run | consulted acts | MOBILIZE | mobilizing per tick | WAIT_FOR_ELECTION | SIGN_PETITION |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    twin_counts: Counter[str] = Counter()
    twin_ticks = 0
    for seed in SEEDS:
        events = run_twin(twin_config(seed=seed, years=YEARS))
        twin_counts += act_counts(events)
        twin_ticks += ticks_of(events)
    lines.append(act_row(f"deterministic twin, p{POPULATION}, {len(SEEDS)} seeds", twin_counts, twin_ticks, POPULATION))

    if args.llm_runs is not None:
        for name, journal in llm_runs(args.llm_runs):
            events = [json.loads(line) for line in journal.open(encoding="utf-8") if line.strip()]
            config = json.loads((journal.parent / "config.json").read_text(encoding="utf-8"))
            population = int(config["run"]["population_size"])
            lines.append(act_row(f"LLM path, `{name}`", act_counts(events), ticks_of(events), population))
    else:
        lines.append("| LLM path | not measured: pass `--llm-runs` | | | | |")

    RESULTS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {RESULTS.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
