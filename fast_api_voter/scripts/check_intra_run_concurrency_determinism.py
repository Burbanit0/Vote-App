"""
scripts/check_intra_run_concurrency_determinism.py

Phase 2 of plan-flagship-30y-run.md: the gate, not a formality. `_check_supported`
now allows `parallel.intra_run_workers > 1` on `provider == "vllm"` (previously a
blanket refusal citing `llm_batching_determinism_results.md`, which is an
Ollama-specific finding). That relaxation does not ship on the argument in
`run_chunks`'s own docstring -- it ships on this proof.

**What this actually tests.** `run_chunks` (llm_behavior_engine.py) is the shared
execution strategy behind the 5 chunked decision types (`cast_votes`,
`decide_candidacies`, `decide_pressure_actions`, `decide_reaction_to_event`,
`decide_chamber_deliberation` -- the only decision types that chunk at all; the
other 4 make one call per tick and have nothing to parallelize). At
`workers > 1` it submits every chunk to a `ThreadPoolExecutor` and returns
results in submission order, not completion order -- a claim already unit-tested
in isolation (`test_run_chunks_workers_many_preserves_chunk_order_regardless_of_
completion_order`). What that unit test CANNOT show is whether vLLM's server-side
behavior under genuine concurrent load stays byte-identical to its own sequential
behavior, end to end, through the full `run_simulation` journal -- that needs a
real run, twice, compared byte for byte.

**Why `replays=0`.** A run with `max_batch_replays > 0` is already documented
elsewhere in this codebase as not byte-reproducible (a replay's own retry count
depends on the model's specific response). This proof is about concurrency,
not retries -- entangling the two would make a diff impossible to attribute to
either cause.

**Why the flagship's own full-richness config.** Reusing `run_polity_flagship.
_flagship_config` (not a bespoke lighter config) means this proof exercises
every parallelized code path at once -- all 5 chunked decision types, not just
one -- because that IS the flagship's own shape. A proof that only tested
`vote_cast` and shipped in a run that also parallelizes `chamber_deliberation`
would be exactly the kind of partial verification this project's own
conventions warn against.

**The verdict.** Byte-identical `events.jsonl` between `workers=1` and
`workers=N`, same seed, same config, `replays=0` => ship it (Phase 2 is done,
the guard change lands for real). Any diff => do NOT ship; revert
`_check_supported`'s relaxation and fall back to sequential + Phase 3's
checkpoint/resume, exactly as the plan's own risk section already names as the
fallback.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    # smoke scale first (minutes, not the full proof)
    python fast_api_voter/scripts/check_intra_run_concurrency_determinism.py \\
        --years 1 --population 100 --seats 30 --workers 8

    # the real proof, matching the plan's own named scale
    python fast_api_voter/scripts/check_intra_run_concurrency_determinism.py \\
        --years 2 --population 100 --seats 30 --workers 8 \\
        --results scripts/check_intra_run_concurrency_determinism_results.md
"""
from __future__ import annotations

import argparse
import filecmp
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_polity_flagship import run_flagship  # noqa: E402


def _journal_for(run_dir: Path, run_id: str) -> Path:
    return run_dir / run_id / "run" / run_id / "events.jsonl"


def run_arm(*, years: int, population: int, seats: int, workers: int, output_dir: Path) -> tuple[Path, float]:
    # The SAME run_id for every arm, deliberately -- run_id is written into
    # every journal event's own "run_id" field (journal.py), so a run_id that
    # varies by worker count would make workers=1 vs workers=N diverge on that
    # field ALONE, on every single line, regardless of whether any decision
    # actually differed. That is exactly what happened on this script's first
    # version: a "FAIL -- NOT byte-identical" whose only diff was
    # "determinism-1y-p100-w1" vs "...-w8" in the run_id field -- a labeling
    # artifact of this script, not a concurrency finding. Arms are kept apart
    # by `output_dir` (one subfolder per worker count) instead, and
    # run_polity_flagship's own run-collision guard still protects each arm
    # individually.
    run_id = f"determinism-{years}y-p{population}"
    arm_output_dir = output_dir / f"workers-{workers}"
    start = time.monotonic()
    run_flagship(
        engine="llm",
        years=years,
        population=population,
        seats=seats,
        seed=42,
        output_dir=arm_output_dir,
        max_batch_replays=0,  # the proof is about concurrency, not retries -- see module docstring
        provider="vllm",
        workers=workers,
        run_id=run_id,
        force=True,
    )
    elapsed = time.monotonic() - start
    return _journal_for(arm_output_dir, run_id), elapsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--years", type=int, default=2)
    parser.add_argument("--population", type=int, default=100)
    parser.add_argument("--seats", type=int, default=30)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output-dir", type=Path, default=Path("scripts/flagship_runs"))
    parser.add_argument("--results", type=Path, default=None)
    args = parser.parse_args(argv)

    lines: list[str] = []

    def log(line: str = "") -> None:
        print(line, flush=True)
        lines.append(line)

    log("# Phase 2 determinism proof -- workers=1 vs workers=N, byte-identical journal\n")
    log(f"years={args.years} population={args.population} seats={args.seats} "
        f"workers_b={args.workers} seed=42 max_batch_replays=0 provider=vllm\n")

    log("## Arm A: workers=1 (sequential, the pre-Phase-2 code path)\n")
    journal_a, elapsed_a = run_arm(
        years=args.years, population=args.population, seats=args.seats, workers=1, output_dir=args.output_dir
    )
    log(f"- {elapsed_a:.1f}s\n")

    log(f"## Arm B: workers={args.workers} (the concurrency unlock)\n")
    journal_b, elapsed_b = run_arm(
        years=args.years, population=args.population, seats=args.seats, workers=args.workers,
        output_dir=args.output_dir,
    )
    log(f"- {elapsed_b:.1f}s\n")

    identical = filecmp.cmp(journal_a, journal_b, shallow=False)
    size_a, size_b = journal_a.stat().st_size, journal_b.stat().st_size
    speedup = elapsed_a / elapsed_b if elapsed_b else float("nan")

    log("## Verdict\n")
    log(f"- {journal_a.name}: workers=1 {size_a} bytes, workers={args.workers} {size_b} bytes")
    log(f"- Speedup: {speedup:.2f}x ({elapsed_a:.1f}s -> {elapsed_b:.1f}s)")
    if identical:
        log(f"\n**PASS -- byte-identical.** `filecmp.cmp({journal_a}, {journal_b}, shallow=False)` is True. "
            "Phase 2's concurrency unlock is safe to ship at this scale.")
    else:
        log("\n**FAIL -- NOT byte-identical.** Do not ship the `_check_supported` relaxation. "
            "Revert to sequential-only and fall back to Phase 3 (checkpoint/resume) per the plan's own risk section.")
        first_a = journal_a.read_text(encoding="utf-8").splitlines()
        first_b = journal_b.read_text(encoding="utf-8").splitlines()
        for i, (line_a, line_b) in enumerate(zip(first_a, first_b)):
            if line_a != line_b:
                log(f"\nFirst differing line ({i}):\nA: {line_a}\nB: {line_b}")
                break
        else:
            log(f"\nOne file is a strict prefix of the other -- lengths {len(first_a)} vs {len(first_b)}.")

    if args.results is not None:
        args.results.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nwrote {args.results}", file=sys.stderr)

    return 0 if identical else 1


if __name__ == "__main__":
    raise SystemExit(main())
