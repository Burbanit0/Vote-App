"""
scripts/calibrate_events.py

v5 Lot 2's own DoD claims ("Poisson arrival rate matches
`scandal_rate_per_tick` within tolerance", "AR(1) series stays
mean-reverting") are evidence claims, not formulas -- this script is that
evidence, the same "sweep a parameter, run the real production path, report
realized rates in a committed markdown doc" convention as
calibrate_awakening.py/calibrate_petition.py.

Two halves, deliberately different in shape:
- The scandal-rate and threshold-crossing-rate numbers need the full
  tick-loop/journal path to be representative (they depend on
  run_simulation's real per-tick sequencing), so those come from real
  run_simulation calls.
- The AR(1) series' own mean/variance against its closed-form steady state
  (mean=0, var = sigma^2 / (1 - phi^2)) needs the UNCENSORED x(t) series,
  which the journal doesn't carry (only economic_shock_tick, gated above
  economy_shock_threshold, is journaled -- see shock.py's module docstring
  on why x(t) is left unclamped and _run_exogenous_events's own gating
  comment). So those numbers come from calling shock.economic_shock_step
  directly in a small standalone loop instead.

candidacy.ambition_threshold is deliberately left at its shipped value
(0.7) throughout -- never produces a winner at seed=42, which keeps every
swept run clear of awakening_threshold's still-pending event_salience
NotImplementedError guard (v5 Lot 3's job to remove), the same load-bearing
property the Lot 2 test suite relies on.

Fully deterministic -- no LLM, no Ollama required.

Usage:
    python fast_api_voter/scripts/calibrate_events.py \
        --results scripts/events_calibration_results.md
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import statistics
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from api.domain.polity.config import PolityConfig, load_config  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402
from api.domain.polity.shock import economic_shock_step  # noqa: E402

_SCANDAL_RATES = [0.05, 0.1, 0.2]
_AR1_PARAMS = [(0.8, 0.1), (0.5, 0.1), (0.95, 0.05)]
_AR1_TRACE_LENGTH = 10_000


def _events_config(output_dir: Path, **overrides) -> PolityConfig:
    config = load_config()
    defaults = {"enabled": True, "scandal_enabled": True, "economic_shock_enabled": True}
    events = dataclasses.replace(config.events, **{**defaults, **overrides})
    return dataclasses.replace(
        config,
        journal=dataclasses.replace(config.journal, output_dir=str(output_dir), index_after_run=False),
        awakening=dataclasses.replace(
            config.awakening,
            enabled=True,
            context_modulation=dataclasses.replace(config.awakening.context_modulation, event_salience=True),
        ),
        events=events,
    )


def _events(journal_path: Path) -> list[dict]:
    return [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]


def run_scandal_sweep(output_dir: Path, scandal_rate_per_tick: float) -> dict:
    config = _events_config(output_dir, scandal_rate_per_tick=scandal_rate_per_tick, economic_shock_enabled=False)
    journal_path = run_simulation(config, run_id="calibration")
    events = _events(journal_path)
    scandals = [e for e in events if e["event_type"] == "scandal_occurred"]
    total_ticks = config.run.total_ticks + 1
    return {
        "scandal_rate_per_tick": scandal_rate_per_tick,
        "configured": scandal_rate_per_tick,
        "empirical": len(scandals) / total_ticks,
        "total_ticks": total_ticks,
    }


def run_ar1_trace(phi: float, sigma: float, seed: int = 42) -> dict:
    """Standalone loop, no Journal/run_simulation -- the uncensored series."""
    rng = np.random.default_rng(seed)
    config = dataclasses.replace(load_config().events, economic_shock_enabled=True, economy_ar1_phi=phi, economy_ar1_sigma=sigma)
    x = 0.0
    trace = []
    for _ in range(_AR1_TRACE_LENGTH):
        x = economic_shock_step(x, rng, config)
        trace.append(x)
    theoretical_var = (sigma ** 2) / (1 - phi ** 2) if phi != 1.0 else float("inf")
    return {
        "phi": phi,
        "sigma": sigma,
        "empirical_mean": statistics.fmean(trace),
        "empirical_std": statistics.pstdev(trace),
        "theoretical_std": math.sqrt(theoretical_var),
        "max_abs": max(abs(v) for v in trace),
    }


def run_threshold_crossing(output_dir: Path, phi: float, sigma: float) -> dict:
    config = _events_config(
        output_dir, scandal_enabled=False, economy_ar1_phi=phi, economy_ar1_sigma=sigma,
    )
    journal_path = run_simulation(config, run_id="calibration")
    events = _events(journal_path)
    shocks = [e for e in events if e["event_type"] == "economic_shock_tick"]
    total_ticks = config.run.total_ticks + 1
    return {
        "phi": phi,
        "sigma": sigma,
        "threshold": config.events.economy_shock_threshold,
        "crossing_rate": len(shocks) / total_ticks,
        "total_ticks": total_ticks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=None)
    args = parser.parse_args()

    lines: list[str] = []

    def log(line: str) -> None:
        print(line, flush=True)
        lines.append(line)

    log("# Exogenous events calibration sweep (v5 Lot 2, §8)\n")

    log("## Scandal arrival rate (Bernoulli-per-tick vs. configured `scandal_rate_per_tick`)\n")
    log("| configured rate | empirical rate | total ticks |")
    log("|---|---|---|")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for rate in _SCANDAL_RATES:
            result = run_scandal_sweep(tmp_path / f"scandal-{rate}", rate)
            log(f"| {result['configured']:.2f} | {result['empirical']:.4f} | {result['total_ticks']} |")
    log("")

    log("## AR(1) economic climate: uncensored series vs. closed-form steady state\n")
    log(
        f"x(t) = phi*x(t-1) + sigma*epsilon(t), epsilon ~ N(0,1); theoretical steady-state "
        f"mean=0, std=sigma/sqrt(1-phi^2). Trace length {_AR1_TRACE_LENGTH} steps, seed=42, "
        "computed via shock.economic_shock_step directly (not journaled -- economic_shock_tick "
        "is threshold-gated, so this is the only way to see the uncensored series).\n"
    )
    log("| phi | sigma | empirical mean | empirical std | theoretical std | max |x| |")
    log("|---|---|---|---|---|---|")
    for phi, sigma in _AR1_PARAMS:
        result = run_ar1_trace(phi, sigma)
        log(
            f"| {result['phi']} | {result['sigma']} | {result['empirical_mean']:.4f} | "
            f"{result['empirical_std']:.4f} | {result['theoretical_std']:.4f} | {result['max_abs']:.4f} |"
        )
    log("")

    log("## `economic_shock_tick` crossing rate at the shipped `economy_shock_threshold` (0.5)\n")
    log("| phi | sigma | threshold | crossing rate | total ticks |")
    log("|---|---|---|---|---|")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for phi, sigma in _AR1_PARAMS:
            result = run_threshold_crossing(tmp_path / f"ar1-{phi}-{sigma}", phi, sigma)
            log(
                f"| {result['phi']} | {result['sigma']} | {result['threshold']} | "
                f"{result['crossing_rate']:.4f} | {result['total_ticks']} |"
            )

    if args.results:
        args.results.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log(f"\n(full log written to {args.results})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
