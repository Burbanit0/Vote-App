"""
scripts/check_pressure_action_size_one_forced_reasoning.py

Sixth follow-up to the chunk-collapse finding (reasoning_budget_and_decision_quality_findings.md).
size=1 (check_pressure_action_size_one.py) eliminated batching as a cause: 0/63 acting codes even
fully isolated, including the most extreme "should act" case (cid=6, ratio=4.226). This tests the
prompt-framing hypothesis raised in discussion -- that the system prompt's explicit reassurance
"0 (NOTHING) et 4 (WAIT_FOR_ELECTION) sont des resultats legitimes... jamais des echecs"
(build_pressure_system_prompt, llm_behavior_engine.py) may dominate the model's decision at the
expense of ever choosing an acting code -- by forcing think=True on the same size=1 calls and
reading the model's own stated reasoning, if any surfaces.

CRITICAL METHODOLOGICAL CHECKPOINT, per direct instruction, checked BEFORE any interpretation:
this project already found, earlier in this same workstream, that single-citizen-batch think=True
for pressure_action collapsed to ZERO visible <think> content and a fixed act=4/motif=305 default
across 4 different citizens (see the "single-citizen-batch think=True collapses to a fixed
default" section above) -- itself the SAME call shape being re-tested here (size=1, think=True).
If that zero-reasoning collapse reproduces again on these two NEW citizens (different population
run, more extreme ratio), this script has learned nothing about the prompt-framing hypothesis --
only rediscovered the same already-catalogued failure mode a third time. This script therefore
checks and reports <think> content presence/length as its OWN first-class result, explicitly
before attempting to read anything into what the reasoning (if any) says.

Two citizens chosen with intent, not at random: both have an EXTREME "should clearly act" ratio
per the deterministic proxy (not an ambiguous case) -- if forced reasoning explicitly cites the
"0/4 are legitimate" line as a justification for NOT acting despite such an extreme signal, that
is direct, strong evidence for the prompt-framing hypothesis.
  - cid=6: self_gap=0.2802, blank_threshold=0.0663, ratio=4.226 -- the single most extreme
    "should act" case in the whole 63-citizen dataset. Original think=False/size=1 result:
    act=0 (NOTHING).
  - cid=270: self_gap=0.4825, blank_threshold=0.1871, ratio=2.579 -- a different chunk/tick
    region (chunk3) than cid=6 (chunk1), for a small amount of diversity. Original
    think=False/size=1 result: act=4 (WAIT_FOR_ELECTION).

Same real ctx discipline as every prior follow-up: target=5, mandate_dev=0.0,
ticks_to_election=15, petition_open=already_signed=False/petition_expires_at_tick=None (verified
zero petition lifecycle events through tick=1 in this run), available=(0,1,2,3,4),
neighbors_acting=None. Generous token budget (_FORCED_THINK_TOKEN_ALLOWANCE), since this call
shape is uncalibrated (never run in production).

Usage:
    python fast_api_voter/scripts/check_pressure_action_size_one_forced_reasoning.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PressureContext,
    build_pressure_system_prompt,
    build_pressure_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import _THINK_TAG_RE, OllamaJsonClient, decode_pressure_batch  # noqa: E402
from api.domain.polity.llm_schemas import PRESSURE_JSON_SCHEMA  # noqa: E402

_FORCED_THINK_TOKEN_ALLOWANCE = 8000
_TARGET = 5
_MANDATE_DEV = 0.0
_TICKS_TO_ELECTION = 15
_ACT_NAMES = {0: "NOTHING", 1: "SIGN_PETITION", 2: "LAUNCH_PETITION", 3: "MOBILIZE", 4: "WAIT_FOR_ELECTION"}

_CASES = [
    {"cid": 6, "self_gap": 0.2802, "blank_threshold": 0.0663, "original_act": 0},
    {"cid": 270, "self_gap": 0.4825, "blank_threshold": 0.1871, "original_act": 4},
]


def main() -> int:
    config = load_config()
    citizens_by_id = {c.citizen_id: c for c in generate_population(config.citizens, 280, config.run.seed)}

    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for case in _CASES:
            cid = int(case["cid"])
            self_gap = float(case["self_gap"])
            blank_threshold = float(case["blank_threshold"])
            ratio = self_gap / blank_threshold
            original_act = int(case["original_act"])
            citizen = citizens_by_id[cid]
            ctx = PressureContext(
                cid=cid, target=_TARGET, self_gap=self_gap, mandate_dev=_MANDATE_DEV,
                ticks_to_election=_TICKS_TO_ELECTION, available=(0, 1, 2, 3, 4),
                petition_open=False, petition_expires_at_tick=None, already_signed=False,
                neighbors_acting=None,
            )
            raw = client.complete_json(
                system_prompt=build_pressure_system_prompt([citizen], config),
                user_prompt=build_pressure_user_prompt([citizen], {cid: ctx}),
                json_schema=PRESSURE_JSON_SCHEMA,
                max_tokens=compute_max_tokens(1) + _FORCED_THINK_TOKEN_ALLOWANCE,
                think=True,
            )

            print(f"\n=== cid={cid} ratio={ratio:.3f} (original think=False/size=1: {_ACT_NAMES[original_act]}) ===")
            think_match = _THINK_TAG_RE.search(raw)
            think_content = think_match.group(0) if think_match else None
            think_len = len(think_content) if think_content else 0
            print(f"--- STEP 1: <think> content present? {'YES' if think_content else 'NO'} (length={think_len} chars) ---")
            if not think_content:
                print(
                    "No <think> content -- reproducing the already-catalogued zero-reasoning "
                    "collapse for single-citizen-batch think=True. Nothing learned about the "
                    "prompt-framing hypothesis from this case; do not interpret the decision "
                    "below as evidence either way."
                )
            else:
                print(f"--- reasoning content ---\n{think_content}\n--- end reasoning ---")
                mentions_legitimacy_line = any(
                    kw in think_content.lower()
                    for kw in ("legitim", "jamais des échecs", "jamais des echecs", "resultat legitime", "résultat légitime")
                )
                print(f"--- explicitly references the '0/4 are legitimate' framing? {mentions_legitimacy_line} ---")

            decision = decode_pressure_batch(raw, [cid])[0]
            print(f"decoded decision: act={decision.act} ({_ACT_NAMES[decision.act]}) motif={decision.motif}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
