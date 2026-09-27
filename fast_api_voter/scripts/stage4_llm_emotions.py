"""Stage 4 on the LLM path, step 5: S4.3's emotions.

Pre-registered in plan-polity-build-order.md ("Stage 4 on the LLM path, pre-registered before
running"), signed off and committed before this ran; ADR-012's prerequisite session was accepted
first (`scripts/bakeoff_emotions_prerequisite_results.md`). The grid, the three facts and the
selection are ADR-012's, unchanged; only the bench is the LLM path.

`record --level L` runs every emotion weight set whose total weight is L, each seed closed-loop on
the LLM path -- population 100, 30 chamber seats, 8 years, the full-mechanism config, 12 relaxed
workers, the shipped grammar and budget -- with `emotions.enabled` on at that set, on the static
population (dynamics stay off: none qualified). Level 0 is the all-zero set, which sorts first. A
completed run is skipped; an incomplete one is moved aside, since a journal appends and must never
be reused. A run whose journal holds no `emotions_updated` event stops the recording: nothing
after it could be measured.

`measure --through L` reads E1-E3 from each recorded journal, a whole level at a time in ascending
total weight, and stops at the first level holding a qualifying set; equal total weights go to the
earlier set in grid order. The facts need only journal events, so nothing is replayed. The reading
is `calibrate_dynamic_citizens`'s own (`_moods`, `emotions_arm`), with E3's full terms as fixed in
#535.

`selfcheck` runs the deterministic twin at the all-zero set and checks that reading its journals
from disk here gives exactly the facts `calibrate_dynamic_citizens.measure` gives.

Usage (from fast_api_voter/; `record` needs the vLLM server):
    python scripts/stage4_llm_emotions.py record --level 0
    python scripts/stage4_llm_emotions.py measure --through 0
    python scripts/stage4_llm_emotions.py selfcheck
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.config import PolityConfig, validate_config  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402
from api.domain.polity.twin_calibration import Arm, full_terms, grid, select  # noqa: E402
from calibrate_dynamic_citizens import EMOTION_AXES, YEARS, Runs, _moods, emotions_arm  # noqa: E402
from calibrate_dynamic_citizens import measure as twin_measure  # noqa: E402
from run_polity_flagship import _flagship_config, _write_digest_safely  # noqa: E402
from stage4_llm_legislation import MIN_FREE_GB, _completed, _events, _free_gb, run_report  # noqa: E402
from twin_runs import SEEDS, twin_config  # noqa: E402

POPULATION, SEATS, WORKERS = 100, 30, 12
RUNS_ROOT = Path(os.environ.get("STAGE4_RUNS", Path(__file__).resolve().parent / "stage4_llm_runs"))
"""Where the recorded runs live; overridable so a second worktree can read the runs of the first."""
RUNS = RUNS_ROOT / "s43-emotions"
RESULTS = Path(__file__).resolve().parent / "stage4_llm_emotions_results"
LEVELS = sorted({round(sum(setting.values()), 6) for setting in grid(EMOTION_AXES)})


def level_of(setting: dict[str, float]) -> float:
    return round(sum(setting.values()), 6)


def level_settings(level: float) -> list[dict[str, float]]:
    """The weight sets of one total weight, in grid order."""
    return [setting for setting in grid(EMOTION_AXES) if level_of(setting) == level]


def slug(setting: dict[str, float]) -> str:
    if not any(setting.values()):
        return "zero"
    short = {"awakening_anger": "aa", "awakening_anxiety": "ax", "awakening_enthusiasm": "ae", "mobilization_anger": "ma"}
    return "-".join(f"{short[name]}{value:g}" for name, value in setting.items())


def llm_config(seed: int, emotions: dict[str, float], output_dir: Path) -> PolityConfig:
    config = _flagship_config(
        engine="llm", years=YEARS, population=POPULATION, seats=SEATS, seed=seed, output_dir=output_dir,
        max_batch_replays=2, provider=None, workers=WORKERS, reproducibility="relaxed",
    )
    config = dataclasses.replace(
        config,
        emotions=dataclasses.replace(config.emotions, enabled=True, **emotions),
        journal=dataclasses.replace(config.journal, output_dir=str(output_dir)),
    )
    validate_config(config)
    return config


def record(level: float) -> int:
    for setting in level_settings(level):
        for seed in SEEDS:
            run_id = f"seed-{seed}"
            seed_dir = RUNS / slug(setting) / run_id
            if _completed(seed_dir, run_id):
                print(f"[record] {slug(setting)} {run_id}: already completed, skipped", flush=True)
                continue
            if seed_dir.exists():
                aside = seed_dir.with_name(f"{run_id}.incomplete-{int(time.time())}")
                seed_dir.rename(aside)
                print(f"[record] {slug(setting)} {run_id}: an incomplete attempt moved aside to {aside.name}", flush=True)
            free = _free_gb()
            if free < MIN_FREE_GB:
                print(f"[record] STOP: {free} GB free on / (< {MIN_FREE_GB}) before {slug(setting)} {run_id}", flush=True)
                return 3
            seed_dir.mkdir(parents=True)
            config = llm_config(seed, setting, seed_dir / "run")
            (seed_dir / "config.json").write_text(json.dumps(dataclasses.asdict(config), indent=2, default=str), encoding="utf-8")
            journal = Path(config.journal.output_dir) / run_id / "events.jsonl"
            print(f"[record] {slug(setting)} {run_id}: {YEARS}y x {POPULATION}, {WORKERS} workers, emotions {setting}", flush=True)
            start = time.monotonic()
            try:
                journal = run_simulation(config, run_id=run_id)
            except BaseException as exc:
                _write_digest_safely(journal, config, run_id=run_id, outcome="crashed", resume=False,
                                     elapsed_seconds=time.monotonic() - start, error=exc)
                raise
            elapsed = time.monotonic() - start
            _write_digest_safely(journal, config, run_id=run_id, outcome="completed", resume=False,
                                 elapsed_seconds=elapsed, error=None)
            events = _events(journal)
            report = run_report(seed, events, elapsed)
            (seed_dir / "run_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print(f"[record] {slug(setting)} {run_id}: completed {report}", flush=True)
            if not any(e["event_type"] == "emotions_updated" for e in events):
                print(f"[record] STOP: {slug(setting)} {run_id} journaled no emotions_updated event", flush=True)
                return 4
    print(f"[record] LEVEL {level:g} DONE", flush=True)
    return 0


def runs_from_journals(journals: list[tuple[int, Path]], config: PolityConfig) -> Runs:
    """E1-E3's inputs from journals on disk, as `calibrate_dynamic_citizens.measure` builds them."""
    runs = Runs()
    term_ticks = config.institutions.president_term_years * config.run.ticks_per_year
    for seed, journal in journals:
        events = _events(journal)
        runs.moods += _moods(seed, events)
        runs.terms += full_terms(seed, events, term_ticks)
    return runs


def measure_setting(setting: dict[str, float]) -> Arm:
    journals = []
    for seed in SEEDS:
        run_id = f"seed-{seed}"
        seed_dir = RUNS / slug(setting) / run_id
        if not _completed(seed_dir, run_id):
            raise FileNotFoundError(f"{slug(setting)} {run_id} has no completed recording")
        journals.append((seed, seed_dir / "run" / run_id / "events.jsonl"))
    return emotions_arm(setting, runs_from_journals(journals, llm_config(SEEDS[0], setting, Path("unused"))))


def measure(through: float) -> int:
    measured: list[tuple[float, list[Arm]]] = []
    selected: Arm | None = None
    for level in [value for value in LEVELS if value <= through]:
        arms = []
        for setting in level_settings(level):
            arms.append(measure_setting(setting))
            print(f"[measure] level {level:g} {slug(setting)}: {'qualifies' if arms[-1].qualifies else 'does not qualify'}", flush=True)
        measured.append((level, arms))
        selected = select(arms, lambda arm: arm.measures["total_weight"])
        if selected is not None:
            break

    RESULTS.with_suffix(".json").write_text(json.dumps({
        "levels": [{"total_weight": level, "arms": [dataclasses.asdict(a) for a in arms]} for level, arms in measured],
        "selected": dataclasses.asdict(selected) if selected else None,
        "through_level": through,
    }, indent=2) + "\n", encoding="utf-8")
    RESULTS.with_suffix(".md").write_text(markdown(measured, selected, through), encoding="utf-8")
    print(f"[measure] wrote {RESULTS.name}.{{md,json}}; selected: {slug(selected.setting) if selected else None}", flush=True)
    return 0


def markdown(measured: list[tuple[float, list[Arm]]], selected: Arm | None, through: float) -> str:
    lines = [
        "# Stage 4 on the LLM path: S4.3's emotions",
        "",
        "Generated by `scripts/stage4_llm_emotions.py`, as pre-registered in `plan-polity-build-order.md` "
        f"(\"Stage 4 on the LLM path, pre-registered before running\"). LLM path, population {POPULATION}, seeds "
        f"{SEEDS[0]}–{SEEDS[-1]}, {YEARS} years, static population; E1–E3 read from each run's journal.",
        "",
        "## Verdict",
        "",
        (f"**Selected:** {selected.setting}." if selected is not None
         else f"**None qualifies within the pre-registered budget** (levels up to {through:g} measured)."),
        "",
    ]
    for level, arms in measured:
        names = [fact.name for fact in arms[0].facts]
        lines += [f"## Total weight {level:g}", "", "| setting | " + " | ".join(names) + " | all |", "|---|" + "---|" * (len(names) + 1)]
        for arm in arms:
            cells = [f"{'✓' if f.holds else '✗'} {f.reading}" for f in arm.facts]
            lines.append(f"| {slug(arm.setting)} | " + " | ".join(cells) + f" | {'✓' if arm.qualifies else '✗'} |")
        lines.append("")
    return "\n".join(lines)


def selfcheck() -> int:
    """The twin at the all-zero set: this script's journal reading against the twin calibration's own."""
    zero = level_settings(0.0)[0]
    expected = emotions_arm(zero, twin_measure(None, zero))
    with tempfile.TemporaryDirectory() as work:
        journals = []
        for seed in SEEDS:
            config = twin_config(seed, YEARS)
            config = dataclasses.replace(
                config, emotions=dataclasses.replace(config.emotions, enabled=True, **zero),
                journal=dataclasses.replace(config.journal, output_dir=work))
            journals.append((seed, run_simulation(config, run_id=f"seed-{seed}")))
        read = emotions_arm(zero, runs_from_journals(journals, config))
    llm_config(SEEDS[0], zero, Path("unused"))  # the LLM config validates with emotions on
    for mine, theirs in zip(read.facts, expected.facts, strict=True):
        print(f"[selfcheck] {mine.name}: {mine.reading} | twin calibration: {theirs.reading}", flush=True)
    if read.facts != expected.facts:
        print("[selfcheck] FAILED: the journal reading differs from the twin calibration's", flush=True)
        return 1
    print(f"[selfcheck] the journal reading matches the twin calibration; levels {LEVELS}", flush=True)
    return 0


def _level(value: str) -> float:
    level = round(float(value), 6)
    if level not in LEVELS:
        raise argparse.ArgumentTypeError(f"{value} is not a total weight of the grid: {LEVELS}")
    return level


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("record").add_argument("--level", type=_level, required=True)
    sub.add_parser("measure").add_argument("--through", type=_level, required=True)
    sub.add_parser("selfcheck")
    args: Any = parser.parse_args()
    if args.mode == "record":
        raise SystemExit(record(args.level))
    if args.mode == "measure":
        raise SystemExit(measure(args.through))
    raise SystemExit(selfcheck())
