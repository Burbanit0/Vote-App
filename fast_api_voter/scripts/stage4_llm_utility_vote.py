"""Stage 4 on the LLM path, steps 2 and 4: S4.1's utility vote.

Pre-registered in plan-polity-build-order.md ("Stage 4 on the LLM path, pre-registered before
running"), signed off and committed before this ran. The grid, the four facts and the selection are
ADR-011's and §9's, unchanged; only the bench is the LLM path.

- **Step 2** records the zero-weight arm, then group 0: the settings whose `partisanship +
  approval` is 0 (the four turnout costs).
- **Step 4** records group 0.05, only if group 0 held no qualifying setting.

`record` runs each (setting, seed) closed-loop on the LLM path -- population 100, 30 chamber
seats, 8 years, the full-mechanism config, 12 relaxed workers, the shipped grammar and budget --
keeping its call log. A completed run is skipped; an incomplete one is moved aside, since a journal
appends and must never be reused.

`measure` reads the facts by **replaying** each recorded run on CPU with
`calibrate_utility_vote.measure_run`'s own wrappers: the attempts and first choices S4.1 needs are
not in the journal, and a replay reproduces the run exactly. Measuring never depends on the
recording process having survived. The replay runs single-threaded, so the wrappers count without
racing; it raises on any call the run never recorded.

`selfcheck` replays the pilot, which is a zero-weight run (the shipped vote settings are ADR-011's
zero arm), through the same measurement.

Usage (from fast_api_voter/; `record` needs the vLLM server):
    python scripts/stage4_llm_utility_vote.py record --step 2
    python scripts/stage4_llm_utility_vote.py measure --through 0.0
    python scripts/stage4_llm_utility_vote.py selfcheck
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
from api.domain.polity.llm_replay import ReplayClient  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402
from api.domain.polity.twin_calibration import (  # noqa: E402
    Arm,
    Election,
    FirstChoices,
    grid,
    select,
    utility_vote_arm,
    utility_vote_choice,
)
from calibrate_utility_vote import AXES, FIXED, YEARS, ZERO, measure_run  # noqa: E402
from run_polity_flagship import _flagship_config, _write_digest_safely  # noqa: E402
from stage4_llm_legislation import MIN_FREE_GB, _completed, _events, _free_gb, run_report  # noqa: E402
from twin_runs import SEEDS  # noqa: E402

POPULATION, SEATS, WORKERS = 100, 30, 12
RUNS_ROOT = Path(os.environ.get("STAGE4_RUNS", Path(__file__).resolve().parent / "stage4_llm_runs"))
"""Where the recorded runs live; overridable so a second worktree can read the runs of the first."""
RUNS = RUNS_ROOT / "s41"
PILOT = RUNS_ROOT / "pilot-8y-p100-seed1" / "run" / "pilot-8y-p100-seed1"
PILOT_LEGISLATION = {"bill_interval_ticks": 4, "max_bill_step": 0.05}
RESULTS = Path(__file__).resolve().parent / "stage4_llm_utility_vote_results"
STEPS = {2: (0.0,), 4: (0.05,)}


def group_of(setting: dict[str, float]) -> float:
    return round(setting["partisanship"] + setting["approval"], 6)


def group_settings(total: float) -> list[dict[str, float]]:
    return [{**setting, **FIXED} for setting in grid(AXES) if group_of(setting) == total]


def slug(vote: dict[str, float]) -> str:
    if vote == ZERO:
        return "zero"
    return f"p{vote['partisanship']:g}-a{vote['approval']:g}-t{vote['turnout_cost']:g}"


def llm_config(seed: int, vote: dict[str, float], output_dir: Path, *, workers: int = WORKERS,
               legislation: dict[str, float] | None = None) -> PolityConfig:
    config = _flagship_config(
        engine="llm", years=YEARS, population=POPULATION, seats=SEATS, seed=seed, output_dir=output_dir,
        max_batch_replays=2, provider=None, workers=WORKERS, reproducibility="relaxed",
    )
    config = dataclasses.replace(
        config,
        vote=dataclasses.replace(config.vote, **vote),
        parallel=dataclasses.replace(config.parallel, intra_run_workers=workers),
        journal=dataclasses.replace(config.journal, output_dir=str(output_dir)),
    )
    if legislation is not None:
        config = dataclasses.replace(config, legislation=dataclasses.replace(config.legislation, enabled=True, **legislation))
    validate_config(config)
    return config


def arms_for(step: int) -> list[dict[str, float]]:
    arms = [dict(ZERO)] if step == 2 else []
    for total in STEPS[step]:
        arms += group_settings(total)
    return arms


def record(step: int) -> int:
    for vote in arms_for(step):
        for seed in SEEDS:
            run_id = f"seed-{seed}"
            seed_dir = RUNS / slug(vote) / run_id
            if _completed(seed_dir, run_id):
                print(f"[record] {slug(vote)} {run_id}: already completed, skipped", flush=True)
                continue
            if seed_dir.exists():
                aside = seed_dir.with_name(f"{run_id}.incomplete-{int(time.time())}")
                seed_dir.rename(aside)
                print(f"[record] {slug(vote)} {run_id}: an incomplete attempt moved aside to {aside.name}", flush=True)
            free = _free_gb()
            if free < MIN_FREE_GB:
                print(f"[record] STOP: {free} GB free on / (< {MIN_FREE_GB}) before {slug(vote)} {run_id}", flush=True)
                return 3
            seed_dir.mkdir(parents=True)
            config = llm_config(seed, vote, seed_dir / "run")
            (seed_dir / "config.json").write_text(json.dumps(dataclasses.asdict(config), indent=2, default=str), encoding="utf-8")
            journal = Path(config.journal.output_dir) / run_id / "events.jsonl"
            print(f"[record] {slug(vote)} {run_id}: {YEARS}y x {POPULATION}, {WORKERS} workers, vote {vote}", flush=True)
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
            print(f"[record] {slug(vote)} {run_id}: completed {report}", flush=True)
    print(f"[record] STEP {step} DONE", flush=True)
    return 0


def replay_measure(seed: int, vote: dict[str, float], run_dir: Path,
                   legislation: dict[str, float] | None = None) -> tuple[list[Election], FirstChoices, int]:
    """One recorded run's attempts and first choices, from a single-threaded replay of its call log."""
    client = ReplayClient.from_run_dir(run_dir)
    with tempfile.TemporaryDirectory() as work:
        config = llm_config(seed, vote, Path(work), workers=1, legislation=legislation)
        elections, choices = measure_run(
            seed, config, lambda cfg: _events(Path(run_simulation(cfg, run_id=run_dir.name, llm_client=client))))
    if client.unserved:
        raise RuntimeError(f"seed {seed} {slug(vote)}: the replay left {client.unserved} recorded calls unasked")
    return elections, choices, client.served


def measure_arm(vote: dict[str, float]) -> tuple[list[Election], FirstChoices]:
    elections: list[Election] = []
    choices = FirstChoices()
    for seed in SEEDS:
        run_id = f"seed-{seed}"
        seed_dir = RUNS / slug(vote) / run_id
        if not _completed(seed_dir, run_id):
            raise FileNotFoundError(f"{slug(vote)} {run_id} has no completed recording")
        run_elections, run_choices, _served = replay_measure(seed, vote, seed_dir / "run" / run_id)
        elections += run_elections
        choices = choices + run_choices
    return elections, choices


def _arm_json(arm: Arm) -> dict[str, Any]:
    return dataclasses.asdict(arm)


def measure(through: float) -> int:
    zero_elections, zero_choices = measure_arm(ZERO)
    zero = utility_vote_arm(ZERO, zero_elections, zero_choices, zero_elections, zero_choices)
    groups = sorted({group_of(s) for s in grid(AXES)})
    measured: list[tuple[float, list[Arm]]] = []
    selected: Arm | None = None
    for total in [g for g in groups if g <= through]:
        arms = []
        for vote in group_settings(total):
            elections, choices = measure_arm(vote)
            arms.append(utility_vote_arm(vote, elections, choices, zero_elections, zero_choices))
            print(f"[measure] group {total:g} {slug(vote)}: {'qualifies' if arms[-1].qualifies else 'does not qualify'}", flush=True)
        measured.append((total, arms))
        qualifying = [arm for arm in arms if arm.qualifies]
        if qualifying:
            selected = select(qualifying, utility_vote_choice)
            break

    RESULTS.with_suffix(".json").write_text(json.dumps({
        "zero": _arm_json(zero),
        "groups": [{"partisanship_plus_approval": total, "arms": [_arm_json(a) for a in arms]} for total, arms in measured],
        "selected": _arm_json(selected) if selected else None,
        "through_group": through,
    }, indent=2) + "\n", encoding="utf-8")

    names = [fact.name for fact in zero.facts]
    lines = [
        "# Stage 4 on the LLM path: S4.1's utility vote",
        "",
        "Generated by `scripts/stage4_llm_utility_vote.py`, as pre-registered in `plan-polity-build-order.md` "
        f"(\"Stage 4 on the LLM path, pre-registered before running\"). LLM path, population {POPULATION}, seeds "
        f"{SEEDS[0]}–{SEEDS[-1]}, {YEARS} years; every fact read by replaying the recorded run.",
        "",
        "## Verdict",
        "",
    ]
    if selected is not None:
        chosen = {k: selected.setting[k] for k in AXES}
        lines.append(f"**Selected:** {chosen} (party carryover {FIXED['approval_party_carryover']}).")
    else:
        lines.append(f"**None qualifies within the pre-registered budget** (groups up to {through:g} measured).")
    lines += ["", "## Zero-weight arm", "", *[f"- {f.name}: {f.reading}" for f in zero.facts], ""]
    for total, arms in measured:
        lines += [f"## Group {total:g}", "", "| setting | " + " | ".join(names) + " | all |", "|---|" + "---|" * (len(names) + 1)]
        for arm in arms:
            cells = [f"{'✓' if f.holds else '✗'} {f.reading}" for f in arm.facts]
            lines.append(f"| {slug(arm.setting)} | " + " | ".join(cells) + f" | {'✓' if arm.qualifies else '✗'} |")
        lines.append("")
    RESULTS.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[measure] wrote {RESULTS.name}.{{md,json}}; selected: {slug(selected.setting) if selected else None}", flush=True)
    return 0


def selfcheck() -> int:
    """The pilot is a zero-weight run: replay it single-threaded through the measurement."""
    elections, choices, served = replay_measure(1, dict(ZERO), PILOT, legislation=PILOT_LEGISLATION)
    arm = utility_vote_arm(ZERO, elections, choices, elections, choices)
    print(f"[selfcheck] {served} recorded calls served at 1 worker (recorded at {WORKERS})", flush=True)
    print(f"[selfcheck] attempts: {[(e.tick, e.ballots, e.voters, e.incumbent_standing, e.winner_id) for e in elections]}", flush=True)
    print(f"[selfcheck] first choices: {choices.own_party_first}/{choices.eligible} own party", flush=True)
    for fact in arm.facts:
        print(f"[selfcheck] {fact.name}: {'holds' if fact.holds else 'fails'} ({fact.reading})", flush=True)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    rec = sub.add_parser("record")
    rec.add_argument("--step", type=int, choices=sorted(STEPS), required=True)
    mea = sub.add_parser("measure")
    mea.add_argument("--through", type=float, choices=[0.0, 0.05], required=True)
    sub.add_parser("selfcheck")
    args = parser.parse_args()
    if args.mode == "record":
        raise SystemExit(record(args.step))
    if args.mode == "measure":
        raise SystemExit(measure(args.through))
    raise SystemExit(selfcheck())
