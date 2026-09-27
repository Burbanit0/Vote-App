"""
scripts/check_ollama_structured_output.py

Verification spike for polity v2 increment 1 (approved plan
"abundant-puzzling-bubble.md"): before writing llm_client.py, confirm that
Ollama's OpenAI-compatible endpoint (/v1/chat/completions, what
polity_config.yaml's llm.base_url actually points at) supports what the
production client needs from qwen3:8b, a reasoning ("thinking") model by
default:

1. model is actually present/pulled
2. <think>...</think> suppression, since a reasoning model's default output
   would either break JSON parsing or eat the whole token budget
3. structured JSON output honoring VoteCastBatch's real Pydantic schema
   (not a toy schema -- this exercises $defs/$ref nesting too)
4. seed fidelity through the /v1 compat layer
5. sequential determinism on the actual code path being built (the earlier
   check_llm_batching_determinism.py protocol tested native /api/generate
   with free text, not the structured-output /v1 surface this project is
   actually going to use)
6. whether a full-size batch (25 citizens x 20 dims) fits Ollama's default
   context window without silent truncation

Setup:
    docker run -d -p 11434:11434 --name ollama ollama/ollama
    docker exec ollama ollama pull qwen3:8b      # ~5GB

Usage:
    python fast_api_voter/scripts/check_ollama_structured_output.py
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.codebook import VOTE_MOTIF_PROMPT_TABLE  # noqa: E402
from api.domain.polity.llm_schemas import VOTE_CAST_JSON_SCHEMA, VoteCastBatch  # noqa: E402

BASE_URL = "http://localhost:11434/v1"
MODEL = "qwen3:8b"
SEED = 42
THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
Log = Callable[[str], None]


def _inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Ollama's structured-output layer cannot handle Pydantic's
    $defs/$ref nesting -- confirmed empirically (see results doc): the
    exact same schema silently consumes the whole token budget with zero
    output when $ref is present, and works correctly once dereferenced.
    Resolves nested BaseModel refs by substitution; adequate for this
    project's one-level-deep decision schemas, not a general $ref resolver."""
    schema = copy.deepcopy(schema)
    defs = schema.pop("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                ref_name = node["$ref"].split("/")[-1]
                return resolve(copy.deepcopy(defs[ref_name]))
            return {key: resolve(value) for key, value in node.items()}
        if isinstance(node, list):
            return [resolve(item) for item in node]
        return node

    return dict(resolve(schema))


RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {"name": "vote_cast_batch", "strict": True, "schema": _inline_refs(VOTE_CAST_JSON_SCHEMA)},
}


def _system_prompt(citizens: list[dict[str, Any]], candidate_count: int) -> str:
    """A bare 'return exactly N decisions' was empirically insufficient
    (see results doc, Finding B) -- the model dropped the last citizen of a
    25-item batch despite this instruction. Enumerating the full cid list
    verbatim plus an explicit self-check fixed it on the first try."""
    truncate_note = "" if candidate_count <= 6 else " (classer au plus les 5 meilleurs)"
    cid_list = ",".join(str(c["cid"]) for c in citizens)
    return (
        "Tu es un moteur de simulation. Pour chaque citoyen recu, decide son "
        f"vote parmi les candidats.\nClasse les candidats du meilleur au "
        f"moins bon{truncate_note}, ou vote blanc (blank=1, ranking vide) si "
        "aucun candidat n'est acceptable.\nMotifs valides (code court "
        f"obligatoire) :\n{VOTE_MOTIF_PROMPT_TABLE}\nIMPORTANT : la liste "
        f"decisions doit contenir EXACTEMENT ces {len(citizens)} cid, chacun "
        f"une seule fois, dans cet ordre : [{cid_list}]. Verifie ta reponse "
        "avant de la finaliser : chaque cid de cette liste doit apparaitre "
        "exactement une fois.\nReponds UNIQUEMENT avec un objet JSON "
        "conforme au schema fourni."
    )


def _citizen_block(cid: int, dims: int, offset: float) -> dict[str, Any]:
    return {
        "cid": cid,
        "positions": [round((offset + i * 0.017) % 1.0, 2) for i in range(dims)],
        "priorities": [round(1.0 / dims, 3) for _ in range(dims)],
        "blank_threshold": 0.5,
    }


def _candidate_block(cid: int, dims: int, offset: float) -> dict[str, Any]:
    return {"cid": cid, "platform": [round((offset + i * 0.031) % 1.0, 2) for i in range(dims)]}


def _user_prompt(citizens: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> str:
    return json.dumps({"candidates": candidates, "voters": citizens}, sort_keys=True, separators=(",", ":"))


def _post(
    client: httpx.Client,
    messages: list[dict[str, str]],
    *,
    seed: int,
    structured: bool,
    max_tokens: int,
) -> httpx.Response:
    body: dict[str, Any] = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.0,
        "seed": seed,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if structured:
        body["response_format"] = RESPONSE_FORMAT
    return client.post(
        f"{BASE_URL}/chat/completions",
        content=json.dumps(body, sort_keys=True, separators=(",", ":")),
        headers={"Content-Type": "application/json"},
        timeout=300.0,
    )


def _content(response: httpx.Response) -> str | None:
    if response.status_code != 200:
        return None
    try:
        return str(response.json()["choices"][0]["message"]["content"])
    except (KeyError, IndexError):
        return None


def check_model_present(client: httpx.Client, log: Log) -> bool:
    response = client.get(f"{BASE_URL}/models", timeout=30.0)
    names = [m["id"] for m in response.json().get("data", [])] if response.status_code == 200 else []
    ok = MODEL in names
    log(f"1. model present at {BASE_URL}/models: {ok} (found: {names})")
    return ok


def check_think_block(client: httpx.Client, log: Log) -> bool:
    messages = [{"role": "user", "content": "Reponds uniquement par le mot OUI ou NON."}]
    response = _post(client, messages, seed=SEED, structured=False, max_tokens=256)
    content = _content(response) or f"<request failed: HTTP {response.status_code}>"
    has_think = "<think>" in content
    log(f"2. plain chat response contains <think>: {has_think}")
    log(f"   raw content (first 300 chars): {content[:300]!r}")
    return has_think


def check_structured_output(client: httpx.Client, log: Log) -> bool:
    citizens = [_citizen_block(1, 4, 0.1), _citizen_block(2, 4, 0.4), _citizen_block(3, 4, 0.8)]
    candidates = [_candidate_block(10, 4, 0.0), _candidate_block(11, 4, 0.5), _candidate_block(12, 4, 0.9)]
    messages = [
        {"role": "system", "content": _system_prompt(citizens, len(candidates))},
        {"role": "user", "content": _user_prompt(citizens, candidates)},
    ]
    start = time.monotonic()
    response = _post(client, messages, seed=SEED, structured=True, max_tokens=512)
    elapsed = time.monotonic() - start
    content = _content(response)
    if content is None:
        log(f"3. structured output (toy 3-citizen batch): request FAILED, HTTP {response.status_code}: "
            f"{response.text[:500]}")
        return False
    body = response.json()
    finish_reason = body["choices"][0].get("finish_reason")
    usage = body.get("usage", {})
    log(f"3. structured output (toy 3-citizen batch): finish_reason={finish_reason}, usage={usage}, "
        f"elapsed={elapsed:.1f}s, content_len={len(content)}")
    stripped = THINK_TAG_RE.sub("", content).strip()
    try:
        batch = VoteCastBatch.model_validate_json(stripped)
        cids_match = [d.cid for d in batch.decisions] == [1, 2, 3]
        log(f"   valid=True, cids in order={cids_match}")
        return cids_match
    except Exception as exc:  # noqa: BLE001 -- spike script: report any validation failure shape
        log(f"   FAILED to validate: {exc}")
        log(f"   raw content (first 800 chars): {content[:800]!r}")
        return False


def check_seed_fidelity(client: httpx.Client, log: Log) -> bool:
    # At temperature=0, decoding is greedy/argmax -- seed has nothing to
    # randomize, so a different seed producing the SAME output is expected
    # and correct, not a failure. Only same-seed-twice-identical matters.
    messages = [{"role": "user", "content": "Choisis un nombre entier entre 1 et 1000000 et reponds uniquement par ce nombre."}]
    a1 = _content(_post(client, messages, seed=42, structured=False, max_tokens=32))
    a2 = _content(_post(client, messages, seed=42, structured=False, max_tokens=32))
    b1 = _content(_post(client, messages, seed=7, structured=False, max_tokens=32))
    same_seed_identical = a1 is not None and a1 == a2
    log(f"4. seed fidelity: same seed twice identical={same_seed_identical} "
        f"(informational: different seed gave {'the same' if a1 == b1 else 'a different'} output -- "
        f"expected to not matter at temperature=0)")
    return same_seed_identical


def check_sequential_determinism(client: httpx.Client, log: Log) -> bool:
    citizens = [_citizen_block(1, 4, 0.1)]
    candidates = [_candidate_block(10, 4, 0.0), _candidate_block(11, 4, 0.5)]
    messages = [
        {"role": "system", "content": _system_prompt(citizens, len(candidates))},
        {"role": "user", "content": _user_prompt(citizens, candidates)},
    ]
    outputs = [
        _content(_post(client, messages, seed=SEED, structured=True, max_tokens=256)) for _ in range(5)
    ]
    identical = None not in outputs and len(set(outputs)) == 1
    log(f"5. sequential determinism on the /v1 structured-output surface, 5 calls: identical={identical}")
    return identical


def check_full_size_batch(client: httpx.Client, log: Log) -> bool:
    citizens = [_citizen_block(i, 20, i * 0.037) for i in range(25)]
    candidates = [_candidate_block(1000 + i, 20, i * 0.081) for i in range(10)]
    messages = [
        {"role": "system", "content": _system_prompt(citizens, len(candidates))},
        {"role": "user", "content": _user_prompt(citizens, candidates)},
    ]
    start = time.monotonic()
    response = _post(client, messages, seed=SEED, structured=True, max_tokens=25 * 40 + 128)
    elapsed = time.monotonic() - start
    content = _content(response)
    if content is None:
        log(f"6. full-size batch (25 citizens x 20 dims) FAILED: HTTP {response.status_code}: {response.text[:500]}")
        return False
    body = response.json()
    finish_reason = body["choices"][0].get("finish_reason")
    usage = body.get("usage", {})
    log(f"6. full-size batch (25 citizens x 20 dims, {len(candidates)} candidates): "
        f"finish_reason={finish_reason}, usage={usage}, elapsed={elapsed:.1f}s, content_len={len(content)}")
    stripped = THINK_TAG_RE.sub("", content).strip()
    ok = False
    try:
        batch = VoteCastBatch.model_validate_json(stripped)
        count_ok = len(batch.decisions) == 25
        cids_ok = [d.cid for d in batch.decisions] == [c["cid"] for c in citizens]
        ok = count_ok and cids_ok and finish_reason == "stop"
        log(f"   valid={ok}, count_ok={count_ok} (got {len(batch.decisions)}), cids_ok={cids_ok}")
    except Exception as exc:  # noqa: BLE001
        log(f"   validation error: {exc}")
        log(f"   raw content (first 1500 chars): {content[:1500]!r}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, help="write the full log to this markdown file")
    args = parser.parse_args()

    lines: list[str] = []

    def log(line: str) -> None:
        print(line)
        lines.append(line)

    log(f"# Ollama structured-output verification -- model={MODEL}, base_url={BASE_URL}\n")

    with httpx.Client() as client:
        results = {
            "model_present": check_model_present(client, log),
            "think_block_present": check_think_block(client, log),
            "structured_output": check_structured_output(client, log),
            "seed_fidelity": check_seed_fidelity(client, log),
            "sequential_determinism": check_sequential_determinism(client, log),
            "full_size_batch": check_full_size_batch(client, log),
        }

    overall = (
        results["model_present"]
        and results["structured_output"]
        and results["seed_fidelity"]
        and results["sequential_determinism"]
        and results["full_size_batch"]
    )
    log(f"\n## Summary\n\n{json.dumps(results, indent=2)}")
    log(f"\n**Overall (excluding the informational <think> check): {'PASS' if overall else 'FAIL'}**")

    if args.results:
        args.results.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log(f"\n(full log written to {args.results})")

    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
