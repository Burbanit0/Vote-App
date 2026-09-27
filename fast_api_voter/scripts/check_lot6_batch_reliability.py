"""
scripts/check_lot6_batch_reliability.py

v4 Lot 6/7 pre-flight spike (dev-plan/merry-hugging-hamming.md, "Principal
risks"): before writing any production prompt-builder code for
representative_response (dt=6) or pressure_action (dt=10), confirm real
qwen3:8b can hold small-batch structured output together for BOTH new
schemas at the batch sizes these decision types will actually see --
neither can use chunk_voters/MIN_SAFE_BATCH_SIZE (same reasoning that
already exempted nominations/positioning/coalition), so this is the
increment-1 precedent (check_ollama_structured_output.py) applied here,
not the later check_batch_size_boundary.py's large-batch-boundary study.

Toy schemas only -- llm_schemas.py has no ResponseDecision/PressureDecision
yet (that's Lot 6/7's own job); these are standalone Pydantic models built
directly from the design doc's own worked examples (§3.6.5, §3.6.6), just
like check_ollama_structured_output.py's VoteCastBatch-shaped toy schema
predated llm_schemas.py's real one. $defs/$ref are inlined before being
sent to Ollama -- confirmed necessary by that same earlier spike (silent
zero-output otherwise).

representative_response (dt=6) is, in real production use, always a batch
of exactly 1 (only the president exists as a tracked office today) -- swept
here anyway at 1/3/5/10 to characterize the SCHEMA's own small-batch
reliability independent of that production constraint, since Lot 7's
pressure_action genuinely does see a variable-size cohort in that same
range.

Setup:
    docker run -d -p 11434:11434 --name ollama ollama/ollama
    docker exec ollama ollama pull qwen3:8b      # ~5GB

Usage:
    python fast_api_voter/scripts/check_lot6_batch_reliability.py \
        --sizes 1 3 5 10 --repeats 2 \
        --results scripts/lot6_batch_reliability_results.md
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BASE_URL = "http://localhost:11434/v1"
MODEL = "qwen3:8b"
SEED = 42
THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


# ── Toy schemas (§3.6.5 / §3.6.6 -- NOT llm_schemas.py, Lot 6/7's own job) ──

class ToyPositionShift(BaseModel):
    model_config = {"extra": "forbid"}
    dimension: int = Field(..., ge=0)
    delta: float = Field(..., ge=-1.0, le=1.0)


class RepresentativeResponseDecision(BaseModel):
    """§3.6.5's worked example: cid, delta (sparse, reuses §3.6.5's own
    'delta borné' framing via PositionShift's shape), stance (enum,
    §3.7.1), motif (300-399 range)."""
    model_config = {"extra": "forbid"}
    cid: int = Field(..., ge=0)
    delta: list[ToyPositionShift] = Field(..., max_length=3)
    stance: Literal[1, 2, 3, 4]
    motif: Literal[301, 302, 303, 304, 305]


class RepresentativeResponseBatch(BaseModel):
    model_config = {"extra": "forbid"}
    decisions: list[RepresentativeResponseDecision] = Field(..., min_length=1)


class PressureActionDecision(BaseModel):
    """§3.6.6's worked example: cid, target (the officeholder), act
    (0-4, §3.7.1), motif (300-399 range, excluding 302/306 per §7bis.9f's
    atomized-regime requirement -- not enforced by this toy schema, since
    that constraint belongs to the real production schema, not this
    reliability spike)."""
    model_config = {"extra": "forbid"}
    cid: int = Field(..., ge=0)
    target: int = Field(..., ge=0)
    act: Literal[0, 1, 2, 3, 4]
    motif: Literal[301, 303, 304, 305]


class PressureActionBatch(BaseModel):
    model_config = {"extra": "forbid"}
    decisions: list[PressureActionDecision] = Field(..., min_length=1)


def _inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Same fix as check_ollama_structured_output.py's own -- Ollama's
    structured-output layer cannot handle Pydantic's $defs/$ref nesting."""
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


_JSON_SCHEMAS = {
    "representative_response": _inline_refs(RepresentativeResponseBatch.model_json_schema()),
    "pressure_action": _inline_refs(PressureActionBatch.model_json_schema()),
}

_MODEL_CLASSES: dict[str, type[BaseModel]] = {
    "representative_response": RepresentativeResponseBatch,
    "pressure_action": PressureActionBatch,
}


def _rep_response_system_prompt(cids: list[int]) -> str:
    cid_list = ",".join(str(c) for c in cids)
    return (
        "Tu es un moteur de simulation. Pour chaque elu recu (representative_response, dt=6), "
        "decide sa reaction a la pression citoyenne recue.\n"
        "stance : 1=concession (ajuste sa position), 2=defiance (maintient/accentue), "
        "3=silence (aucun ajustement), 4=counter_mobilization.\n"
        "delta : au plus 3 deplacements de dimension, chaque delta entre -1.0 et 1.0.\n"
        "motif : un code parmi 301,302,303,304,305.\n"
        f"IMPORTANT : la liste decisions doit contenir EXACTEMENT ces {len(cids)} cid, "
        f"chacun une seule fois, dans cet ordre : [{cid_list}]. Verifie ta reponse avant de "
        "la finaliser.\nReponds UNIQUEMENT avec un objet JSON conforme au schema fourni."
    )


def _rep_response_user_prompt(cids: list[int]) -> str:
    holders = [
        {"cid": cid, "office": 1, "L": 0.34, "mandate_dev": 0.41, "street": 0.58, "lame_duck": 0, "ticks_left": 6}
        for cid in cids
    ]
    return json.dumps({"holders": holders}, sort_keys=True, separators=(",", ":"))


def _pressure_action_system_prompt(cids: list[int], target: int) -> str:
    cid_list = ",".join(str(c) for c in cids)
    return (
        "Tu es un moteur de simulation. Pour chaque citoyen mecontent recu (pressure_action, "
        "dt=10), decide son action envers l'elu cible.\n"
        "act : 0=rien, 1=signer une petition, 2=lancer une petition, 3=mobiliser, "
        "4=attendre la prochaine election.\n"
        "motif : un code parmi 301,303,304,305.\n"
        f"IMPORTANT : la liste decisions doit contenir EXACTEMENT ces {len(cids)} cid, "
        f"chacun une seule fois, dans cet ordre : [{cid_list}]. target doit valoir {target} "
        "pour chaque decision. Verifie ta reponse avant de la finaliser.\n"
        "Reponds UNIQUEMENT avec un objet JSON conforme au schema fourni."
    )


def _pressure_action_user_prompt(cids: list[int], target: int) -> str:
    citizens = [
        {"cid": cid, "target": target, "self_gap": round(0.3 + (cid % 5) * 0.08, 2),
         "mandate_dev": 0.41, "neighbors_acting": None, "ticks_to_election": 9}
        for cid in cids
    ]
    return json.dumps({"citizens": citizens}, sort_keys=True, separators=(",", ":"))


def _compute_max_tokens(batch_size: int) -> int:
    """Same formula as llm_behavior_engine.compute_max_tokens: a flat
    reasoning allowance, not scaled by batch size -- a live consolidation
    run showed <think> reasoning length is unpredictable, not proportional
    to the number of decisions to emit."""
    return max(batch_size * 60 + 1536, 1536)


def _post(client: httpx.Client, messages: list[dict[str, str]], *, json_schema: dict, max_tokens: int) -> httpx.Response:
    """think=False via Ollama's NATIVE /api/chat endpoint, not the /v1
    structured-output surface -- llm_client.py's own class docstring (and
    this spike's own first smoke-test failure, both schemas hitting
    finish_reason='length' with zero visible output at think=True) confirm
    qwen3:8b reliably burns its entire completion budget on invisible
    <think> reasoning on the /v1 endpoint regardless of a `think` body
    field; only the native endpoint's think=false actually suppresses it.
    Every non-vote_cast decision type in production (candidacy, party
    nomination, positioning, coalition) already made this same choice --
    representative_response/pressure_action are structurally the same
    shape of short, per-citizen structured decision."""
    native_base = BASE_URL.removesuffix("/v1")
    body: dict[str, Any] = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "think": False,
        "format": json_schema,
        "options": {"temperature": 0.0, "seed": SEED, "num_predict": max_tokens},
    }
    return client.post(
        f"{native_base}/api/chat",
        content=json.dumps(body, sort_keys=True, separators=(",", ":")),
        headers={"Content-Type": "application/json"},
        timeout=600.0,
    )


def _content(response: httpx.Response) -> str | None:
    if response.status_code != 200:
        return None
    try:
        return str(response.json()["message"]["content"])
    except (KeyError, TypeError):
        return None


def _finish_reason(response: httpx.Response) -> str | None:
    try:
        reason = response.json().get("done_reason")
        return str(reason) if reason is not None else None
    except (KeyError, TypeError, ValueError):
        return None


def run_one(client: httpx.Client, schema_name: str, batch_size: int) -> dict[str, Any]:
    cids = [100 + i for i in range(batch_size)]
    target = 205
    if schema_name == "representative_response":
        messages = [
            {"role": "system", "content": _rep_response_system_prompt(cids)},
            {"role": "user", "content": _rep_response_user_prompt(cids)},
        ]
    else:
        messages = [
            {"role": "system", "content": _pressure_action_system_prompt(cids, target)},
            {"role": "user", "content": _pressure_action_user_prompt(cids, target)},
        ]

    max_tokens = _compute_max_tokens(batch_size)
    start = time.monotonic()
    response = _post(client, messages, json_schema=_JSON_SCHEMAS[schema_name], max_tokens=max_tokens)
    elapsed = time.monotonic() - start
    content = _content(response)
    if content is None:
        return {"ok": False, "elapsed": elapsed, "reason": f"HTTP {response.status_code}: {response.text[:300]}"}

    finish_reason = _finish_reason(response)
    stripped = THINK_TAG_RE.sub("", content).strip()
    model_cls = _MODEL_CLASSES[schema_name]
    try:
        batch = model_cls.model_validate_json(stripped)
    except (ValidationError, json.JSONDecodeError) as exc:
        return {
            "ok": False, "elapsed": elapsed, "finish_reason": finish_reason,
            "reason": f"validation failed: {exc}", "raw": content[:500],
        }

    got_cids = [d.cid for d in batch.decisions]  # type: ignore[attr-defined]
    cids_ok = got_cids == cids
    if schema_name == "pressure_action":
        target_ok = all(d.target == target for d in batch.decisions)  # type: ignore[attr-defined]
    else:
        target_ok = True
    ok = cids_ok and target_ok and finish_reason == "stop"
    return {
        "ok": ok, "elapsed": elapsed, "finish_reason": finish_reason,
        "cids_ok": cids_ok, "target_ok": target_ok, "got_cids": got_cids, "expected_cids": cids,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=[1, 3, 5, 10])
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--results", type=Path, default=None)
    args = parser.parse_args()

    lines: list[str] = []

    def log(line: str) -> None:
        print(line, flush=True)
        lines.append(line)

    log(f"# Lot 6/7 small-batch reliability spike -- model={MODEL}, base_url={BASE_URL}\n")
    log(f"sizes={args.sizes}, repeats={args.repeats}\n")
    log("| schema | batch_size | rep | ok | finish_reason | elapsed(s) | detail |")
    log("|---|---|---|---|---|---|---|")

    failure_count = 0
    total_count = 0

    with httpx.Client() as client:
        for schema_name in ("representative_response", "pressure_action"):
            for size in args.sizes:
                for rep in range(1, args.repeats + 1):
                    result = run_one(client, schema_name, size)
                    total_count += 1
                    if not result["ok"]:
                        failure_count += 1
                    detail = (
                        f"got={result.get('got_cids')}" if result["ok"]
                        else result.get("reason", "unknown failure")
                    )
                    log(
                        f"| {schema_name} | {size} | {rep} | {result['ok']} | "
                        f"{result.get('finish_reason', 'n/a')} | {result['elapsed']:.1f} | {detail} |"
                    )

    log(f"\n## Summary\n\nfailures: {failure_count}/{total_count}")
    log(f"\n**Overall: {'PASS' if failure_count == 0 else 'FAIL'}**")

    if args.results:
        args.results.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log(f"\n(full log written to {args.results})")

    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
