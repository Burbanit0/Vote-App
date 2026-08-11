"""
scripts/calibrate_petition.py

v4 Lot 5's calibration gate (dev-plan/merry-hugging-hamming.md) -- the
petition lever's own knobs (petition.signature_threshold,
petition_lifespan_ticks, cooldown_ticks) sit inside a narrow reachable band
against Lot 4's measured awakening/action rates (see
awakening_calibration_results.md: the acting cohort peaks at ~0.33 of the
population early-term under the shipped citizens.base_threshold_dist, falling
to ~0 late-term), and petition.weight_in_ecart inherits the same
amplification problem Lot 4 quantified for street_pressure's weight_in_ecart.
This script sweeps signature_threshold, petition_lifespan_ticks and
cooldown_ticks at the shipped base_threshold_dist/modulation_amplitude, under
both petition-only and the full menu, to report what the shipped values
actually produce before Lot 8 builds its 4-modality comparison on top of
them.

Fully deterministic -- no LLM, no Ollama required. Runs the real production
path (run_simulation) rather than a standalone toy loop, so the numbers are
exactly what a real run would journal.

Usage:
    python fast_api_voter/scripts/calibrate_petition.py \
        --results scripts/petition_calibration_results.md
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

_SIGNATURE_THRESHOLDS = [0.10, 0.25, 0.40]
_LIFESPANS = [2, 4, 8]
_COOLDOWNS = [4, 16]  # 16 == one full presidential term at the shipped 4x4 calendar
_MODALITIES = ["petition_only", "both"]


def _config_for(
    output_dir: Path, signature_threshold: float, lifespan: int, cooldown: int, modality: str
) -> PolityConfig:
    config = load_config()
    config = dataclasses.replace(
        config,
        journal=dataclasses.replace(config.journal, output_dir=str(output_dir)),
        candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0),
        legitimacy=dataclasses.replace(config.legitimacy, enabled=True),
        awakening=dataclasses.replace(config.awakening, enabled=True),  # shipped amp=0.5
        petition=dataclasses.replace(
            config.petition,
            enabled=True,
            signature_threshold=signature_threshold,
            petition_lifespan_ticks=lifespan,
            cooldown_ticks=cooldown,
        ),
    )
    if modality == "petition_only":
        return dataclasses.replace(
            config,
            pressure_menu=dataclasses.replace(
                config.pressure_menu, electoral_only=False, petition_enabled=True, mobilization_enabled=False
            ),
            street_pressure=dataclasses.replace(config.street_pressure, enabled=False),
        )
    return dataclasses.replace(
        config,
        pressure_menu=dataclasses.replace(
            config.pressure_menu, electoral_only=False, petition_enabled=True, mobilization_enabled=True
        ),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True),
    )


def _events(journal_path: Path) -> list[dict]:
    return [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]


def run_one(output_dir: Path, signature_threshold: float, lifespan: int, cooldown: int, modality: str) -> dict:
    config = _config_for(output_dir, signature_threshold, lifespan, cooldown, modality)
    journal_path = run_simulation(config, run_id="calibration")
    events = _events(journal_path)

    launched = [e for e in events if e["event_type"] == "petition_launched"]
    expired = [e for e in events if e["event_type"] == "petition_expired"]
    triggered = [e for e in events if e["event_type"] == "confidence_vote_triggered"]
    results = [e for e in events if e["event_type"] == "confidence_vote_result"]
    recalled = [e for e in events if e["event_type"] == "recalled"]

    total_ticks = config.run.duration_years * config.run.ticks_per_year + 1
    presided_ticks = {e["tick"] for e in events if e["event_type"] == "legitimacy_updated"}
    open_petition_ticks = 0
    open_since: int | None = None
    for e in sorted(events, key=lambda e: (e["tick"], e["event_type"] != "petition_launched")):
        if e["event_type"] == "petition_launched":
            open_since = e["tick"]
        elif e["event_type"] in ("confidence_vote_triggered", "petition_expired", "recalled") and open_since is not None:
            open_petition_ticks += e["tick"] - open_since + 1
            open_since = None
    if open_since is not None:
        open_petition_ticks += total_ticks - open_since

    signed_ratios = [e["payload"]["signed_ratio"] for e in launched] + [
        e["payload"]["signed_ratio"] for e in events if e["event_type"] == "petition_signed"
    ]
    legitimacy_events = [e for e in events if e["event_type"] == "legitimacy_updated"]
    ecarts = [e["payload"]["ecart"] for e in legitimacy_events]
    legitimacies = [e["payload"]["legitimacy"] for e in legitimacy_events]

    act_histogram: dict[int, int] = {}
    for e in events:
        if e["event_type"] == "pressure_action":
            act = e["payload"]["act"]
            act_histogram[act] = act_histogram.get(act, 0) + 1

    return {
        "signature_threshold": signature_threshold,
        "lifespan": lifespan,
        "cooldown": cooldown,
        "modality": modality,
        "launched": len(launched),
        "expired": len(expired),
        "triggered": len(triggered),
        "success_rate": (sum(1 for r in results if r["payload"]["retained"] is False) / len(results))
        if results
        else float("nan"),
        "signed_ratio_mean": statistics.fmean(signed_ratios) if signed_ratios else 0.0,
        "signed_ratio_max": max(signed_ratios) if signed_ratios else 0.0,
        "duty_cycle": open_petition_ticks / total_ticks if presided_ticks else 0.0,
        "ecart_mean": statistics.fmean(ecarts) if ecarts else 0.0,
        "ecart_max": max(ecarts) if ecarts else 0.0,
        "legitimacy_min": min(legitimacies) if legitimacies else float("nan"),
        "recalls_floor": sum(1 for e in recalled if e["payload"]["trigger"] == "legitimacy_floor"),
        "recalls_confidence_vote": sum(1 for e in recalled if e["payload"]["trigger"] == "confidence_vote"),
        "act_histogram": act_histogram,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=None)
    args = parser.parse_args()

    lines: list[str] = []

    def log(line: str) -> None:
        print(line, flush=True)
        lines.append(line)

    log("# Petition calibration sweep (v4 Lot 5)\n")
    log(
        "Shipped base_threshold_dist (beta(3,5)) / modulation_amplitude (0.5), per "
        "awakening_calibration_results.md: the acting cohort (past the awakening gate AND clearing "
        "its own blank_threshold) peaks at ~0.33 of the population early-term, against a shipped "
        "petition.signature_threshold of 0.25 -- reachable, narrowly, early-term only.\n"
    )
    log(
        "w_pet inherits the same amplification problem Lot 4 quantified for w_mob: "
        "w_pet/(1-decay_L) = 0.5/0.1 = 5x per unit of STANDING signed_ratio (petition_pressure has no "
        "decay term of its own, unlike street_pressure -- it is either the live signed_ratio or 0.0), "
        "so a petition that lingers open near its threshold costs L proportionally more per tick than "
        "an equivalent one-off mobilization spike.\n"
    )
    log(
        "| signature_threshold | lifespan | cooldown | modality | launched | expired | triggered | "
        "success rate | signed_ratio mean | signed_ratio max | duty cycle | ecart mean | ecart max | "
        "L min | recalls (floor) | recalls (confidence_vote) | act histogram |"
    )
    log("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

    never_triggers: list[str] = []
    always_triggers_on_launch: list[str] = []
    any_confidence_removal = False

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for signature_threshold in _SIGNATURE_THRESHOLDS:
            for lifespan in _LIFESPANS:
                for cooldown in _COOLDOWNS:
                    for modality in _MODALITIES:
                        label = f"{signature_threshold}-{lifespan}-{cooldown}-{modality}"
                        output_dir = tmp_path / label
                        result = run_one(output_dir, signature_threshold, lifespan, cooldown, modality)
                        log(
                            f"| {result['signature_threshold']} | {result['lifespan']} | {result['cooldown']} | "
                            f"{result['modality']} | {result['launched']} | {result['expired']} | "
                            f"{result['triggered']} | {result['success_rate']:.2f} | "
                            f"{result['signed_ratio_mean']:.3f} | {result['signed_ratio_max']:.3f} | "
                            f"{result['duty_cycle']:.3f} | {result['ecart_mean']:.3f} | "
                            f"{result['ecart_max']:.3f} | {result['legitimacy_min']:.3f} | "
                            f"{result['recalls_floor']} | {result['recalls_confidence_vote']} | "
                            f"{result['act_histogram']} |"
                        )
                        if result["launched"] > 0 and result["triggered"] == 0:
                            never_triggers.append(label)
                        if result["launched"] > 0 and result["triggered"] == result["launched"]:
                            always_triggers_on_launch.append(label)
                        if result["recalls_confidence_vote"] > 0:
                            any_confidence_removal = True

    log("\n## Headline questions\n")
    log(
        f"- Configs where the petition NEVER triggers a confidence vote despite launching: "
        f"{never_triggers if never_triggers else 'none'}."
    )
    log(
        f"- Configs where every launched petition triggers a confidence vote (a degenerate, "
        f"instant-trigger arm): {always_triggers_on_launch if always_triggers_on_launch else 'none'}."
    )
    log(
        f"- Does any confidence vote ever remove a president under the deterministic baseline? "
        f"{'YES' if any_confidence_removal else 'NO'} -- predicted NO by the keep_ratio == "
        f"mandate_strength identity (build_confidence_ballot's docstring); a YES would mean that "
        f"identity broke somewhere in this sweep and needs investigating before trusting it."
    )
    log(
        "- Does the hard floor still do all the recalling, making the confidence vote decorative "
        "until Lot 6? Compare the 'recalls (floor)' and 'recalls (confidence_vote)' columns above."
    )

    if args.results:
        args.results.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log(f"\n(full log written to {args.results})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
