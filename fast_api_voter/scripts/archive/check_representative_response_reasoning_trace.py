"""
scripts/check_representative_response_reasoning_trace.py

Reads the model's own reasoning on the two opposite poles that produced representative_response's
"collapse" verdict (4/4 identical stance) -- the same microscope applied to pressure_action, which
turned out to dissolve that collapse entirely.

CONFIG-GATING PRE-CHECK, done before writing this and recorded here because its absence is what
destroyed the pressure_action evidence: representative_response's option set is NOT restricted by
any config. The production prompt (verified by building it under the shipped config) lists all four
stances -- 1 CONCESSION / 2 DEFIANCE / 3 SILENCE / 4 COUNTER_MOBILIZATION -- with no menu gate.
Every answer the poles could call for is expressible, so the pressure_action defect (expecting an
act the constitution forbids) does not apply here.

WHAT IS STILL NOT ESTABLISHED, and is exactly what the traces should settle: the collapse claim
assumes the two poles OUGHT to produce different stances. Nothing in the design says so. A crisis
officeholder (L=0.05, street=3.0, ticks_left=2) and an untroubled one (L=0.95, street=0.0,
ticks_left=20) both answering, say, CONCESSION could be sound reasoning rather than content
blindness -- pressure_action's lesson is that "identical output" is only evidence of collapse once
you have checked the expected difference was both possible AND actually required.

think=True is a diagnostic microscope only: production ships think=False for this type
(llm_behavior_engine.py). Anything found here must be re-validated on the think=False path.

Usage:
    python fast_api_voter/scripts/check_representative_response_reasoning_trace.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    ResponseContext,
    build_response_system_prompt,
    build_response_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import OllamaJsonClient, _inline_refs, _post_with_transport_retry  # noqa: E402
from api.domain.polity.llm_schemas import RESPONSE_JSON_SCHEMA  # noqa: E402
from api.domain.polity.simple_rules import declare_candidacy  # noqa: E402

_POPULATION_SIZE = 190
_HOLDER_CIDS = [1, 2, 3]
_THINK_TOKEN_ALLOWANCE = 8000
_STANCE_NAMES = {1: "CONCESSION", 2: "DEFIANCE", 3: "SILENCE", 4: "COUNTER_MOBILIZATION"}
_POLES = {
    "CRISIS": ResponseContext(cid=-1, legitimacy=0.05, mandate_dev=0.8, street=3.0, lame_duck=False, ticks_left=2),
    "NO-PROBLEM": ResponseContext(cid=-1, legitimacy=0.95, mandate_dev=0.0, street=0.0, lame_duck=False, ticks_left=20),
}
_DUMP_DIR = Path(
    r"C:\Users\burba\AppData\Local\Temp\claude\c--Users-burba-Vote-App-polity"
    r"\22458a2f-ddf0-45bc-bb54-2e029e1a45ce\scratchpad\representative_response_traces"
)


def raw_response_call_thinking(
    client: OllamaJsonClient, system_prompt: str, user_prompt: str, max_tokens: int,
) -> dict[str, Any]:
    """Mirrors _complete_json_openai_compat's request body, but parses the response directly so
    message.reasoning survives -- complete_json() returns only content, the exact mistake that
    made two earlier scripts report 'zero reasoning' (llm_test_harness/README.md documents it)."""
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
                "schema": _inline_refs(RESPONSE_JSON_SCHEMA),
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
    population = list(generate_population(config.citizens, _POPULATION_SIZE, config.run.seed))
    by_id = {c.citizen_id: c for c in population}
    _DUMP_DIR.mkdir(parents=True, exist_ok=True)

    seen: list[tuple[str, int, int | None]] = []
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        for pole_label, template in _POLES.items():
            print(f"\n########## {pole_label} ##########")
            for cid in _HOLDER_CIDS:
                holder = by_id[cid]
                declare_candidacy(holder)
                ctx = ResponseContext(
                    cid=cid, legitimacy=template.legitimacy, mandate_dev=template.mandate_dev,
                    street=template.street, lame_duck=template.lame_duck, ticks_left=template.ticks_left,
                )
                system_prompt = build_response_system_prompt([holder], config)
                user_prompt = build_response_user_prompt([holder], {cid: ctx})
                body = raw_response_call_thinking(
                    client, system_prompt, user_prompt, compute_max_tokens(1) + _THINK_TOKEN_ALLOWANCE
                )
                choice = (body.get("choices") or [{}])[0]
                message = choice.get("message") or {}
                reasoning = message.get("reasoning") or ""
                content = message.get("content") or ""
                stance = motif = None
                try:
                    decision = json.loads(content)["decisions"][0]
                    stance, motif = decision.get("stance"), decision.get("motif")
                except Exception:  # noqa: BLE001 -- a malformed answer is itself a result
                    pass
                seen.append((pole_label, cid, stance))
                print(
                    f"  cid={cid} -> stance={stance} ({_STANCE_NAMES.get(stance, '?') if stance else '?'}) "
                    f"motif={motif} finish={choice.get('finish_reason')!r} reasoning_chars={len(reasoning)}"
                )
                (_DUMP_DIR / f"{pole_label}_cid{cid}_reasoning.txt").write_text(reasoning, encoding="utf-8")

    print("\n--- result ---")
    for pole in _POLES:
        stances = [s for p, _c, s in seen if p == pole]
        print(f"  {pole}: stances={stances}")
    distinct = {s for _p, _c, s in seen if s is not None}
    print(f"  stances distinctes toutes poles confondues : {sorted(distinct)}")
    print(f"\nTraces dumped to {_DUMP_DIR}")
    print("NOTE: think=True is a microscope here; production ships think=False for this type.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
