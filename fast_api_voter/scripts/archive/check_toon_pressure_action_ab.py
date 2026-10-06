"""
scripts/check_toon_pressure_action_ab.py

plan-llm-protocol-and-theory-program.md §5.E's own blocking reservation on
pressure_action: "Changing its prompt format invalidates every prior
collapse measurement on it ... So the TOON test there must be PAIRED
WITH §5.C's logprob instrumentation (measure P(act) before and after),
or it produces a new prompt with no comparable baseline."

This reuses check_logprob_pressure_action_gap_tracking.py's own probe
EXACTLY (same 17 self_gap points spanning clearly-satisfied to clearly-
discontented, same target/mandate_dev/ticks_to_election, same shipped
closed menu) and runs it through BOTH build_pressure_system_prompt/
build_pressure_user_prompt (JSON, the production shape) and
build_pressure_system_prompt_toon/build_pressure_user_prompt_toon (TOON,
which additionally hoists target/mandate_dev/ticks_to_election/available/
petition/neighbors_acting out of the per-citizen rows -- see that
function's own docstring for why that hoist is architecturally correct
under the shipped config, not an artifact of this probe's own
construction). Reads P(act=4) via the same locate_decision_field_logprobs
+ binary_probability instrument already validated this session, so the
"before" and "after" readings are directly comparable, not just each
individually plausible.

Two gates, exactly matching check_toon_candidacy_ab.py's own discipline:
(a) token count via count_prompt_tokens; (b) here, decision quality is
read as the P(act=4) GRADIENT itself (not a ground-truth accuracy, since
none exists for this type) -- does TOON preserve, worsen, or somehow
rescue the flat, collapsed signal the JSON baseline already measured?

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_toon_pressure_action_ab.py
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.codebook import PressureAct  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PressureContext,
    build_pressure_system_prompt,
    build_pressure_system_prompt_toon,
    build_pressure_user_prompt,
    build_pressure_user_prompt_toon,
    compute_max_tokens,
    menu_acts,
)
from api.domain.polity.llm_client import VllmJsonClient, decode_pressure_batch  # noqa: E402
from api.domain.polity.llm_logprob_instrumentation import (  # noqa: E402
    LogprobAlignmentError,
    binary_probability,
    locate_decision_field_logprobs,
)
from api.domain.polity.llm_schemas import PRESSURE_JSON_SCHEMA  # noqa: E402

# Verbatim from check_logprob_pressure_action_gap_tracking.py, for direct comparability.
_TARGET_CID = 999
_BLANK_THRESHOLD = 0.5
_MANDATE_DEV = 0.1
_TICKS_TO_ELECTION = 10
_SELF_GAPS = [
    0.02, 0.05, 0.08, 0.10, 0.15, 0.18,
    0.42, 0.47,
    0.53, 0.58,
    0.60, 0.80, 1.00, 1.30, 1.60, 1.90, 2.20,
]


def _vllm_config():
    shipped = load_config()
    return dataclasses.replace(shipped, llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1"))


def _probe_citizen(cid: int, self_gap: float) -> tuple[Citizen, PressureContext]:
    citizen = Citizen(
        citizen_id=cid,
        issue_positions=tuple((cid * 0.017 + d * 0.013) % 1.0 for d in range(20)),
        issue_priorities=tuple(1.0 / 20 for _ in range(20)),
        blank_threshold=_BLANK_THRESHOLD,
        ambition_score=0.5,
    )
    context = PressureContext(
        cid=cid, target=_TARGET_CID, self_gap=self_gap, mandate_dev=_MANDATE_DEV,
        ticks_to_election=_TICKS_TO_ELECTION, available=(0, 4),
        petition_open=False, petition_expires_at_tick=None, already_signed=False, neighbors_acting=None,
    )
    return citizen, context


def main() -> int:
    config = _vllm_config()
    assert menu_acts(config.pressure_menu) == (0, 4)

    citizens = []
    contexts: dict[int, PressureContext] = {}
    for i, gap in enumerate(_SELF_GAPS):
        cid = 8000 + i
        citizen, context = _probe_citizen(cid, gap)
        citizens.append(citizen)
        contexts[cid] = context
    expected_cids = [c.citizen_id for c in citizens]

    print(f"pressure_action TOON A/B: {len(citizens)} citizens, self_gap {min(_SELF_GAPS)}-{max(_SELF_GAPS)}, "
          f"legal acts={menu_acts(config.pressure_menu)}")

    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        readings: dict[str, list[tuple[float, float]]] = {"JSON": [], "TOON": []}
        for label, sys_prompt, user_prompt in [
            ("JSON", build_pressure_system_prompt(citizens, config), build_pressure_user_prompt(citizens, contexts)),
            ("TOON", build_pressure_system_prompt_toon(citizens, config), build_pressure_user_prompt_toon(citizens, contexts)),
        ]:
            prompt_tokens = client.count_prompt_tokens(system_prompt=sys_prompt, user_prompt=user_prompt, think=False)
            content, tokens = client.complete_json_with_logprobs(
                system_prompt=sys_prompt, user_prompt=user_prompt,
                json_schema=PRESSURE_JSON_SCHEMA, max_tokens=compute_max_tokens(len(citizens)),
                think=False, top_logprobs=10,
            )
            try:
                decisions = decode_pressure_batch(content, expected_cids)
                decode_ok = True
            except Exception as exc:  # noqa: BLE001 -- reporting, not re-raising
                decisions = []
                decode_ok = False
                print(f"  {label}: DECODE FAILED: {exc}")

            try:
                probes = locate_decision_field_logprobs(content, tokens, field="act")
            except LogprobAlignmentError as exc:
                print(f"  {label}: ALIGNMENT FAILED: {exc}")
                probes = []

            for probe in probes:
                gap = contexts[probe.cid].self_gap
                p_wait = binary_probability(
                    probe.token,
                    true_value=str(int(PressureAct.WAIT_FOR_ELECTION)), false_value=str(int(PressureAct.NOTHING)),
                )
                readings[label].append((gap, p_wait))

            print(f"  {label}: prompt_tokens={prompt_tokens} decode_ok={decode_ok} "
                  f"decisions={len(decisions)}/{len(citizens)} aligned={len(probes)}/{len(citizens)}")

    print(f"\n{'self_gap':>9}  {'P(act=4) JSON':>13}  {'P(act=4) TOON':>13}")
    json_by_gap = dict(readings["JSON"])
    toon_by_gap = dict(readings["TOON"])
    for gap in sorted(set(json_by_gap) | set(toon_by_gap)):
        j = f"{json_by_gap[gap]:.6f}" if gap in json_by_gap else "MISSING"
        t = f"{toon_by_gap[gap]:.6f}" if gap in toon_by_gap else "MISSING"
        print(f"{gap:>9.2f}  {j:>13}  {t:>13}")

    for label in ("JSON", "TOON"):
        ps = [p for _, p in readings[label]]
        if ps:
            below = [p for g, p in readings[label] if g < _BLANK_THRESHOLD]
            above = [p for g, p in readings[label] if g >= _BLANK_THRESHOLD]
            print(f"\n{label}: mean P(act=4) below threshold={sum(below)/len(below):.6f} "
                  f"(n={len(below)}), above={sum(above)/len(above):.6f} (n={len(above)}), "
                  f"full spread={max(ps) - min(ps):.6f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
