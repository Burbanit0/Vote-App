"""
scripts/check_logprob_response_stance_tracking.py

plan-llm-protocol-and-theory-program.md §5.C, second application of the
logprob instrument to a decision type with no ground truth:
representative_response (dt=6).

decide_representative_response's own RELIABILITY WARNING (2026-08-30,
plan-adversarial-framing-collapse.md) already found the collapse SIGNATURE
here: two structurally opposite ctx poles (crisis: L=0.05/mandate_dev=0.8/
street=3.0/ticks_left=2; no-problem: L=0.95/mandate_dev=0.0/street=0.0/
ticks_left=20), 3 different holders each, size=1/think=False -- all 4
successfully-decoded calls returned the EXACT SAME stance, shift count,
and motif at both poles. That finding used a categorical draw at exactly
two points; it could not say whether the response is flat EVERYWHERE
between the poles or whether there is some real but narrow region of
sensitivity a 2-point probe would miss entirely. This re-uses the SAME
two pre-registered poles (not new ones -- the whole point is comparability
with the existing finding) and interpolates a real gradient between them,
reading P(stance=1, CONCESSION) continuously via logprobs instead of a
single draw per point.

Real production shape throughout: build_response_system_prompt/
build_response_user_prompt, RESPONSE_JSON_SCHEMA, think=False (this
decision type's own production value), and -- like the original
diagnostic -- every call is SOLO (size=1): decide_representative_response
deliberately never batches (0-or-1 sitting president), so there is no
separate batching control to run here the way pressure_action needed one.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_logprob_response_stance_tracking.py
"""
from __future__ import annotations

import dataclasses
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    ResponseContext,
    build_response_system_prompt,
    build_response_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import VllmJsonClient  # noqa: E402
from api.domain.polity.llm_logprob_instrumentation import (  # noqa: E402
    LogprobAlignmentError,
    candidate_probability,
    locate_decision_field_logprobs,
)
from api.domain.polity.llm_schemas import RESPONSE_JSON_SCHEMA  # noqa: E402

# The two poles ARE plan-adversarial-framing-collapse.md's own, verbatim
# from decide_representative_response's own docstring -- not re-chosen.
_NO_PROBLEM = {"legitimacy": 0.95, "mandate_dev": 0.0, "street": 0.0, "ticks_left": 20}
_CRISIS = {"legitimacy": 0.05, "mandate_dev": 0.8, "street": 3.0, "ticks_left": 2}
_STEPS = 9  # t=0 (no-problem) .. t=1 (crisis), 9 evenly spaced points including both poles


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


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _holder(cid: int) -> Citizen:
    citizen = Citizen(
        citizen_id=cid,
        issue_positions=tuple((cid * 0.019 + d * 0.011) % 1.0 for d in range(20)),
        issue_priorities=tuple(1.0 / 20 for _ in range(20)),
        blank_threshold=0.5,
        ambition_score=0.5,
    )
    citizen.pledged_platform = citizen.issue_positions
    citizen.revealed_position = citizen.issue_positions  # no drift yet -- isolates ctx's own effect
    return citizen


def main() -> int:
    config = _vllm_config()

    rows = []
    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for i in range(_STEPS):
            t = i / (_STEPS - 1)
            cid = 6000 + i
            holder = _holder(cid)
            context = ResponseContext(
                cid=cid,
                legitimacy=_lerp(_NO_PROBLEM["legitimacy"], _CRISIS["legitimacy"], t),
                mandate_dev=_lerp(_NO_PROBLEM["mandate_dev"], _CRISIS["mandate_dev"], t),
                street=_lerp(_NO_PROBLEM["street"], _CRISIS["street"], t),
                lame_duck=False,  # held fixed -- not one of the two original poles' own axes
                ticks_left=round(_lerp(_NO_PROBLEM["ticks_left"], _CRISIS["ticks_left"], t)),
            )
            system_prompt = build_response_system_prompt([holder], config)
            user_prompt = build_response_user_prompt([holder], {cid: context})
            content, tokens = client.complete_json_with_logprobs(
                system_prompt=system_prompt, user_prompt=user_prompt,
                json_schema=RESPONSE_JSON_SCHEMA, max_tokens=compute_max_tokens(1),
                think=False,  # decide_representative_response's own production value
                top_logprobs=10,
            )
            try:
                probes = locate_decision_field_logprobs(content, tokens, field="stance")
            except LogprobAlignmentError as exc:
                print(f"  ALIGNMENT FAILED at t={t:.3f}: {exc}")
                continue
            p_concession = candidate_probability(probes[0].token, "1")
            rows.append((t, context.legitimacy, context.street, p_concession, probes[0].token.token))

    print(f"{'t':>5}  {'L':>6}  {'street':>7}  {'P(stance=1)':>12}  {'chosen_stance':>13}")
    for t, legitimacy, street, p_concession, chosen in rows:
        pole = "no-problem" if t == 0.0 else ("crisis" if t == 1.0 else "")
        print(f"{t:>5.3f}  {legitimacy:>6.2f}  {street:>7.2f}  {p_concession:>12.6f}  {chosen:>13}  {pole}")

    print(f"\naligned decisions: {len(rows)}/{_STEPS}")
    if len(rows) >= 2:
        no_problem_p = rows[0][3]
        crisis_p = rows[-1][3]
        print(f"P(stance=1) at no-problem pole: {no_problem_p:.6f}")
        print(f"P(stance=1) at crisis pole:     {crisis_p:.6f}")
        print(f"pole-to-pole difference:        {crisis_p - no_problem_p:+.6f}")
        ps = [p for *_, p, _ in rows]
        spread = max(ps) - min(ps)
        print(f"full spread across all {len(rows)} interpolated points: {spread:.6f} "
              f"(min={min(ps):.6f}, max={max(ps):.6f})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
