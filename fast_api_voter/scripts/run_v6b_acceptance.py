"""
scripts/run_v6b_acceptance.py

v6b Lot 4's acceptance deliverable: the elected-vs-sortition comparison design doc §6bis.3 itself
frames as its whole reason for existing --

    "Interet scientifique direct : groupe de controle insensible a toute pression electorale
    (aucune reelection possible), comparable a la chambre elue soumise aux trois canaux du §7bis.
    Hypothese a tester : l'absence de pression electorale produit-elle des decisions plus
    « sinceres » (alignees sur ses propres issue_positions) ou plus erratiques (aucun garde-fou de
    responsabilite) ?"

-- and §6bis.5's own interaction table names it explicitly: "Groupe de controle elu vs tire au
sort." Unlike v6a Lot 4 (which isolated ONE variable, neighbors_acting, and could therefore cite an
already-committed run as its own atomized reference), this comparison needs BOTH quantities
(mandate_deviation for the elected side, chamber_deviation for the sortition side) from the SAME
run, at the SAME ticks -- there is no existing acceptance row that already carries both, so this
lot runs one new, single, self-contained comparison rather than citing a prior one.

The elected side reuses run_acceptance_comparison.py's own "both" arm shape verbatim (full pressure
menu -- petition + mobilization, legitimacy/mandate/awakening all enabled, ambition_threshold=0.0
guaranteeing a real elected president) -- NOT electoral_only/mobilization_only/petition_only:
§6bis.3's own comparison is against a president "soumise aux TROIS canaux du §7bis", all three, not
one isolated lever, unlike v6a Lot 4's own single-variable-isolation goal. social_graph.enabled and
events.enabled both stay at their shipped-off default -- the same confound-avoidance call v5 Lot 5
and v6a Lot 4 already made independently, restated here for a third time: neither is part of
§6bis.3's own comparison, and adding either would introduce a second, simultaneously-changing
variable this lot's own comparison doesn't ask for.

sortition_chamber stays at every shipped default (seats=30, term_years=1, max_deliberation_delta=0.3,
max_deliberation_shifts=3) -- a measurement of the shipped configuration, not a calibration sweep;
v6b Lot 2's own sortition_calibration_results.md already measured chamber-size behavior at exactly
these values.

chamber_deviation itself required a small, deliberate production-code change (v6b Lot 4's own PR,
run_polity_simulation.py's _run_chamber_deliberation): the already-shipped-but-never-called
accountability.chamber_deviation(member) is now journaled as a new "chamber_deviation" key on every
chamber_deliberation event's own payload, computed AFTER chamber_position is updated (the
POST-decision value, mirroring mandate_deviation_recorded's own already-established convention) --
unlike v6a Lot 4 and v5 Lot 5, which both touched zero files under api/, this lot's own one addition
is what makes this comparison possible at all: chamber_deviation had no journal path before it.

Calibration-before-commit is a go/no-go CHECKPOINT here, not a sweep (the same shape v6a Lot 4
used): every value is already shipped and already measured independently (v4 Lot 8's own "both"
arm, v6b Lot 2's own pool-exhaustion calibration). Run --engine deterministic first (near-free,
seconds); confirm it produces the expected shape (zero chamber_deliberation events -- the
deterministic fallback IS the absence of the call, v6b Lot 3's own precedent -- sortition_rotation
events present, and a recall count / final mean_legitimacy in the same range as
both/deterministic/8y's own committed anchor, scripts/acceptance_v4_results.md: legitimacy_floor=2,
mean L 0.345 at 8y) before proceeding to the expensive --engine llm run.

Wall-clock forecast (not a promise -- the real run reports its own elapsed time, exactly like every
prior acceptance script): both/llm/8y's own already-measured 6311.7s (acceptance_v4_results.md) is
the elected side's own closest real anchor. The chamber side adds sortition_chamber.enabled=True at
shipped defaults -- _run_chamber_deliberation runs EVERY tick, not just rotation ticks, chunked at
_CHAMBER_MAX_CHUNK_SIZE=10 (v6b Lot 3's own finding) => 3 chunks/tick. The reliability spike measured
a chunk of 10 at ~79.5-80s (lot3_chamber_reliability_results.md, confirmatory diagnostics table). At
duration_years=8 (33 ticks, 0..32, matching every prior LLM acceptance run's own established
minimum-observability floor): 33 * 3 * ~80s ~= 7920s (~2.2h) for the chamber alone. Forecast total:
~6312s + 7920s ~= 14232s ~= 3.95h -- the most expensive single acceptance run in this palier's own
history, but not disproportionate: electoral_only/llm/8y already measured 11776.3s (~3.27h) in v4
Lot 8.

Usage:
    # calibration dry-run, deterministic, seconds -- compare its own printed recall count / final
    # mean_legitimacy against both/deterministic/8y's own committed anchor before proceeding
    python fast_api_voter/scripts/run_v6b_acceptance.py \\
        --engine deterministic --output-dir scripts/acceptance_v6b_runs

    # the real qwen3:8b run, once the deterministic dry-run above looks safe
    python fast_api_voter/scripts/run_v6b_acceptance.py \\
        --engine llm --max-batch-replays 2 --output-dir scripts/acceptance_v6b_runs

    # render the committed results doc from both arms' metrics.json/chamber.json
    python fast_api_voter/scripts/run_v6b_acceptance.py \\
        --summarize scripts/acceptance_v6b_runs --results scripts/acceptance_v6b_results.md
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
from api.domain.polity.indexer import RunMetrics, index_run, read_journal  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402


def _config_for_v6b_run(
    engine: str, *, duration_years: int, output_dir: Path, max_batch_replays: int,
) -> PolityConfig:
    config = load_config()
    config = dataclasses.replace(
        config,
        journal=dataclasses.replace(config.journal, output_dir=str(output_dir)),
        candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0),
        run=dataclasses.replace(config.run, duration_years=duration_years),
        legitimacy=dataclasses.replace(config.legitimacy, enabled=True),
        mandate=dataclasses.replace(config.mandate, enabled=True),
        awakening=dataclasses.replace(config.awakening, enabled=True),
        pressure_menu=dataclasses.replace(
            config.pressure_menu, electoral_only=False, petition_enabled=True, mobilization_enabled=True
        ),
        petition=dataclasses.replace(config.petition, enabled=True),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True),
        # social_graph / events stay at their shipped-off default -- deliberately,
        # see this module's own docstring.
        sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True),
    )
    if engine == "llm":
        config = dataclasses.replace(
            config,
            llm=dataclasses.replace(
                config.llm, enabled=True, max_batch_replays=max_batch_replays,
                # bug 4 mitigation (llm_batching_determinism_results_gpu.md,
                # 2026-08-20): recycle the Ollama model every 6 calls, safely
                # under the measured risk zone (cache>=7). Not wiring this in
                # is exactly what let the first real-run attempt of this lot
                # die on campaign_positioning's very first think=True call.
                recycle_after_n_calls=6,
            ),
        )
    return config


def _metrics_to_json(metrics: RunMetrics) -> dict[str, Any]:
    return {
        "run_id": metrics.run_id,
        "total_ticks": metrics.total_ticks,
        "terms": [dataclasses.asdict(t) for t in metrics.terms],
        "mean_legitimacy": metrics.mean_legitimacy,
        "recalls_by_trigger": metrics.recalls_by_trigger,
        "recalls_per_term": metrics.recalls_per_term,
        "mandate_deviation": metrics.mandate_deviation,
        "mandate_deviation_source": metrics.mandate_deviation_source,
        "mandate_deviation_coverage": metrics.mandate_deviation_coverage,
        "inaction_rate": metrics.inaction_rate,
        "pressure_lever_mix": metrics.pressure_lever_mix,
        "pressure_lever_counts": metrics.pressure_lever_counts,
        "stance_distribution": metrics.stance_distribution,
        "petition_downgrades": metrics.petition_downgrades,
        "petition_success_rate": metrics.petition_success_rate,
        "petition_removal_rate": metrics.petition_removal_rate,
    }


def _compute_chamber_metrics(journal_path: Path, total_ticks: int) -> dict[str, Any]:
    """The one computation this lot needs that indexer.py doesn't already
    provide -- single consumer (this script), stays ad hoc here rather than
    becoming a new indexer.py/metrics.py row, per calibrate_*.py/
    run_v5_acceptance.py/run_v6a_acceptance.py's own precedent.

    Iterates the FULL tick range (0..total_ticks inclusive), not just ticks
    that happen to have an event -- a tick with zero chamber_deliberation
    events is a real, informative observation (run_v5_acceptance.
    _compute_spark's own already-learned lesson), not an absent one.

    The deterministic arm's own special case: llm.enabled=False means
    _run_chamber_deliberation returns before any journal write at all --
    zero chamber_deliberation events exist, not because chamber_deviation
    is unknown, but because it is KNOWN to be 0.0 by construction (v6b
    Lot 3's own already-unit-tested deterministic-fallback guarantee:
    chamber_position stays pinned to issue_positions forever). Reported as
    an explicit 0.0 with a note, never None (which would read as "not
    tracked" when it is in fact a certain value) and never silently
    omitted."""
    deviations_by_tick: dict[int, list[float]] = {}
    motif_counts: dict[str, int] = {"701": 0, "702": 0}
    rotations: list[dict[str, int]] = []
    for event in read_journal(journal_path):
        if event["event_type"] == "chamber_deliberation":
            tick = event["tick"]
            deviations_by_tick.setdefault(tick, []).append(event["payload"]["chamber_deviation"])
            motif = event["motif"]
            motif_counts[motif] = motif_counts.get(motif, 0) + 1
        elif event["event_type"] == "sortition_rotation":
            rotations.append({"tick": event["tick"], "seated": len(event["payload"]["seated"])})

    # bool(...): `not X and Y` returns Y itself (Python's and/or return an
    # operand, not necessarily a bool), so an un-wrapped expression here
    # would silently serialize the rotations list instead of a boolean.
    known_zero_by_construction = bool(not deviations_by_tick and rotations)
    all_ticks = range(total_ticks + 1)
    per_tick_means = [
        (sum(deviations_by_tick[tick]) / len(deviations_by_tick[tick])) if tick in deviations_by_tick else 0.0
        for tick in all_ticks
    ]
    all_values = [v for values in deviations_by_tick.values() for v in values]

    total_motif = sum(motif_counts.values())
    motif_mix = (
        {code: count / total_motif for code, count in sorted(motif_counts.items())} if total_motif else None
    )

    return {
        "known_zero_by_construction": known_zero_by_construction,
        "chamber_deviation_mean": sum(all_values) / len(all_values) if all_values else 0.0,
        "chamber_deviation_max": max(all_values) if all_values else 0.0,
        "chamber_deviation_per_tick_mean": sum(per_tick_means) / len(per_tick_means),
        "chamber_motif_mix": motif_mix,
        "chamber_motif_counts": motif_counts,
        "rotations": rotations,
        "last_seated_size": rotations[-1]["seated"] if rotations else None,
    }


def run_arm(engine: str, *, duration_years: int, output_dir: Path, max_batch_replays: int) -> Path:
    # Journal opens its file in append mode (journal.py, §16.1's deliberate
    # append-only contract) -- a pre-existing run_dir must fail loudly rather
    # than silently concatenate two runs into one journal (run_v5_acceptance.py's
    # own already-learned lesson).
    run_dir = output_dir / f"sortition-{engine}-{duration_years}y"
    if run_dir.exists():
        raise FileExistsError(f"{run_dir} already exists -- remove it before re-running this arm.")
    run_dir.mkdir(parents=True)
    config = _config_for_v6b_run(
        engine, duration_years=duration_years, output_dir=run_dir / "run", max_batch_replays=max_batch_replays
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
        journal_path = run_simulation(config, run_id=f"sortition-{engine}-{duration_years}y", llm_client=None)
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
        "engine": engine, "duration_years": duration_years,
        "elapsed_seconds": round(elapsed, 1), "replay_count": replay_count,
    }
    metrics_path = run_dir / "metrics.json"
    metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    chamber = _compute_chamber_metrics(journal_path, config.run.total_ticks)
    chamber_path = run_dir / "chamber.json"
    chamber_path.write_text(json.dumps(chamber, indent=2), encoding="utf-8")

    recalls = metrics.recalls_by_trigger or {}
    total_recalls = sum(recalls.values())
    print(
        f"sortition/{engine}/{duration_years}y: {elapsed:.1f}s, {replay_count} replays, "
        f"recalls={total_recalls}, mean_legitimacy(last)={(metrics.mean_legitimacy or [(0, None)])[-1][1]}, "
        f"mandate_deviation(last)={(metrics.mandate_deviation or [(0, None)])[-1][1]}, "
        f"chamber_deviation(mean)={chamber['chamber_deviation_mean']:.4f}, "
        f"last_seated_size={chamber['last_seated_size']} "
        f"-- metrics={metrics_path}, chamber={chamber_path}"
    )
    if engine == "deterministic" and total_recalls > 6:
        print(
            "WARNING: this arm recalled more than 3x both/deterministic/8y's own committed anchor "
            "(2 recalls) -- inspect before committing to the expensive --engine llm run; sortition "
            "rotation is architecturally independent of the presidency, so it should not perturb "
            "this number at all.",
            file=sys.stderr,
        )
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

    log("# v6b acceptance run — elected vs. sortition (§6bis.3), Lot 4\n")
    log(
        "n=1 (one seed, no Monte Carlo band), the same limit every prior acceptance run in this "
        "project has already named. The elected side reuses `run_acceptance_comparison.py`'s own "
        "`both` arm shape (full pressure menu, legitimacy/mandate/awakening enabled) -- §6bis.3's "
        "own comparison is against a president \"soumise aux trois canaux du §7bis\", all three, "
        "not one isolated lever. `social_graph.enabled`/`events.enabled` stay OFF throughout, the "
        "same confound-avoidance call v5 Lot 5 and v6a Lot 4 already made independently. Unlike v6a "
        "Lot 4, this comparison needs BOTH quantities from the SAME run at the SAME ticks, so there "
        "is no prior acceptance row to cite -- this is one new, self-contained run.\n"
    )
    log(
        "| arm | engine | years | elapsed(s) | replays | mean L (last) | recalls | "
        "mandate_dev (mean/max) | chamber_dev (mean/max) | motif mix | last seated size |"
    )
    log("|---|---|---|---|---|---|---|---|---|---|---|")

    for path in metrics_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta = payload["_meta"]
        mean_l = payload["mean_legitimacy"]
        last_l = mean_l[-1][1] if mean_l else None
        deviation = payload["mandate_deviation"]
        dev_values = [v for _, v in deviation] if deviation else []
        dev_mean = sum(dev_values) / len(dev_values) if dev_values else None
        dev_max = max(dev_values) if dev_values else None
        recalls = payload["recalls_by_trigger"]
        chamber_path = path.parent / "chamber.json"
        chamber = json.loads(chamber_path.read_text(encoding="utf-8")) if chamber_path.is_file() else {}
        note = " (known 0.0, no LLM call)" if chamber.get("known_zero_by_construction") else ""
        log(
            f"| sortition | {meta['engine']} | {meta['duration_years']} | {meta['elapsed_seconds']} | "
            f"{meta['replay_count']} | {_fmt(last_l)} | {_fmt(recalls)} | "
            f"{_fmt(dev_mean)}/{_fmt(dev_max)} | "
            f"{_fmt(chamber.get('chamber_deviation_mean'))}/{_fmt(chamber.get('chamber_deviation_max'))}{note} | "
            f"{_fmt(chamber.get('chamber_motif_mix'))} | {_fmt(chamber.get('last_seated_size'))} |"
        )

    log("\n## §6bis.3's own headline question\n")
    log(
        "*« L'absence de pression électorale produit-elle des décisions plus « sincères » "
        "(alignées sur ses propres issue_positions) ou plus erratiques (aucun garde-fou de "
        "responsabilité) ? »*"
    )
    log(
        "- Compare `mandate_dev (mean/max)` against `chamber_dev (mean/max)` in the `llm` row above: "
        "a materially LOWER chamber_deviation than mandate_deviation is the signature of insulation "
        "producing more sincere (less drifted) decisions; a comparable or higher chamber_deviation "
        "would say the opposite -- that accountability pressure alone doesn't explain the elected "
        "side's own drift."
    )
    log(
        "- `motif mix` (701 SINCERE_POSITION vs 702 DELIBERATIVE_SHIFT) is the model's own stated "
        "label for each decision -- not enforced by any coherence rule (v6b Lot 3's own removed "
        "validator), so it is informative but non-binding: a chamber that stays mostly 701 is "
        "sincere by its own account; a chamber that trends toward 702 is not, independent of "
        "whether the resulting `chamber_deviation` values are themselves large or small."
    )
    log(
        "- `last_seated_size` cross-checks v6b Lot 2's own pool-exhaustion calibration finding "
        "(`sortition_calibration_results.md`) lands the same way inside a real LLM run: the chamber "
        "should stay at or near `seats=30` for the whole run once the relaxed-pool fallback engages."
    )
    log(
        "- **Not claimed here**: the sortition chamber's own institutional consequence (veto power, "
        "design doc point ouvert n°11) -- this MVP is comparison-only, with no lawmaking concept "
        "for a veto to act on."
    )

    if results_path is not None:
        results_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n(full report written to {results_path})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engine", choices=["llm", "deterministic"])
    parser.add_argument("--duration-years", type=int, default=8)
    parser.add_argument("--max-batch-replays", type=int, default=2)
    parser.add_argument("--output-dir", type=Path, default=Path("scripts/acceptance_v6b_runs"))
    parser.add_argument("--summarize", type=Path, help="render the results doc from every metrics.json under this dir")
    parser.add_argument("--results", type=Path, help="where --summarize writes the rendered markdown")
    args = parser.parse_args()

    if args.summarize:
        summarize(args.summarize, args.results)
        return 0

    if not args.engine:
        parser.error("--engine is required unless --summarize is given")

    run_arm(
        args.engine, duration_years=args.duration_years,
        output_dir=args.output_dir, max_batch_replays=args.max_batch_replays,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
