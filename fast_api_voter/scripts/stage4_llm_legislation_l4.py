"""Stage 4 on the LLM path, step 3: S4.2's L4, in selection order.

Pre-registered in plan-polity-build-order.md ("Stage 4 on the LLM path, pre-registered before
running"), signed off and committed before this ran. L4 (ADR-009): the governing parties' combined
vote share falls from the election that made them the government to the next, and by more than at
`policy_retrospection` 0.

- **Which settings.** Only those step 1 found passing L1–L3, in selection order: longest bill
  interval first, then smallest step (`stage4_llm_legislation_results.json` lists them so).
- **Which weights.** For each setting, 2, then 5, then 10: ADR-009 adopts the smallest weight that
  meets L4.
- **Stopping.** The first (setting, weight) to meet L4, on a setting that already passes L1–L3,
  is the selection, and nothing further runs. At most three (setting, weight) evaluations are
  budgeted; if none qualifies by then, the result is "none qualifies within the pre-registered
  budget".
- **The baseline.** The zero-weight spells for a setting come from replaying step 1's recordings at
  that setting on CPU; at weight 0 no governing record exists before the first assembly, so the
  change should read 0, and is reported as measured.

Each evaluation records ten closed-loop 16-year LLM runs, then is measured at once from their
journals. A completed run is skipped on restart and an incomplete one moved aside.

Usage (from fast_api_voter/; `record` needs the vLLM server):
    python scripts/stage4_llm_legislation_l4.py record
    python scripts/stage4_llm_legislation_l4.py measure
    python scripts/stage4_llm_legislation_l4.py selfcheck
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.config import PolityConfig, validate_config  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402
from api.domain.polity.twin_calibration import GovernmentSpell, cost_of_ruling, mean_share_change  # noqa: E402
from calibrate_legislation import _spells  # noqa: E402
from run_polity_flagship import _write_digest_safely  # noqa: E402
from stage4_llm_legislation import (  # noqa: E402
    MIN_FREE_GB,
    YEARS,
    _completed,
    _events,
    _free_gb,
    llm_config,
    replay_setting,
    run_report,
)
from twin_runs import SEEDS  # noqa: E402

WEIGHTS = (2.0, 5.0, 10.0)
MAX_EVALUATIONS = 3
RUNS_ROOT = Path(os.environ.get("STAGE4_RUNS", Path(__file__).resolve().parent / "stage4_llm_runs"))
STEP1_RECORDINGS = RUNS_ROOT / "s42-record"
RUNS = RUNS_ROOT / "s42-l4"
STEP1_RESULTS = Path(__file__).resolve().parent / "stage4_llm_legislation_results.json"
RESULTS = Path(__file__).resolve().parent / "stage4_llm_legislation_l4_results"

Setting = dict[str, float]


def l4_config(seed: int, setting: Setting, weight: float, output_dir: Path) -> PolityConfig:
    config = llm_config(seed, YEARS, setting, output_dir)
    config = dataclasses.replace(config, vote=dataclasses.replace(config.vote, policy_retrospection=weight))
    validate_config(config)
    return config


def plan(passing: list[Setting]) -> list[tuple[Setting, float]]:
    """The (setting, weight) evaluations in pre-registered order, cut at the budget."""
    ordered = sorted(passing, key=lambda s: (-s["bill_interval_ticks"], s["max_bill_step"]))
    return [(setting, weight) for setting in ordered for weight in WEIGHTS][:MAX_EVALUATIONS]


def slug(setting: Setting, weight: float) -> str:
    return f"i{setting['bill_interval_ticks']:g}-s{setting['max_bill_step']:g}-w{weight:g}"


def _passing_settings() -> list[Setting]:
    results = json.loads(STEP1_RESULTS.read_text(encoding="utf-8"))
    return [{"bill_interval_ticks": s["bill_interval_ticks"], "max_bill_step": s["max_bill_step"]}
            for s in results["settings"] if s["l1_l3_hold"]]


def zero_spells(setting: Setting) -> list[GovernmentSpell]:
    """The weight-0 baseline: step 1's recordings replayed at this setting, on CPU."""
    recorded = [(seed, STEP1_RECORDINGS / f"seed-{seed}" / "run" / f"seed-{seed}") for seed in SEEDS]
    runs, served = replay_setting(recorded, YEARS, int(setting["bill_interval_ticks"]), setting["max_bill_step"])
    if any(s["unserved"] for s in served):
        raise RuntimeError(f"the weight-0 replay at {setting} left recorded calls unasked: {served}")
    return runs.spells


def record_evaluation(setting: Setting, weight: float) -> list[dict[str, Any]]:
    reports = []
    for seed in SEEDS:
        run_id = f"seed-{seed}"
        seed_dir = RUNS / slug(setting, weight) / run_id
        if _completed(seed_dir, run_id):
            reports.append(json.loads((seed_dir / "run_report.json").read_text()))
            continue
        if seed_dir.exists():
            aside = seed_dir.with_name(f"{run_id}.incomplete-{int(time.time())}")
            seed_dir.rename(aside)
            print(f"[l4] {slug(setting, weight)} {run_id}: an incomplete attempt moved aside to {aside.name}", flush=True)
        free = _free_gb()
        if free < MIN_FREE_GB:
            raise SystemExit(f"[l4] STOP: {free} GB free on / (< {MIN_FREE_GB})")
        seed_dir.mkdir(parents=True)
        config = l4_config(seed, setting, weight, seed_dir / "run")
        (seed_dir / "config.json").write_text(json.dumps(dataclasses.asdict(config), indent=2, default=str), encoding="utf-8")
        journal = Path(config.journal.output_dir) / run_id / "events.jsonl"
        print(f"[l4] {slug(setting, weight)} {run_id}: recording", flush=True)
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
        reports.append(report)
        print(f"[l4] {slug(setting, weight)} {run_id}: completed {report}", flush=True)
    return reports


def recorded_spells(setting: Setting, weight: float) -> list[GovernmentSpell] | None:
    spells: list[GovernmentSpell] = []
    for seed in SEEDS:
        run_id = f"seed-{seed}"
        seed_dir = RUNS / slug(setting, weight) / run_id
        if not _completed(seed_dir, run_id):
            return None
        spells += _spells(seed, _events(seed_dir / "run" / run_id / "events.jsonl"))
    return spells


def write_results(evaluations: list[dict[str, Any]], selected: dict[str, Any] | None, exhausted: bool) -> None:
    RESULTS.with_suffix(".json").write_text(json.dumps(
        {"evaluations": evaluations, "selected": selected, "budget_exhausted": exhausted}, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Stage 4 on the LLM path, step 3: S4.2's L4",
        "",
        "Generated by `scripts/stage4_llm_legislation_l4.py`, as pre-registered in `plan-polity-build-order.md` "
        "(\"Stage 4 on the LLM path, pre-registered before running\"): settings passing L1–L3 in selection order, "
        f"weights {', '.join(f'{w:g}' for w in WEIGHTS)}, at most {MAX_EVALUATIONS} evaluations.",
        "",
        "## Verdict",
        "",
    ]
    if selected:
        lines.append(f"**Selected:** interval {selected['bill_interval_ticks']:g}, step {selected['max_bill_step']:g}, "
                     f"`policy_retrospection` {selected['weight']:g}.")
    elif exhausted:
        lines.append("**None qualifies within the pre-registered budget.**")
    else:
        lines.append("Not finished: evaluations remain within the budget.")
    lines += ["", "| interval | step | weight | L4 | weight-0 baseline |", "|---:|---:|---:|---|---:|"]
    for e in evaluations:
        baseline = "–" if e["zero_change"] is None else f"{100 * e['zero_change']:+.2f} points"
        lines.append(f"| {e['bill_interval_ticks']:g} | {e['max_bill_step']:g} | {e['weight']:g} | "
                     f"{'✓' if e['holds'] else '✗'} {e['reading']} | {baseline} |")
    RESULTS.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def evaluate(record_missing: bool) -> int:
    evaluations: list[dict[str, Any]] = []
    selected = None
    baselines: dict[tuple[float, float], list[GovernmentSpell]] = {}
    steps = plan(_passing_settings())
    if not steps:
        print("[l4] step 1 found no setting passing L1-L3: nothing can qualify, nothing to run", flush=True)
        write_results([], None, exhausted=True)
        return 0
    for setting, weight in steps:
        spells = recorded_spells(setting, weight)
        if spells is None:
            if not record_missing:
                print(f"[l4] {slug(setting, weight)} is not recorded yet; stopping the measurement here", flush=True)
                write_results(evaluations, None, exhausted=False)
                return 0
            record_evaluation(setting, weight)
            spells = recorded_spells(setting, weight)
            assert spells is not None
        key = (setting["bill_interval_ticks"], setting["max_bill_step"])
        if key not in baselines:
            baselines[key] = zero_spells(setting)
        fact = cost_of_ruling(spells, baselines[key])
        evaluations.append({**setting, "weight": weight, "holds": fact.holds, "reading": fact.reading,
                            "zero_change": mean_share_change(baselines[key]), "spells": len(spells)})
        print(f"[l4] {slug(setting, weight)}: L4 {'holds' if fact.holds else 'fails'} ({fact.reading})", flush=True)
        if fact.holds:
            selected = {**setting, "weight": weight}
            break
    write_results(evaluations, selected, exhausted=selected is None)
    print(f"[l4] {'SELECTED ' + str(selected) if selected else 'none qualifies within the pre-registered budget'}", flush=True)
    return 0


def selfcheck() -> int:
    """No GPU: the plan's order and budget, and a config at a weight that validates."""
    passing = [{"bill_interval_ticks": 2, "max_bill_step": 0.1}, {"bill_interval_ticks": 4, "max_bill_step": 0.2},
               {"bill_interval_ticks": 4, "max_bill_step": 0.05}]
    steps = [(s["bill_interval_ticks"], s["max_bill_step"], w) for s, w in plan(passing)]
    assert steps == [(4, 0.05, 2.0), (4, 0.05, 5.0), (4, 0.05, 10.0)], steps
    config = l4_config(1, passing[2], 5.0, Path("/tmp/unused"))
    assert config.vote.policy_retrospection == 5.0 and config.legislation.bill_interval_ticks == 4
    print(f"[selfcheck] plan order and budget: {steps}; a weight-5 config validates", flush=True)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("mode", choices=["record", "measure", "selfcheck"])
    mode = parser.parse_args().mode
    raise SystemExit(selfcheck() if mode == "selfcheck" else evaluate(record_missing=mode == "record"))
