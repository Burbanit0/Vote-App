"""
scripts/run_v7_acceptance.py

v7's own acceptance deliverable: does the multi-round coalition negotiation loop (§3.4 Cas 2, Lot 2,
PR #223) change anything real at population scale, and does Lot 3's own open finding -- no round-to-
round revision was observed in 30 live spike trials, including one purpose-built to force it
(coalition_negotiation_v7_lot3_reliability_results.md) -- still hold once real, varied elections
(not hand-engineered seat/platform fixtures) are the source of the party compositions being
negotiated over?

**The one variable**: `parties.coalition_max_negotiation_rounds`, 1 (structurally identical to the
pre-v7 single-shot call -- the round loop's own hard cap fires after round 1, before a fixed-point
check is even possible, verified directly in decide_coalition's own docstring and its round-1-parity
tests) vs 3 (the shipped v7 default). Both arms run FRESH here, today, rather than citing an
existing pre-v7 run for the rounds=1 side: this project's own calibration has changed materially
since any earlier `electoral_only` run was produced (ADR-002's ambition_threshold 0.7->0.30,
ADR-003's rupture-signature fix, this week alone) -- citing an old run would confound TWO variables
(rounds AND calibration vintage) instead of isolating one, exactly the mistake v6a Lot 4's own
citation discipline warns against making carelessly. Two fresh, identical-except-for-one-field runs
is the only way to actually isolate this variable.

**Base arm: `electoral_only`** (run_acceptance_comparison._config_for_arm's own verbatim recipe --
ambition_threshold=0.0, legitimacy/awakening/mandate enabled, menu={electoral_only}). Chosen because
it is the cleanest existing baseline that already exercises real legislative elections and coalition
formation (D'Hondt seat allocation is unconditional; coalition formation only needs a seated
assembly, not any pressure/petition/mobilization machinery) without those unrelated channels adding
noise or wall-clock cost this comparison doesn't need. `sortition_chamber` stays at its shipped
default (off) -- orthogonal to coalition formation by construction (`run_polity_simulation`'s own
"architecturally independent" framing, v6b Lot 3), and leaving it off keeps this run cheap (no
chamber_deliberation calls, which dominate cost in every run that has them on).

**Duration: 8 years** (33 ticks), matching every prior acceptance run's own "minimum-observability
floor". At `assembly_term_years=4`, this yields ~2 coalition formations per arm -- thin, but
consistent with this project's own established convention rather than an ad hoc choice. If this run
doesn't resolve Lot 3's open "does a revision ever happen" question (too few formations either way),
that stays open for a longer-duration follow-up, not force-extended here.

**Pre-registered read, before looking at any result**: with only ~2 formations per arm, this run is
NOT powered to give a confident population-level verdict on the "does conditional revision ever
happen" question either way -- a single new formation showing rounds_used=3 or a revision would be
suggestive, not proof, and zero such formations would not prove the mechanism never revises (n=2 is
not a reliability spike's n=30). What this run CAN answer cleanly: does the negotiation loop run
correctly end to end against REAL journaled party/seat/platform state (not hand-built fixtures), and
does coalition_lifespans/cohabitation_rate/every other RunMetrics quantity stay unaffected by the
rounds change when the final decisions match (the parity claim Lot 2's own tests only checked with
fakes). Reported honestly as what it is: a real-data confirmation pass, not a statistically powered
verdict on the open scientific question.

Calibration-before-commit is a go/no-go CHECKPOINT (v6a/v6b Lot 4's own precedent), not a sweep:
every value here is already shipped and already measured independently. Run --engine deterministic
for both arms first (near-free, seconds); the deterministic path never calls decide_coalition at all
(form_coalition, simple_rules.py, unconditional -- see run_polity_simulation.py), so both arms MUST
produce byte-identical coalition_formed/coalition_failed payloads (minus the `rounds_used` key,
which is LLM-path-only) -- confirms the config plumbing (parties.coalition_max_negotiation_rounds
actually reaching the run) without spending any GPU time, before the real qwen3:8b arms.

Wall-clock forecast (not a promise): `electoral_only/llm/8y` measured 11776.3s (~3.27h,
acceptance_v4_results.md) is the closest real anchor for EACH arm -- coalition negotiation itself is
2-3 orders of magnitude cheaper than vote_cast/candidacy_considered, which dominate this arm's cost
either way (coalition_negotiation_v7_lot3_reliability_results.md's own cost analysis). Forecast
total for both LLM arms: ~2 x 11776s ~= 6.5h.

Usage:
    # calibration dry-run, deterministic, seconds -- both arms must match except rounds_used
    python fast_api_voter/scripts/run_v7_acceptance.py \\
        --rounds 1 --engine deterministic --output-dir scripts/acceptance_v7_runs
    python fast_api_voter/scripts/run_v7_acceptance.py \\
        --rounds 3 --engine deterministic --output-dir scripts/acceptance_v7_runs

    # the real qwen3:8b arms, once the deterministic dry-run looks safe
    python fast_api_voter/scripts/run_v7_acceptance.py \\
        --rounds 1 --engine llm --max-batch-replays 2 --output-dir scripts/acceptance_v7_runs
    python fast_api_voter/scripts/run_v7_acceptance.py \\
        --rounds 3 --engine llm --max-batch-replays 2 --output-dir scripts/acceptance_v7_runs

    # render the committed results doc from both arms' metrics.json/coalition.json
    python fast_api_voter/scripts/run_v7_acceptance.py \\
        --summarize scripts/acceptance_v7_runs --results scripts/acceptance_v7_results.md
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.config import PolityConfig, load_config  # noqa: E402
from api.domain.polity.indexer import RunMetrics, index_run, read_journal  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402


def _config_for_v7_arm(
    rounds: int, engine: str, *, duration_years: int, output_dir: Path, max_batch_replays: int,
) -> PolityConfig:
    config = load_config()
    config = dataclasses.replace(
        config,
        journal=dataclasses.replace(config.journal, output_dir=str(output_dir)),
        candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0),
        run=dataclasses.replace(config.run, duration_years=duration_years),
        legitimacy=dataclasses.replace(config.legitimacy, enabled=True),
        awakening=dataclasses.replace(config.awakening, enabled=True),
        mandate=dataclasses.replace(config.mandate, enabled=True),
        pressure_menu=dataclasses.replace(
            config.pressure_menu, electoral_only=True, petition_enabled=False, mobilization_enabled=False
        ),
        parties=dataclasses.replace(config.parties, coalition_max_negotiation_rounds=rounds),
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
        "effective_parties": metrics.effective_parties,
        "cohabitation_rate": metrics.cohabitation_rate,
        "coalition_lifespans": metrics.coalition_lifespans,
        "mean_legitimacy": metrics.mean_legitimacy,
        "recalls_by_trigger": metrics.recalls_by_trigger,
        "mandate_deviation": metrics.mandate_deviation,
        "mandate_deviation_source": metrics.mandate_deviation_source,
    }


def _compute_coalition_metrics(journal_path: Path) -> dict[str, Any]:
    """v7 Lot 2's own new payload keys (round on coalition_decision;
    rounds_used on coalition_formed; aborted_at_round/rounds_completed on
    coalition_failed) aren't in RunMetrics yet -- single consumer (this
    script), stays ad hoc here, same precedent as v6a Lot 4's own
    _compute_contagion_metrics / v6b Lot 4's own chamber-side extraction.

    Revision detection: per formation tick, compares round 1's party->action
    mapping against the LAST round's -- the same definition decide_coalition's
    own fixed-point check uses (a motif-only change doesn't count)."""
    decisions_by_tick: dict[int, list[dict]] = {}
    formations: list[dict] = []
    for event in read_journal(journal_path):
        if event["event_type"] == "coalition_decision":
            decisions_by_tick.setdefault(event["tick"], []).append(event["payload"])
        elif event["event_type"] in ("coalition_formed", "coalition_failed"):
            formations.append({"tick": event["tick"], "event_type": event["event_type"], **event["payload"]})

    rounds_used_values = [f["rounds_used"] for f in formations if "rounds_used" in f]
    aborted = [f for f in formations if "aborted_at_round" in f]

    revised_ticks: list[int] = []
    for tick, decisions in decisions_by_tick.items():
        by_round: dict[int, dict[int, int]] = {}
        for d in decisions:
            by_round.setdefault(d["round"], {})[d["party_id"]] = d["action"]
        if len(by_round) < 2:
            continue
        first_round, last_round = min(by_round), max(by_round)
        if by_round[first_round] != by_round[last_round]:
            revised_ticks.append(tick)

    return {
        "formations": len(formations),
        "coalition_formed_count": sum(1 for f in formations if f["event_type"] == "coalition_formed"),
        "coalition_failed_count": sum(1 for f in formations if f["event_type"] == "coalition_failed"),
        "rounds_used_distribution": dict(sorted(Counter(rounds_used_values).items())),
        "aborted_formations": len(aborted),
        "ticks_with_a_revision": revised_ticks,
    }


def run_arm(rounds: int, engine: str, *, duration_years: int, output_dir: Path, max_batch_replays: int) -> Path:
    arm = f"rounds{rounds}"
    run_dir = output_dir / f"{arm}-{engine}-{duration_years}y"
    if run_dir.exists():
        raise FileExistsError(f"{run_dir} already exists -- remove it before re-running this arm.")
    run_dir.mkdir(parents=True)
    config = _config_for_v7_arm(
        rounds, engine, duration_years=duration_years, output_dir=run_dir / "run", max_batch_replays=max_batch_replays
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
        "rounds": rounds, "engine": engine, "duration_years": duration_years,
        "elapsed_seconds": round(elapsed, 1), "replay_count": replay_count,
    }
    metrics_path = run_dir / "metrics.json"
    metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    coalition = _compute_coalition_metrics(journal_path)
    coalition_path = run_dir / "coalition.json"
    coalition_path.write_text(json.dumps(coalition, indent=2), encoding="utf-8")

    print(
        f"{arm}/{engine}/{duration_years}y: {elapsed:.1f}s, {replay_count} replays, "
        f"formations={coalition['formations']} (formed={coalition['coalition_formed_count']}, "
        f"failed={coalition['coalition_failed_count']}), "
        f"rounds_used={coalition['rounds_used_distribution']}, "
        f"revisions={coalition['ticks_with_a_revision']} "
        f"-- metrics={metrics_path}, coalition={coalition_path}"
    )
    return metrics_path


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, dict):
        return ", ".join(f"{k}={_fmt(v)}" for k, v in sorted(value.items())) if value else "—"
    if isinstance(value, list):
        return str(value) if value else "—"
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

    log("# v7 acceptance run — coalition negotiation, rounds=1 vs rounds=3 (§3.4 Cas 2)\n")
    log(
        "n=1 per arm (one seed, no Monte Carlo band), the same limit every prior acceptance run in "
        "this palier already named. Isolates the one variable §13 assigns v7 --  "
        "`parties.coalition_max_negotiation_rounds` -- on top of the `electoral_only` baseline. Not "
        "statistically powered on the \"does a revision ever happen\" question at this scale (~2 "
        "formations/arm); see this script's own docstring for what this run can and cannot answer.\n"
    )
    log("| arm | rounds | engine | years | elapsed(s) | replays | mean L (last) | mandate_dev (last) | effective_parties (last) | cohabitation_rate |")
    log("|---|---|---|---|---|---|---|---|---|---|")

    for path in metrics_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta = payload["_meta"]
        mean_l = payload["mean_legitimacy"]
        last_l = mean_l[-1][1] if mean_l else None
        deviation = payload["mandate_deviation"]
        last_dev = deviation[-1][1] if deviation else None
        eff_parties = payload["effective_parties"]
        last_eff = eff_parties[-1][1] if eff_parties else None
        log(
            f"| rounds{meta['rounds']} | {meta['rounds']} | {meta['engine']} | {meta['duration_years']} | "
            f"{meta['elapsed_seconds']} | {meta['replay_count']} | {_fmt(last_l)} | {_fmt(last_dev)} | "
            f"{_fmt(last_eff)} | {_fmt(payload['cohabitation_rate'])} |"
        )

    log("\n## Coalition negotiation detail (v7's own new fields, not in `RunMetrics`)\n")
    log("| arm | engine | formations | formed | failed | rounds_used distribution | aborted | ticks with a revision |")
    log("|---|---|---|---|---|---|---|---|")
    for path in metrics_files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta = payload["_meta"]
        coalition_path = path.parent / "coalition.json"
        coalition = json.loads(coalition_path.read_text(encoding="utf-8")) if coalition_path.is_file() else {}
        log(
            f"| rounds{meta['rounds']} | {meta['engine']} | {_fmt(coalition.get('formations'))} | "
            f"{_fmt(coalition.get('coalition_formed_count'))} | {_fmt(coalition.get('coalition_failed_count'))} | "
            f"{_fmt(coalition.get('rounds_used_distribution'))} | {_fmt(coalition.get('aborted_formations'))} | "
            f"{_fmt(coalition.get('ticks_with_a_revision'))} |"
        )

    log("\n## Reading this table\n")
    log(
        "- **Parity check**: with identical seed/config apart from `rounds`, do `rounds1` and "
        "`rounds3`'s pre-coalition quantities (effective_parties, mean_legitimacy, mandate_deviation) "
        "match up to the point coalition formation could plausibly diverge? Divergence anywhere "
        "upstream of the first coalition formation would indicate a bug unrelated to negotiation "
        "itself (a config leak), not a real effect of the variable being isolated."
    )
    log(
        "- **rounds_used distribution** on the `rounds1` arm should be `{1: N}` for every N -- the "
        "hard cap fires immediately, exactly like the pre-v7 single-shot call (this is the direct, "
        "real-data version of Lot 2's own parity tests, which only checked this with fakes)."
    )
    log(
        "- **rounds_used distribution** on the `rounds3` arm and **ticks with a revision**: this is "
        "the real-data continuation of Lot 3's own open finding (30/30 live spike trials converged in "
        "exactly 2 rounds with no revision, including one scenario engineered to force one). A "
        "revision or a rounds_used=3 here, on REAL journaled party/seat/platform state rather than a "
        "hand-built fixture, would be the first evidence either way -- reported honestly regardless "
        "of which way it comes out, and not treated as conclusive at n~2 either way."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rounds", type=int, choices=[1, 3], help="parties.coalition_max_negotiation_rounds for this arm")
    parser.add_argument("--engine", choices=["llm", "deterministic"])
    parser.add_argument("--duration-years", type=int, default=8)
    parser.add_argument("--max-batch-replays", type=int, default=2)
    parser.add_argument("--output-dir", type=Path, default=Path("scripts/acceptance_v7_runs"))
    parser.add_argument("--summarize", type=Path, help="render the results doc from every metrics.json under this dir")
    parser.add_argument("--results", type=Path, help="where --summarize writes the rendered markdown")
    args = parser.parse_args()

    if args.summarize:
        summarize(args.summarize, args.results)
        return 0

    if not args.engine:
        parser.error("--engine is required unless --summarize is given")
    if not args.rounds:
        parser.error("--rounds is required unless --summarize is given")

    run_arm(
        args.rounds, args.engine, duration_years=args.duration_years,
        output_dir=args.output_dir, max_batch_replays=args.max_batch_replays,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
