"""
scripts/run_polity_flagship.py

The runner for the flagship arm: 30 simulated years at population 500, every
substantive mechanism on, on vLLM. Scoped by `plan-flagship-30y-run.md`.

**Why a new runner rather than another `run_v*_acceptance.py`.** Every existing
runner here answers a comparison question -- two arms differing in one field,
sized to isolate that field. This one answers a *production* question: can the
simulator actually run at the scale it was designed for, for long enough to
produce something a UI can be built against? That changes what the script needs:
population is a knob (no existing runner has one), the sortition chamber is ON
(every existing runner turns it off to stay cheap), and the run is long enough
that wall-clock, checkpointing and progress reporting stop being incidental.

**Full richness, explicitly.** `_flagship_config` turns on every substantive
mechanism at once: legitimacy, mandate drift, petitions, street pressure,
awakening (with contagion), exogenous events (scandal + economic shock), the
social graph, and the sortition chamber. This is deliberately NOT an acceptance
arm -- nothing is being isolated, so nothing is being held back. The config's own
cross-validation rules are respected by construction and re-asserted in
`_assert_coherent` (the shipped rules fire in `load_config`, on the YAML, and do
not re-fire through `dataclasses.replace`).

**`candidacy.ambition_threshold` stays at its shipped value**, unlike
`run_acceptance_comparison._config_for_arm`, which forces it to 0.0. That 0.0 is
a comparison device (it makes candidacy unconditional so the arms differ only in
the pressure menu); the flagship wants the calibrated institution, and ADR-002's
0.30 is that calibration. What pop 500 does to the mechanism the threshold
protects is Phase 5's question, measured separately and cheaply.

Staged ramp (each stage gates the next -- see the plan's Phase 7):

    # 1. smoke: proves the wiring, minutes
    python fast_api_voter/scripts/run_polity_flagship.py \\
        --years 2 --population 100 --engine llm --max-batch-replays 2 \\
        --output-dir scripts/flagship_runs

    # 2. parity: compare against acceptance_v6b_results.md's measured baseline
    python fast_api_voter/scripts/run_polity_flagship.py \\
        --years 8 --population 100 --engine llm --max-batch-replays 2 \\
        --output-dir scripts/flagship_runs

    # 3. scale probe: real per-tick cost at the target population
    python fast_api_voter/scripts/run_polity_flagship.py \\
        --years 8 --population 500 --seats 75 --engine llm --max-batch-replays 2 \\
        --output-dir scripts/flagship_runs

    # 4. the flagship
    python fast_api_voter/scripts/run_polity_flagship.py \\
        --years 30 --population 500 --seats 75 --engine llm --max-batch-replays 2 \\
        --output-dir scripts/flagship_runs

    # if the flagship (or any arm) is interrupted, continue it with the SAME
    # args plus --resume -- it picks up from its own last per-tick checkpoint
    python fast_api_voter/scripts/run_polity_flagship.py \\
        --years 30 --population 500 --seats 75 --engine llm --max-batch-replays 2 \\
        --output-dir scripts/flagship_runs --resume

`--engine deterministic` runs the same config through `simple_rules.py` in
seconds and spends no GPU -- the cheap way to confirm the config plumbing before
committing hours to an LLM arm, the same calibration-before-commit checkpoint
`run_v7_acceptance.py` uses.

`--workers` is plumbed (it sets `parallel.intra_run_workers`) but the engine's
own `_check_supported()` refuses anything above 1 unconditionally -- Phase 2
built the concurrency mechanism and then found, via its own live determinism
proof, that vLLM concurrent batching breaks reproducibility too (not just
Ollama's already-known issue): 20/497 events diverged between workers=1 and
workers=8 on an otherwise identical run. See plan-flagship-30y-run.md's own
Phase 2 writeup and check_intra_run_concurrency_determinism_results.md. The
flagship therefore runs sequential; `--workers` stays plumbed as ready-to-
enable groundwork, not a live knob.

`--resume` (Phase 3): continues a crashed or deliberately-stopped run from its
own last per-tick checkpoint (`checkpoint.json`, beside `events.jsonl` in the
run's own directory) -- see `api.domain.polity.checkpoint` and
`run_simulation`'s own `resume` parameter for the mechanism. Requires the SAME
CLI args (config) the original attempt used; `run_simulation`'s own
`config_hash` check refuses loudly, not silently, if they differ. Mutually
exclusive with `--force`, which destroys the very run `--resume` continues.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import shutil
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.config import PolityConfig, load_config  # noqa: E402
from api.domain.polity.indexer import RunMetrics, index_run  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402


def _flagship_config(
    *,
    engine: str,
    years: int,
    population: int,
    seats: int,
    seed: int,
    output_dir: Path,
    max_batch_replays: int,
    provider: str | None,
    workers: int,
) -> PolityConfig:
    config = load_config()
    config = dataclasses.replace(
        config,
        run=dataclasses.replace(
            config.run,
            seed=seed,
            duration_years=years,
            population_size=population,
            run_label=f"flagship-{years}y-p{population}",
        ),
        journal=dataclasses.replace(config.journal, output_dir=str(output_dir)),
        # --- full richness: every substantive mechanism on ---
        # Two flags here are shipped `false` and are NOT merely defaults left
        # alone -- both are implemented, consequential mechanisms, and the
        # flagship is the run that is supposed to exercise them:
        #   * candidacy.rupture_path_enabled -- the §2.4 rare path by which a
        #     citizen declares against their own party. Without it the candidate
        #     field is a flat one-nominee-per-party at every scale, which is also
        #     why `max_candidates_hard_cap` can never bind and why Class B counts
        #     zero rupture declarations (measured: polity_scale_gate_pop500_
        #     results.md).
        #   * institutions.blank_vote_competitive -- v4 Lot 9's live mechanism
        #     letting a blank plurality invalidate a presidential election and
        #     force a rerun with the previous field barred. It is bounded by
        #     reelection_max_attempts=2, so it cannot loop.
        # Deliberately still OFF: parties.birth_enabled/death_enabled, which are
        # parsed but not implemented (parties.py's own module docstring), and
        # social_graph.evolving / sortition_chamber.renewable, which load_config
        # rejects outright as designs this codebase decided against.
        candidacy=dataclasses.replace(config.candidacy, rupture_path_enabled=True),
        institutions=dataclasses.replace(config.institutions, blank_vote_competitive=True),
        legitimacy=dataclasses.replace(config.legitimacy, enabled=True),
        mandate=dataclasses.replace(config.mandate, enabled=True),
        petition=dataclasses.replace(config.petition, enabled=True),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True),
        social_graph=dataclasses.replace(config.social_graph, enabled=True),
        events=dataclasses.replace(
            config.events, enabled=True, scandal_enabled=True, economic_shock_enabled=True
        ),
        awakening=dataclasses.replace(
            config.awakening,
            enabled=True,
            context_modulation=dataclasses.replace(
                config.awakening.context_modulation,
                # both required by load_config's own cross-validation once
                # events/social_graph are on -- see _assert_coherent
                event_salience=True,
                neighbors_acting=True,
            ),
        ),
        sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True, seats=seats),
        pressure_menu=dataclasses.replace(
            config.pressure_menu,
            electoral_only=False,
            petition_enabled=True,
            mobilization_enabled=True,
        ),
        parallel=dataclasses.replace(config.parallel, intra_run_workers=workers),
    )

    if engine == "llm":
        llm = dataclasses.replace(config.llm, enabled=True, max_batch_replays=max_batch_replays)
        if provider is not None:
            # Baseline A/B only (plan Phase 0): the shipped default is the
            # single source of truth for which provider production uses --
            # this override exists to time the OTHER one, not to make the
            # choice configurable per run.
            base_url = {
                "vllm": "http://localhost:8000/v1",
                "ollama": "http://localhost:11434/v1",
            }[provider]
            llm = dataclasses.replace(llm, provider=provider, base_url=base_url)
        config = dataclasses.replace(config, llm=llm)
    return config


def _assert_coherent(config: PolityConfig) -> None:
    """Re-assert the cross-config rules load_config enforces on the YAML.

    Those rules fire at parse time and do not re-fire through
    `dataclasses.replace`, so a full-richness config assembled in Python can
    silently violate one. Cheap to check, and a violation here means a days-long
    run producing quietly wrong output.
    """
    if config.events.enabled and not config.awakening.context_modulation.event_salience:
        raise ValueError("events.enabled requires awakening.context_modulation.event_salience")
    if config.awakening.context_modulation.neighbors_acting and not config.social_graph.enabled:
        raise ValueError("awakening.context_modulation.neighbors_acting requires social_graph.enabled")
    if config.events.enabled != (config.events.scandal_enabled or config.events.economic_shock_enabled):
        raise ValueError("events.enabled must equal (scandal_enabled or economic_shock_enabled)")
    if config.pressure_menu.petition_enabled != config.petition.enabled:
        raise ValueError("pressure_menu.petition_enabled must match petition.enabled")
    if config.pressure_menu.mobilization_enabled != config.street_pressure.enabled:
        raise ValueError("pressure_menu.mobilization_enabled must match street_pressure.enabled")
    if config.sortition_chamber.enabled and config.sortition_chamber.seats > config.run.population_size:
        raise ValueError("sortition_chamber.seats must not exceed run.population_size")
    if config.institutions.blank_vote_competitive and not config.institutions.blank_vote_enabled:
        raise ValueError("institutions.blank_vote_competitive requires institutions.blank_vote_enabled")


def _metrics_to_json(metrics: RunMetrics) -> dict[str, Any]:
    return {
        "run_id": metrics.run_id,
        "total_ticks": metrics.total_ticks,
        "terms": [dataclasses.asdict(t) for t in metrics.terms],
        "effective_parties": metrics.effective_parties,
        "cohabitation_rate": metrics.cohabitation_rate,
        "coalition_lifespans": metrics.coalition_lifespans,
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


def _count_llm_decisions(journal_path: Path) -> dict[str, int]:
    """Per-event-type counts of LLM-sourced decisions, straight off the journal.

    The engine keeps no cross-run counter, and this is the number every cost
    projection in the plan is built from -- so it is measured rather than
    inferred from population x ticks, which would miss the awakening gate
    entirely (it decides who is consulted at all, so the real count is well
    below the naive product).

    `codebook_version` is the discriminator: the deterministic path writes it
    empty, the LLM path writes `config.llm.codebook_version` on every decision
    it journals. There is no `decision_type` field on the wire.

    One exception, checked rather than assumed: `_run_reaction_to_event` writes
    `codebook_version` unconditionally, on the deterministic branch too. That
    makes this count wrong for a deterministic run (it reports every
    reaction_to_event as LLM-sourced), so the caller only runs it for
    `engine == "llm"`, where the discriminator holds for every type.

    These are *decisions*, not HTTP calls -- a chunked batch answers for several
    citizens in one call, so calls = decisions / chunk size for the batched
    types (and equal for the chunk-size-1 ones: vote_cast, chamber).
    """
    counts: Counter[str] = Counter()
    with journal_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("codebook_version"):
                counts[str(event.get("event_type"))] += 1
    return dict(sorted(counts.items()))


def run_flagship(
    *,
    engine: str,
    years: int,
    population: int,
    seats: int,
    seed: int,
    output_dir: Path,
    max_batch_replays: int,
    provider: str | None,
    workers: int,
    run_id: str | None,
    force: bool = False,
    resume: bool = False,
) -> Path:
    config = _flagship_config(
        engine=engine,
        years=years,
        population=population,
        seats=seats,
        seed=seed,
        output_dir=output_dir / "placeholder",
        max_batch_replays=max_batch_replays,
        provider=provider,
        workers=workers,
    )
    _assert_coherent(config)

    effective_provider = config.llm.provider if engine == "llm" else "none"
    run_id = run_id or f"flagship-{years}y-p{population}-{engine}"
    run_dir = output_dir / run_id
    if resume:
        # Phase 3 (plan-flagship-30y-run.md): --resume needs the SAME run_dir
        # (and, inside it, the SAME config -- run_simulation's own config_hash
        # check is the real guard here) a crashed or deliberately-stopped
        # attempt already created. Never deleted, never recreated -- that
        # would destroy the checkpoint/journal this flag exists to continue.
        if not run_dir.exists():
            raise FileNotFoundError(f"--resume requested but {run_dir} does not exist -- nothing to resume")
    elif run_dir.exists() and not force:
        # Journal.__init__ opens events.jsonl in append mode, so a re-run into
        # an existing run_id silently CONCATENATES two runs into one file --
        # event_id restarts at 0 mid-file and every count downstream doubles.
        # Every other runner here guards this; measured the hard way when this
        # one did not (the Phase 5 scale gate reported 62 sortition rotations
        # for a 30-year run that has 31).
        raise FileExistsError(
            f"{run_dir} already exists -- Journal appends rather than overwrites, so re-running "
            "into it would concatenate two runs. Remove it, pass --run-id, --resume, or --force."
        )
    elif run_dir.exists() and force:
        shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
    else:
        run_dir.mkdir(parents=True, exist_ok=True)
    config = dataclasses.replace(
        config, journal=dataclasses.replace(config.journal, output_dir=str(run_dir / "run"))
    )
    if not resume:
        # Skipped on resume, deliberately: rewriting this from a possibly-
        # different set of CLI args right before run_simulation's own
        # config_hash check might reject them would overwrite the one record
        # of what the crashed attempt actually ran, for no benefit -- the
        # hash check is the real guard either way.
        (run_dir / "config.json").write_text(
            json.dumps(dataclasses.asdict(config), indent=2, default=str), encoding="utf-8"
        )

    replay_handler = None
    if engine == "llm":
        engine_logger = logging.getLogger("api.domain.polity.llm_behavior_engine")
        replay_handler = logging.FileHandler(run_dir / "replays.log", encoding="utf-8")
        replay_handler.setLevel(logging.WARNING)
        engine_logger.addHandler(replay_handler)
        engine_logger.setLevel(logging.WARNING)

    print(
        f"[flagship] {run_id}: {years}y x {population} citizens, {seats} chamber seats, "
        f"engine={engine}, provider={effective_provider}, workers={workers}, "
        f"replays={max_batch_replays if engine == 'llm' else 0}",
        file=sys.stderr,
        flush=True,
    )

    start = time.monotonic()
    try:
        journal_path = run_simulation(config, run_id=run_id, llm_client=None, resume=resume)
    finally:
        elapsed = time.monotonic() - start
        if replay_handler is not None:
            logging.getLogger("api.domain.polity.llm_behavior_engine").removeHandler(replay_handler)
            replay_handler.close()

    replay_count = 0
    replays_log = run_dir / "replays.log"
    if replays_log.is_file():
        replay_count = sum(1 for _ in replays_log.read_text(encoding="utf-8").splitlines())

    decision_counts = _count_llm_decisions(journal_path) if engine == "llm" else {}
    total_calls = sum(decision_counts.values())

    metrics = index_run(journal_path, config)
    payload = _metrics_to_json(metrics)
    payload["_meta"] = {
        "run_id": run_id,
        "engine": engine,
        "provider": effective_provider,
        "model": config.llm.model if engine == "llm" else None,
        "duration_years": years,
        "population_size": population,
        "sortition_seats": seats,
        "seed": seed,
        "intra_run_workers": workers,
        "max_batch_replays": max_batch_replays if engine == "llm" else 0,
        "elapsed_seconds": round(elapsed, 1),
        "replay_count": replay_count,
        "decisions_total": total_calls,
        "decisions_by_type": decision_counts,
        "seconds_per_decision": round(elapsed / total_calls, 3) if total_calls else None,
        "seconds_per_tick": round(elapsed / metrics.total_ticks, 2) if metrics.total_ticks else None,
    }
    metrics_path = run_dir / "metrics.json"
    metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(
        f"[flagship] {run_id}: {elapsed:.1f}s over {metrics.total_ticks} ticks, "
        f"{total_calls} decisions, {replay_count} replays -> {metrics_path}",
        file=sys.stderr,
        flush=True,
    )
    return metrics_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--years", type=int, default=30)
    parser.add_argument("--population", type=int, default=500)
    parser.add_argument("--seats", type=int, default=75, help="sortition_chamber.seats (plan Phase 5: 15%% of pop)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--engine", choices=["llm", "deterministic"], default="deterministic")
    parser.add_argument(
        "--provider",
        choices=["vllm", "ollama"],
        default=None,
        help="override the shipped provider -- baseline A/B timing only (plan Phase 0)",
    )
    parser.add_argument("--max-batch-replays", type=int, default=2)
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help=(
            "parallel.intra_run_workers; >1 is refused by the engine on every provider -- Phase 2's own "
            "determinism proof found vLLM concurrency unsafe too, not just Ollama's already-known issue "
            "(see plan-flagship-30y-run.md Phase 2 and check_intra_run_concurrency_determinism_results.md)"
        ),
    )
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--force", action="store_true", help="delete an existing run dir instead of refusing")
    parser.add_argument(
        "--resume", action="store_true",
        help="continue a crashed or deliberately-stopped run from its own last checkpoint (Phase 3)",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("scripts/flagship_runs"))
    args = parser.parse_args(argv)

    if args.force and args.resume:
        parser.error("--force and --resume are mutually exclusive -- --force destroys the run --resume continues")

    run_flagship(
        engine=args.engine,
        years=args.years,
        population=args.population,
        seats=args.seats,
        seed=args.seed,
        output_dir=args.output_dir,
        max_batch_replays=args.max_batch_replays,
        provider=args.provider,
        workers=args.workers,
        run_id=args.run_id,
        force=args.force,
        resume=args.resume,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
