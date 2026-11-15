"""
scripts/check_vllm_pressure_action_sort_keys_truncation.py

Found while comparing vLLM against Ollama on pressure_action's real, unmodified production
schema (PressureDecision -- no test-only fields, unlike check_vllm_pressure_action_reasoning_
field_first.py's a_reasoning variant): check_vllm_pressure_action_open_menu_baseline.py measured
60/70 (85.7%) truncations under vLLM, a rate far beyond anything seen on Ollama for this decision
type. Root-caused here to `sort_keys=True` (llm_client.py's shared canonical serialization,
applied to every decision type, every provider): reordering PressureDecision's wire fields from
their natural declaration order (cid, target, act, motif) to alphabetical (act, cid, motif,
target) reliably triggers a non-terminating whitespace-generation loop under vLLM's structured-
output backend -- the model emits valid tokens through `"motif": <n>` and then generates `\\n   `
repeated hundreds of times, never reaching `target` or closing the object, burning the entire
token budget (finish_reason='length').

This is NOT the same finding as plan-pressure-action-remediation.md's own sort_keys discovery
(§3.4 -- reasoning generated after, not before, act/motif). That was about FIELD OMISSION ORDER
changing what information the model has already committed to before writing a given field. This
is different and more severe: the reordering itself, with no reasoning field involved at all,
induces complete non-termination on a real production schema PressureDecision has always shipped
with.

Isolated with a controlled A/B (this script), both providers, both orderings, same 4 citizens,
same prompts, exact production request shapes (VllmJsonClient's OpenAI-compat body; Ollama's
native /api/chat body, matching pressure_action_harness.raw_pressure_call exactly):

  vLLM:   sort_keys=False -> 4/4 clean.  sort_keys=True (shipped) -> 4/4 FAIL (whitespace loop).
  Ollama: sort_keys=False -> 4/4 clean.  sort_keys=True (shipped) -> 4/4 clean.

Deterministic (temperature=0, same seed) and vLLM-specific -- Ollama is unaffected by the exact
same reordering on the exact same schema/prompts. The precise xgrammar/vLLM-internal mechanism
that makes THIS schema shape (four flat integer fields, two of them `enum`-constrained) vulnerable
is not investigated here -- out of scope without vLLM-internals-level tooling this project
doesn't have.

NOT fixed here, deliberately: sort_keys is shared code across every decision type in the project,
and plan-pressure-action-resolution.md already establishes the discipline that touching it needs
its own separate scoping decision, never a workaround folded into an unrelated investigation. This
script exists to make the finding reproducible on demand, not to resolve it.

Usage:
    docker compose -f docker-compose.llm.yml up -d   # for the vLLM half
    docker compose -f docker-compose.ollama.yml up -d   # for the Ollama half (stop the other first
                                                          # -- see the GPU-contention note in
                                                          # docker-compose.ollama.yml)
    python fast_api_voter/scripts/check_vllm_pressure_action_sort_keys_truncation.py --backend vllm
    python fast_api_voter/scripts/check_vllm_pressure_action_sort_keys_truncation.py --backend ollama
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    PressureContext,
    build_pressure_system_prompt,
    build_pressure_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import _inline_refs  # noqa: E402
from api.domain.polity.llm_schemas import PRESSURE_JSON_SCHEMA  # noqa: E402

_CASES = [(3, 0.1718), (8, 0.2023), (18, 0.2562), (27, 0.4965)]


class _Citizen:
    citizen_id: int


def _prompts(config, cid: int, gap: float) -> tuple[str, str]:
    c = _Citizen()
    c.citizen_id = cid
    system_prompt = build_pressure_system_prompt([c], config)
    ctx = PressureContext(
        cid=cid, target=5, self_gap=gap, mandate_dev=0.0, ticks_to_election=15,
        available=(0, 1, 2, 3, 4), petition_open=False, petition_expires_at_tick=None,
        already_signed=False, neighbors_acting=None,
    )
    user_prompt = build_pressure_user_prompt([c], {cid: ctx})
    return system_prompt, user_prompt


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

    shipped = load_config()
    config = dataclasses.replace(
        shipped,
        pressure_menu=dataclasses.replace(
            shipped.pressure_menu, electoral_only=False, petition_enabled=True, mobilization_enabled=True,
        ),
    )
    schema = _inline_refs(PRESSURE_JSON_SCHEMA)
    build_body = _vllm_body if args.backend == "vllm" else _ollama_body

    results: dict[bool, list[bool]] = {False: [], True: []}
    for cid, gap in _CASES:
        system_prompt, user_prompt = _prompts(config, cid, gap)
        for sort_keys in (False, True):
            url, payload = build_body(system_prompt, user_prompt, schema, sort_keys)
            response = httpx.post(url, content=payload, headers={"Content-Type": "application/json"}, timeout=120.0)
            data = response.json()
            if args.backend == "vllm":
                finish_reason = data["choices"][0]["finish_reason"]
                content = data["choices"][0]["message"]["content"] or ""
                ok = finish_reason == "stop"
            else:
                content = data.get("message", {}).get("content") or ""
                ok = data.get("done_reason") == "stop"
            results[sort_keys].append(ok)
            print(f"cid={cid} sort_keys={sort_keys}: {'OK' if ok else 'FAILED'} content_len={len(content)}")

    print(f"\n--- result ({args.backend}) ---")
    for sort_keys in (False, True):
        oks = results[sort_keys]
        print(f"sort_keys={sort_keys}: {sum(oks)}/{len(oks)} clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
