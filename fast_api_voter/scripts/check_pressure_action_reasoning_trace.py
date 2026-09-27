"""
scripts/check_pressure_action_reasoning_trace.py

Applies the diagnostic method that worked for chamber_deliberation and campaign_positioning (read
the FULL raw reasoning trace, find the exact thing the model is confused about, fix it with one
targeted prompt sentence) to pressure_action -- the best-characterized of the 4 confirmed
content-blind collapses (plan-adversarial-framing-collapse.md).

WHY THIS IS NOT A DIRECT TRANSFER, stated up front: the 2 types where that method worked both run
think=True in production, so their traces WERE the production path. All 4 collapsing types run
think=False -- they generate no reasoning at all, so there is nothing to read on their real path.
This script therefore forces think=True as a DIAGNOSTIC MICROSCOPE ONLY: it asks "when this model
is allowed to reason about this exact prompt, what does it say while getting the answer wrong?".
Any prompt ambiguity found this way must then be fixed AND validated on the production think=False
path -- a fix that only works under think=True would not be a fix at all.

WHY THE EARLIER FORCED-REASONING ATTEMPTS FOUND "ZERO REASONING" (corrected here): both
check_pressure_action_size_one_forced_reasoning.py and check_candidacy_forced_reasoning_
comparison.py called client.complete_json(), which returns only message.content, then searched it
for <think> tags. Ollama's OpenAI-compat endpoint puts reasoning in a SEPARATE message.reasoning
field -- llm_test_harness/README.md documents this exact pitfall, including a measured case with
64,101 characters of reasoning invisible to a content-only read. Their "total reasoning
suppression" finding is therefore an extraction artifact, not an observation about the model, and
the conclusion drawn from it (that the suppression is disconnected from the collapse theory) rests
on an invalid measurement. This script reads message.reasoning directly, via a raw call.

DESIGN: 4 citizens whose ground truth is "should act" and that collapse to act=0 every time, plus
2 whose ground truth is "should not act" and that the model answers CORRECTLY. Comparing a trace
it gets wrong against a trace it gets right on the same prompt shape is what localizes the
divergence -- a wrong-only sample cannot distinguish "confused by X" from "always says X".

Usage:
    python fast_api_voter/scripts/check_pressure_action_reasoning_trace.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PressureContext,
    build_pressure_system_prompt,
    build_pressure_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import OllamaJsonClient, _inline_refs, _post_with_transport_retry  # noqa: E402
from api.domain.polity.llm_schemas import PRESSURE_JSON_SCHEMA  # noqa: E402
from pressure_action_harness import (  # noqa: E402
    ACT_NAMES,
    ACTING_CODES,
    MANDATE_DEV,
    TICKS_TO_ELECTION,
    harvest_unambiguous_citizens,
)

_THINK_TOKEN_ALLOWANCE = 8000
# From the §2.3/§2.4 runs: every one of these 17 "should act" citizens returned act=0 on every
# variant tested. These 4 are simply the first 4 of that set, no cherry-picking on trace content
# (which is not visible until after the call).
_WRONG_CIDS = [3, 18, 27, 28]
# Correctly answered "should not act" cases, for the contrast read.
_RIGHT_CIDS = [8, 12]
_DUMP_DIR = Path(
    r"C:\Users\burba\AppData\Local\Temp\claude\c--Users-burba-Vote-App-polity"
    r"\22458a2f-ddf0-45bc-bb54-2e029e1a45ce\scratchpad\pressure_action_traces"
)


def raw_pressure_call_thinking(
    client: OllamaJsonClient, system_prompt: str, user_prompt: str, max_tokens: int,
) -> dict[str, Any]:
    """Mirrors OllamaJsonClient._complete_json_openai_compat's request body (the think=True path),
    but parses the full response directly instead of calling _extract_content -- so
    message.reasoning survives, and a non-'stop' finish_reason does not discard everything."""
    body = {
        "model": client._model,  # noqa: SLF001 -- exploratory probe, documented reuse
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": client._temperature,  # noqa: SLF001
        "seed": client._seed,  # noqa: SLF001
        "max_tokens": max_tokens,
        "stream": False,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "polity_decision_batch",
                "strict": True,
                "schema": _inline_refs(PRESSURE_JSON_SCHEMA),
            },
        },
    }
    payload = json.dumps(body, sort_keys=True, separators=(",", ":"))
    response: httpx.Response = _post_with_transport_retry(  # noqa: SLF001
        client._client, f"{client._base_url}/chat/completions", payload  # noqa: SLF001
    )
    return dict(response.json())


def main() -> int:
    config = load_config()
    holder, cases = harvest_unambiguous_citizens(config)
    by_cid = {c.citizen_id: (c, gap, expected) for c, gap, expected in cases}
    print(f"harvested {len(cases)} unambiguous citizens (holder=cid{holder.citizen_id})")

    _DUMP_DIR.mkdir(parents=True, exist_ok=True)
    targets = [(cid, "WRONG-in-production") for cid in _WRONG_CIDS]
    targets += [(cid, "RIGHT-in-production") for cid in _RIGHT_CIDS]

    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for cid, label in targets:
            citizen, gap, expected_act = by_cid[cid]
            ratio = gap / citizen.blank_threshold
            ctx = PressureContext(
                cid=cid, target=holder.citizen_id, self_gap=gap, mandate_dev=MANDATE_DEV,
                ticks_to_election=TICKS_TO_ELECTION, available=(0, 1, 2, 3, 4),
                petition_open=False, petition_expires_at_tick=None, already_signed=False,
                neighbors_acting=None,
            )
            citizen_stub = type("C", (), {"citizen_id": cid})()
            system_prompt = build_pressure_system_prompt([citizen_stub], config)
            user_prompt = build_pressure_user_prompt([citizen_stub], {cid: ctx})

            body = raw_pressure_call_thinking(
                client, system_prompt, user_prompt, compute_max_tokens(1) + _THINK_TOKEN_ALLOWANCE
            )
            choices = body.get("choices") or [{}]
            choice = choices[0] if isinstance(choices, list) and choices else {}
            finish_reason = choice.get("finish_reason")
            message = choice.get("message") or {}
            reasoning = message.get("reasoning") or ""
            content = message.get("content") or ""

            act = None
            try:
                act = json.loads(content)["decisions"][0]["act"]
            except Exception:  # noqa: BLE001 -- a malformed answer is itself a result here
                pass
            acted = act in ACTING_CODES if act is not None else None
            agree = (acted == expected_act) if acted is not None else None

            print(f"\n########## cid={cid} [{label}] ##########")
            act_name = ACT_NAMES.get(act, "?") if act is not None else "?"
            print(f"  ratio={ratio:.2f} expected_act={expected_act} -> act={act} ({act_name}) agree={agree}")
            print(f"  finish_reason={finish_reason!r} message.keys()={sorted(message.keys())}")
            print(f"  reasoning_chars={len(reasoning)} content_chars={len(content)}")

            (_DUMP_DIR / f"cid{cid}_{label}_reasoning.txt").write_text(reasoning, encoding="utf-8")
            (_DUMP_DIR / f"cid{cid}_{label}_system_prompt.txt").write_text(system_prompt, encoding="utf-8")
            (_DUMP_DIR / f"cid{cid}_{label}_user_prompt.txt").write_text(user_prompt, encoding="utf-8")

    print(f"\nAll traces dumped to {_DUMP_DIR}")
    print(
        "\nNOTE: think=True here is a diagnostic microscope, NOT the production path "
        "(pressure_action ships think=False). Any fix derived from these traces must be "
        "validated on the think=False path before being called a fix."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
