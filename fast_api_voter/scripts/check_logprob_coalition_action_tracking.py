"""
scripts/check_logprob_coalition_action_tracking.py

plan-llm-protocol-and-theory-program.md §5.C, third application of the
logprob instrument: coalition_decision (dt=9).

decide_coalition's own RELIABILITY WARNING (2026-08-30,
plan-adversarial-framing-collapse.md) found the collapse signature at two
opposite poles -- join-obvious (identical platform to initiator, pushes
comfortably past majority, initiator needs it) vs decline-obvious
(maximum platform distance across all 20 issue dimensions, initiator
already has a majority alone) -- 3 responder parties each, ALL 6 calls
returned JOIN. That docstring itself names TWO open gaps this script
closes together: (1) the categorical 2-point/6-sample measurement can't
rule out a real gradient between the poles, same limitation the
representative_response re-measurement addressed; (2) "Not tested at real
production batch size: decide_coalition batches seated non-initiator
parties directly (up to ~4 in the shipped config), and this test used
size=1 ... an open gap" -- the original diagnostic never exercised
batching at all.

5 responder parties, with 5 FIXED platforms interpolated from "identical
to the initiator" to "maximally distant across all 20 dims" (the same
distance axis the original poles used). 5 CALLS, one per interpolation
point on the OTHER original axis (the initiator's own institutional
shortfall, from "needs this party badly" to "already has a majority
alone") -- each call batches ALL 5 responders together (real production
batch shape, closing the "up to ~4, never tested" gap: this project's own
established precedent, per pressure_action/vote_cast, is that a batching
artifact must be checked, not assumed absent), and this script reads out
the ONE responder in that call whose own fixed distance matches the
call's own institutional t -- the "diagonal" reading, so the party being
read has BOTH axes at the same point along the original poles'
join-obvious->decline-obvious line, exactly like the original diagnostic,
while every call still exercises a real multi-party batch. Reads
P(action=1, JOIN) continuously via candidate_probability instead of a
single categorical draw per party. Real production shape throughout:
build_coalition_system_prompt/build_coalition_user_prompt,
COALITION_JSON_SCHEMA, think=False (this decision type's own production
value, flagged in decide_coalition's own docstring as "the same guess ...
flagged for live verification rather than assumed").

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_logprob_coalition_action_tracking.py
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    build_coalition_system_prompt,
    build_coalition_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import VllmJsonClient  # noqa: E402
from api.domain.polity.llm_logprob_instrumentation import (  # noqa: E402
    LogprobAlignmentError,
    candidate_probability,
    locate_decision_field_logprobs,
)
from api.domain.polity.llm_schemas import COALITION_JSON_SCHEMA  # noqa: E402

_INITIATOR = 0
_ISSUE_COUNT = 20
_TOTAL_SEATS = 100
_MAJORITY_THRESHOLD = 50.0
_RESPONDER_SEATS = 30  # fixed for every responder -- isolates the two poles' own axes
_STEPS = 5  # t=0 (join-obvious) .. t=1 (decline-obvious)


def _vllm_config():
    shipped = load_config()
    return dataclasses.replace(shipped, llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1"))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def main() -> int:
    config = _vllm_config()

    initiator_platform = tuple(0.0 for _ in range(_ISSUE_COUNT))
    responder_ids = [_INITIATOR + 1 + i for i in range(_STEPS)]
    ts = [i / (_STEPS - 1) for i in range(_STEPS)]

    party_platforms: dict[int, tuple[float, ...]] = {_INITIATOR: initiator_platform}
    seats: dict[int, int] = {_INITIATOR: 0}  # placeholder, real value set per-point below is per-call, not per-party
    votes: dict[int, float] = {}

    print(f"coalition_decision gradient probe: 5 FIXED responder platforms spanning distance "
          f"0->{(_ISSUE_COUNT ** 0.5):.3f} from the initiator, read across 5 CALLS spanning the "
          f"initiator's own institutional shortfall from needs-this-party to already-majority. "
          f"Every call batches all 5 responders together (real production shape -- "
          f"decide_coalition's own docstring flags 'up to ~4, never tested' as an open gap); "
          f"this script reads out the one responder whose own fixed distance matches that call's "
          f"own institutional t -- the diagonal reading, both axes moving together like the "
          f"original two-pole diagnostic")

    for pid, t in zip(responder_ids, ts):
        party_platforms[pid] = tuple(_lerp(0.0, 1.0, t) for _ in range(_ISSUE_COUNT))
        seats[pid] = _RESPONDER_SEATS
        votes[pid] = _RESPONDER_SEATS / _TOTAL_SEATS

    # Institutional shortfall is a call-level fact (the initiator's own
    # seats), not a per-responder one -- every responder in one call sees
    # the SAME initiator state. So the diagonal (both axes moving
    # together) is read across 5 SEPARATE calls, one per institutional-t;
    # each call still batches all 5 (fixed-platform) responders together,
    # real production shape, and this script only reads out the one
    # responder whose own platform-t matches that call's institutional-t.
    rows = []
    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for pid, t in zip(responder_ids, ts):
            initiator_seats = round(_lerp(25.0, 60.0, t))
            call_seats = dict(seats)
            call_seats[_INITIATOR] = initiator_seats
            call_votes = dict(votes)
            call_votes[_INITIATOR] = initiator_seats / _TOTAL_SEATS
            call_responders = sorted(responder_ids)  # all 5, every call -- real batch shape
            call_platforms = dict(party_platforms)
            call_platforms[_INITIATOR] = initiator_platform

            system_prompt = build_coalition_system_prompt(
                call_responders, _INITIATOR, initiator_seats, _TOTAL_SEATS, _MAJORITY_THRESHOLD,
            )
            user_prompt = build_coalition_user_prompt(
                call_responders, _INITIATOR, call_platforms, call_seats, call_votes,
                _TOTAL_SEATS, _MAJORITY_THRESHOLD,
            )
            content, tokens = client.complete_json_with_logprobs(
                system_prompt=system_prompt, user_prompt=user_prompt,
                json_schema=COALITION_JSON_SCHEMA, max_tokens=compute_max_tokens(len(call_responders)),
                think=False,  # decide_coalition's own production value
                top_logprobs=10,
            )
            try:
                probes = locate_decision_field_logprobs(content, tokens, field="action", cid_field="party_id")
            except LogprobAlignmentError as exc:
                print(f"  ALIGNMENT FAILED at t={t:.2f} (pid={pid}): {exc}")
                continue
            target_probe = next(p for p in probes if p.cid == pid)
            distance = sum((a - b) ** 2 for a, b in zip(call_platforms[pid], initiator_platform)) ** 0.5
            p_join = candidate_probability(target_probe.token, "1")
            shortfall = max(0.0, _MAJORITY_THRESHOLD - initiator_seats)
            rows.append((t, distance, shortfall, p_join, target_probe.token.token))

    print(f"\n{'t':>5}  {'distance':>9}  {'shortfall':>9}  {'P(action=1)':>12}  {'chosen_action':>13}")
    for t, distance, shortfall, p_join, chosen in rows:
        pole = "join-obvious" if t == 0.0 else ("decline-obvious" if t == 1.0 else "")
        print(f"{t:>5.2f}  {distance:>9.3f}  {shortfall:>9.1f}  {p_join:>12.6f}  {chosen:>13}  {pole}")

    print(f"\naligned decisions: {len(rows)}/{_STEPS}")
    if len(rows) >= 2:
        join_obvious_p = rows[0][3]
        decline_obvious_p = rows[-1][3]
        print(f"P(action=1) at join-obvious pole:    {join_obvious_p:.6f}")
        print(f"P(action=1) at decline-obvious pole: {decline_obvious_p:.6f}")
        print(f"pole-to-pole difference:             {decline_obvious_p - join_obvious_p:+.6f}")
        ps = [p for *_, p, _ in rows]
        print(f"full spread across all {len(rows)} points: {max(ps) - min(ps):.6f} "
              f"(min={min(ps):.6f}, max={max(ps):.6f})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
