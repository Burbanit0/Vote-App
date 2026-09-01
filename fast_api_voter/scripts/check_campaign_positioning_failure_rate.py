"""
scripts/check_campaign_positioning_failure_rate.py

plan-adversarial-framing-collapse.md's campaign_positioning section, follow-up per user decision
(2026-08-31): decide_campaign_positioning's own docstring (llm_behavior_engine.py:1396-1410)
claims think=True + _POSITIONING_THINK_TOKEN_ALLOWANCE=8000 gives "5/5 correct batches" and
resolves the earlier think=False degenerate-batch bug cleanly. check_campaign_positioning_
collapse_signature.py's n=6 run (2026-08-31, same protocol, same budget) found 3/6 failures (50%)
-- a truncation and two cid/motif-swap misalignments. This script re-measures the failure rate at
a larger n (16 per pole, 32 total -- the harness's own sample_size.required_sample_size for
resolving "is the true rate above 25%?" at 95% confidence against a 0.5 point estimate) to tell
whether that 50% was real or small-n noise, per the user's own explicit choice over just
documenting the discrepancy or leaving it alone.

Same selection method as the n=6 script (population=300, sorted by distance to the electorate
mean, most-extreme citizens per pole), same think=True/size=1/8000-token-allowance protocol,
extended to more nominees per pole. Pre-registered: experiment 20260831T233502Z-586e3c0e.

Usage:
    python fast_api_voter/scripts/check_campaign_positioning_failure_rate.py <experiment_id>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.citizen import Citizen, generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    build_positioning_system_prompt,
    build_positioning_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import OllamaJsonClient, decode_positioning_batch  # noqa: E402
from api.domain.polity.llm_schemas import POSITIONING_JSON_SCHEMA  # noqa: E402
from api.domain.polity.parties import initialize_parties  # noqa: E402
from api.domain.polity.simple_rules import assign_party_affiliation  # noqa: E402
from llm_test_harness import trial  # noqa: E402

_POPULATION_SIZE = 300
_THINK_TOKEN_ALLOWANCE = 8000
_N_PER_POLE = 16


def _electorate_mean(population: list[Citizen]) -> tuple[float, ...]:
    issue_count = len(population[0].issue_positions)
    sums = [0.0] * issue_count
    for c in population:
        for i, v in enumerate(c.issue_positions):
            sums[i] += v
    return tuple(s / len(population) for s in sums)


def _classify_failure(message: str) -> str:
    if "finish_reason='length'" in message or "finish_reason=\"length\"" in message:
        return "truncation"
    if "batch misaligned" in message:
        return "cid_motif_leak_or_misalignment"
    return "other"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: check_campaign_positioning_failure_rate.py <experiment_id>")
        return 1
    experiment_id = sys.argv[1]

    config = load_config()
    population = list(generate_population(config.citizens, _POPULATION_SIZE, config.run.seed))
    parties = initialize_parties(population, config.parties.initial_count, config.run.seed)
    for c in population:
        c.party_affiliation = assign_party_affiliation(c, parties)
    parties_by_id = {p.party_id: p for p in parties}
    mean = _electorate_mean(population)

    ranked = sorted(population, key=lambda c: math.dist(c.issue_positions, mean))
    aligned = ranked[:_N_PER_POLE]
    far = ranked[-_N_PER_POLE:]

    failure_modes: dict[str, int] = {}
    pole_failures: dict[str, int] = {"FAR": 0, "ALIGNED": 0}
    pole_totals: dict[str, int] = {"FAR": 0, "ALIGNED": 0}
    trial_index = 0

    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for pole_label, pole_key, nominees in (
            ("FAR from electorate mean", "FAR", far),
            ("ALIGNED with electorate mean", "ALIGNED", aligned),
        ):
            print(f"\n########## {pole_label} ##########")
            for nominee in nominees:
                trial_index += 1
                dist = math.dist(nominee.issue_positions, mean)
                pole_totals[pole_key] += 1

                def run_call(
                    nominee: Citizen = nominee, dist: float = dist, pole_key: str = pole_key,
                ) -> trial.TrialResult:
                    try:
                        raw = client.complete_json(
                            system_prompt=build_positioning_system_prompt([nominee], config),
                            user_prompt=build_positioning_user_prompt([nominee], parties_by_id, mean),
                            json_schema=POSITIONING_JSON_SCHEMA,
                            max_tokens=compute_max_tokens(1) + _THINK_TOKEN_ALLOWANCE,
                            think=True,
                        )
                        decision = decode_positioning_batch(raw, [nominee.citizen_id])[0]
                        shift_content = tuple(sorted((s.dimension, s.delta) for s in decision.shifts))
                        print(
                            f"  cid={nominee.citizen_id} dist_to_mean={dist:.4f} -> "
                            f"shifts={len(decision.shifts)} content={shift_content} motif={decision.motif}"
                        )
                        return trial.TrialResult(
                            ok=True, finish_reason="stop", truncated=False, decoded_tokens=None,
                            detail=json.dumps({
                                "cid": nominee.citizen_id, "pole": pole_key, "dist_to_mean": round(dist, 4),
                                "shifts": len(decision.shifts), "content": list(shift_content),
                                "motif": decision.motif, "failure_mode": None,
                            }, sort_keys=True, default=str),
                        )
                    except Exception as exc:  # noqa: BLE001 -- a failure IS the measurement here
                        message = str(exc)
                        mode = _classify_failure(message)
                        failure_modes[mode] = failure_modes.get(mode, 0) + 1
                        pole_failures[pole_key] += 1
                        print(f"  cid={nominee.citizen_id} dist_to_mean={dist:.4f} FAILED ({mode}): {message}")
                        return trial.TrialResult(
                            ok=False, finish_reason=("length" if mode == "truncation" else "error"),
                            truncated=(mode == "truncation"), decoded_tokens=None,
                            detail=json.dumps({
                                "cid": nominee.citizen_id, "pole": pole_key, "dist_to_mean": round(dist, 4),
                                "failure_mode": mode, "error": message,
                            }, sort_keys=True, default=str),
                        )

                trial.record_trial(experiment_id, trial_index, container_name="ollama-polity", run_call=run_call)

    total = pole_totals["FAR"] + pole_totals["ALIGNED"]
    total_failures = pole_failures["FAR"] + pole_failures["ALIGNED"]
    rate = total_failures / total if total else 0.0

    print("\n--- result ---")
    print(f"FAR pole: {pole_failures['FAR']}/{pole_totals['FAR']} failed")
    print(f"ALIGNED pole: {pole_failures['ALIGNED']}/{pole_totals['ALIGNED']} failed")
    print(f"overall failure rate: {total_failures}/{total} ({rate:.1%})")
    print(f"failure modes: {failure_modes}")
    print("pre-registered threshold: failure_rate >= 25% -> docstring's '5/5 clean' claim is false for size=1")
    print("MEETS" if rate >= 0.25 else "BELOW", "the pre-registered threshold")
    print(f"All {total} trials recorded under experiment {experiment_id}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
