"""
scripts/check_pressure_calibration_matrix.py

Phase C of the approved plan (polity-decision-contracts.md's pilot
correction for pressure_action): the decisive experiment matrix for the
diagnostic calibration builders added in llm_behavior_engine.py
(build_pressure_*_prompt_calibrated, PRESSURE_*_SIGNAL).

**Already measured this session -- not re-run here:**
  - production prompt (V0), batch 1  -> separation +0.000008 (check_
    logprob_pressure_action_gap_tracking_results.md's solo control)
  - production prompt (V0), batch 17 -> separation +0.004
  - act-mapping capability control, batch 1  -> separation +0.993
  - act-mapping capability control, batch 17 -> separation +0.0001
So the open cell this script fills is precisely: does CALIBRATION ALONE
(no rule, C4-compliant) work at batch 1, and does it survive larger
batches?

**Design choices, each responding to a specific measured failure mode
from earlier in this investigation:**

1. **Heterogeneous blank_threshold, drawn from generate_population.**
   Every earlier pressure_action probe this session used ONE fixed
   blank_threshold for the whole population. Under a fixed threshold,
   PRESSURE_PERCENTILE_SIGNAL's rank is monotone in self_gap AND in the
   proxy label -- it would measure nothing. A real population is required
   for that variant to be a real test.

2. **self_gap computed via the REAL formula**
   (accountability.self_gap = weighted_euclidean(citizen.issue_positions,
   officeholder.revealed_position, citizen.issue_priorities)), not
   assigned directly as in every prior script. This lets gap_vs_pledge
   and self_gap_prev_tick be computed the same way, from the same
   officeholder, rather than invented independently.

3. **Only unambiguous citizens are sent at all** (gap < 0.5*bt or
   gap > 1.5*bt, plan-decision-quality-validation.md's own definition) --
   selected from a large pool, never hand-tuned, same discipline as
   check_logprob_blank_calibration.py. This maximises statistical power
   per call and means the whole probe set IS the scored subset, with no
   separate "sent vs scored" bookkeeping to get wrong.

4. **Randomised composition, several trials per (variant, size), per-
   trial results reported -- never a single mean.** A wrong conclusion
   was nearly shipped earlier in this investigation
   (check_pressure_missing_threshold_results.md) from a batch built with
   a regular alternating pattern that let the model pattern-complete
   instead of reading values. Every batch here is an independently
   randomised subset in randomised order.

5. **One open-menu follow-up**, not a full open-menu cross of the whole
   matrix (the plan calls for "one arm"): after the closed-menu matrix
   completes, whichever (variant, size) cell scored highest is re-run
   under the opened menu, to check the closed menu's own two-option shape
   is not doing the work.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_pressure_calibration_matrix.py
"""
from __future__ import annotations

import dataclasses
import os
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.accountability import weighted_euclidean  # noqa: E402
from api.domain.polity.citizen import Citizen, generate_population  # noqa: E402
from api.domain.polity.codebook import PressureAct  # noqa: E402
from api.domain.polity.config import PressureMenuConfig, load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PRESSURE_HISTORY_SIGNAL,
    PRESSURE_PERCENTILE_SIGNAL,
    PRESSURE_PLEDGE_SIGNAL,
    PRESSURE_THRESHOLD_SIGNAL,
    PressureContext,
    build_pressure_system_prompt_calibrated,
    build_pressure_user_prompt_calibrated,
    compute_max_tokens,
    menu_acts,
)
from api.domain.polity.llm_client import VllmJsonClient  # noqa: E402
from api.domain.polity.llm_logprob_instrumentation import (  # noqa: E402
    LogprobAlignmentError,
    binary_probability,
    candidate_probability,
    locate_decision_field_logprobs,
)
from api.domain.polity.llm_schemas import PRESSURE_JSON_SCHEMA  # noqa: E402

_TARGET_CID = 999
_TICKS_TO_ELECTION = 10
_SIZES = [1, 5, 25]
_TRIALS = 3
_POOL_SIZE = 300

_VARIANTS = {
    "V1_threshold": [PRESSURE_THRESHOLD_SIGNAL],
    "V3_history": [PRESSURE_HISTORY_SIGNAL],
    "V4_threshold+history": [PRESSURE_THRESHOLD_SIGNAL, PRESSURE_HISTORY_SIGNAL],
    "V2_percentile": [PRESSURE_PERCENTILE_SIGNAL],
    "V5_pledge": [PRESSURE_PLEDGE_SIGNAL],
}


def _vllm_config():
    shipped = load_config()
    model = os.environ.get("POLITY_PROBE_MODEL", shipped.llm.model)
    return dataclasses.replace(
        shipped,
        llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1", model=model),
    )


def _make_officeholder(issue_count: int) -> tuple[Citizen, tuple[float, ...]]:
    """A fixed, documented officeholder: pledged the centre of the issue
    space, then drifted by +0.3 in every dimension (clamped to [0,1]).
    Returns (officeholder, prev_tick_revealed_position) -- the previous
    position is a half-drift, standing in for "one tick less drifted"."""
    pledged = tuple(0.5 for _ in range(issue_count))
    revealed = tuple(min(1.0, p + 0.3) for p in pledged)
    prev_revealed = tuple(min(1.0, p + 0.15) for p in pledged)
    officeholder = Citizen(
        citizen_id=_TARGET_CID,
        issue_positions=pledged,
        issue_priorities=tuple(1.0 / issue_count for _ in range(issue_count)),
        blank_threshold=0.5,
        ambition_score=0.5,
    )
    officeholder.pledged_platform = pledged
    officeholder.revealed_position = revealed
    return officeholder, prev_revealed


def _classify(pool: list[Citizen], officeholder: Citizen) -> tuple[list[Citizen], list[Citizen], dict[int, float]]:
    """Splits the pool into (unambiguous-below, unambiguous-above) per
    plan-decision-quality-validation.md's own definition, relative to each
    citizen's OWN blank_threshold -- never a population-wide constant.
    Ambiguous citizens are dropped, not sent."""
    below, above = [], []
    gaps: dict[int, float] = {}
    for citizen in pool:
        gap = weighted_euclidean(citizen.issue_positions, officeholder.revealed_position, citizen.issue_priorities)
        gaps[citizen.citizen_id] = gap
        if gap < 0.5 * citizen.blank_threshold:
            below.append(citizen)
        elif gap > 1.5 * citizen.blank_threshold:
            above.append(citizen)
    return below, above, gaps


def _percentile_ranks(values: dict[int, float]) -> dict[int, float]:
    ordered = sorted(values, key=lambda cid: values[cid])
    n = len(ordered)
    return {cid: (100.0 * rank / (n - 1) if n > 1 else 50.0) for rank, cid in enumerate(ordered)}


def _signal_values(
    signals, batch: list[Citizen], gaps: dict[int, float], gaps_prev: dict[int, float], gaps_pledge: dict[int, float],
) -> dict[str, dict[int, float]]:
    values: dict[str, dict[int, float]] = {}
    for signal in signals:
        if signal is PRESSURE_THRESHOLD_SIGNAL:
            values[signal.field] = {c.citizen_id: c.blank_threshold for c in batch}
        elif signal is PRESSURE_HISTORY_SIGNAL:
            values[signal.field] = {c.citizen_id: gaps_prev[c.citizen_id] for c in batch}
        elif signal is PRESSURE_PERCENTILE_SIGNAL:
            values[signal.field] = _percentile_ranks({c.citizen_id: gaps[c.citizen_id] for c in batch})
        elif signal is PRESSURE_PLEDGE_SIGNAL:
            values[signal.field] = {c.citizen_id: gaps_pledge[c.citizen_id] for c in batch}
        else:
            raise ValueError(f"unhandled signal {signal!r}")
    return values


def _run_batch(
    client, config, signals, batch: list[Citizen], contexts: dict[int, PressureContext], open_menu: bool,
    gaps: dict[int, float], gaps_prev: dict[int, float], gaps_pledge: dict[int, float],
):
    system_prompt = build_pressure_system_prompt_calibrated(batch, config, signals)
    user_prompt = build_pressure_user_prompt_calibrated(
        batch, contexts, _signal_values(signals, batch, gaps, gaps_prev, gaps_pledge),
    )
    content, tokens = client.complete_json_with_logprobs(
        system_prompt=system_prompt, user_prompt=user_prompt,
        json_schema=PRESSURE_JSON_SCHEMA, max_tokens=compute_max_tokens(len(batch)),
        think=False, top_logprobs=10,
    )
    probes = locate_decision_field_logprobs(content, tokens, field="act")
    results = {}
    for probe in probes:
        if open_menu:
            p_act = sum(candidate_probability(probe.token, str(a)) for a in (1, 2, 3, 4))
            p_nothing = candidate_probability(probe.token, "0")
            total = p_act + p_nothing
            p_should_act = p_act / total if total > 0 else 0.5
        else:
            p_should_act = binary_probability(
                probe.token, true_value=str(int(PressureAct.WAIT_FOR_ELECTION)),
                false_value=str(int(PressureAct.NOTHING)),
            )
        results[probe.cid] = (p_should_act, probe.token.token)
    return results


def _score(batch: list[Citizen], expect_above: set[int], results: dict[int, tuple[float, str]]):
    correct = 0
    histogram: dict[str, int] = {}
    for citizen in batch:
        if citizen.citizen_id not in results:
            continue
        p_should_act, chosen = results[citizen.citizen_id]
        histogram[chosen] = histogram.get(chosen, 0) + 1
        predicted_should_act = p_should_act > 0.5
        actually_should_act = citizen.citizen_id in expect_above
        if predicted_should_act == actually_should_act:
            correct += 1
    return correct, len(results), histogram


def _verdict(agreement: float) -> str:
    if agreement >= 0.90:
        return "PASS"
    if agreement >= 0.75:
        return "GREY"
    return "FAIL"


def main() -> int:
    config = _vllm_config()
    assert menu_acts(config.pressure_menu) == (0, 4)
    issue_count = config.citizens.issue_count

    officeholder, prev_revealed = _make_officeholder(issue_count)
    pool = generate_population(config.citizens, _POOL_SIZE, config.run.seed)

    below, above, gaps = _classify(pool, officeholder)
    gaps_prev = {
        c.citizen_id: weighted_euclidean(c.issue_positions, prev_revealed, c.issue_priorities) for c in pool
    }
    gaps_pledge = {
        c.citizen_id: weighted_euclidean(c.issue_positions, officeholder.pledged_platform, c.issue_priorities)
        for c in pool
    }
    unambiguous = below + above
    expect_above = {c.citizen_id for c in above}

    print(f"pool={len(pool)}  unambiguous-below={len(below)}  unambiguous-above={len(above)}  "
          f"model={config.llm.model}")
    if len(below) < 13 or len(above) < 13:
        print("WARNING: fewer than 13 citizens on one side -- batch 25 will not be balanced.")

    best: tuple[float, str, int] | None = None  # (mean_accuracy, variant, size)
    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for variant_name, signals in _VARIANTS.items():
            print(f"\n===== {variant_name} =====")
            for size in _SIZES:
                if variant_name == "V2_percentile" and size == 1:
                    print(f"  size={size:>2}: n/a -- percentile is undefined for a cohort of one")
                    continue
                rates = []
                combined_histogram: dict[str, int] = {}
                for trial in range(_TRIALS):
                    rng = random.Random(f"{config.run.seed}|{variant_name}|{size}|{trial}")
                    # Real defect fixed 2026-09-11 (Track B6, lets-build-a-solid-spicy-otter.md):
                    # `half = size // 2` gave the odd remainder to `above` unconditionally, so at
                    # size=1 (half=0) every trial sampled ONLY from the unambiguous-HIGH pole,
                    # never `below` -- a constant "act" answer scores 100% there by construction,
                    # which is not evidence of calibration working. Randomize which pole gets the
                    # remainder instead of hardcoding it, so size=1 actually alternates poles
                    # across trials rather than being structurally one-sided.
                    half = size // 2
                    remainder = size - half
                    if size % 2 == 1 and rng.random() < 0.5:
                        below_n, above_n = remainder, half
                    else:
                        below_n, above_n = half, remainder
                    chosen = rng.sample(below, min(below_n, len(below))) + rng.sample(above, min(above_n, len(above)))
                    if len(chosen) < size:
                        chosen += rng.sample([c for c in unambiguous if c not in chosen], size - len(chosen))
                    rng.shuffle(chosen)
                    contexts = {
                        c.citizen_id: PressureContext(
                            cid=c.citizen_id, target=_TARGET_CID, self_gap=gaps[c.citizen_id],
                            mandate_dev=weighted_euclidean(
                                officeholder.pledged_platform, officeholder.revealed_position, officeholder.issue_priorities,
                            ),
                            ticks_to_election=_TICKS_TO_ELECTION, available=(0, 4),
                            petition_open=False, petition_expires_at_tick=None, already_signed=False,
                            neighbors_acting=None,
                        )
                        for c in chosen
                    }
                    try:
                        results = _run_batch(
                            client, config, signals, chosen, contexts, False, gaps, gaps_prev, gaps_pledge,
                        )
                    except LogprobAlignmentError as exc:
                        print(f"  size={size:>2} trial={trial}: ALIGNMENT FAILED: {exc}")
                        continue
                    correct, n, histogram = _score(chosen, expect_above, results)
                    rates.append(correct / n if n else 0.0)
                    for act, count in histogram.items():
                        combined_histogram[act] = combined_histogram.get(act, 0) + count
                if not rates:
                    continue
                mean = statistics.fmean(rates)
                verdict = _verdict(min(rates)) if len(rates) > 1 else _verdict(mean)
                cells = "  ".join(f"{r:>5.0%}" for r in rates)
                print(f"  size={size:>2}: {cells:>22}  mean={mean:>5.0%}  verdict={verdict}  "
                      f"act histogram (pooled over trials)={combined_histogram}")
                if best is None or mean > best[0]:
                    best = (mean, variant_name, size)

    if best is None:
        print("\nNo cell produced a result -- nothing to follow up with an open-menu check.")
        return 1

    best_mean, best_variant, best_size = best
    print(f"\n===== open-menu follow-up on the best closed-menu cell: {best_variant} @ size={best_size} "
          f"(closed-menu mean {best_mean:.0%}) =====")
    open_config = dataclasses.replace(
        config, pressure_menu=PressureMenuConfig(petition_enabled=True, mobilization_enabled=True, electoral_only=False),
    )
    open_legal = menu_acts(open_config.pressure_menu)
    signals = _VARIANTS[best_variant]
    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        rates = []
        for trial in range(_TRIALS):
            rng = random.Random(f"{config.run.seed}|open|{best_variant}|{best_size}|{trial}")
            half = best_size // 2
            chosen = rng.sample(below, min(half, len(below))) + rng.sample(above, min(best_size - half, len(above)))
            if len(chosen) < best_size:
                chosen += rng.sample([c for c in unambiguous if c not in chosen], best_size - len(chosen))
            rng.shuffle(chosen)
            contexts = {
                c.citizen_id: PressureContext(
                    cid=c.citizen_id, target=_TARGET_CID, self_gap=gaps[c.citizen_id],
                    mandate_dev=weighted_euclidean(
                        officeholder.pledged_platform, officeholder.revealed_position, officeholder.issue_priorities,
                    ),
                    ticks_to_election=_TICKS_TO_ELECTION, available=open_legal,
                    petition_open=False, petition_expires_at_tick=None, already_signed=False,
                    neighbors_acting=None,
                )
                for c in chosen
            }
            try:
                results = _run_batch(
                    client, open_config, signals, chosen, contexts, True, gaps, gaps_prev, gaps_pledge,
                )
            except LogprobAlignmentError as exc:
                print(f"  trial={trial}: ALIGNMENT FAILED: {exc}")
                continue
            correct, n, histogram = _score(chosen, expect_above, results)
            rates.append(correct / n if n else 0.0)
            print(f"  trial={trial}: {correct}/{n} correct, act histogram={histogram}")
    if rates:
        print(f"  open-menu mean = {statistics.fmean(rates):.0%}  "
              f"(closed-menu mean for the same cell was {best_mean:.0%})")

    print("\nVerdict bar (plan-decision-quality-validation.md): PASS >=90% agreement, "
          "GREY 75-90%, FAIL below -- computed here on unambiguous cases only, using min(rates) "
          "as the verdict input (not the mean) so a single bad trial cannot be averaged away.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
