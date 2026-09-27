"""
scripts/run_acceptance_comparison.py

v4 Lot 8's acceptance deliverable: the 4-modality pressure-menu comparison
(electoral_only / petition_only / mobilization_only / both) design doc §11
exists to run, at population_size=100 (this project's own current scale --
no v3 population-scale-up palier has ever been done, so every calibration
number in this repo is measured at 100, not 1000), seed=42.

Follows the calibrate_*.py precedent (module docstring stating the
question, real run_simulation on the real production path, not in CI,
results doc committed) with two deliberate breaks, both forced by the wall
clock a full LLM sweep costs on CPU-only Ollama (see this lot's own plan in
merry-hugging-hamming.md for the measured-per-call arithmetic behind the
numbers below):

1. --arm runs exactly ONE modality per invocation. A single process running
   all four arms end to end is an hours-long transaction whose failure at
   hour 9 costs the previous three arms' work for nothing.
2. Metrics are written as JSON next to each arm's journal (metrics.json),
   and the markdown results doc is rendered FROM those files (--summarize),
   never from a live run -- so a single arm can be re-run in isolation and
   the doc regenerated without repeating the other three.

Protocol (renegotiated from the roadmap's literal "four arms x 30 years
under the LLM", ~34h on this hardware, to something an overnight run can
actually finish -- see this lot's own plan for the full arithmetic and
justification):
    - 4 arms x llm.enabled=True,  duration_years=8  (~11h total measured
      forecast; 3 elections, 2 full presidential terms -- the minimum that
      makes "term", "re-election", "recall within a term" and "a new term
      after a vacancy" all observable).
    - 4 arms x llm.enabled=False, duration_years=8  (the exactly-matched
      §11.4 baseline for the LLM arms above -- same duration, deterministic
      engine, seconds to run).
    - 4 arms x llm.enabled=False, duration_years=30 (the long-horizon
      reference the roadmap's own one-paragraph description asked for --
      also cheap, since it's deterministic).
    The roadmap's literal 4x30y LLM sweep is NOT run here -- priced and
    explicitly deferred to a vLLM host (§15bis.6's own criterion), named as
    this lot's top v5-adjacent handoff item, not smuggled into this script.

A batch rejected by the LLM (LlmResponseError) is replayed up to
--max-batch-replays times (config.llm.max_batch_replays, shipped 0 --
this script is the one place that raises it) and every replay is logged,
never journaled -- see llm_behavior_engine._complete_and_decode_with_replay.
Each arm's replay count is written to that arm's own replays.log and
carried into its metrics.json under "_meta" -- it is data (this project's
first direct measurement of its real batch-misalignment rate at production
batch sizes), not an error log nobody reads.

Usage:
    # one arm, deterministic, 8 years -- seconds
    python fast_api_voter/scripts/run_acceptance_comparison.py \\
        --arm electoral_only --engine deterministic --duration-years 8 \\
        --output-dir scripts/acceptance_runs

    # one arm, real qwen3:8b, 8 years, up to 2 replays per rejected batch
    python fast_api_voter/scripts/run_acceptance_comparison.py \\
        --arm electoral_only --engine llm --duration-years 8 \\
        --max-batch-replays 2 --output-dir scripts/acceptance_runs

    # index an already-produced journal without re-running anything
    python fast_api_voter/scripts/run_acceptance_comparison.py \\
        --index scripts/acceptance_runs/electoral_only-llm-8y/run/events.jsonl \\
        --index-config scripts/acceptance_runs/electoral_only-llm-8y/config.json

    # render the committed results doc from every metrics.json under a dir
    python fast_api_voter/scripts/run_acceptance_comparison.py \\
        --summarize scripts/acceptance_runs --results scripts/acceptance_v4_results.md
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.config import PolityConfig, load_config  # noqa: E402
from api.domain.polity.indexer import RunMetrics, index_run  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402

_ARMS = ("electoral_only", "petition_only", "mobilization_only", "both")


def _config_for_arm(arm: str, *, engine: str, duration_years: int, output_dir: Path, max_batch_replays: int) -> PolityConfig:
    config = load_config()
    config = dataclasses.replace(
        config,
        journal=dataclasses.replace(config.journal, output_dir=str(output_dir)),
        candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0),
        run=dataclasses.replace(config.run, duration_years=duration_years),
        legitimacy=dataclasses.replace(config.legitimacy, enabled=True),
        awakening=dataclasses.replace(config.awakening, enabled=True),
        mandate=dataclasses.replace(config.mandate, enabled=True),
    )
    if arm == "electoral_only":
        menu = dataclasses.replace(config.pressure_menu, electoral_only=True, petition_enabled=False, mobilization_enabled=False)
        petition = config.petition
        street = config.street_pressure
    elif arm == "petition_only":
        menu = dataclasses.replace(config.pressure_menu, electoral_only=False, petition_enabled=True, mobilization_enabled=False)
        petition = dataclasses.replace(config.petition, enabled=True)
        street = config.street_pressure
    elif arm == "mobilization_only":
        menu = dataclasses.replace(config.pressure_menu, electoral_only=False, petition_enabled=False, mobilization_enabled=True)
        petition = config.petition
        street = dataclasses.replace(config.street_pressure, enabled=True)
    elif arm == "both":
        menu = dataclasses.replace(config.pressure_menu, electoral_only=False, petition_enabled=True, mobilization_enabled=True)
        petition = dataclasses.replace(config.petition, enabled=True)
        street = dataclasses.replace(config.street_pressure, enabled=True)
    else:
        raise ValueError(f"unknown --arm {arm!r}, expected one of {_ARMS}")
    config = dataclasses.replace(config, pressure_menu=menu, petition=petition, street_pressure=street)

    if engine == "llm":
        config = dataclasses.replace(
            config, llm=dataclasses.replace(config.llm, enabled=True, max_batch_replays=max_batch_replays)
        )
    return config


def _metrics_to_json(metrics: RunMetrics) -> dict[str, Any]:
    return {
        "run_id": metrics.run_id,
        "total_ticks": metrics.total_ticks,
        "terms": [dataclasses.asdict(t) for t in metrics.terms],
        "effective_parties": metrics.effective_parties,
        "cohabitation_rate": metrics.cohabitation_rate,
        "coalition_lifespans": metrics.coalition_lifespans,
        "blank_vote_rate": metrics.blank_vote_rate,
        "mean_legitimacy": metrics.mean_legitimacy,
        "recalls_by_trigger": metrics.recalls_by_trigger,
        "recalls_per_term": metrics.recalls_per_term,
        "mandate_deviation": metrics.mandate_deviation,
        "mandate_deviation_source": metrics.mandate_deviation_source,
        "mandate_deviation_coverage": metrics.mandate_deviation_coverage,
        "lame_duck_deviation_delta": metrics.lame_duck_deviation_delta,
        "inaction_rate": metrics.inaction_rate,
        "pressure_lever_mix": metrics.pressure_lever_mix,
        "pressure_lever_counts": metrics.pressure_lever_counts,
        "petition_downgrades": metrics.petition_downgrades,
        "petition_success_rate": metrics.petition_success_rate,
        "petition_removal_rate": metrics.petition_removal_rate,
        "stance_distribution": metrics.stance_distribution,
    }


def run_arm(arm: str, *, engine: str, duration_years: int, output_dir: Path, max_batch_replays: int) -> Path:
    run_dir = output_dir / f"{arm}-{engine}-{duration_years}y"
    run_dir.mkdir(parents=True, exist_ok=True)
    config = _config_for_arm(
        arm, engine=engine, duration_years=duration_years, output_dir=run_dir / "run", max_batch_replays=max_batch_replays
    )
    (run_dir / "config.json").write_text(json.dumps(dataclasses.asdict(config), indent=2, default=str), encoding="utf-8")

    replay_handler = None
    if engine == "llm":
        engine_logger = logging.getLogger("api.domain.polity.llm_behavior_engine")
        replay_handler = logging.FileHandler(run_dir / "replays.log", encoding="utf-8")
        replay_handler.setLevel(logging.WARNING)
        engine_logger.addHandler(replay_handler)
        engine_logger.setLevel(logging.WARNING)

    start = time.monotonic()
    try:
        # llm_client=None: run_simulation constructs and closes a real
        # OllamaJsonClient itself whenever config.llm.enabled is True
        # (_llm_client_scope) -- this script never touches the client.
        journal_path = run_simulation(config, run_id=f"{arm}-{engine}-{duration_years}y", llm_client=None)
    finally:
        elapsed = time.monotonic() - start
        if replay_handler is not None:
            logging.getLogger("api.domain.polity.llm_behavior_engine").removeHandler(replay_handler)
            replay_handler.close()

    replay_count = 0
    replays_log = run_dir / "replays.log"
    if replays_log.is_file():
        replay_count = sum(1 for _ in replays_log.read_text(encoding="utf-8").splitlines())

    metrics = index_run(journal_path, config)
    payload = _metrics_to_json(metrics)
    payload["_meta"] = {
        "arm": arm, "engine": engine, "duration_years": duration_years,
        "elapsed_seconds": round(elapsed, 1), "replay_count": replay_count,
    }
    metrics_path = run_dir / "metrics.json"
    metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"{arm}/{engine}/{duration_years}y: {elapsed:.1f}s, {replay_count} replays, metrics={metrics_path}")
    return metrics_path


def index_existing(journal_path: Path, config_path: Path) -> Path:
    raw_config = json.loads(config_path.read_text(encoding="utf-8"))
    # config.json is a dataclasses.asdict() dump -- rebuild via load_config's
    # own YAML section parsers is overkill for a one-off re-index; the
    # shipped config plus the same overrides run_arm applies is sufficient
    # since only run.duration_years/journal.output_dir/the toggled sections
    # actually varied between arms, all reconstructible from the archive.
    config = load_config()
    config = dataclasses.replace(config, run=dataclasses.replace(config.run, duration_years=raw_config["run"]["duration_years"]))
    metrics = index_run(journal_path, config)
    payload = _metrics_to_json(metrics)
    metrics_path = journal_path.parent.parent / "metrics.json"
    metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"indexed {journal_path} -> {metrics_path}")
    return metrics_path


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, dict):
        return ", ".join(f"{k}={_fmt(v)}" for k, v in sorted(value.items()))
    return str(value)


def summarize(runs_dir: Path, results_path: Path | None) -> None:
    metrics_files = sorted(runs_dir.glob("*/metrics.json"))
    if not metrics_files:
        print(f"no metrics.json found under {runs_dir}", file=sys.stderr)
        return

    lines: list[str] = []

    def log(line: str) -> None:
        print(line)
        lines.append(line)

    log("# v4 acceptance comparison — the 4-modality pressure-menu sweep (Lot 8)\n")
    log(
        "n=1 per arm (one seed, no Monte Carlo band) -- the honest limit of this deliverable at "
        "this hardware's wall-clock cost; see this lot's own residual risks in merry-hugging-hamming.md.\n"
    )
    log(
        "| arm | engine | years | elapsed(s) | replays | mean L (last) | recalls | "
        "mandate_dev (last, src) | inaction_rate (last) | lever mix | stance mix | "
        "petition success/removal |"
    )
    log("|---|---|---|---|---|---|---|---|---|---|---|---|")

    for path in metrics_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta = payload["_meta"]
        mean_l = payload["mean_legitimacy"]
        last_l = mean_l[-1][1] if mean_l else None
        deviation = payload["mandate_deviation"]
        last_dev = deviation[-1][1] if deviation else None
        inaction = payload["inaction_rate"]
        last_inaction = inaction[-1][1] if inaction else None
        recalls = payload["recalls_by_trigger"]
        log(
            f"| {meta['arm']} | {meta['engine']} | {meta['duration_years']} | {meta['elapsed_seconds']} | "
            f"{meta['replay_count']} | {_fmt(last_l)} | {_fmt(recalls)} | "
            f"{_fmt(last_dev)} ({payload['mandate_deviation_source'] or '—'}) | {_fmt(last_inaction)} | "
            f"{_fmt(payload['pressure_lever_mix'])} | {_fmt(payload['stance_distribution'])} | "
            f"{_fmt(payload['petition_success_rate'])}/{_fmt(payload['petition_removal_rate'])} |"
        )

    log("\n## Headline questions (§0's research question, stated as an experiment)\n")
    log("- Does `electoral_only` really never recall anyone? Compare the `recalls` column across arms.")
    log(
        "- Does a free arbitration (llm engine) produce a different lever mix than the rigid "
        "sign>launch>mobilize>wait priority chain (deterministic engine)? Compare `lever mix` "
        "for the same arm across engines."
    )
    log(
        "- What is the inaction rate of the discontented (§7bis.3: \"probablement le résultat le "
        "plus intéressant du modèle\")? See the `inaction_rate` column, llm engine rows."
    )
    log(
        "- Does the confidence vote stop being decorative once revealed_position can drift "
        "(llm.enabled + mandate.enabled)? Compare `petition success/removal` for the llm engine "
        "against the deterministic baseline, where removal is provably 0 (keep_ratio == m identity, "
        "test_confidence_vote_keep_ratio_equals_mandate_strength_on_the_deterministic_path)."
    )

    if results_path is not None:
        results_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n(full report written to {results_path})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--arm", choices=_ARMS)
    parser.add_argument("--engine", choices=["llm", "deterministic"], default="deterministic")
    parser.add_argument("--duration-years", type=int, default=8)
    parser.add_argument("--max-batch-replays", type=int, default=2)
    parser.add_argument("--output-dir", type=Path, default=Path("scripts/acceptance_runs"))
    parser.add_argument("--index", type=Path, help="index an existing journal instead of running one")
    parser.add_argument("--index-config", type=Path, help="the config.json archived next to --index's journal")
    parser.add_argument("--summarize", type=Path, help="render the results doc from every metrics.json under this dir")
    parser.add_argument("--results", type=Path, help="where --summarize writes the rendered markdown")
    args = parser.parse_args()

    if args.summarize:
        summarize(args.summarize, args.results)
        return 0

    if args.index:
        if not args.index_config:
            parser.error("--index requires --index-config")
        index_existing(args.index, args.index_config)
        return 0

    if not args.arm:
        parser.error("--arm is required unless --summarize or --index is given")

    run_arm(
        args.arm, engine=args.engine, duration_years=args.duration_years,
        output_dir=args.output_dir, max_batch_replays=args.max_batch_replays,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
