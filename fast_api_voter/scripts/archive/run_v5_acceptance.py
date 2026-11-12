"""
scripts/run_v5_acceptance.py

v5 Lot 5's acceptance deliverable: a single dedicated run, atop the
already-enabled v4 palier, with `events.enabled=True` -- verifying the
narrow, honest half of §7bis.9e's "spark" claim that v5 can actually
demonstrate: a shock tick produces a punctual, visible consultation-rate
spike, distinct in kind from v4's own gradual, monotonic mandate-deviation
erosion, in the SAME run. A full Gilets-Jaunes-style cascade is explicitly
NOT claimed here -- §7bis.9e's own text says that needs v6's social graph
too ("n'est pas atteignable avant v6"); this script never asserts otherwise.

Arm: `electoral_only`, not "both" -- corrected DURING this lot's own
implementation, against a real measured result, not assumed in advance.
A first attempt at "both" (petition+mobilization) recalled the president
within 1-2 ticks of nearly every election under a tuned, elevated
scandal_rate (the same street_pressure amplification v4 Lot 4 already
measured, now compounded by more consulted citizens from a lowered
awakening threshold), leaving the office vacant ~82% of an 8-year
deterministic dry run -- most scandal ticks landed during a vacancy, where
select_consulted never runs at all, crushing the very signal this lot exists
to observe. `electoral_only` is v4's own designated CONTROL arm (THEORY.md
§10.5): no petition/mobilization means no écart(t) pressure term beyond
passive_erosion_weight (shipped 0.0), so the office stays continuously
occupied for the whole run. select_consulted (the awakening gate) still
runs every tick regardless of menu -- only the ACT a consulted citizen may
choose is restricted (menu_acts={0,4}) -- so consultation COUNTS, the thing
this lot measures, are unaffected by the menu choice, and this arm removes
the vacancy confound entirely. `mandate.enabled=True` still runs dt=6 every
presided tick regardless of menu, so the "gradual erosion" half of the
claim is unaffected by this choice either.

Reuses `electoral_only`/`llm`/`8y` from `scripts/acceptance_v4_results.md`
(v4 Lot 8) as the "no spark" reference row -- same seed (42), same
population_size (100), same ambition_threshold (0.0), same menu, same
duration, same legitimacy/mandate/awakening -- differing only in
`events.enabled`. That row is NOT re-run here; it is cited verbatim by
--summarize, the same "don't re-derive already-committed evidence"
discipline indexer.py's own docstring already states for
calibrate_awakening.py/calibrate_petition.py.

Follows run_acceptance_comparison.py's own conventions (module docstring
stating the question, real run_simulation on the real production path, not
in CI, --run/--summarize split so a multi-hour LLM run's failure doesn't cost
a re-render of already-computed results) with one addition specific to this
lot: --scandal-rate/--economy-sigma are CLI-overridable so the tuned `events`
config can be calibrated via a cheap `--run deterministic` dry-run BEFORE the
expensive `--run llm` arm is committed to. The shipped `events` config
essentially never fires within a short run (scripts/events_calibration_results.md
measured ZERO economic_shock_tick crossings at shipped (phi=0.8, sigma=0.1,
threshold=0.5) over a full 121-tick run -- the threshold sits ~3 steady-state
std away); the starting values below put the threshold within 1.5 std,
expected to fire a handful of times over an 8-year (33-tick) window, but the
REAL fired counts (not this estimate) are what the deterministic dry-run
reports and what the results doc records.

Wall-clock forecast (not a promise -- the real run reports its own elapsed
time): `electoral_only`/`llm`/`8y` is v4's own MOST expensive arm --
11776.3s (~196 min, acceptance_v4_results.md) -- because it never recalls,
so every tick keeps consulting the same standing population (the
counter-intuitive finding v4 Lot 7's own residual risks already flagged:
"the control arm is the most expensive one"). Lot 4's own reliability spike
measured real reaction_to_event chunks of size 25 at ~80-90s
(lot4_reaction_reliability_results.md); at population_size=100/
max_batch_size=25, one firing tick costs 4 chunks (~340s). At the starting
tuning (scandal_rate_per_tick=0.15, expected ~4.95 fires; economy_ar1_sigma=0.2,
expected ~4.4 fires over 33 ticks), that's ~53 min added -- forecast total
~4.15h for this lot's own LLM arm.

Usage:
    # calibration dry-run, deterministic, seconds -- inspect the printed
    # scandal/shock counts; escalate --scandal-rate/--economy-sigma by 0.05
    # steps if either count is below 2, then re-run before proceeding
    python fast_api_voter/scripts/run_v5_acceptance.py \\
        --run deterministic --scandal-rate 0.15 --economy-sigma 0.2 \\
        --output-dir scripts/acceptance_v5_runs

    # the real qwen3:8b arm, once the deterministic dry-run above confirms
    # both generators fire at least twice in the 8-year window
    python fast_api_voter/scripts/run_v5_acceptance.py \\
        --run llm --scandal-rate 0.15 --economy-sigma 0.2 \\
        --max-batch-replays 2 --output-dir scripts/acceptance_v5_runs

    # render the committed results doc from both arms' metrics.json/spark.json
    python fast_api_voter/scripts/run_v5_acceptance.py \\
        --summarize scripts/acceptance_v5_runs --results scripts/acceptance_v5_results.md
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
from api.domain.polity.metrics import consultation_rate  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402

# The one already-committed number this script cites rather than re-derives
# -- acceptance_v4_results.md's own `electoral_only`/`llm`/`8y` row, same
# seed/population_size/ambition_threshold/menu/duration, events.enabled=False.
_V4_BASELINE_CITATION = (
    "electoral_only | llm | 8 | 11776.3 | 0 | 0.710 |  | 0.000 (ctx) | 0.343 | "
    "0=0.112, 1=0.000, 2=0.000, 3=0.000, 4=0.888 | 1=0.061, 2=0.000, 3=0.939, 4=0.000 | —/—"
)


def _config_for_v5_run(
    engine: str, *, duration_years: int, output_dir: Path, scandal_rate: float,
    economy_sigma: float, max_batch_replays: int,
) -> PolityConfig:
    config = load_config()
    config = dataclasses.replace(
        config,
        journal=dataclasses.replace(config.journal, output_dir=str(output_dir)),
        candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0),
        run=dataclasses.replace(config.run, duration_years=duration_years),
        legitimacy=dataclasses.replace(config.legitimacy, enabled=True),
        awakening=dataclasses.replace(
            config.awakening,
            enabled=True,
            context_modulation=dataclasses.replace(config.awakening.context_modulation, event_salience=True),
        ),
        mandate=dataclasses.replace(config.mandate, enabled=True),
        # electoral_only, not "both" -- verified live during this lot's own
        # dry run: "both" (petition+mobilization) recalls the president
        # within 1-2 ticks of nearly every election under a tuned, elevated
        # scandal_rate (the same 33.3x street_pressure amplification v4 Lot
        # 4 already measured, now compounded by more consulted citizens),
        # leaving the office vacant ~82% of an 8-year run -- most scandal
        # ticks land during a vacancy, where select_consulted never runs at
        # all, which crushes the very signal this lot exists to observe.
        # electoral_only is v4's own designated CONTROL arm (THEORY.md
        # §10.5): no petition/mobilization means no écart(t) pressure term
        # beyond passive_erosion_weight (shipped 0.0), so the office stays
        # continuously occupied for the whole run. select_consulted (the
        # awakening gate) still runs every tick regardless of menu -- only
        # the ACT a consulted citizen may choose is restricted (menu_acts
        #={0,4}) -- so consultation COUNTS, the thing this lot measures,
        # are unaffected by the menu choice, and this arm removes the
        # vacancy confound entirely.
        pressure_menu=dataclasses.replace(
            config.pressure_menu, electoral_only=True, petition_enabled=False, mobilization_enabled=False
        ),
        petition=config.petition,
        street_pressure=config.street_pressure,
        events=dataclasses.replace(
            config.events,
            enabled=True,
            scandal_enabled=True,
            scandal_rate_per_tick=scandal_rate,
            economic_shock_enabled=True,
            economy_ar1_sigma=economy_sigma,
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
        "petition_downgrades": metrics.petition_downgrades,
        "petition_success_rate": metrics.petition_success_rate,
        "petition_removal_rate": metrics.petition_removal_rate,
        "stance_distribution": metrics.stance_distribution,
    }


def _compute_spark(journal_path: Path, population_size: int, total_ticks: int) -> dict[str, Any]:
    """The one computation this lot needs that indexer.py doesn't already
    provide -- consultation count per tick, cross-referenced against
    scandal_occurred/economic_shock_tick tick numbers. Single consumer (this
    script), so it stays ad hoc here rather than becoming a new indexer.py/
    metrics.py row, per calibrate_awakening.py/calibrate_petition.py's own
    precedent. Reuses the already-shipped, generic
    metrics.consultation_rate(consulted, population_size) directly.

    Iterates the FULL tick range (0..total_ticks inclusive), not just the
    ticks that happen to have a pressure_action event -- a tick with zero
    consultation (no citizen crossed the awakening gate that tick) is a
    real, informative zero, not an absent observation, and averaging only
    over ticks that already have data would silently drop every such zero
    from the "quiet" baseline, inflating it. Caught live during this lot's
    own first (mis-scoped "both") dry run, where most ticks were vacant."""
    events = list(read_journal(journal_path))
    consulted_by_tick: dict[int, int] = {}
    firing_ticks: set[int] = set()
    scandal_count = 0
    shock_count = 0
    for event in events:
        if event["event_type"] == "pressure_action":
            tick = event["tick"]
            consulted_by_tick[tick] = consulted_by_tick.get(tick, 0) + 1
        elif event["event_type"] == "scandal_occurred":
            firing_ticks.add(event["tick"])
            scandal_count += 1
        elif event["event_type"] == "economic_shock_tick":
            firing_ticks.add(event["tick"])
            shock_count += 1

    all_ticks = range(total_ticks + 1)
    firing_rates = [
        consultation_rate(consulted_by_tick.get(tick, 0), population_size)
        for tick in all_ticks if tick in firing_ticks
    ]
    quiet_rates = [
        consultation_rate(consulted_by_tick.get(tick, 0), population_size)
        for tick in all_ticks if tick not in firing_ticks
    ]

    firing_mean = sum(firing_rates) / len(firing_rates) if firing_rates else None
    quiet_mean = sum(quiet_rates) / len(quiet_rates) if quiet_rates else None
    ratio = (firing_mean / quiet_mean) if firing_mean is not None and quiet_mean not in (None, 0.0) else None

    return {
        "scandal_count": scandal_count,
        "shock_count": shock_count,
        "firing_ticks": sorted(firing_ticks),
        "firing_mean_consultation_rate": firing_mean,
        "quiet_mean_consultation_rate": quiet_mean,
        "ratio": ratio,
    }


def run_arm(
    engine: str, *, duration_years: int, scandal_rate: float, economy_sigma: float,
    output_dir: Path, max_batch_replays: int,
) -> Path:
    # scandal_rate/economy_sigma in the dir name: Journal opens its file in
    # append mode ("a", journal.py -- deliberate, §16.1's append-only
    # contract), so two invocations sharing one run_dir would silently
    # concatenate two runs into one journal rather than overwriting --
    # caught live during this lot's own calibration dry-run, where a second
    # invocation at a bumped economy_sigma landed in the same default
    # run_dir as the first and doubled every tick's event count. Distinct
    # tuning values now always get a distinct, fresh directory.
    run_dir = output_dir / f"electoral_only-{engine}-{duration_years}y-events-r{scandal_rate}-s{economy_sigma}"
    if run_dir.exists():
        raise FileExistsError(
            f"{run_dir} already exists -- Journal appends rather than overwrites; remove it or "
            "pick different --scandal-rate/--economy-sigma values before re-running this arm."
        )
    run_dir.mkdir(parents=True)
    config = _config_for_v5_run(
        engine, duration_years=duration_years, output_dir=run_dir / "run",
        scandal_rate=scandal_rate, economy_sigma=economy_sigma, max_batch_replays=max_batch_replays,
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
        journal_path = run_simulation(
            config, run_id=f"electoral_only-{engine}-{duration_years}y-events", llm_client=None
        )
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
        "engine": engine, "duration_years": duration_years, "scandal_rate": scandal_rate,
        "economy_sigma": economy_sigma, "elapsed_seconds": round(elapsed, 1), "replay_count": replay_count,
    }
    metrics_path = run_dir / "metrics.json"
    metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    spark = _compute_spark(journal_path, config.run.population_size, config.run.total_ticks)
    spark_path = run_dir / "spark.json"
    spark_path.write_text(json.dumps(spark, indent=2), encoding="utf-8")

    print(
        f"{engine}/{duration_years}y: {elapsed:.1f}s, {replay_count} replays, "
        f"scandals={spark['scandal_count']}, shocks={spark['shock_count']}, "
        f"firing_mean_consultation={spark['firing_mean_consultation_rate']}, "
        f"quiet_mean_consultation={spark['quiet_mean_consultation_rate']} "
        f"-- metrics={metrics_path}, spark={spark_path}"
    )
    if engine == "deterministic" and (spark["scandal_count"] < 2 or spark["shock_count"] < 2):
        print(
            "WARNING: fewer than 2 of one event type fired in this calibration dry-run -- "
            "escalate --scandal-rate/--economy-sigma by +0.05 and re-run before committing "
            "to the expensive --run llm arm.",
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

    log("# v5 acceptance run — the \"spark\" (§7bis.9e), events atop the v4 `electoral_only` control arm (Lot 5)\n")
    log(
        "n=1 (one seed, no Monte Carlo band), same limit as v4 Lot 8's own acceptance run. Verifies "
        "the narrow claim v5 can actually demonstrate: a shock tick's consultation-rate spike, "
        "distinct from v4's own gradual mandate-deviation erosion, in the same run. A full cascade "
        "needs v6's social graph too (§7bis.9e: \"n'est pas atteignable avant v6\") — not claimed here.\n"
    )
    log(
        "| arm | engine | years | elapsed(s) | replays | scandal_rate | economy_sigma | mean L (last) | "
        "recalls | mandate_dev (last, src) | lever mix | scandals | shocks | firing consult. | "
        "quiet consult. | ratio |"
    )
    log("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

    for path in metrics_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta = payload["_meta"]
        spark_path = path.parent / "spark.json"
        spark = json.loads(spark_path.read_text(encoding="utf-8")) if spark_path.is_file() else {}
        mean_l = payload["mean_legitimacy"]
        last_l = mean_l[-1][1] if mean_l else None
        deviation = payload["mandate_deviation"]
        last_dev = deviation[-1][1] if deviation else None
        recalls = payload["recalls_by_trigger"]
        log(
            f"| electoral_only | {meta['engine']} | {meta['duration_years']} | {meta['elapsed_seconds']} | "
            f"{meta['replay_count']} | {meta['scandal_rate']} | {meta['economy_sigma']} | "
            f"{_fmt(last_l)} | {_fmt(recalls)} | {_fmt(last_dev)} ({payload['mandate_deviation_source'] or '—'}) | "
            f"{_fmt(payload['pressure_lever_mix'])} | {_fmt(spark.get('scandal_count'))} | "
            f"{_fmt(spark.get('shock_count'))} | {_fmt(spark.get('firing_mean_consultation_rate'))} | "
            f"{_fmt(spark.get('quiet_mean_consultation_rate'))} | {_fmt(spark.get('ratio'))} |"
        )

    log("\n## No-spark reference (v4 Lot 8, `scripts/acceptance_v4_results.md`, NOT re-run here)\n")
    log(
        "| arm | engine | years | elapsed(s) | replays | mean L (last) | recalls | "
        "mandate_dev (last, src) | inaction_rate (last) | lever mix | stance mix | "
        "petition success/removal |"
    )
    log("|---|---|---|---|---|---|---|---|---|---|---|---|")
    log(f"| {_V4_BASELINE_CITATION} |")
    log(
        "\nSame seed (42), same `population_size` (100), same `ambition_threshold` (0.0), same full "
        "menu, same duration (8y), same `legitimacy`/`mandate`/`awakening` enabled — differing only "
        "in `events.enabled`. Cited verbatim, not re-derived (see `indexer.py`'s own module docstring "
        "for why the shipped calibration/acceptance evidence is never re-run through new code)."
    )

    log("\n## The spark claim\n")
    log(
        "- **Punctual, not gradual**: compare `firing consult.` against `quiet consult.` in the "
        "table above — the ratio column is the size of the spike. A shock tick's consultation rate "
        "should measurably exceed the run's own quiet-tick average."
    )
    log(
        "- **Distinct from v4's own erosion, in the same run**: `mandate_dev` is dt=6's own gradual, "
        "monotonic-ish drift (already documented in `THEORY.md` §10.4/§10.7) — read its full series "
        "from this run's own `metrics.json` (`mandate_deviation`) alongside the punctual spikes "
        "above; the two should read as two different shapes off one journal, not two journals "
        "compared to each other."
    )
    log(
        "- **Not a cascade**: `neighbors_acting` stays structurally `null` through v5 — no citizen "
        "sees another citizen's action, so nothing here demonstrates collective bandwagon behavior. "
        "That remains v6 scope (§7bis.9e)."
    )

    if results_path is not None:
        results_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n(full report written to {results_path})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", choices=["llm", "deterministic"])
    parser.add_argument("--duration-years", type=int, default=8)
    parser.add_argument("--scandal-rate", type=float, default=0.15)
    parser.add_argument("--economy-sigma", type=float, default=0.2)
    parser.add_argument("--max-batch-replays", type=int, default=2)
    parser.add_argument("--output-dir", type=Path, default=Path("scripts/acceptance_v5_runs"))
    parser.add_argument("--summarize", type=Path, help="render the results doc from every metrics.json under this dir")
    parser.add_argument("--results", type=Path, help="where --summarize writes the rendered markdown")
    args = parser.parse_args()

    if args.summarize:
        summarize(args.summarize, args.results)
        return 0

    if not args.run:
        parser.error("--run is required unless --summarize is given")

    run_arm(
        args.run, duration_years=args.duration_years, scandal_rate=args.scandal_rate,
        economy_sigma=args.economy_sigma, output_dir=args.output_dir, max_batch_replays=args.max_batch_replays,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
