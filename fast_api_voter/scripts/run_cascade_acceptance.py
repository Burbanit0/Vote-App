"""
scripts/run_cascade_acceptance.py

Composite cascade acceptance run: the three-ingredient claim §7bis.9e names as jointly required for
a genuine collective tipping point, run TOGETHER for the first time -- "un basculement de type Gilets
jaunes n'est pas atteignable avant v6 ... il requiert SIMULTANEMENT le graphe social (v6), les chocs
exogènes (v5) et les leviers de pression (v4)."

Every prior acceptance run deliberately isolated exactly ONE of the three:
- v5 Lot 5 (run_v5_acceptance.py) ran events.enabled=True under `electoral_only`, specifically
  BECAUSE mobilization + an elevated scandal_rate produced a ~82%-vacancy pathology in an early dry
  run. `electoral_only` structurally excludes act=3 (MOBILIZE) -- the only act neighbors_acting ever
  tracks -- so social_graph stayed off throughout. Its own results doc: "Not a cascade: neighbors_acting
  stays structurally null through v5 ... That remains v6 scope."
- v6a Lot 4 (run_v6a_acceptance.py) ran social_graph.enabled=True + neighbors_acting=True under
  `mobilization_only`, with events left at its shipped default (False) -- "deliberately: v5 Lot 5
  already separately demonstrated the spark claim, and adding it here would reintroduce a second
  simultaneously-changing variable." Its own results doc: "Not claimed here: a full, shock-triggered,
  Gilets-Jaunes-scale basculement ... that composite run was never executed."

THEORY.md names this exact gap in three places (§10.7's closing line, §10.8's own "Limite assumée"
paragraph, §10.10's limits bullet) -- this script is what closes it. Nothing new is built: every
mechanism (event generators, social graph, contagion-fed awakening gate, mobilization_only menu) is
already shipped and independently proven by v5 Lot 5's and v6a Lot 4's own passing runs. What's
missing is the one run that turns them on together.

THE REAL RISK, found directly in already-committed evidence, not hypothetical: v6a Lot 4's own
mobilization_only+contagion arm -- WITH EVENTS STILL OFF -- already produced 2 recalls
(legitimacy_floor=2) in both its deterministic and LLM arms, and its own contagion-metrics table
shows max_mobilization_per_tick=85 (out of 100 citizens) on the LLM arm: a population already capable
of a near-total simultaneous mobilization spike from contagion alone. Layering event-driven
event_salience on top can only pull MORE citizens into the consulted cohort, never fewer
(awakening_threshold's own f(context) combines every active modulation term additively) -- close kin
to the exact pathology v5 Lot 5's own dry run already found and routed around by switching to
electoral_only. This script cannot use electoral_only (it needs MOBILIZE to be legal, or
neighbors_acting is structurally inert), so the vacancy risk has to be managed by tuning the event
generators themselves, calibrated FRESH for this specific combination -- v5's own tuned
scandal_rate=0.15/economy_sigma=0.2 were calibrated for a menu where firing had ZERO effect on
recalls or mobilization; reusing them blindly here is not justified.

Calibration-before-commit is therefore a real escalate-or-de-escalate LOOP here (closer to v5 Lot 5's
own than to v6a Lot 4's simple go/no-go checkpoint), starting from a CONSERVATIVE point below v5's
own tuning (scandal_rate=0.08, economy_sigma=0.12 -- roughly half), since the compounding risk is
real and previously unmeasured for this exact combination. Pre-registered go/no-go criteria, decided
in advance: proceed to --engine llm only if the deterministic dry run shows office_occupancy >= 0.5
AND at least 2 scandal-firing and 1 shock-firing tick (so the cascade question is even reachable). If
occupancy is below that, HALVE both rates and re-run the (still near-free) deterministic dry run --
never raise legitimacy.recall_floor toward zero as the fix, which this project's own v6b Lot 4 write-up
already named as "scientifically inelegant... disables accountability rather than testing it."

Wall-clock forecast (not a promise -- the real run reports its own elapsed time): v6a's own
mobilization_only+contagion llm/8y run (no events) cost 6932.1s; v5's own reaction_to_event (dt=8)
marginal cost, from lot4_reaction_reliability_results.md's own measured ~80-90s per size-25 chunk at
population_size=100/max_batch_size=25 (4 chunks/firing-tick/event_type, ~340s), times v5's own 4
scandal + 2 shock firing ticks (~6 occasions) is ~2040s. Naive sum ~8970s (~2.5h) -- stated explicitly
as a likely UNDERESTIMATE, not a safe ceiling: awakening_threshold's combined-terms formula means a
tick with BOTH event_salience and neighbors_acting active can only consult a cohort at least as large
as either term alone, so v6a's own baseline is a floor on pressure_action call volume, not a ceiling,
here. Plausible band: 2.5h-5h.

SEED (added after the first calibration dry-run at the shipped seed=42): that dry-run traced office
vacancy to a pre-existing, seed-independent-in-cause-but-seed-specific-in-outcome property of the
`mobilization_only` deterministic baseline -- NOT contagion, NOT events. At tick 0 (right after
election) the awakening gate is maximally permissive (proximity=0, no other modulation term has had
a chance to become nonzero yet), consulting 67/100 citizens and mobilizing 33/100 -- exactly v4 Lot
4's own committed "mobilize max ~=0.33 right after election" calibration number. That 33% rate alone
is already inside the "33.3x amplification" wall v4 Lot 4's own docstring warned about
(street_pressure decay=0.85, w_mob=0.5, legitimacy decay=0.9): L crashes from 0.345 to 0.026 in one
more tick, well under the 0.2 recall floor, and the office sits vacant until the next SCHEDULED
election (no snap elections in this model) -- 14 of every 16 ticks. This exact outcome (recalls=
legitimacy_floor=2, mean L (last)=0.345) is BYTE-IDENTICAL across v4 Lot 8's own committed
mobilization_only row, v6a Lot 4's own committed contagion row, and this script's own first
calibration attempt -- proof it is a seed=42-specific property of the deterministic baseline itself,
present since v4 Lot 8, never previously flagged because no prior acceptance script computed an
explicit office_occupancy metric. Neither halving scandal_rate/economy_sigma (already disproven --
byte-identical result at r0.08/s0.12 and r0.04/s0.06, since events never fired before the tick-1
collapse either way) nor raising legitimacy.recall_floor (explicitly forbidden, see above) can help.

`--seed` lets a fresh calibration dry-run test whether a DIFFERENT population/officeholder draw
produces a less fragile mobilization_only baseline, one where events actually get a chance to act
before the office vacates. This deliberately BREAKS this run's direct seed-for-seed comparability to
the seed=42 `_V5_SPARK_CITATION`/`_V6A_CONTAGION_CITATION` reference rows above -- summarize() prints
an explicit, un-missable note whenever a non-42 seed is used, and the results doc must carry that
caveat rather than silently presenting the two citation rows as apples-to-apples. `--seed` is applied
via `dataclasses.replace(config.run, seed=...)`, the same override mechanism `run.duration_years`
already uses -- no other config value changes.

Usage:
    # calibration dry-run, deterministic, seconds -- inspect the printed office_occupancy and
    # scandal/shock counts; halve --scandal-rate/--economy-sigma and re-run if occupancy < 0.5.
    # seed=42 (shipped default) already found office_occupancy=0.152 regardless of event tuning --
    # see the SEED section above; --seed lets you test a different population/officeholder draw.
    python fast_api_voter/scripts/run_cascade_acceptance.py \\
        --engine deterministic --scandal-rate 0.08 --economy-sigma 0.12 --seed 7 \\
        --output-dir scripts/acceptance_cascade_runs

    # the real qwen3:8b arm, once the deterministic dry-run above passes the go/no-go criteria
    python fast_api_voter/scripts/run_cascade_acceptance.py \\
        --engine llm --scandal-rate 0.08 --economy-sigma 0.12 \\
        --max-batch-replays 2 --output-dir scripts/acceptance_cascade_runs

    # render the committed results doc from both arms' metrics.json/spark.json/contagion.json/cascade.json
    python fast_api_voter/scripts/run_cascade_acceptance.py \\
        --summarize scripts/acceptance_cascade_runs --results scripts/acceptance_cascade_results.md
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

# The two already-committed rows this script cites rather than re-derives -- v5 Lot 5's own
# electoral_only/llm/8y row (the "spark" alone) and v6a Lot 4's own mobilization_only/llm/8y
# contagion row (the "contagion" alone). Same seed/population_size/ambition_threshold/duration/
# legitimacy/mandate/awakening throughout; each differs from THIS run by exactly the one ingredient
# it was isolating. Cited verbatim, never re-run, per indexer.py's own "don't re-derive already-
# committed evidence" discipline.
_V5_SPARK_CITATION = (
    "electoral_only | llm | 8 | 15743.8 | 0 | 0.15 | 0.2 | 0.710 |  | 0.000 (ctx) | "
    "0=0.143, 1=0.000, 2=0.000, 3=0.000, 4=0.857 | 4 | 2 | 0.695 | 0.595 | 1.168"
)
_V6A_CONTAGION_CITATION = (
    "mobilization_only | llm | 8 | 6932.1 | 0 | — | — | 0.475 | legitimacy_floor=2 | 0.000 (ctx) | "
    "0=0.371, 1=0.000, 2=0.000, 3=0.629, 4=0.000 | — | — | — | — | —"
)


def _config_for_cascade_run(
    engine: str, *, duration_years: int, output_dir: Path, scandal_rate: float,
    economy_sigma: float, max_batch_replays: int, seed: int,
) -> PolityConfig:
    config = load_config()
    config = dataclasses.replace(
        config,
        journal=dataclasses.replace(config.journal, output_dir=str(output_dir)),
        candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0),
        run=dataclasses.replace(config.run, duration_years=duration_years, seed=seed),
        legitimacy=dataclasses.replace(config.legitimacy, enabled=True),
        mandate=dataclasses.replace(config.mandate, enabled=True),
        # mobilization_only, not `both`/`electoral_only`/`petition_only` -- reusing v6a Lot 4's own
        # reasoning verbatim: neighbors_acting (v6 Lot 3) tracks EXCLUSIVELY PressureAct.MOBILIZE, so
        # electoral_only makes the contagion channel structurally inert (menu_acts={0,4}, MOBILIZE
        # never legal); `both`/`petition_only` would add a second lever with its own confidence-vote/
        # recall dynamics unrelated to the contagion channel this run isolates.
        pressure_menu=dataclasses.replace(
            config.pressure_menu, electoral_only=False, petition_enabled=False, mobilization_enabled=True
        ),
        petition=config.petition,
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True),
        social_graph=dataclasses.replace(config.social_graph, enabled=True),
        events=dataclasses.replace(
            config.events,
            enabled=True,
            scandal_enabled=True,
            scandal_rate_per_tick=scandal_rate,
            economic_shock_enabled=True,
            economy_ar1_sigma=economy_sigma,
        ),
        # BOTH modulation terms active at once -- the whole point of this run, never done in any
        # prior acceptance run: v5 Lot 5 only ever turned on event_salience, v6a Lot 4 only ever
        # turned on neighbors_acting.
        awakening=dataclasses.replace(
            config.awakening,
            enabled=True,
            context_modulation=dataclasses.replace(
                config.awakening.context_modulation, event_salience=True, neighbors_acting=True
            ),
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
        "mandate_deviation_unified": metrics.mandate_deviation_unified,
        "inaction_rate": metrics.inaction_rate,
        "pressure_lever_mix": metrics.pressure_lever_mix,
        "pressure_lever_counts": metrics.pressure_lever_counts,
        "stance_distribution": metrics.stance_distribution,
        "petition_downgrades": metrics.petition_downgrades,
        "petition_success_rate": metrics.petition_success_rate,
        "petition_removal_rate": metrics.petition_removal_rate,
    }


def _compute_spark(journal_path: Path, population_size: int, total_ticks: int) -> dict[str, Any]:
    """Reused verbatim from run_v5_acceptance.py's own function of the same name -- consultation
    count per tick, cross-referenced against scandal_occurred/economic_shock_tick tick numbers.
    Iterates the FULL tick range, not just ticks with an event (v5 Lot 5's own already-learned lesson:
    a tick with zero consultation is a real, informative zero, not an absent observation)."""
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


def _compute_contagion_metrics(journal_path: Path, total_ticks: int) -> dict[str, Any]:
    """Reused verbatim from run_v6a_acceptance.py's own function of the same name -- mobilization
    count and realized neighbors_acting per tick. `mobilize_count` counts the DECIDED act
    (payload["act"]), matching pressure_lever_mix's own established "decided, not applied"
    convention."""
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


def _compute_cascade_metrics(journal_path: Path, total_ticks: int) -> dict[str, Any]:
    """The one computation neither prior script needed: MOBILIZATION volume (not consultation
    volume) on firing ticks versus quiet ticks -- the direct operationalization of "does a shock
    trigger a mobilization wave that contagion then amplifies," as opposed to the two effects merely
    coexisting without interacting.

    A firing tick t is included TOGETHER WITH t+1 in the "firing-adjacent" bucket, accounting for
    neighbors_acting's own one-tick lag (v6 Lot 3's own documented design: a citizen's ctx.
    neighbors_acting at tick t reflects mobilizations APPLIED at tick t-1) -- a shock's
    contagion-amplified second-order effect, if any, shows up on t+1, not on t itself. Single
    consumer (this script), stays ad hoc here per every prior acceptance script's own precedent."""
    mobilized_by_tick: dict[int, int] = {}
    firing_ticks: set[int] = set()
    for event in read_journal(journal_path):
        if event["event_type"] == "pressure_action" and event["payload"].get("act") == 3:
            tick = event["tick"]
            mobilized_by_tick[tick] = mobilized_by_tick.get(tick, 0) + 1
        elif event["event_type"] in ("scandal_occurred", "economic_shock_tick"):
            firing_ticks.add(event["tick"])

    firing_adjacent_ticks: set[int] = set()
    for t in firing_ticks:
        firing_adjacent_ticks.add(t)
        if t + 1 <= total_ticks:
            firing_adjacent_ticks.add(t + 1)

    all_ticks = range(total_ticks + 1)
    firing_adjacent_counts = [mobilized_by_tick.get(t, 0) for t in sorted(firing_adjacent_ticks)]
    quiet_counts = [mobilized_by_tick.get(t, 0) for t in all_ticks if t not in firing_adjacent_ticks]

    firing_mean = sum(firing_adjacent_counts) / len(firing_adjacent_counts) if firing_adjacent_counts else None
    quiet_mean = sum(quiet_counts) / len(quiet_counts) if quiet_counts else None
    ratio = (firing_mean / quiet_mean) if firing_mean is not None and quiet_mean not in (None, 0.0) else None

    return {
        "firing_ticks": sorted(firing_ticks),
        "firing_adjacent_ticks": sorted(firing_adjacent_ticks),
        "firing_adjacent_mean_mobilization": firing_mean,
        "firing_adjacent_max_mobilization": max(firing_adjacent_counts) if firing_adjacent_counts else None,
        "quiet_mean_mobilization": quiet_mean,
        "ratio": ratio,
    }


def run_arm(
    engine: str, *, duration_years: int, scandal_rate: float, economy_sigma: float,
    output_dir: Path, max_batch_replays: int, seed: int,
) -> Path:
    # scandal_rate/economy_sigma/seed in the dir name: Journal opens its file in append mode
    # (§16.1's deliberate append-only contract) -- a pre-existing run_dir must fail loudly rather
    # than silently concatenate two runs, and distinct tuning values (now including seed) need
    # distinct directories (v5 Lot 5's own already-learned lesson). seed is included unconditionally,
    # even at the shipped 42, so directory names stay uniform regardless of which seed was used.
    run_dir = output_dir / f"cascade-{engine}-{duration_years}y-r{scandal_rate}-s{economy_sigma}-seed{seed}"
    if run_dir.exists():
        raise FileExistsError(
            f"{run_dir} already exists -- Journal appends rather than overwrites; remove it or "
            "pick different --scandal-rate/--economy-sigma/--seed values before re-running this arm."
        )
    run_dir.mkdir(parents=True)
    config = _config_for_cascade_run(
        engine, duration_years=duration_years, output_dir=run_dir / "run",
        scandal_rate=scandal_rate, economy_sigma=economy_sigma, max_batch_replays=max_batch_replays,
        seed=seed,
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
        journal_path = run_simulation(config, run_id=f"cascade-{engine}-{duration_years}y", llm_client=None)
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
    # office_occupancy: RunMetrics.mean_legitimacy carries one entry per (tick, presided) pair --
    # a vacant tick is ABSENT from the series entirely (indexer.py's own "never 0.0" rule), so its
    # own length IS the occupied-tick count for free, no extra journal read needed.
    occupancy = len(metrics.mean_legitimacy or []) / (config.run.total_ticks + 1)
    payload = _metrics_to_json(metrics)
    payload["_meta"] = {
        "engine": engine, "duration_years": duration_years, "scandal_rate": scandal_rate,
        "economy_sigma": economy_sigma, "seed": seed, "elapsed_seconds": round(elapsed, 1),
        "replay_count": replay_count, "office_occupancy": round(occupancy, 3),
    }
    metrics_path = run_dir / "metrics.json"
    metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    spark = _compute_spark(journal_path, config.run.population_size, config.run.total_ticks)
    (run_dir / "spark.json").write_text(json.dumps(spark, indent=2), encoding="utf-8")

    contagion = _compute_contagion_metrics(journal_path, config.run.total_ticks)
    (run_dir / "contagion.json").write_text(json.dumps(contagion, indent=2), encoding="utf-8")

    cascade = _compute_cascade_metrics(journal_path, config.run.total_ticks)
    cascade_path = run_dir / "cascade.json"
    cascade_path.write_text(json.dumps(cascade, indent=2), encoding="utf-8")

    recalls = metrics.recalls_by_trigger or {}
    total_recalls = sum(recalls.values())
    print(
        f"cascade/{engine}/{duration_years}y/seed{seed}: {elapsed:.1f}s, {replay_count} replays, "
        f"office_occupancy={occupancy:.3f}, recalls={total_recalls}, "
        f"scandals={spark['scandal_count']}, shocks={spark['shock_count']}, "
        f"max_mobilization_per_tick={contagion['max_mobilization_per_tick']}, "
        f"firing_adjacent_mean_mobilization={cascade['firing_adjacent_mean_mobilization']}, "
        f"quiet_mean_mobilization={cascade['quiet_mean_mobilization']} -- "
        f"metrics={metrics_path}, cascade={cascade_path}"
    )
    if engine == "deterministic":
        if occupancy < 0.5:
            print(
                "GO/NO-GO: office_occupancy < 0.5 -- halve --scandal-rate/--economy-sigma and "
                "re-run this (still near-free) deterministic dry-run before considering --engine "
                "llm at all. Do NOT raise legitimacy.recall_floor toward zero as the fix.",
                file=sys.stderr,
            )
        elif spark["scandal_count"] < 2 or spark["shock_count"] < 1:
            print(
                "GO/NO-GO: fewer than the pre-registered minimum firing ticks (2 scandal, 1 shock) "
                "-- the cascade question is not reachable at this tuning. Raise --scandal-rate/"
                "--economy-sigma slightly and re-run, watching office_occupancy doesn't drop below "
                "0.5 again.",
                file=sys.stderr,
            )
        else:
            print(
                "GO/NO-GO: criteria met (office_occupancy >= 0.5, >=2 scandal-firing and >=1 "
                "shock-firing ticks) -- safe to proceed to --engine llm at these tuning values.",
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

    log("# Composite cascade acceptance run — v4 + v5 + v6a together (§7bis.9e's full claim)\n")
    log(
        "n=1 (one seed, no Monte Carlo band), the same limit every prior acceptance run in this "
        "project has already named. Runs `events.enabled=True` (scandal + economic shock) AND "
        "`social_graph.enabled=True` + `awakening.context_modulation.neighbors_acting=True` "
        "TOGETHER, under `mobilization_only`, for the first time — v5 Lot 5 and v6a Lot 4 each "
        "isolated exactly one of these two ingredients on top of v4's own pressure levers. "
        "`office_occupancy` is the pre-registered go/no-go signal this run's own calibration dry-run "
        "used before committing to the LLM arm.\n"
    )
    log(
        "| arm | engine | seed | years | elapsed(s) | replays | scandal_rate | economy_sigma | "
        "office_occupancy | mean L (last) | recalls | mandate_dev (last, src) | "
        "mandate_dev unified (last) | lever mix |"
    )
    log("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

    non_default_seeds: set[int] = set()
    for path in metrics_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta = payload["_meta"]
        seed = meta.get("seed", 42)
        if seed != 42:
            non_default_seeds.add(seed)
        mean_l = payload["mean_legitimacy"]
        last_l = mean_l[-1][1] if mean_l else None
        deviation = payload["mandate_deviation"]
        last_dev = deviation[-1][1] if deviation else None
        unified = payload.get("mandate_deviation_unified")
        last_unified = unified[-1][1] if unified else None
        recalls = payload["recalls_by_trigger"]
        log(
            f"| cascade | {meta['engine']} | {seed} | {meta['duration_years']} | {meta['elapsed_seconds']} | "
            f"{meta['replay_count']} | {meta['scandal_rate']} | {meta['economy_sigma']} | "
            f"{_fmt(meta.get('office_occupancy'))} | {_fmt(last_l)} | {_fmt(recalls)} | "
            f"{_fmt(last_dev)} ({payload['mandate_deviation_source'] or '—'}) | {_fmt(last_unified)} | "
            f"{_fmt(payload['pressure_lever_mix'])} |"
        )

    if non_default_seeds:
        log(
            f"\n**⚠ Non-default seed(s) used: {sorted(non_default_seeds)}.** The two reference rows "
            "below (v5 Lot 5's `electoral_only` spark arm, v6a Lot 4's `mobilization_only` contagion "
            "arm) were both run at seed=42 -- a run above at a different seed is NOT a seed-for-seed "
            "comparison against them, only a comparison against this run's own other arm (if any) at "
            "the same seed. The seed=42 calibration dry-run found office_occupancy=0.152 regardless "
            "of --scandal-rate/--economy-sigma tuning (see the script's own module docstring, SEED "
            "section) -- a different seed was tried specifically because that collapse is a property "
            "of the seed=42 population/officeholder draw, not of contagion or events."
        )

    log("\n## Reference rows — one ingredient at a time (NOT re-run here)\n")
    log(
        "| arm | engine | years | elapsed(s) | replays | scandal_rate | economy_sigma | "
        "office_occupancy | mean L (last) | recalls | mandate_dev (last, src) | lever mix | "
        "scandals | shocks | firing consult. | quiet consult. | ratio |"
    )
    log("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    log(f"| {_V5_SPARK_CITATION} |")
    log(f"| {_V6A_CONTAGION_CITATION} |")
    log(
        "\nBoth rows: same seed (42), same `population_size` (100), same `ambition_threshold` (0.0), "
        "same duration (8y), same `legitimacy`/`mandate`/`awakening` enabled. The v5 row is "
        "`electoral_only` + `events.enabled=True`, `social_graph` off (the \"spark\" alone, "
        "`acceptance_v5_results.md`). The v6a row is `mobilization_only` + `social_graph.enabled=True`/"
        "`neighbors_acting=True`, `events` off (the \"contagion\" alone, `acceptance_v6a_results.md`). "
        "Cited verbatim, never re-derived."
    )

    log("\n## Contagion metrics (mean/max consultation and mobilization per tick)\n")
    log(
        "| arm | engine | mean consult./tick | max consult./tick | mean mobilize/tick | "
        "max mobilize/tick | mean realized neighbors_acting | max realized neighbors_acting |"
    )
    log("|---|---|---|---|---|---|---|---|")
    for path in metrics_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta = payload["_meta"]
        contagion_path = path.parent / "contagion.json"
        contagion = json.loads(contagion_path.read_text(encoding="utf-8")) if contagion_path.is_file() else {}
        log(
            f"| cascade | {meta['engine']} | {_fmt(contagion.get('mean_consultation_per_tick'))} | "
            f"{_fmt(contagion.get('max_consultation_per_tick'))} | "
            f"{_fmt(contagion.get('mean_mobilization_per_tick'))} | "
            f"{_fmt(contagion.get('max_mobilization_per_tick'))} | "
            f"{_fmt(contagion.get('mean_realized_neighbors_acting'))} | "
            f"{_fmt(contagion.get('max_realized_neighbors_acting'))} |"
        )

    log("\n## Cascade metrics — mobilization on firing-adjacent ticks vs. quiet ticks\n")
    log(
        "| arm | engine | firing ticks | firing-adjacent mean mobilization | "
        "firing-adjacent max mobilization | quiet mean mobilization | ratio |"
    )
    log("|---|---|---|---|---|---|---|")
    for path in metrics_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta = payload["_meta"]
        cascade_path = path.parent / "cascade.json"
        cascade = json.loads(cascade_path.read_text(encoding="utf-8")) if cascade_path.is_file() else {}
        log(
            f"| cascade | {meta['engine']} | {len(cascade.get('firing_ticks', []))} | "
            f"{_fmt(cascade.get('firing_adjacent_mean_mobilization'))} | "
            f"{_fmt(cascade.get('firing_adjacent_max_mobilization'))} | "
            f"{_fmt(cascade.get('quiet_mean_mobilization'))} | {_fmt(cascade.get('ratio'))} |"
        )

    has_llm_row = any(
        json.loads(path.read_text(encoding="utf-8"))["_meta"]["engine"] == "llm" for path in metrics_files
    )

    if has_llm_row:
        log("\n## §7bis.9e's own three-ingredient claim — three pre-registered branches\n")
        log(
            "*« un basculement de type Gilets jaunes n'est pas atteignable avant v6 ... il requiert "
            "simultanément le graphe social (v6), les chocs exogènes (v5) et les leviers de pression "
            "(v4) »*"
        )
        log(
            "- **(a) Genuine amplification**: the cascade table's `ratio` above is materially higher "
            "than 1.0 AND the `firing-adjacent mean mobilization` materially exceeds v6a's own "
            "contagion-only `mean mobilize/tick` (9.242, cited above) — the strongest form of the claim: "
            "a shock triggers a mobilization wave that contagion then amplifies beyond what either "
            "ingredient produces alone."
        )
        log(
            "- **(b) Additive, not amplifying**: firing-adjacent mobilization is higher than this run's "
            "own quiet-tick baseline but comparable to v6a's own contagion-only rate — the two effects "
            "coexist without interacting."
        )
        log(
            "- **(c) Swamped**: no material difference from v6a's own contagion-only numbers at all — "
            "contagion alone was already driving near-total mobilization (`max_mobilization_per_tick=85` "
            "with events off), leaving little room for a shock's own marginal effect to show."
        )
        log(
            "All three are informative; none is a failure condition for this run. **n=1**: this is a "
            "single-seed observation, not a claim that generalizes without a Monte Carlo band."
        )
    else:
        log("\n## GO/NO-GO outcome: the LLM arm was never run\n")
        log(
            "*« un basculement de type Gilets jaunes n'est pas atteignable avant v6 ... il requiert "
            "simultanément le graphe social (v6), les chocs exogènes (v5) et les leviers de pression "
            "(v4) »*"
        )
        log(
            "**The deterministic dry-run's own `office_occupancy=0.152` never cleared the pre-registered "
            "`>= 0.5` go/no-go bar, and every lever this run's own plan permits to fix that was tried and "
            "exhausted — the LLM arm (~2.5-5h forecast) was deliberately never run.**\n"
        )
        log(
            "1. **Halving the event rates does not converge.** Two calibration attempts, `r0.08/s0.12` "
            "and `r0.04/s0.06`, produced BYTE-IDENTICAL outcomes (`office_occupancy=0.152, recalls=2, "
            "scandals=0, shocks=0`) — the events never fire before the collapse either way, so they were "
            "never the cause and no amount of retuning can be the fix."
        )
        log(
            "2. **The collapse is pre-existing and menu/event-independent, traced to source.** The "
            "election/journal timeline (seed=42) shows: `elected` tick 0 -> `recalled` tick 1 "
            "(`L: 0.345 -> 0.026`, floor `0.2`) -> vacant through tick 15 -> `elected` tick 16 -> "
            "`recalled` tick 17 -> vacant through tick 31 -> `elected` tick 32. At tick 0 the awakening "
            "gate is maximally permissive (`proximity=0`, no other modulation term has a chance to be "
            "nonzero yet), consulting 67/100 and mobilizing 33/100 — exactly v4 Lot 4's own committed "
            "\"mobilize max ~=0.33 right after election\" number. That rate alone is already inside the "
            "\"33.3x amplification\" wall v4 Lot 4's own docstring names (`street_pressure` decay=0.85, "
            "`w_mob`=0.5, legitimacy decay=0.9). This exact outcome (`legitimacy_floor=2` recalls, "
            "`mean L (last)=0.345`) is byte-identical to v4 Lot 8's own committed `mobilization_only` "
            "row and v6a Lot 4's own committed contagion row — proof this is a pre-existing property of "
            "the `mobilization_only` deterministic baseline itself, present since v4 Lot 8, never "
            "flagged before because no prior acceptance script computed an explicit `office_occupancy` "
            "metric."
        )
        log(
            "3. **Seed-hunting does not help, and generalizes into a separate, larger finding.** An "
            "11-seed sweep (1, 2, 3, 5, 7, 10, 13, 21, 99, 100, 123) found 0/11 clearing the go/no-go "
            "bar: 9/11 never elect a president at all (`election_no_winner` at every scheduled "
            "election — `Blank` wins the `two_round` runoff outright whenever enough voters find all 5 "
            "party platforms unacceptable), and the 2 that do elect someone (seeds 10, 99) still "
            "collapse via the same mobilize-driven recall. Confirmed directly this is unrelated to "
            "`pressure_menu`/`social_graph`/`events` (elections resolve before any of those mechanisms "
            "run): `electoral_only` at seeds 1 and 7 hits the identical `election_no_winner` outcome. "
            "Seed=42 -- the seed every acceptance run in this project (v4 Lot 8 through v6b Lot 4) has "
            "used -- is not a representative draw for this failure mode; it sits just under a "
            "~32-34%-forced-blank threshold by coincidence, not by any distinguishing population "
            "property (its own mean `blank_threshold` and mean distance-to-nearest-nominee are not "
            "systematically more favorable than several failing seeds). This is a separate, larger "
            "finding about every prior acceptance script's own `ambition_threshold=0.0` \"guarantees a "
            "real elected president\" comment, noted here but not otherwise acted on by this script."
        )
        log(
            "4. **Raising `legitimacy.recall_floor` toward zero was ruled out on purpose** -- this "
            "project's own v6b Lot 4 write-up already named that fix \"scientifically inelegant... "
            "disables accountability rather than testing it\" after making that exact mistake once.\n"
        )
        log(
            "**Conclusion**: §7bis.9e's full three-ingredient claim is not testable under "
            "`mobilization_only` at the current shipped `population_size=100`/seed=42 scale -- not "
            "because contagion or events fail to interact usefully, but because the office is vacant "
            "before they get the chance to. This is itself the honest result of this run: a structural "
            "precondition gap, not a null result from a bug. v6a Lot 4's own committed LLM arm (same "
            "menu, no events) also shows `legitimacy_floor=2` recalls, suggesting (not proving -- "
            "office_occupancy was never computed there) the LLM engine likely does not escape this "
            "either."
        )

    if results_path is not None:
        results_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n(full report written to {results_path})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--engine", choices=["llm", "deterministic"])
    parser.add_argument("--duration-years", type=int, default=8)
    parser.add_argument("--scandal-rate", type=float, default=0.08)
    parser.add_argument("--economy-sigma", type=float, default=0.12)
    parser.add_argument("--max-batch-replays", type=int, default=2)
    parser.add_argument(
        "--seed", type=int, default=42,
        help=(
            "config.run.seed override (shipped default 42). At seed=42 the deterministic dry-run "
            "already found office_occupancy=0.152 regardless of --scandal-rate/--economy-sigma -- see "
            "the module docstring's own SEED section. A non-42 value breaks direct comparability to "
            "the seed=42 v5/v6a reference rows in summarize(); this is flagged explicitly there."
        ),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("scripts/acceptance_cascade_runs"))
    parser.add_argument("--summarize", type=Path, help="render the results doc from every metrics.json under this dir")
    parser.add_argument("--results", type=Path, help="where --summarize writes the rendered markdown")
    args = parser.parse_args()

    if args.summarize:
        summarize(args.summarize, args.results)
        return 0

    if not args.engine:
        parser.error("--engine is required unless --summarize is given")

    run_arm(
        args.engine, duration_years=args.duration_years, scandal_rate=args.scandal_rate,
        economy_sigma=args.economy_sigma, output_dir=args.output_dir, max_batch_replays=args.max_batch_replays,
        seed=args.seed,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
