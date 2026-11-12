"""
scripts/check_pressure_action_quality_pilot.py

Pilot for plan-decision-quality-validation.md's Group A quality-probe method
-- the actual v8 prerequisite (decision-quality validation, never started
since reasoning_budget_and_decision_quality_findings.md named it "the single
most important finding" on 2026-08-24), not fine-tuning itself.

Pre-registered criterion, written before any live call (plan-decision-
quality-validation.md's own "Critère pré-enregistré du pilote" section --
do not change this after seeing results):

    deterministic_pressure_action is a single binary gate (gap < blank_
    threshold -> NOTHING, else -> an act chosen by a rigid menu priority),
    not a graded scale. This pilot does NOT compare which specific lever
    (sign/launch/mobilize) the LLM picks against that rigid priority --
    that arbitration is this palier's own free-choice research question
    (§11.4), not something to validate against a baseline that is
    deliberately not what the LLM is supposed to reproduce. It checks the
    coarser, defensible question: ACT vs DON'T ACT, in the direction each
    citizen's own gap/blank_threshold relationship predicts.

    Unambiguous case (per citizen, not an absolute cutoff): gap <
    0.5*blank_threshold (NOTHING expected) or gap > 1.5*blank_threshold (an
    act expected, guaranteed by the deterministic rule whenever the pressure
    menu has mobilization_enabled=True -- see "both" arm below). Everything
    between is excluded from the agreement calculation.

        >= 90% agreement on unambiguous cases, disagreements explicable on
           inspection -> method validated, build the other 6 probes.
        ~10-20-25% disagreement -> grey zone, report honestly, no forced
           reading (same discipline as this week's ~50% stationarity test).
        > ~20-25% disagreement, OR a structural collapse signature (same
           act regardless of gap) -> method has a problem, stop, investigate
           before building anything else.

Config: run_acceptance_comparison.py's own "both" arm recipe verbatim
(ambition_threshold=0.0, legitimacy/awakening/mandate enabled, petition AND
mobilization both on) -- mobilization_enabled=True is what makes the
deterministic rule's gap>=threshold branch unconditionally an "act" (SIGN/
LAUNCH/MOBILIZE all real acts; only mobilization_enabled=False would let it
fall through to WAIT_FOR_ELECTION, itself a "no act" outcome) regardless of
can_sign/can_launch specifics -- which is why this script never needs to
reconstruct those two facts from the journal.

Usage:
    python fast_api_voter/scripts/check_pressure_action_quality_pilot.py \\
        --output-dir scripts/pressure_action_quality_pilot
"""
from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import generate_population  # noqa: E402
from api.domain.polity.config import PolityConfig, load_config  # noqa: E402
from api.domain.polity.indexer import read_journal  # noqa: E402
from api.domain.polity.run_polity_simulation import run_simulation  # noqa: E402

_ACTING_CODES = {1, 2, 3}  # SIGN_PETITION, LAUNCH_PETITION, MOBILIZE (codebook.PressureAct)


def pilot_config(output_dir: Path, duration_years: int, max_batch_replays: int = 2) -> PolityConfig:
    config = load_config()
    return dataclasses.replace(
        config,
        journal=dataclasses.replace(config.journal, output_dir=str(output_dir)),
        candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0),
        run=dataclasses.replace(config.run, duration_years=duration_years),
        legitimacy=dataclasses.replace(config.legitimacy, enabled=True),
        awakening=dataclasses.replace(config.awakening, enabled=True),
        mandate=dataclasses.replace(config.mandate, enabled=True),
        pressure_menu=dataclasses.replace(
            config.pressure_menu, electoral_only=False, petition_enabled=True, mobilization_enabled=True
        ),
        petition=dataclasses.replace(config.petition, enabled=True),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True),
        # Shipped default is 0 (no replay) -- every acceptance/reliability
        # script in this project overrides it; a single Mode A/B roll would
        # otherwise abort the whole run instead of retrying (as it just did).
        llm=dataclasses.replace(config.llm, enabled=True, max_batch_replays=max_batch_replays),
    )


def extract_cases(journal_path: Path, config: PolityConfig) -> list[dict]:
    citizens_by_id = {
        c.citizen_id: c
        for c in generate_population(config.citizens, config.run.population_size, config.run.seed)
    }
    cases = []
    for event in read_journal(journal_path):
        if event["event_type"] != "pressure_action" or not event.get("motif"):
            continue  # motif filter, not event_type alone -- deterministic-path events carry no motif
        ctx = event["payload"].get("ctx")
        if not ctx or ctx.get("self_gap") is None:
            continue
        cid = event["citizen_id"]
        citizen = citizens_by_id.get(cid)
        if citizen is None or citizen.blank_threshold <= 0:
            continue  # degenerate threshold, ratio undefined
        cases.append(
            {
                "cid": cid,
                "tick": event["tick"],
                "gap": ctx["self_gap"],
                "blank_threshold": citizen.blank_threshold,
                "act": event["payload"]["act"],
            }
        )
    return cases


def classify(cases: list[dict]) -> tuple[list[dict], list[dict]]:
    unambiguous, ambiguous = [], []
    for case in cases:
        ratio = case["gap"] / case["blank_threshold"]
        if ratio < 0.5:
            case["expected_act"] = False
        elif ratio > 1.5:
            case["expected_act"] = True
        else:
            ambiguous.append(case)
            continue
        case["actual_act"] = case["act"] in _ACTING_CODES
        case["agree"] = case["actual_act"] == case["expected_act"]
        unambiguous.append(case)
    return unambiguous, ambiguous


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-dir", type=Path, default=Path("scripts/pressure_action_quality_pilot"))
    parser.add_argument("--duration-years", type=int, default=4)
    parser.add_argument("--max-batch-replays", type=int, default=2)
    parser.add_argument(
        "--population-size", type=int, default=None,
        help="overrides run.population_size -- default None keeps the shipped config value",
    )
    args = parser.parse_args()

    config = pilot_config(args.output_dir, args.duration_years, args.max_batch_replays)
    if args.population_size is not None:
        config = dataclasses.replace(config, run=dataclasses.replace(config.run, population_size=args.population_size))
    print(f"running {args.duration_years}y pilot (llm=on, both menu, population_size={config.run.population_size}) -> {args.output_dir}")
    journal_path = run_simulation(config, run_id="pressure-action-quality-pilot")

    cases = extract_cases(journal_path, config)
    unambiguous, ambiguous = classify(cases)
    agree = [c for c in unambiguous if c["agree"]]
    disagree = [c for c in unambiguous if not c["agree"]]
    rate = len(agree) / len(unambiguous) if unambiguous else float("nan")

    distinct_consulted = {c["cid"] for c in cases}
    distinct_unambiguous = {c["cid"] for c in unambiguous}
    distinct_disagree = {c["cid"] for c in disagree}

    print(f"\ntotal LLM pressure_action decisions: {len(cases)} ({len(distinct_consulted)} distinct citizens)")
    print(f"unambiguous (|gap/threshold - 1| outside [0.5, 1.5]): {len(unambiguous)} ({len(distinct_unambiguous)} distinct citizens)")
    print(f"ambiguous (excluded): {len(ambiguous)}")
    print(f"agreement rate on unambiguous cases: {rate:.1%}" if unambiguous else "no unambiguous cases -- cannot conclude")
    print(
        f"\nconcentration: {len(disagree)} disagreement(s) among {len(distinct_disagree)} distinct citizen(s) "
        f"out of {len(distinct_unambiguous)} distinct unambiguous citizens "
        f"({len(distinct_disagree) / len(distinct_unambiguous):.1%} of the unambiguous population, "
        "not to be confused with the disagreement RATE above -- this is how concentrated vs. spread out "
        "the disagreements are across distinct individuals)" if distinct_unambiguous else ""
    )
    if disagree:
        print(f"\n{len(disagree)} disagreement(s), with blank_threshold for profile comparison:")
        for c in disagree:
            print(
                f"  cid={c['cid']} tick={c['tick']} gap={c['gap']:.3f} "
                f"blank_threshold={c['blank_threshold']:.3f} act={c['act']} "
                f"expected_act={c['expected_act']} actual_act={c['actual_act']}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
