"""Stage 4 on the LLM path, step 1: S4.2's L1-L3 from one recorded run per seed.

Pre-registered in plan-polity-build-order.md ("Stage 4 on the LLM path, pre-registered before
running"), signed off and committed before this ran.

`record` runs each seed once on the LLM path -- population 100, 30 chamber seats, 16 years, the
full-mechanism config, 12 relaxed workers, the shipped grammar and thinking budget -- with
legislation on at interval 4 and step 0.05 and `policy_retrospection` 0. Each run keeps its call
log. A seed already completed is skipped; a seed left incomplete is moved aside and run again,
since a journal appends and must never be reused.

`replay` re-runs every seed at each of the nine (interval, step) settings from its call log, on
CPU. At weight 0 a legislation setting changes nothing the model is asked, so each replay is the
model's own run under a different legislature. A replay asking for a call it never recorded raises;
the pre-registration then runs that setting closed-loop instead, so the failure is reported, not
absorbed. L1-L3 are read exactly as the twin calibration read them (`calibrate_legislation`), from
the same observer and the same journal parsers.

`selfcheck` pushes the pilot's recorded 8-year run through the replay and the measurement, so the
pipeline is proven on real model output before any GPU hour is spent on recording.

Usage (from fast_api_voter/; `record` needs the vLLM server, the others do not):
    python scripts/stage4_llm_legislation.py record
    python scripts/stage4_llm_legislation.py replay
    python scripts/stage4_llm_legislation.py selfcheck
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.accountability import current_office_holders  # noqa: E402
from api.domain.polity.citizen import Office  # noqa: E402
from api.domain.polity.config import PolityConfig, validate_config  # noqa: E402
from api.domain.polity.legislation import population_median, rms_distance  # noqa: E402
from api.domain.polity.llm_replay import ReplayClient  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402
from api.domain.polity.twin_calibration import (  # noqa: E402
    PolicyTick,
    checks_moderate,
    full_terms,
    gridlock_under_cohabitation,
    legislation_alive,
)
from calibrate_legislation import INTERVALS, STEPS, Runs, _drafts, _spells  # noqa: E402
from run_polity_flagship import _flagship_config, _write_digest_safely  # noqa: E402
from twin_runs import SEEDS, observing  # noqa: E402

YEARS = 16
POPULATION, SEATS, WORKERS = 100, 30, 12
RECORDED = {"bill_interval_ticks": 4, "max_bill_step": 0.05}
TERM_TICKS = 16
MIN_FREE_GB = 10
RUNS = Path(__file__).resolve().parent / "stage4_llm_runs" / "s42-record"
PILOT = Path(__file__).resolve().parent / "stage4_llm_runs" / "pilot-8y-p100-seed1" / "run" / "pilot-8y-p100-seed1"
RESULTS = Path(__file__).resolve().parent / "stage4_llm_legislation_results"


def llm_config(seed: int, years: int, legislation: dict[str, float], output_dir: Path) -> PolityConfig:
    config = _flagship_config(
        engine="llm", years=years, population=POPULATION, seats=SEATS, seed=seed, output_dir=output_dir,
        max_batch_replays=2, provider=None, workers=WORKERS, reproducibility="relaxed",
    )
    config = dataclasses.replace(
        config,
        legislation=dataclasses.replace(config.legislation, enabled=True, **legislation),
        vote=dataclasses.replace(config.vote, policy_retrospection=0.0),
        journal=dataclasses.replace(config.journal, output_dir=str(output_dir)),
    )
    validate_config(config)
    return config


def _events(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_report(seed: int, events: list[dict[str, Any]], elapsed: float | None) -> dict[str, Any]:
    """What the pre-registration reports for every run, and never selects on."""
    decided: Counter[str] = Counter()
    fell_back: Counter[str] = Counter()
    for e in events:
        payload = e.get("payload") or {}
        if "llm_fallback" in payload:
            decided[e["event_type"]] += 1
            fell_back[e["event_type"]] += bool(payload["llm_fallback"])
    return {
        "seed": seed,
        "wall_clock_minutes": round(elapsed / 60, 1) if elapsed is not None else None,
        "elections": sum(e["event_type"] == "elected" for e in events),
        "recalls": sum(e["event_type"] == "recalled" for e in events),
        "full_terms": _completed_terms(seed, events),
        "fallbacks": {t: f"{fell_back[t]}/{decided[t]}" for t in sorted(decided) if fell_back[t]},
    }


def _completed_terms(seed: int, events: list[dict[str, Any]]) -> int:
    """Full terms that fit inside the run. `full_terms` also counts a presidency elected too late to
    run its term before the run ends -- honeymoon_decline leaves that one unmeasured -- and a report
    of how many terms completed should not."""
    last_tick = max((int(e["tick"]) for e in events), default=0)
    return sum(1 for term in full_terms(seed, events, TERM_TICKS) if term.start + TERM_TICKS <= last_tick)


def _free_gb() -> int:
    out = subprocess.run(["df", "-BG", "--output=avail", "/"], capture_output=True, text=True).stdout
    return int("".join(ch for ch in out.splitlines()[-1] if ch.isdigit()))


def _completed(seed_dir: Path, run_id: str) -> bool:
    digest = seed_dir / "run" / run_id / "digest.json"
    if not digest.is_file() or not digest.stat().st_size:
        return False
    return json.loads(digest.read_text(encoding="utf-8")).get("outcome") == "completed"


def record() -> int:
    RUNS.mkdir(parents=True, exist_ok=True)
    for seed in SEEDS:
        run_id = f"seed-{seed}"
        seed_dir = RUNS / run_id
        if _completed(seed_dir, run_id):
            print(f"[record] {run_id}: already completed, skipped", flush=True)
            continue
        if seed_dir.exists():
            aside = seed_dir.with_name(f"{run_id}.incomplete-{int(time.time())}")
            seed_dir.rename(aside)
            print(f"[record] {run_id}: an incomplete attempt moved aside to {aside.name}", flush=True)
        free = _free_gb()
        if free < MIN_FREE_GB:
            print(f"[record] STOP: {free} GB free on / (< {MIN_FREE_GB}) before {run_id}", flush=True)
            return 3
        seed_dir.mkdir(parents=True)
        config = llm_config(seed, YEARS, RECORDED, seed_dir / "run")
        (seed_dir / "config.json").write_text(json.dumps(dataclasses.asdict(config), indent=2, default=str), encoding="utf-8")
        journal = Path(config.journal.output_dir) / run_id / "events.jsonl"
        print(f"[record] {run_id}: {YEARS}y x {POPULATION}, {WORKERS} workers, legislation {RECORDED}, {free} GB free", flush=True)
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
        report = run_report(seed, _events(journal), elapsed)
        (seed_dir / "run_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"[record] {run_id}: completed {report}", flush=True)
    print("[record] ALL SEEDS DONE", flush=True)
    return 0


def replay_setting(recorded: list[tuple[int, Path]], years: int, interval: int, step: float) -> tuple[Runs, list[dict[str, int]]]:
    """L1-L3's inputs for one (interval, step) setting, every seed replayed from its call log."""
    runs = Runs()
    served: list[dict[str, int]] = []
    for seed, run_dir in recorded:
        client = ReplayClient.from_run_dir(run_dir)

        def observe(context: Any, state: Any, seed: int = seed) -> None:
            legislature = state.legislature
            president = next((h for h in current_office_holders(state.citizens, Office.PRESIDENT)
                              if h.revealed_position is not None), None)
            if legislature is None or legislature.seats is None or president is None:
                return
            median = population_median(state.citizens)
            runs.ticks.append(PolicyTick(seed=seed, tick=context.tick, policy_distance=rms_distance(legislature.policy, median),
                                         president_distance=rms_distance(president.revealed_position, median)))

        with tempfile.TemporaryDirectory() as work:
            config = llm_config(seed, years, {"bill_interval_ticks": interval, "max_bill_step": step}, Path(work))
            with observing(observe):
                journal = run_simulation(config, run_id=run_dir.name, llm_client=client)
            events = _events(journal)
        runs.drafts += _drafts(seed, events)
        runs.enacted.append(sum(e["event_type"] == "bill_enacted" for e in events))
        runs.terms.append(sum(e["event_type"] == "elected" for e in events))
        runs.spells += _spells(seed, events)
        served.append({"seed": seed, "served": client.served, "unserved": client.unserved})
    return runs, served


def facts(runs: Runs) -> list[Any]:
    return [checks_moderate(runs.ticks), legislation_alive(runs.enacted, runs.terms), gridlock_under_cohabitation(runs.drafts)]


def selfcheck() -> int:
    """The pilot's run, replayed at two settings: the pipeline works on real model output."""
    for interval, step in ((4, 0.05), (1, 0.20)):
        _runs, served = replay_setting([(1, PILOT)], 8, interval, step)
        readings = [f"{fact.name}: {'holds' if fact.holds else 'fails'} ({fact.reading})" for fact in facts(_runs)]
        print(f"[selfcheck] interval {interval}, step {step}: {served} | " + " | ".join(readings), flush=True)
        if any(s["unserved"] for s in served):
            print("[selfcheck] FAILED: the replay left recorded calls unasked", flush=True)
            return 1
    print("[selfcheck] the replay and the measurement run on real model output", flush=True)
    return 0


def replay() -> int:
    recorded = []
    for seed in SEEDS:
        run_id = f"seed-{seed}"
        if not _completed(RUNS / run_id, run_id):
            print(f"[replay] {run_id} has no completed recording; record first", flush=True)
            return 2
        recorded.append((seed, RUNS / run_id / "run" / run_id))

    settings = []
    for interval in sorted(INTERVALS, reverse=True):  # selection order: longest interval, then smallest step
        for step in sorted(STEPS):
            runs, served = replay_setting(recorded, YEARS, interval, step)
            result = facts(runs)
            settings.append({
                "bill_interval_ticks": interval, "max_bill_step": step,
                "facts": [{"name": f.name, "holds": f.holds, "reading": f.reading} for f in result],
                "l1_l3_hold": all(f.holds for f in result),
                "replay": served,
            })
            print(f"[replay] interval {interval}, step {step}: "
                  + " | ".join(f"{f.name} {'holds' if f.holds else 'fails'}" for f in result), flush=True)

    # Re-read every count from the run's own journal: only the wall clock is taken from the stored
    # report, so a report written before a counting fix cannot carry the old count forward.
    reports = []
    for seed, run_dir in recorded:
        stored = json.loads((RUNS / f"seed-{seed}" / "run_report.json").read_text())
        elapsed = stored["wall_clock_minutes"] * 60 if stored.get("wall_clock_minutes") is not None else None
        reports.append(run_report(seed, _events(run_dir / "events.jsonl"), elapsed))
    RESULTS.with_suffix(".json").write_text(json.dumps({"settings": settings, "runs": reports}, indent=2) + "\n", encoding="utf-8")

    names = [f["name"] for f in settings[0]["facts"]]
    lines = [
        "# Stage 4 on the LLM path, step 1: S4.2's L1–L3",
        "",
        "Generated by `scripts/stage4_llm_legislation.py`, as pre-registered in `plan-polity-build-order.md` "
        "(\"Stage 4 on the LLM path, pre-registered before running\"). One recorded LLM run per seed "
        f"(seeds {SEEDS[0]}–{SEEDS[-1]}, population {POPULATION}, {YEARS} years, legislation recorded at interval "
        f"{RECORDED['bill_interval_ticks']} and step {RECORDED['max_bill_step']}, `policy_retrospection` 0), "
        "replayed at each setting. L4 is step 3.",
        "",
        "## L1–L3, in selection order",
        "",
        "| interval | step | " + " | ".join(names) + " | L1–L3 | every recorded call served |",
        "|---:|---:|" + "---|" * (len(names) + 2),
    ]
    for s in settings:
        cells = [f"{'✓' if f['holds'] else '✗'} {f['reading']}" for f in s["facts"]]
        clean = all(r["unserved"] == 0 for r in s["replay"])
        lines.append(f"| {s['bill_interval_ticks']} | {s['max_bill_step']} | " + " | ".join(cells)
                     + f" | {'**holds**' if s['l1_l3_hold'] else 'fails'} | {'yes' if clean else '**no**'} |")
    passing = [s for s in settings if s["l1_l3_hold"]]
    lines += ["", "## For step 3", "",
              (f"{len(passing)} of {len(settings)} settings pass L1–L3; step 3 takes them in this order for L4: "
               + ", ".join(f"({s['bill_interval_ticks']}, {s['max_bill_step']})" for s in passing) + "."
               if passing else "**No setting passes L1–L3**, so no setting can qualify and step 3 has nothing to run.")]
    lines += ["", "## The recorded runs (reported, never selected on)", "",
              "| seed | wall clock | elections | recalls | full terms | fallbacks |", "|---:|---:|---:|---:|---:|---|"]
    for r in reports:
        fb = ", ".join(f"{t} {v}" for t, v in r["fallbacks"].items()) or "none"
        lines.append(f"| {r['seed']} | {r['wall_clock_minutes']} min | {r['elections']} | {r['recalls']} | {r['full_terms']} | {fb} |")
    RESULTS.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[replay] wrote {RESULTS.name}.{{md,json}}", flush=True)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("mode", choices=["record", "replay", "selfcheck"])
    mode = parser.parse_args().mode
    raise SystemExit({"record": record, "replay": replay, "selfcheck": selfcheck}[mode]())
