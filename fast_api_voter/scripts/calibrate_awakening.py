"""
scripts/calibrate_awakening.py

v4 Lot 4's "calibration gate" (dev-plan/merry-hugging-hamming.md) -- the
petition lever (Lot 5) and mobilization lever (this lot) are both capped by
the awakening gate's own realized consultation rate: only a consulted
citizen can ever sign/launch a petition or mobilize. Before Lot 5 builds on
top of this, this script reports what the shipped `citizens.base_threshold_dist`
(beta(3,5)) actually produces, alongside a few alternatives, so that
distribution -- and `petition.signature_threshold` later -- get tuned with
evidence instead of a guess. It also forecasts Lot 7's per-run LLM call
volume for free: every consulted citizen is one future dt=10 call.

Fully deterministic -- no LLM, no Ollama required. Runs the real production
path (run_simulation) rather than a standalone toy loop, so the numbers are
exactly what a real run would journal.

Usage:
    python fast_api_voter/scripts/calibrate_awakening.py \
        --results scripts/awakening_calibration_results.md
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import statistics
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.config import PolityConfig, load_config  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402

_BASE_THRESHOLD_DISTS = ["beta(3,5)", "beta(6,4)", "beta(7,3)", "beta(8,3)"]
_AMPLITUDES = [0.0, 0.5]
_MODALITIES = ["electoral_only", "mobilization_only"]


def _config_for(output_dir: Path, base_threshold_dist: str, amplitude: float, modality: str) -> PolityConfig:
    config = load_config()
    config = dataclasses.replace(
        config,
        journal=dataclasses.replace(config.journal, output_dir=str(output_dir)),
        candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0),
        citizens=dataclasses.replace(config.citizens, base_threshold_dist=base_threshold_dist),
        legitimacy=dataclasses.replace(config.legitimacy, enabled=True),
        awakening=dataclasses.replace(config.awakening, enabled=True, modulation_amplitude=amplitude),
    )
    if modality == "electoral_only":
        return dataclasses.replace(
            config,
            pressure_menu=dataclasses.replace(
                config.pressure_menu, electoral_only=True, mobilization_enabled=False
            ),
            street_pressure=dataclasses.replace(config.street_pressure, enabled=False),
        )
    return dataclasses.replace(
        config,
        pressure_menu=dataclasses.replace(
            config.pressure_menu, electoral_only=False, mobilization_enabled=True
        ),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True),
    )


def _events(journal_path: Path) -> list[dict]:
    return [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]


def run_one(output_dir: Path, base_threshold_dist: str, amplitude: float, modality: str) -> dict:
    config = _config_for(output_dir, base_threshold_dist, amplitude, modality)
    journal_path = run_simulation(config, run_id="calibration")
    events = _events(journal_path)

    pressure_events = [e for e in events if e["event_type"] == "pressure_action"]
    by_tick: dict[int, list[dict]] = {}
    for e in pressure_events:
        by_tick.setdefault(e["tick"], []).append(e)

    total_ticks = config.run.duration_years * config.run.ticks_per_year + 1
    population_size = config.run.population_size
    consultation_rates = [len(by_tick.get(t, [])) / population_size for t in range(total_ticks)]
    mobilization_rates = [
        sum(1 for e in by_tick.get(t, []) if e["payload"]["act"] == 3) / population_size
        for t in range(total_ticks)
    ]

    term_ticks = config.institutions.president_term_years * config.run.ticks_per_year
    early_term_rates = [consultation_rates[t] for t in range(total_ticks) if (t % term_ticks) < term_ticks // 4]
    late_term_rates = [consultation_rates[t] for t in range(total_ticks) if (t % term_ticks) >= 3 * term_ticks // 4]

    legitimacy_events = [e for e in events if e["event_type"] == "legitimacy_updated"]
    ecarts = [e["payload"]["ecart"] for e in legitimacy_events]
    legitimacies = [e["payload"]["legitimacy"] for e in legitimacy_events]
    street_pressures = [e["payload"].get("ecart", 0.0) for e in legitimacy_events]  # placeholder, overwritten below

    # street_pressure itself isn't journaled directly (only ecart is) --
    # recover it from ecart / street_weight when mobilization is the only
    # active lever (petition_pressure is always 0.0 through Lot 4).
    street_weight = config.street_pressure.weight_in_ecart
    if modality == "mobilization_only" and street_weight > 0:
        street_pressures = [e / street_weight for e in ecarts]
    else:
        street_pressures = [0.0 for _ in ecarts]

    return {
        "base_threshold_dist": base_threshold_dist,
        "amplitude": amplitude,
        "modality": modality,
        "consultation_mean": statistics.fmean(consultation_rates),
        "consultation_min": min(consultation_rates),
        "consultation_max": max(consultation_rates),
        "consultation_early_term_mean": statistics.fmean(early_term_rates) if early_term_rates else 0.0,
        "consultation_late_term_mean": statistics.fmean(late_term_rates) if late_term_rates else 0.0,
        "mobilization_mean": statistics.fmean(mobilization_rates),
        "mobilization_max": max(mobilization_rates),
        "street_pressure_max": max(street_pressures) if street_pressures else 0.0,
        "ecart_max": max(ecarts) if ecarts else 0.0,
        "legitimacy_min": min(legitimacies) if legitimacies else float("nan"),
        "recall_count": sum(1 for e in events if e["event_type"] == "recalled"),
        "llm_calls_forecast": sum(len(v) for v in by_tick.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=None)
    args = parser.parse_args()

    lines: list[str] = []

    def log(line: str) -> None:
        print(line, flush=True)
        lines.append(line)

    log("# Awakening/mobilization calibration sweep (v4 Lot 4)\n")
    log(
        "Steady-state amplification factor L(t) drop per unit sustained mobilization rate: "
        "w_mob/(1-decay_street) / (1-decay_L) = 0.5/0.15 / 0.1 = 33.3x (shipped legitimacy.decay=0.9, "
        "street_pressure.decay=0.85, street_pressure.weight_in_ecart=0.5) -- this is why "
        "deterministic_pressure_action gates MOBILIZE on blank_threshold instead of mobilizing "
        "unconditionally.\n"
    )
    log(
        "mandate_deviation is provably 0.0 through Lot 5 (no representative_response yet), so "
        "f(context) = 1 + amp*proximity this lot -- consultation rate is maximal right after an "
        "election and falls as the next one approaches (the 'early_term' vs 'late_term' columns "
        "below isolate this).\n"
    )
    log(
        "| base_threshold_dist | amp | modality | consult mean | consult early-term | "
        "consult late-term | mobilize mean | mobilize max | street_pressure max | ecart max | "
        "L min | recalls | dt=10 calls/run |"
    )
    log(
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|"
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for base_threshold_dist in _BASE_THRESHOLD_DISTS:
            for amplitude in _AMPLITUDES:
                for modality in _MODALITIES:
                    output_dir = tmp_path / f"{base_threshold_dist}-{amplitude}-{modality}"
                    result = run_one(output_dir, base_threshold_dist, amplitude, modality)
                    log(
                        f"| {result['base_threshold_dist']} | {result['amplitude']} | {result['modality']} | "
                        f"{result['consultation_mean']:.3f} | {result['consultation_early_term_mean']:.3f} | "
                        f"{result['consultation_late_term_mean']:.3f} | {result['mobilization_mean']:.3f} | "
                        f"{result['mobilization_max']:.3f} | {result['street_pressure_max']:.2f} | "
                        f"{result['ecart_max']:.3f} | {result['legitimacy_min']:.3f} | "
                        f"{result['recall_count']} | {result['llm_calls_forecast']} |"
                    )

    if args.results:
        args.results.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log(f"\n(full log written to {args.results})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
