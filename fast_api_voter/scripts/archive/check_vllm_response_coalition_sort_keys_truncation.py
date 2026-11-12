"""
scripts/check_vllm_response_coalition_sort_keys_truncation.py

Follow-up to check_vllm_pressure_action_sort_keys_truncation.py's finding (a severe, vLLM-specific
non-terminating whitespace loop triggered by sort_keys=True reordering PressureDecision's flat
integer fields alphabetically). Checks the two schemas flagged there as the plausible next
candidates: `ResponseDecision` (representative_response) and `CoalitionDecision`
(coalition_decision).

Field shapes, declared vs. alphabetical order under sort_keys=True:
  ResponseDecision:   cid, shifts, stance, motif  ->  cid, motif, shifts, stance
                       (has an array field, `shifts` -- closer to PositioningDecision/
                       ChamberDecision's shape, both already confirmed clean under vLLM in
                       scripts/vllm_switch_results.md's axis (b))
  CoalitionDecision:  party_id, action, motif      ->  action, motif, party_id
                       (three flat fields, no array -- the closer match to PressureDecision's
                       vulnerable shape: cid, target, act, motif -> act, cid, motif, target)

Real production prompts/contexts, reused directly from check_representative_response_collapse_
signature.py (NO-PROBLEM pole, cid=1) and check_coalition_decision_collapse_signature.py
(JOIN-OBVIOUS pole, party 50) -- not reconstructed, so this tests the actual shape those
investigations already used. think=False, compute_max_tokens(1), matching each decision type's
real production call.

Usage:
    docker compose -f docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_vllm_response_coalition_sort_keys_truncation.py --backend vllm
    python fast_api_voter/scripts/check_vllm_response_coalition_sort_keys_truncation.py --backend ollama
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import generate_population  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    ResponseContext,
    build_coalition_system_prompt,
    build_coalition_user_prompt,
    build_response_system_prompt,
    build_response_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import _inline_refs  # noqa: E402
from api.domain.polity.llm_schemas import COALITION_JSON_SCHEMA, RESPONSE_JSON_SCHEMA  # noqa: E402
from api.domain.polity.simple_rules import declare_candidacy  # noqa: E402

_INITIATOR = 1
_RESPONDER_ID = 50


def _response_prompts() -> tuple[str, str, dict]:
    config = load_config()
    population = list(generate_population(config.citizens, 190, config.run.seed))
    holder = next(c for c in population if c.citizen_id == 1)
    declare_candidacy(holder)
    ctx = ResponseContext(cid=1, legitimacy=0.95, mandate_dev=0.0, street=0.0, lame_duck=False, ticks_left=20)
    system_prompt = build_response_system_prompt([holder], config)
    user_prompt = build_response_user_prompt([holder], {1: ctx})
    return system_prompt, user_prompt, _inline_refs(RESPONSE_JSON_SCHEMA)


def _coalition_prompts() -> tuple[str, str, dict]:
    config = load_config()
    issue_count = config.citizens.issue_count
    platforms = {_INITIATOR: (0.5,) * issue_count, _RESPONDER_ID: (0.5,) * issue_count}
    seats = {_INITIATOR: 48, _RESPONDER_ID: 10}
    votes = {_INITIATOR: 0.45, _RESPONDER_ID: 0.10}
    system_prompt = build_coalition_system_prompt([_RESPONDER_ID], _INITIATOR, 48, 100, 50.0)
    user_prompt = build_coalition_user_prompt([_RESPONDER_ID], _INITIATOR, platforms, seats, votes, 100, 50.0)
    return system_prompt, user_prompt, _inline_refs(COALITION_JSON_SCHEMA)


_DECISION_TYPES = {
    "response": _response_prompts,
    "coalition": _coalition_prompts,
}


def _vllm_body(system_prompt: str, user_prompt: str, schema: dict, sort_keys: bool) -> tuple[str, str]:
    body = {
        "model": "qwen3:8b",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "temperature": 0.0, "seed": 42, "max_tokens": compute_max_tokens(1), "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
        "response_format": {"type": "json_schema", "json_schema": {"name": "x", "strict": True, "schema": schema}},
    }
    payload = json.dumps(body, sort_keys=sort_keys, separators=(",", ":"))
    return "http://localhost:8000/v1/chat/completions", payload


def _ollama_body(system_prompt: str, user_prompt: str, schema: dict, sort_keys: bool) -> tuple[str, str]:
    body = {
        "model": "qwen3:8b",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "stream": False, "think": False,
        "options": {"temperature": 0.0, "seed": 42, "num_predict": compute_max_tokens(1)},
        "format": schema,
    }
    payload = json.dumps(body, sort_keys=sort_keys, separators=(",", ":"))
    return "http://localhost:11434/api/chat", payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=["vllm", "ollama"], required=True)
    args = parser.parse_args()
    build_url_body = _vllm_body if args.backend == "vllm" else _ollama_body

    overall_ok = True
    for decision_type, build_prompts in _DECISION_TYPES.items():
        system_prompt, user_prompt, schema = build_prompts()
        print(f"\n=== {decision_type} ===")
        for sort_keys in (False, True):
            url, payload = build_url_body(system_prompt, user_prompt, schema, sort_keys)
            response = httpx.post(url, content=payload, headers={"Content-Type": "application/json"}, timeout=120.0)
            data = response.json()
            if args.backend == "vllm":
                finish_reason = data["choices"][0]["finish_reason"]
                content = data["choices"][0]["message"]["content"] or ""
                ok = finish_reason == "stop"
            else:
                content = data.get("message", {}).get("content") or ""
                ok = data.get("done_reason") == "stop"
            overall_ok = overall_ok and ok
            print(f"  sort_keys={sort_keys}: {'OK' if ok else 'FAILED'} content_len={len(content)}")
            if not ok:
                print(f"    tail: {content[-80:]!r}")

    print(f"\n--- result ({args.backend}) ---")
    print("ALL CLEAN" if overall_ok else "AT LEAST ONE FAILURE -- see detail above")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
