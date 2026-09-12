"""
scripts/run_polity_seed_sweep.py

Track D (lets-build-a-solid-spicy-otter.md, 2026-09-11): the multi-seed sweep.
Every published polity result to date is n=1 on a seed (42) already shown once to
be unrepresentative (`plan-distribution-positions-seeds.md`'s own open §4.3
`seed_representativeness: unvalidated` marking) -- this is the thin driver that
finally wires `scripts/llm_test_harness/` the way that plan's own §4.1 asked for,
rather than inventing a parallel mechanism.

**Why a thin subprocess wrapper around `run_polity_flagship.py`, not an in-process
call to `run_flagship`.** Each seed is 1-6+ hours; a hang or crash in one seed's
run must not corrupt or take down the whole sweep's own driver process, and a
separate subprocess per seed is exactly what a human running the staged commands
by hand would do anyway -- this only automates the loop, not the mechanism.
`run_flagship`'s own `--resume`/`--force`/existing-run-dir guards are reused
unchanged; this script never re-implements them.

**Why `llm_test_harness` only for pre-registration + the "did every seed
complete" summary, not for the substantive analysis.** `trial.TrialResult`'s own
fields (`finish_reason`, `truncated`, `decoded_tokens`) and `registration.
Experiment`'s structured `metric: Literal["failure_rate", "success_rate"]` are
shaped for repeated LLM-call trials, not multi-hour simulation runs -- forcing
Track D's real question (does `office_occupancy`/fallback rate vary meaningfully
across seeds?) into that binary mold would answer a different, less useful
question. This script uses the harness for what it is actually built for
(pre-registration discipline, environment capture, queryable SQLite storage, a
generated "N trials, N ok" report) and writes its own seed-sweep summary,
generated from each run's own `digest.json` -- never hand-typed -- for the
variance analysis itself.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/run_polity_seed_sweep.py \\
        --population 100 --years 8 --seeds 1,2,3,4,5,6,7,8,9,10 \\
        --output-dir scripts/seed_sweep_runs

    # resume a sweep that was interrupted partway through (skips any seed whose
    # run_dir already has a digest.json; re-launches an incomplete one with
    # --resume automatically)
    python fast_api_voter/scripts/run_polity_seed_sweep.py \\
        --population 100 --years 8 --seeds 1,2,3,4,5,6,7,8,9,10 \\
        --output-dir scripts/seed_sweep_runs --resume-sweep
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from llm_test_harness import registration, report, trial  # noqa: E402

_SCRIPTS_DIR = Path(__file__).resolve().parent
_FAST_API_VOTER_DIR = _SCRIPTS_DIR.parent
_FLAGSHIP_SCRIPT = _SCRIPTS_DIR / "run_polity_flagship.py"


def _run_id_for(years: int, population: int, seed: int) -> str:
    return f"sweep-{years}y-p{population}-seed{seed}"


def _digest_path(output_dir: Path, run_id: str) -> Path:
    return output_dir / run_id / "run" / run_id / "digest.json"


def _run_one_seed(
    *, years: int, population: int, seed: int, seats: int, output_dir: Path, max_batch_replays: int,
    resume_sweep: bool,
) -> trial.TrialResult:
    run_id = _run_id_for(years, population, seed)
    run_dir = output_dir / run_id
    digest_path = _digest_path(output_dir, run_id)

    if resume_sweep and digest_path.exists():
        digest = json.loads(digest_path.read_text(encoding="utf-8"))
        if digest.get("outcome") == "completed":
            return trial.TrialResult(ok=True, detail=f"already completed (skipped): {run_id}")

    args = [
        sys.executable, str(_FLAGSHIP_SCRIPT),
        "--engine", "llm",
        "--years", str(years),
        "--population", str(population),
        "--seats", str(seats),
        "--seed", str(seed),
        "--run-id", run_id,
        "--output-dir", str(output_dir),
        "--max-batch-replays", str(max_batch_replays),
    ]
    checkpoint_path = run_dir / "run" / run_id / "checkpoint.json"
    if resume_sweep and run_dir.exists():
        if checkpoint_path.exists():
            args.append("--resume")
        else:
            # A run_dir with no checkpoint yet means an earlier attempt was
            # interrupted before its first per-tick checkpoint -- run_flagship
            # itself refuses --resume in that case (FileNotFoundError), and
            # there is nothing worth resuming anyway. --force clears it and
            # starts this seed clean, mirroring run_flagship's own "an empty
            # or half-started run_dir is not worth preserving" judgment.
            args.append("--force")

    log_path = output_dir / f"{run_id}.log"
    output_dir.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log_file:
        completed = subprocess.run(
            args, cwd=_FAST_API_VOTER_DIR, stdout=log_file, stderr=subprocess.STDOUT, check=False,
        )

    if completed.returncode != 0:
        return trial.TrialResult(
            ok=False, detail=f"run_id={run_id} exited {completed.returncode} -- see {log_path}",
        )

    if not digest_path.exists():
        return trial.TrialResult(ok=False, detail=f"run_id={run_id} exited 0 but no digest.json at {digest_path}")

    digest = json.loads(digest_path.read_text(encoding="utf-8"))
    summary = {
        "run_id": run_id,
        "outcome": digest.get("outcome"),
        "office_occupancy": digest.get("office_occupancy"),
        "llm_fallbacks": digest.get("llm_fallbacks"),
        "llm_fallback_alerts": digest.get("llm_fallback_alerts"),
        "last_tick_journaled": (digest.get("ticks") or {}).get("last_tick_journaled"),
        "planned_total": (digest.get("ticks") or {}).get("planned_total"),
    }
    return trial.TrialResult(
        ok=digest.get("outcome") == "completed",
        decoded_tokens=sum((digest.get("llm_decisions") or {}).values()) or None,
        detail=json.dumps(summary, sort_keys=True),
    )


def _write_sweep_summary(output_dir: Path, years: int, population: int, seeds: list[int]) -> Path:
    """Generated from each seed's own digest.json -- never hand-typed. This is
    the substantive artifact: per-metric mean/stdev/range across seeds, the
    actual answer to "is a single seed representative" that the harness's own
    generic report.py does not compute (its own metric vocabulary is
    failure_rate/success_rate only)."""
    rows: list[dict[str, Any]] = []
    for seed in seeds:
        run_id = _run_id_for(years, population, seed)
        digest_path = _digest_path(output_dir, run_id)
        if not digest_path.exists():
            rows.append({"seed": seed, "run_id": run_id, "outcome": "missing"})
            continue
        digest = json.loads(digest_path.read_text(encoding="utf-8"))
        rows.append({
            "seed": seed,
            "run_id": run_id,
            "outcome": digest.get("outcome"),
            "office_occupancy": digest.get("office_occupancy"),
            "llm_fallback_alerts": digest.get("llm_fallback_alerts") or {},
        })

    completed_rows = [r for r in rows if r.get("outcome") == "completed"]
    occupancy_values = [r["office_occupancy"] for r in completed_rows if r.get("office_occupancy") is not None]

    lines = [
        f"# Seed sweep — {years}y, population {population} ({len(seeds)} seeds)\n",
        f"- seeds: {seeds}",
        f"- completed: {len(completed_rows)}/{len(seeds)}\n",
        "## Per-seed results\n",
        "| seed | run_id | outcome | office_occupancy | fallback alerts |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        alerts = r.get("llm_fallback_alerts") or {}
        lines.append(
            f"| {r['seed']} | {r['run_id']} | {r['outcome']} | "
            f"{r.get('office_occupancy', '-')} | {alerts or '-'} |"
        )
    lines.append("")

    lines.append("## office_occupancy across seeds\n")
    if len(occupancy_values) >= 2:
        mean = statistics.fmean(occupancy_values)
        stdev = statistics.stdev(occupancy_values)
        lines.append(
            f"- n={len(occupancy_values)}, mean={mean:.4f}, stdev={stdev:.4f}, "
            f"min={min(occupancy_values):.4f}, max={max(occupancy_values):.4f}"
        )
    elif len(occupancy_values) == 1:
        lines.append(f"- only one completed seed with office_occupancy: {occupancy_values[0]:.4f} (no variance to report)")
    else:
        lines.append("- no completed seed produced an office_occupancy value yet")
    lines.append("")

    summary_path = output_dir / f"sweep-{years}y-p{population}-summary.md"
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return summary_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--population", type=int, required=True)
    parser.add_argument(
        "--seats", type=int, default=None,
        help="sortition_chamber.seats -- defaults to run_polity_flagship.py's own default (75); "
             "override for a small smoke-test population where 75 would exceed it",
    )
    parser.add_argument("--years", type=int, required=True)
    parser.add_argument("--seeds", required=True, help="comma-separated list of integer seeds")
    parser.add_argument("--max-batch-replays", type=int, default=2)
    parser.add_argument("--output-dir", type=Path, default=Path("scripts/seed_sweep_runs"))
    parser.add_argument(
        "--resume-sweep", action="store_true",
        help="skip seeds whose digest.json already shows outcome=completed; --resume any partial run_dir",
    )
    parser.add_argument("--hypothesis", default=None, help="override the default pre-registered hypothesis text")
    parser.add_argument("--planned-n", type=int, default=None, help="defaults to len(seeds)")
    args = parser.parse_args(argv)

    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    if not seeds:
        parser.error("--seeds must name at least one seed")

    hypothesis = args.hypothesis or (
        f"office_occupancy and the per-type LLM fallback rate at population={args.population}, "
        f"years={args.years} are stable across seeds (low seed-to-seed variance), i.e. a single "
        "seed is representative of this configuration -- plan-distribution-positions-seeds.md's "
        "own open §4.3 'seed_representativeness: unvalidated' question."
    )
    experiment = registration.register(
        hypothesis=hypothesis,
        decision_criterion=(
            "No structured threshold registered -- office_occupancy's stdev across seeds is read "
            "against its own mean by a human, alongside whether any seed's fallback alerts differ "
            "qualitatively from the others (see the generated sweep summary, not this report)."
        ),
        planned_n=args.planned_n or len(seeds),
        budget_description=f"{len(seeds)} seeds x ~{args.years}y/p{args.population} flagship runs",
    )
    print(f"registered experiment {experiment.experiment_id}: {experiment.hypothesis}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for i, seed in enumerate(seeds, start=1):
        print(f"[{i}/{len(seeds)}] seed={seed} ...", flush=True)
        result = trial.record_trial(
            experiment.experiment_id, i,
            container_name="vllm-polity",
            inference_backend="vllm",
            run_call=lambda seed=seed: _run_one_seed(
                years=args.years, population=args.population, seed=seed, seats=args.seats or 75,
                output_dir=args.output_dir, max_batch_replays=args.max_batch_replays,
                resume_sweep=args.resume_sweep,
            ),
        )
        print(f"  -> ok={result.ok} detail={result.detail}", flush=True)

    report_path = args.output_dir / f"harness-report-{experiment.experiment_id}.md"
    report_path.write_text(report.generate_report(experiment.experiment_id), encoding="utf-8")
    summary_path = _write_sweep_summary(args.output_dir, args.years, args.population, seeds)

    print(f"\nharness report: {report_path}")
    print(f"sweep summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
