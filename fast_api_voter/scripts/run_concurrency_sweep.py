"""S2.1's concurrency sweep: the same 1-year, population-100 flagship run at several worker
counts, then the comparison pre-registered in plan-polity-build-order.md against workers = 1.

`run` needs the vLLM server (GPU). The FP8 KV cache is a server setting -- vLLM's
`--kv-cache-dtype fp8`, which docker-compose.llm.yml does not set today (auto): run the
arms once per server configuration, under a --label that names it.

`compare` needs no GPU: it replays every arm from its own call log (S0.6) to read vote_cast
agreement with build_ranking, and checks each arm replays to its own journal (see
api/domain/polity/concurrency_comparison.py), then writes <label>/comparison.md and .json.

Usage (from fast_api_voter/):
    python scripts/run_concurrency_sweep.py run --label kv-auto --workers 1 4 8 12
    python scripts/run_concurrency_sweep.py compare --label kv-auto
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.concurrency_comparison import compare_to_baseline, measure_run  # noqa: E402
from api.domain.polity.run_polity_simulation import config_hash  # noqa: E402
from run_polity_flagship import _flagship_config  # noqa: E402

DEFAULT_ROOT = Path(__file__).resolve().parent / "concurrency_sweep_runs"
SHAPE = {"years": 1, "population": 100, "seats": 30, "seed": 42, "max_batch_replays": 2}


def _arm(workers: int) -> dict[str, Any]:
    return {**SHAPE, "workers": workers, "reproducibility": "strict" if workers == 1 else "relaxed", "run_id": f"w{workers}"}


def run(label: str, workers: list[int], root: Path) -> int:
    sweep_dir = root / label
    sweep_dir.mkdir(parents=True, exist_ok=True)
    arms = [_arm(w) for w in workers]
    (sweep_dir / "manifest.json").write_text(json.dumps({"label": label, "arms": arms}, indent=2))
    for arm in arms:
        command = [sys.executable, str(Path(__file__).resolve().parent / "run_polity_flagship.py"), "--engine", "llm",
                   "--years", str(arm["years"]), "--population", str(arm["population"]), "--seats", str(arm["seats"]),
                   "--seed", str(arm["seed"]), "--max-batch-replays", str(arm["max_batch_replays"]),
                   "--workers", str(arm["workers"]), "--reproducibility", arm["reproducibility"],
                   "--run-id", arm["run_id"], "--output-dir", str(sweep_dir)]
        print("$", " ".join(command), flush=True)
        if subprocess.run(command, check=False).returncode != 0:
            print(f"arm {arm['run_id']} failed; stopping", file=sys.stderr)
            return 1
    return 0


def _speedup(value: float | None) -> str:
    return "–" if value is None else f"{value:.2f}"


def _markdown(label: str, measures: list[Any], verdicts: list[dict[str, Any]]) -> str:
    def pct(pair: tuple[int, int]) -> str:
        return f"{pair[0]}/{pair[1]} = {100 * pair[0] / pair[1]:.1f}%" if pair[1] else "–"

    def signed(value: float | None) -> str:
        return "–" if value is None else f"{value:+.1f}"

    lines = [f"# Concurrency sweep {label} (S2.1)", "",
             "Pre-registered against workers = 1: vote_cast agreement with build_ranking within ±2 points, "
             "first-attempt failure rate within ±5 points, speedup reported whatever it is; each run replays to its journal.", "",
             "| arm | workers | vote agreement | Δ points | in band | vote first-attempt failures | Δ points | in band | wall-clock s | speedup | replays |",
             "|---|---:|---|---:|---|---|---:|---|---:|---:|---|"]
    for measure, verdict in zip(measures, verdicts):
        failures = measure.first_attempt_failures.get("vote_cast", (0, 0))
        lines.append(
            f"| {measure.label} | {measure.workers} | {pct(measure.vote_agreement)} | {signed(verdict['vote_agreement_points'])} "
            f"| {verdict['vote_agreement_within_band']} | {pct(failures)} | {signed(verdict['first_attempt_failure_points'].get('vote_cast'))} "
            f"| {verdict['vote_first_attempt_failure_within_band']} | {measure.wall_clock_seconds} | "
            f"{_speedup(verdict['speedup'])} | {measure.replays_to_its_journal} |"
        )
    return "\n".join(lines) + "\n"


def compare(label: str, root: Path) -> int:
    sweep_dir = root / label
    arms = json.loads((sweep_dir / "manifest.json").read_text())["arms"]
    measures = []
    for arm in arms:
        run_dir = sweep_dir / arm["run_id"] / "run" / arm["run_id"]
        config = _flagship_config(engine="llm", years=arm["years"], population=arm["population"], seats=arm["seats"],
                                  seed=arm["seed"], output_dir=Path("unused"), max_batch_replays=arm["max_batch_replays"],
                                  provider="vllm", workers=arm["workers"], reproducibility=arm["reproducibility"])
        recorded = json.loads((run_dir / "run_metadata.json").read_text())["config_hash"]
        if recorded != config_hash(config):
            print(f"{run_dir}: recorded under a different config than the manifest describes", file=sys.stderr)
            return 1
        measures.append(measure_run(run_dir, config, label=arm["run_id"]))
    baseline = next(m for m in measures if m.workers == 1)
    verdicts = [compare_to_baseline(baseline, m) for m in measures]
    (sweep_dir / "comparison.json").write_text(json.dumps(
        {"label": label, "measures": [dataclasses.asdict(m) for m in measures], "verdicts": verdicts}, indent=2))
    (sweep_dir / "comparison.md").write_text(_markdown(label, measures, verdicts))
    print((sweep_dir / "comparison.md").read_text())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("run", "compare"))
    parser.add_argument("--label", required=True, help="names the server configuration, e.g. kv-auto or kv-fp8")
    parser.add_argument("--workers", type=int, nargs="+", default=[1, 4, 8, 12])
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args(argv)
    if args.command == "run":
        return run(args.label, args.workers, args.root)
    return compare(args.label, args.root)


if __name__ == "__main__":
    raise SystemExit(main())
