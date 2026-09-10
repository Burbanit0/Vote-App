"""
scripts/check_pressure_shipped_wiring.py

Live sanity check of Phase E's actual shipped wiring (polity-decision-
contracts.md / plan-llm-protocol-and-theory-program.md): decide_
pressure_actions itself -- not its prompt builders in isolation -- now
calls build_pressure_system_prompt_calibrated/build_pressure_user_
prompt_calibrated with PRESSURE_THRESHOLD_SIGNAL, chunked one citizen per
call. This calls decide_pressure_actions directly against the real vLLM
server with a heterogeneous cohort (blank_threshold varies per citizen,
self_gap spans clearly-satisfied to clearly-discontented) and checks:
1. Every citizen gets exactly one decision, decoded cleanly, act legal.
2. Each HTTP call the client actually made carries blank_threshold in
   its ctx (proof the signal reached the wire, not just unit-tested
   against a fake client).
3. Agreement with the >=90% unambiguous-subset bar the calibration
   matrix already validated -- one more real data point, not a
   replacement for that matrix's own 9-trial result.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_pressure_shipped_wiring.py
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PressureContext,
    decide_pressure_actions,
)
from api.domain.polity.llm_client import VllmJsonClient  # noqa: E402

_TARGET_CID = 999
_TICKS_TO_ELECTION = 10
_MANDATE_DEV = 0.1
_N_CITIZENS = 12


def _vllm_config():
    shipped = load_config()
    return dataclasses.replace(shipped, llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1"))


class _RecordingClient:
    """Wraps a real VllmJsonClient and records every user_prompt sent, so
    this script can assert blank_threshold actually reached the wire --
    not just that decide_pressure_actions returned something plausible."""

    def __init__(self, inner):
        self._inner = inner
        self.user_prompts: list[str] = []

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
        self.user_prompts.append(user_prompt)
        return self._inner.complete_json(
            system_prompt=system_prompt, user_prompt=user_prompt, json_schema=json_schema,
            max_tokens=max_tokens, think=think,
        )

    def count_prompt_tokens(self, **kwargs):
        return self._inner.count_prompt_tokens(**kwargs)


def main() -> int:
    config = _vllm_config()

    citizens = []
    contexts = {}
    for i in range(_N_CITIZENS):
        cid = 8000 + i
        # Unambiguous per the pre-registered criterion (plan-decision-quality-validation.md):
        # gap < 0.5*bt or gap > 1.5*bt. Alternating below/above, distinct blank_thresholds per
        # citizen so this is a real heterogeneous cohort, not one constant threshold.
        blank_threshold = 0.3 + 0.05 * i
        below = i % 2 == 0
        gap = blank_threshold * (0.2 if below else 2.0)
        citizen = Citizen(
            citizen_id=cid,
            issue_positions=tuple((cid * 0.017 + d * 0.013) % 1.0 for d in range(20)),
            issue_priorities=tuple(1.0 / 20 for _ in range(20)),
            blank_threshold=blank_threshold,
            ambition_score=0.5,
        )
        context = PressureContext(
            cid=cid, target=_TARGET_CID, self_gap=gap, mandate_dev=_MANDATE_DEV,
            ticks_to_election=_TICKS_TO_ELECTION, available=(0, 4),
            petition_open=False, petition_expires_at_tick=None, already_signed=False, neighbors_acting=None,
        )
        citizens.append(citizen)
        contexts[cid] = context

    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as real_client:
        client = _RecordingClient(real_client)
        outcome = decide_pressure_actions(citizens, contexts, config, client)

    print(f"HTTP calls made: {len(client.user_prompts)} (expect {_N_CITIZENS}, one per citizen)")
    assert len(client.user_prompts) == _N_CITIZENS

    for raw in client.user_prompts:
        payload = json.loads(raw)
        assert len(payload["consulted"]) == 1
        ctx = payload["consulted"][0]["ctx"]
        assert "blank_threshold" in ctx, f"blank_threshold missing from wire payload: {ctx!r}"
    print("blank_threshold present in every wire payload: OK")

    assert len(outcome.decisions) == _N_CITIZENS
    assert {d.cid for d in outcome.decisions} == {c.citizen_id for c in citizens}
    for d in outcome.decisions:
        assert d.act in (0, 4), f"act={d.act} outside the closed menu"
    print(f"decoded cleanly: {len(outcome.decisions)}/{_N_CITIZENS}, all acts legal")

    n_correct = 0
    for d in outcome.decisions:
        gap = contexts[d.cid].self_gap
        bt = next(c.blank_threshold for c in citizens if c.citizen_id == d.cid)
        expect_nothing = gap < 0.5 * bt
        expect_wait = gap > 1.5 * bt
        assert expect_nothing != expect_wait  # every point here is unambiguous by construction
        correct = (d.act == 0) if expect_nothing else (d.act == 4)
        n_correct += int(correct)
    print(f"agreement with the pre-registered unambiguous criterion: {n_correct}/{_N_CITIZENS}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
