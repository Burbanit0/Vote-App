"""
scripts/check_vllm_remaining_decisions_sort_keys_truncation.py

Completes the sort_keys=True truncation sweep started by check_vllm_pressure_action_sort_keys_
truncation.py (found the bug on PressureDecision) and check_vllm_response_coalition_sort_keys_
truncation.py (ResponseDecision/CoalitionDecision clean). Covers the 3 decision types not yet
checked: CandidacyDecision, PartyNominationDecision, ReactionDecision -- completing coverage of
all 9 decision types in the engine.

Field shapes, declared vs. alphabetical order under sort_keys=True:
  CandidacyDecision:       cid, outcome, motif        -> cid, motif, outcome
  PartyNominationDecision: party_id, winner_position, motif -> motif, party_id, winner_position
  ReactionDecision:        cid, salience_delta, motif  -> cid, motif, salience_delta

All three are flat (no array fields), matching PressureDecision's general shape more than
ResponseDecision's (which has an array field and was clean). CandidacyDecision and
ReactionDecision are the closest match in field COUNT (3, like CoalitionDecision, already clean);
PartyNominationDecision's `winner_position` is a plain int like the others.

Real production prompts/schemas, minimal synthetic-but-valid setups (not full population
harnesses -- these three don't need one to test a single legal request). think=False,
compute_max_tokens(1) throughout, matching each decision type's real production call.

Usage:
    docker compose -f docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_vllm_remaining_decisions_sort_keys_truncation.py --backend vllm
    python fast_api_voter/scripts/check_vllm_remaining_decisions_sort_keys_truncation.py --backend ollama
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen  # noqa: E402
from api.domain.polity.codebook import EventType  # noqa: E402
from api.domain.polity.config import load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    ReactionContext,
    build_candidacy_system_prompt,
    build_candidacy_user_prompt,
    build_party_nomination_system_prompt,
    build_party_nomination_user_prompt,
    build_reaction_system_prompt,
    build_reaction_user_prompt,
    compute_max_tokens,
)
from api.domain.polity.llm_client import _inline_refs  # noqa: E402
from api.domain.polity.llm_schemas import (  # noqa: E402
    CANDIDACY_JSON_SCHEMA,
    PARTY_NOMINATION_JSON_SCHEMA,
    REACTION_JSON_SCHEMA,
)
from api.domain.polity.parties import Party  # noqa: E402


def _citizen(cid: int, ambition: float = 0.5) -> Citizen:
    return Citizen(
        citizen_id=cid,
        issue_positions=tuple((cid * 0.037 + i * 0.017) % 1.0 for i in range(20)),
        issue_priorities=tuple(1.0 / 20 for _ in range(20)),
        blank_threshold=0.5,
        ambition_score=ambition,
    )


def _candidacy_prompts() -> tuple[str, str, dict]:
    c = _citizen(3, ambition=0.6)
    system_prompt = build_candidacy_system_prompt([c])
    user_prompt = build_candidacy_user_prompt([c], {3: 0.4})
    return system_prompt, user_prompt, _inline_refs(CANDIDACY_JSON_SCHEMA)


def _party_nomination_prompts() -> tuple[str, str, dict]:
    party = Party(party_id=10, platform=(0.5,) * 20)
    members = [_citizen(1, ambition=0.9), _citizen(2, ambition=0.3)]
    contested = {10: members}
    parties_by_id = {10: party}
    support = {1: 0.5, 2: 0.5}
    system_prompt = build_party_nomination_system_prompt(contested)
    user_prompt = build_party_nomination_user_prompt(contested, parties_by_id, support)
    return system_prompt, user_prompt, _inline_refs(PARTY_NOMINATION_JSON_SCHEMA)


def _reaction_prompts() -> tuple[str, str, dict]:
    config = load_config()
    c = _citizen(5)
    ctx = ReactionContext(cid=5, event_salience=0.2)
    system_prompt = build_reaction_system_prompt([c], EventType.SCANDAL, config)
    user_prompt = build_reaction_user_prompt([c], {5: ctx}, event_type=EventType.SCANDAL, target=1, magnitude=0.0)
    return system_prompt, user_prompt, _inline_refs(REACTION_JSON_SCHEMA)


_DECISION_TYPES = {
    "candidacy": _candidacy_prompts,
    "party_nomination": _party_nomination_prompts,
    "reaction": _reaction_prompts,
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
