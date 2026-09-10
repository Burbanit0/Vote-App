"""
scripts/check_logprob_pressure_action_gap_tracking.py

plan-llm-protocol-and-theory-program.md §5.C, first application of the
validated logprob instrument (check_logprob_blank_calibration.py) to a
decision type with NO ground truth: pressure_action (dt=10), the project's
own named §5.C target and one of the four "lands on another agent" types
§2's collapse hypothesis flags.

The specific, precisely-scoped open question this answers -- named
verbatim in decide_pressure_actions's own docstring and never measured
before now: "Under the SHIPPED (closed) menu, pressure_action's real task
is only choosing between 0 and 4; whether it tracks self_gap across that
pair has not been measured either." Under the shipped default config
(pressure_menu.electoral_only=true), menu_acts() legally allows ONLY
{0=NOTHING, 4=WAIT_FOR_ELECTION} -- the exact "forced binary choice"
complete_with_logprobs's own docstring already alludes to. This runs the
REAL production prompt builders (build_pressure_system_prompt/
build_pressure_user_prompt), the real PRESSURE_JSON_SCHEMA, think=False
(decide_pressure_actions's own production value), unmodified shipped
config -- and reads P(act=4) directly instead of a single categorical
draw, across citizens whose self_gap spans well below to well above their
own blank_threshold, including near-boundary cases the first §5.C
application (vote_cast blank calibration) deliberately flagged as an
open gap.

Only self_gap varies across the probe set; mandate_dev/ticks_to_election
are held fixed so any P(act=4) variation attributes to self_gap alone.
`simple_rules.deterministic_pressure_action` (the project's own §11.4
baseline/proxy, NOT ground truth -- explicitly documented as a modelling
assumption in decide_pressure_actions's own docstring) provides a
reference direction, not an accuracy bar to clear.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_logprob_pressure_action_gap_tracking.py
"""
from __future__ import annotations

import dataclasses
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.codebook import PressureAct  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PressureContext,
    build_pressure_system_prompt,
    build_pressure_user_prompt,
    compute_max_tokens,
    menu_acts,
)
from api.domain.polity.llm_client import VllmJsonClient  # noqa: E402
from api.domain.polity.llm_logprob_instrumentation import (  # noqa: E402
    LogprobAlignmentError,
    binary_probability,
    locate_decision_field_logprobs,
)
from api.domain.polity.llm_schemas import PRESSURE_JSON_SCHEMA  # noqa: E402
from api.domain.polity.simple_rules import deterministic_pressure_action  # noqa: E402

_TARGET_CID = 999  # a synthetic officeholder id; ctx never carries the target's own data
_BLANK_THRESHOLD = 0.5
_MANDATE_DEV = 0.1  # fixed across every probe citizen -- isolates self_gap's own effect
_TICKS_TO_ELECTION = 10

# Deliberately spans three regimes: clearly satisfied (self_gap << threshold),
# near-boundary on both sides (the case check_logprob_blank_calibration.py's
# own results doc flagged as untested), and clearly discontented (self_gap >>
# threshold) -- "wildly different citizens" per §5.C's own collapse-detection
# framing, plus the specific hard case a clean two-pole sample skips.
_SELF_GAPS = [
    0.02, 0.05, 0.08, 0.10, 0.15, 0.18,      # clearly satisfied
    0.42, 0.47,                               # boundary, below threshold
    0.53, 0.58,                               # boundary, above threshold
    0.60, 0.80, 1.00, 1.30, 1.60, 1.90, 2.20, # clearly discontented
]


def _vllm_config():
    """`POLITY_PROBE_MODEL` overrides llm.model so this probe can be pointed
    at a bench server (docker-compose.llm-4b.yml, §2bis's base-vs-instruct
    arms) without editing the shipped polity_config.yaml. Unset, it uses the
    shipped model exactly as before -- every measurement already recorded
    against this script was taken on that default path."""
    shipped = load_config()
    model = os.environ.get("POLITY_PROBE_MODEL", shipped.llm.model)
    return dataclasses.replace(
        shipped,
        llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1", model=model),
    )


def _probe_citizen(cid: int, self_gap: float) -> tuple[Citizen, PressureContext]:
    citizen = Citizen(
        citizen_id=cid,
        issue_positions=tuple((cid * 0.017 + d * 0.013) % 1.0 for d in range(20)),
        issue_priorities=tuple(1.0 / 20 for _ in range(20)),
        blank_threshold=_BLANK_THRESHOLD,
        ambition_score=0.5,
    )
    context = PressureContext(
        cid=cid,
        target=_TARGET_CID,
        self_gap=self_gap,
        mandate_dev=_MANDATE_DEV,
        ticks_to_election=_TICKS_TO_ELECTION,
        available=(0, 4),
        petition_open=False,
        petition_expires_at_tick=None,
        already_signed=False,
        neighbors_acting=None,
    )
    return citizen, context


def main() -> int:
    config = _vllm_config()
    assert menu_acts(config.pressure_menu) == (0, 4), (
        f"expected the shipped config's pressure_menu to legally allow only "
        f"{{0,4}}, got {menu_acts(config.pressure_menu)} -- this script's whole "
        f"premise (a genuine binary choice) depends on the electoral_only default"
    )

    citizens = []
    contexts: dict[int, PressureContext] = {}
    proxy: dict[int, int] = {}
    for i, gap in enumerate(_SELF_GAPS):
        cid = 4000 + i
        citizen, context = _probe_citizen(cid, gap)
        citizens.append(citizen)
        contexts[cid] = context
        proxy[cid] = int(deterministic_pressure_action(citizen, gap, config.pressure_menu))

    print(f"pressure_action gap-tracking probe: {len(citizens)} citizens, self_gap "
          f"{min(_SELF_GAPS)}-{max(_SELF_GAPS)}, blank_threshold={_BLANK_THRESHOLD} (fixed), "
          f"legal acts={menu_acts(config.pressure_menu)}")

    system_prompt = build_pressure_system_prompt(citizens, config)
    user_prompt = build_pressure_user_prompt(citizens, contexts)
    max_tokens = compute_max_tokens(len(citizens))

    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        content, tokens = client.complete_json_with_logprobs(
            system_prompt=system_prompt, user_prompt=user_prompt,
            json_schema=PRESSURE_JSON_SCHEMA, max_tokens=max_tokens,
            think=False,  # decide_pressure_actions's own production value for this decision type
            top_logprobs=10,
        )

    try:
        probes = locate_decision_field_logprobs(content, tokens, field="act")
    except LogprobAlignmentError as exc:
        print(f"ALIGNMENT FAILED: {exc}")
        return 1

    rows = []
    for probe in probes:
        gap = contexts[probe.cid].self_gap
        p_wait = binary_probability(probe.token, true_value=str(int(PressureAct.WAIT_FOR_ELECTION)), false_value=str(int(PressureAct.NOTHING)))
        rows.append((gap, probe.cid, p_wait, probe.token.token, proxy[probe.cid]))

    print(f"\n{'self_gap':>9}  {'cid':>5}  {'P(act=4)':>9}  {'chosen_act':>10}  {'proxy':>18}")
    for gap, cid, p_wait, chosen, proxy_act in sorted(rows):
        proxy_label = PressureAct(proxy_act).name
        print(f"{gap:>9.2f}  {cid:>5}  {p_wait:>9.6f}  {chosen:>10}  {proxy_label:>18}")

    print(f"\naligned decisions: {len(rows)}/{len(citizens)}")
    below = [p for g, _, p, _, _ in rows if g < _BLANK_THRESHOLD]
    above = [p for g, _, p, _, _ in rows if g >= _BLANK_THRESHOLD]
    if below and above:
        mean_below = sum(below) / len(below)
        mean_above = sum(above) / len(above)
        print(f"mean P(act=4) | self_gap < blank_threshold:  {mean_below:.6f}  (n={len(below)})")
        print(f"mean P(act=4) | self_gap >= blank_threshold: {mean_above:.6f}  (n={len(above)})")
        print(f"separation (higher is better discrimination): {mean_above - mean_below:+.6f}")
    # Monotonicity: does P(act=4) rise as self_gap rises? A content-blind
    # collapse would show near-zero correlation regardless of sign.
    ordered = sorted(rows)
    ps = [p for _, _, p, _, _ in ordered]
    n = len(ps)
    if n > 1 and len(set(round(p, 6) for p in ps)) > 1:
        mean_p = sum(ps) / n
        gaps_only = [g for g, _, _, _, _ in ordered]
        mean_g = sum(gaps_only) / n
        cov = sum((g - mean_g) * (p - mean_p) for g, p in zip(gaps_only, ps))
        var_g = sum((g - mean_g) ** 2 for g in gaps_only)
        var_p = sum((p - mean_p) ** 2 for p in ps)
        if var_g > 0 and var_p > 0:
            corr = cov / (var_g * var_p) ** 0.5
            print(f"Pearson correlation(self_gap, P(act=4)): {corr:+.4f}")
    else:
        print("P(act=4) is IDENTICAL (to 6 decimals) across every citizen regardless of self_gap "
              "-- this IS the content-blind collapse, quantified rather than inferred.")

    # Batching control: this project has independently found a real
    # batching-specific collapse before (vote_cast's own "chunk 4+ ignores
    # each voter's own distances" finding, historical on Ollama) -- a flat
    # P(act=4) across 17 citizens in ONE call could be that pattern rather
    # than a property of the decision itself. Re-run the two most extreme
    # self_gap values completely ALONE (chunk_size=1, decide_pressure_
    # actions's own min_batch_size floor) to see if the same flatness
    # survives outside a batch.
    print("\n== batching control: the two most extreme self_gap values, solo (chunk_size=1) ==")
    extreme_gaps = sorted({gap for gap, *_ in [min(rows), max(rows)]})
    solo_rows = []
    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for i, gap in enumerate(extreme_gaps):
            cid = 5000 + i
            citizen, context = _probe_citizen(cid, gap)
            solo_system_prompt = build_pressure_system_prompt([citizen], config)
            solo_user_prompt = build_pressure_user_prompt([citizen], {cid: context})
            solo_content, solo_tokens = client.complete_json_with_logprobs(
                system_prompt=solo_system_prompt, user_prompt=solo_user_prompt,
                json_schema=PRESSURE_JSON_SCHEMA, max_tokens=compute_max_tokens(1),
                think=False, top_logprobs=10,
            )
            try:
                solo_probes = locate_decision_field_logprobs(solo_content, solo_tokens, field="act")
            except LogprobAlignmentError as exc:
                print(f"  ALIGNMENT FAILED for solo self_gap={gap}: {exc}")
                continue
            p_wait = binary_probability(
                solo_probes[0].token,
                true_value=str(int(PressureAct.WAIT_FOR_ELECTION)), false_value=str(int(PressureAct.NOTHING)),
            )
            solo_rows.append((gap, p_wait, solo_probes[0].token.token))
            print(f"  self_gap={gap:.2f}  P(act=4)={p_wait:.6f}  chosen_act={solo_probes[0].token.token}")

    if len(solo_rows) == 2:
        solo_low, solo_high = sorted(solo_rows)
        print(f"\nsolo separation (high-self_gap minus low-self_gap): {solo_high[1] - solo_low[1]:+.6f}")
        print("Compare against the batch separation above -- if the solo separation is also "
              "near-zero, the flatness is not a batching artifact.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
