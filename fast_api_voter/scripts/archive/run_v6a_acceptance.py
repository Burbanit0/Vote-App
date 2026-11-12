"""
scripts/run_v6a_acceptance.py

v6a Lot 4's acceptance deliverable: the atomized-vs-contagion comparison §7bis.9f itself frames as a
table --

| Régime | Palier | f(contexte) inclut le voisinage ? | Cascade possible ? |
|---|---|---|---|
| Pression atomisée | v4 | Non | Non, par construction |
| Pression avec contagion | v6 | Oui | Oui |

-- and its own headline question: "une population isolée se mobilise-t-elle jamais, ou la contagion
sociale est-elle la condition nécessaire de toute mobilisation d'ampleur ?" That table names exactly
ONE variable that differs between regimes: whether the awakening threshold's f(contexte) includes the
neighborhood term. Not the pressure menu, not the exogenous-events config.

Only ONE new arm is run here. Confirmed by direct inspection: run_acceptance_comparison._config_for_arm
("mobilization_only", ...) never touches social_graph or events -- both stay at their shipped,
loaded defaults (social_graph.enabled: false, events.enabled: false). scripts/acceptance_v4_results.md's
own committed mobilization_only rows are therefore ALREADY, EXACTLY the "atomized" side of §7bis.9f's
own table, at this project's own standard seed (42) and scale (population_size=100). Cited verbatim
below (_V4_MOBILIZATION_ONLY_CITATION), never re-derived -- the same discipline indexer.py's own
module docstring states and v5 Lot 5 already used for its own `electoral_only` citation. This lot's
own contagion arm is the IDENTICAL config plus social_graph.enabled=True (shipped topology:
watts_strogatz, mean_degree=8, rewiring_prob=0.1 -- connected, exact mean degree 8.0 at n=100, v6 Lot
2's own measured property) and awakening.context_modulation.neighbors_acting=True.

Three deliberate choices, each independently justified (full reasoning in this lot's own plan,
merry-hugging-hamming.md):
- mobilization_only, not `both` or `petition_only`: neighbors_acting (v6 Lot 3) tracks EXCLUSIVELY
  PressureAct.MOBILIZE -- sign/launch never feed it. A menu that also includes petitions would add a
  second lever with its own confidence-vote/recall consequences unrelated to the contagion channel
  this lot isolates.
- Not `electoral_only`: under electoral_only, menu_acts={0,4} -- MOBILIZE is never a legal act, so
  neighbors_acting would be identically 0.0 for every citizen, every tick, by construction. The one
  arm this lot cannot use.
- events.enabled stays OFF: §7bis.9e's own "cascade needs a spark" claim was already separately and
  honestly demonstrated by v5 Lot 5, specifically in `electoral_only` BECAUSE mobilization/petition +
  elevated scandal_rate produced a near-permanent-vacancy pathology that crushed the very signal being
  measured. §7bis.9f's own table names exactly one variable; adding events reintroduces a confound
  this lot doesn't need to accept. Consequence, stated honestly: this run does not attempt a full,
  shock-triggered, Gilets-Jaunes-scale basculement (§7bis.9e's own three-ingredient claim) -- it
  isolates the narrower, well-defined marginal effect of the contagion channel alone.

Calibration-before-commit is a go/no-go CHECKPOINT here, not a sweep (unlike v5 Lot 5's own
--scandal-rate/--economy-sigma escalation loop): topology, modulation_amplitude, and the base
mobilization_only menu are all already-shipped, already-safe constants -- nothing here is tuned.
Run --engine deterministic first (near-free), compare its own recall count / final mean_legitimacy
against mobilization_only/deterministic/8y's own committed anchor (mean L 0.345, legitimacy_floor=2
recalls); proceed to --engine llm only if not qualitatively worse. If it IS worse, the one lever
available without expanding this lot's own scope is a reduced awakening.modulation_amplitude for this
run specifically -- named here, not built preemptively.

Wall-clock forecast (not a promise -- the real run reports its own elapsed time and its own max
per-tick consultation count, which is what actually lands in the results doc): mobilization_only/
llm/8y's own already-measured 6525.0s (acceptance_v4_results.md) is the closest real anchor, since
the config is identical apart from the graph; §7bis.9g's own "size for the peak, not the mean" risk
means the real number could run higher on a tick where contagion produces an unusually large
simultaneous cohort -- chunk_voters already handles this structurally (no cap, §15bis.1: a spike
costs time, not money), so the run completes either way.

Usage:
    # calibration dry-run, deterministic, seconds -- compare its own printed recall count against
    # mobilization_only/deterministic/8y's own committed anchor before proceeding
    python fast_api_voter/scripts/run_v6a_acceptance.py \\
        --engine deterministic --output-dir scripts/acceptance_v6a_runs

    # the real qwen3:8b arm, once the deterministic dry-run above looks safe
    python fast_api_voter/scripts/run_v6a_acceptance.py \\
        --engine llm --max-batch-replays 2 --output-dir scripts/acceptance_v6a_runs

    # render the committed results doc from both arms' metrics.json/contagion.json
    python fast_api_voter/scripts/run_v6a_acceptance.py \\
        --summarize scripts/acceptance_v6a_runs --results scripts/acceptance_v6a_results.md
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

# The two already-committed rows this script cites rather than re-derives --
# acceptance_v4_results.md's own mobilization_only rows, same seed/population_size/ambition_threshold/
# menu/duration, social_graph.enabled=False, events.enabled=False.
_V4_MOBILIZATION_ONLY_CITATION = (
    "| mobilization_only | deterministic | 8 | 0.0 | 0 | 0.345 | legitimacy_floor=2 | — (recorded) | "
    "0.507 | 0=0.511, 1=0.000, 2=0.000, 3=0.489, 4=0.000 | 1=0.000, 2=0.000, 3=0.000, 4=0.000 | —/— |\n"
    "| mobilization_only | llm | 8 | 6525.0 | 0 | 0.370 | legitimacy_floor=2 | 0.000 (ctx) | 0.000 | "
    "0=0.301, 1=0.000, 2=0.000, 3=0.699, 4=0.000 | 1=1.000, 2=0.000, 3=0.000, 4=0.000 | —/— |"
)


def _config_for_contagion_run(
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
        pressure_menu=dataclasses.replace(
            config.pressure_menu, electoral_only=False, petition_enabled=False, mobilization_enabled=True
        ),
        petition=config.petition,
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True),
        # events stays at its shipped default (enabled=False) -- deliberately,
        # see this module's own docstring.
        social_graph=dataclasses.replace(config.social_graph, enabled=True),
        awakening=dataclasses.replace(
            config.awakening,
            enabled=True,
            context_modulation=dataclasses.replace(config.awakening.context_modulation, neighbors_acting=True),
        ),
    )
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


def _compute_contagion_metrics(journal_path: Path, total_ticks: int) -> dict[str, Any]:
    """The one computation this lot needs that indexer.py doesn't already
    provide -- single consumer (this script), stays ad hoc here rather than
    becoming a new indexer.py/metrics.py row, per calibrate_*.py/
    run_v5_acceptance.py's own precedent.

    Iterates the FULL tick range (0..total_ticks inclusive), not just ticks
    that happen to have an event -- a tick with zero consultation is a real,
    informative zero (run_v5_acceptance._compute_spark's own already-learned
    lesson), not an absent observation.

    `mobilize_count` counts the DECIDED act (payload["act"], matching
    pressure_lever_mix's own already-established "decided, not applied"
    convention), not the applied one -- consistent with every other metric
    this run cites."""
    consulted_by_tick: dict[int, int] = {}
    mobilized_by_tick: dict[int, int] = {}
    neighbors_acting_values: list[float] = []
    for event in read_journal(journal_path):
        if event["event_type"] != "pressure_action":
            continue
        tick = event["tick"]
        consulted_by_tick[tick] = consulted_by_tick.get(tick, 0) + 1
        if event["payload"].get("act") == 3:  # PressureAct.MOBILIZE
            mobilized_by_tick[tick] = mobilized_by_tick.get(tick, 0) + 1
        ctx = event["payload"].get("ctx")
        if ctx is not None and ctx.get("neighbors_acting") is not None:
            neighbors_acting_values.append(ctx["neighbors_acting"])

    all_ticks = range(total_ticks + 1)
    consultation_counts = [consulted_by_tick.get(tick, 0) for tick in all_ticks]
    mobilization_counts = [mobilized_by_tick.get(tick, 0) for tick in all_ticks]

    return {
        "mean_consultation_per_tick": sum(consultation_counts) / len(consultation_counts),
        "max_consultation_per_tick": max(consultation_counts),
        "mean_mobilization_per_tick": sum(mobilization_counts) / len(mobilization_counts),
        "max_mobilization_per_tick": max(mobilization_counts),
        "mean_realized_neighbors_acting": (
            sum(neighbors_acting_values) / len(neighbors_acting_values) if neighbors_acting_values else None
        ),
        "max_realized_neighbors_acting": max(neighbors_acting_values) if neighbors_acting_values else None,
    }


def run_arm(engine: str, *, duration_years: int, output_dir: Path, max_batch_replays: int) -> Path:
    # Journal opens its file in append mode (journal.py, §16.1's deliberate
    # append-only contract) -- a pre-existing run_dir must fail loudly rather
    # than silently concatenate two runs into one journal (run_v5_acceptance.py's
    # own already-learned lesson).
    run_dir = output_dir / f"contagion-{engine}-{duration_years}y"
    if run_dir.exists():
        raise FileExistsError(f"{run_dir} already exists -- remove it before re-running this arm.")
    run_dir.mkdir(parents=True)
    config = _config_for_contagion_run(
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
        journal_path = run_simulation(config, run_id=f"contagion-{engine}-{duration_years}y", llm_client=None)
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

    contagion = _compute_contagion_metrics(journal_path, config.run.total_ticks)
    contagion_path = run_dir / "contagion.json"
    contagion_path.write_text(json.dumps(contagion, indent=2), encoding="utf-8")

    recalls = metrics.recalls_by_trigger or {}
    total_recalls = sum(recalls.values())
    print(
        f"contagion/{engine}/{duration_years}y: {elapsed:.1f}s, {replay_count} replays, "
        f"recalls={total_recalls}, mean_legitimacy(last)={(metrics.mean_legitimacy or [(0, None)])[-1][1]}, "
        f"max_consultation_per_tick={contagion['max_consultation_per_tick']}, "
        f"max_mobilization_per_tick={contagion['max_mobilization_per_tick']} "
        f"-- metrics={metrics_path}, contagion={contagion_path}"
    )
    if engine == "deterministic" and total_recalls > 6:
        print(
            "WARNING: this arm recalled more than 3x mobilization_only/deterministic/8y's own "
            "committed anchor (2 recalls) -- inspect before committing to the expensive --engine llm "
            "run; see this lot's own plan for the documented modulation_amplitude fallback.",
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

    log("# v6a acceptance run — atomized vs. contagion (§7bis.9f), Lot 4\n")
    log(
        "n=1 (one seed, no Monte Carlo band), the same limit v4 Lot 8's own acceptance run already "
        "named. Isolates §7bis.9f's own one-variable comparison — whether the awakening threshold's "
        "f(contexte) includes the neighborhood term — on top of an already-mobilization-capable "
        "population. `events.enabled` stays OFF throughout: v5 Lot 5 already separately demonstrated "
        "the \"spark\" claim, and adding it here would reintroduce a second simultaneously-changing "
        "variable §7bis.9f's own table doesn't ask for. **Not claimed here**: a full, shock-triggered, "
        "Gilets-Jaunes-scale basculement (§7bis.9e's own three-ingredient claim, v4+v5+v6 together) — "
        "that composite run was never executed.\n"
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
            f"| contagion | {meta['engine']} | {meta['duration_years']} | {meta['elapsed_seconds']} | "
            f"{meta['replay_count']} | {_fmt(last_l)} | {_fmt(recalls)} | "
            f"{_fmt(last_dev)} ({payload['mandate_deviation_source'] or '—'}) | {_fmt(last_inaction)} | "
            f"{_fmt(payload['pressure_lever_mix'])} | {_fmt(payload['stance_distribution'])} | "
            f"{_fmt(payload['petition_success_rate'])}/{_fmt(payload['petition_removal_rate'])} |"
        )

    log("\n## Atomized reference (v4 Lot 8, `scripts/acceptance_v4_results.md`, NOT re-run here)\n")
    log(
        "| arm | engine | years | elapsed(s) | replays | mean L (last) | recalls | "
        "mandate_dev (last, src) | inaction_rate (last) | lever mix | stance mix | "
        "petition success/removal |"
    )
    log("|---|---|---|---|---|---|---|---|---|---|---|---|")
    log(_V4_MOBILIZATION_ONLY_CITATION)
    log(
        "\nSame seed (42), same `population_size` (100), same `ambition_threshold` (0.0), same "
        "`mobilization_only` menu, same duration (8y), same `legitimacy`/`mandate`/`awakening` "
        "enabled — differing only in `social_graph.enabled`/`awakening.context_modulation."
        "neighbors_acting`. Cited verbatim, not re-derived."
    )

    log("\n## Contagion metrics (v6 Lot 3's own `neighbors_acting`, not in `RunMetrics`)\n")
    log("| arm | engine | mean consult./tick | max consult./tick | mean mobilize/tick | max mobilize/tick | mean realized neighbors_acting | max realized neighbors_acting |")
    log("|---|---|---|---|---|---|---|---|")
    for path in metrics_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta = payload["_meta"]
        contagion_path = path.parent / "contagion.json"
        contagion = json.loads(contagion_path.read_text(encoding="utf-8")) if contagion_path.is_file() else {}
        log(
            f"| contagion | {meta['engine']} | {_fmt(contagion.get('mean_consultation_per_tick'))} | "
            f"{_fmt(contagion.get('max_consultation_per_tick'))} | "
            f"{_fmt(contagion.get('mean_mobilization_per_tick'))} | "
            f"{_fmt(contagion.get('max_mobilization_per_tick'))} | "
            f"{_fmt(contagion.get('mean_realized_neighbors_acting'))} | "
            f"{_fmt(contagion.get('max_realized_neighbors_acting'))} |"
        )

    log("\n## §7bis.9f's own headline question\n")
    log(
        "*« Une population isolée se mobilise-t-elle jamais, ou la contagion sociale est-elle la "
        "condition nécessaire de toute mobilisation d'ampleur ? »*"
    )
    log(
        "- Compare the `lever mix` `3=` (MOBILIZE) share and the `recalls` column between the "
        "contagion row above and the atomized reference — a materially higher mobilize share and/or "
        "recall count under contagion is the signature of the neighborhood term actually amplifying "
        "collective action, not just individual decisions."
    )
    log(
        "- Compare `max mobilize/tick` (this run's own new metric, absent from the atomized "
        "reference) against the run's own `mean mobilize/tick` — the ratio is the size of any single "
        "tick's own collective spike, the closest this lot gets to observing a bandwagon moment "
        "without claiming a full cascade."
    )
    log(
        "- `mean/max realized neighbors_acting` confirms the channel was genuinely active and "
        "non-degenerate in this run, not just theoretically wired."
    )

    if results_path is not None:
        results_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n(full report written to {results_path})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engine", choices=["llm", "deterministic"])
    parser.add_argument("--duration-years", type=int, default=8)
    parser.add_argument("--max-batch-replays", type=int, default=2)
    parser.add_argument("--output-dir", type=Path, default=Path("scripts/acceptance_v6a_runs"))
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
