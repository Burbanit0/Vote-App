"""
scripts/check_vllm_chunk_size_throughput.py

Phase 2's own "also worth testing" item, never actually run: `_VOTE_CAST_MAX_CHUNK_SIZE` and
`_CHAMBER_MAX_CHUNK_SIZE` are both pinned to 1. Chamber's own docstring pins it purely on TOKEN-BUDGET
EXHAUSTION under a flat think-token allowance ("Mode B": chunk=5 failed EXACTLY at
`compute_max_tokens(5)+8000=9836`, on the nose -- converges once given enough budget). vote_cast's
history is different and more serious: cast_votes's own docstring documents a SEPARATE, independently
measured "Mode A" collapse -- batches of 4+ produce structurally valid, schema-conformant rankings
that are simply WRONG relative to each voter's own precomputed weighted_distance (an identity-
permutation collapse, 0-2/5 correct at chunk=5) -- verified directly against ground truth, not fixed
by any amount of extra budget, and never re-tested since the vLLM switch (every citation is Ollama:
`OLLAMA_CONTEXT_LENGTH`). This script re-tests both, on the real vLLM/AWQ backend, against real
production prompts.

**Why this doesn't touch Phase 2's own reproducibility finding at all**: chunk size is orthogonal to
concurrency. At `workers=1`, every chunk size still submits exactly ONE request at a time to vLLM --
batch composition is always a single sequence, so the batch-composition-dependent floating-point
sensitivity Phase 2 found (and `VLLM_BATCH_INVARIANT` confirmed the mechanism of, at prohibitive
cost -- `check_vllm_batch_invariant_results.md`) never enters the picture. A bigger request, one at a
time, is not a differently-shaped concurrency question.

**What this measures, and what it deliberately does not decide**: per-citizen wall-clock throughput
at chunk sizes {1, 2, 3, 5} for both decision types, AND decode correctness against ground truth at
each size -- for vote_cast that means diffing the decoded ranking against `simple_rules.build_ranking`
(the same sincere-ballot logic `_deterministic_vote_fallback` uses), not just schema validity, because
an identity-permutation collapse passes schema validation cleanly. A size that merely avoids
truncation but silently corrupts ballots is not a real win. Whether any measured speedup is worth
adopting (and at what size) is a judgment call for whoever reads this, not decided here -- same
discipline as the chunk-size investigations this constant's own docstring already cites.

**Sizing max_tokens**: an earlier version of this script scaled the think-token allowance up with
chunk size (`chunk_size * 6000`, etc.), on the theory that more citizens sharing one call need more
shared reasoning room. That contradicts this project's own established finding baked into
`compute_max_tokens` -- Qwen3's reasoning length is "unpredictable, not proportional to the number
of decisions", which is why production uses a flat addend, not a scaled one -- and in practice it
demanded more tokens than `--max-model-len 16384` allows once chunk_size >= 3 (a real request for
19716 tokens was rejected outright). This version instead probes the REAL prompt_tokens for the
exact prompt about to be sent (one cheap `max_tokens=1` call) and requests the maximum budget the
context window has left, greedily: `16384 - prompt_tokens - safety_margin`. That maximizes headroom
against truncation without guessing a formula, and (once the token-budget/Mode-B failure is out of
the way) is what makes it possible to see whether Mode A -- a pure reasoning/attention failure,
unaffected by budget size -- still happens on vLLM.

Usage:
    docker compose -f fast_api_voter/docker-compose.llm.yml up -d
    python fast_api_voter/scripts/check_vllm_chunk_size_throughput.py
    python fast_api_voter/scripts/check_vllm_chunk_size_throughput.py \\
        --results scripts/check_vllm_chunk_size_throughput_results.md
"""
from __future__ import annotations

import argparse
import dataclasses
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.domain.polity.citizen import Citizen, generate_population  # noqa: E402
from api.domain.polity.codebook import ChamberMotif  # noqa: E402
from api.domain.polity.config import PolityConfig, load_config  # noqa: E402
from api.domain.polity.llm_behavior_engine import (  # noqa: E402
    ChamberContext,
    build_chamber_system_prompt,
    build_chamber_user_prompt,
    build_system_prompt,
    build_user_prompt,
    compute_max_tokens,
    resolve_ranking_cids,
    validate_chamber_decision,
    validate_decision,
)
from api.domain.polity.llm_client import (  # noqa: E402
    LlmError,
    VllmJsonClient,
    decode_chamber_batch,
    decode_vote_batch,
)
from api.domain.polity.llm_schemas import CHAMBER_JSON_SCHEMA, VOTE_CAST_JSON_SCHEMA  # noqa: E402
from api.domain.polity.parties import initialize_parties  # noqa: E402
from api.domain.polity.simple_rules import (  # noqa: E402
    BLANK_LABEL,
    assign_party_affiliation,
    build_ranking,
    citizen_id_from_label,
    declare_candidacy,
)

import httpx  # noqa: E402

_CHUNK_SIZES = (1, 2, 3, 5)
# vLLM's own --max-model-len 16384 caps prompt_tokens + max_tokens together (not
# max_tokens alone, contrary to an earlier read of the error text -- confirmed by
# directly measuring real prompt_tokens per chunk size: vote_cast {1661, 1999,
# 2335, 3000} for chunk {1,2,3,5}, chamber {774, 1141, 1508, 2242}). A FLAT think
# allowance that scales with chunk size (as first tried here) both contradicts
# this project's own established philosophy -- `compute_max_tokens`'s addend is
# deliberately flat because reasoning length is "unpredictable, not proportional
# to the number of decisions", not because it was never considered -- and blows
# the ceiling outright once chunk_size >= 3. Instead: probe the real prompt_tokens
# for the exact prompt about to be sent, then request the MAXIMUM budget the
# context window allows, greedily -- this maximizes headroom against truncation
# without guessing a scaling formula.
_CONTEXT_LIMIT = 16384
_SAFETY_MARGIN = 300


def _probe_prompt_tokens(base_url: str, model: str, system_prompt: str, user_prompt: str) -> int:
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "temperature": 0.0,
        "seed": 42,
        "max_tokens": 1,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": True},
    }
    response = httpx.post(f"{base_url}/chat/completions", json=body, timeout=60)
    response.raise_for_status()
    return int(response.json()["usage"]["prompt_tokens"])


def _max_safe_tokens(prompt_tokens: int, floor: int) -> int:
    return max(floor, _CONTEXT_LIMIT - prompt_tokens - _SAFETY_MARGIN)


def _vllm_config() -> PolityConfig:
    shipped = load_config()
    return dataclasses.replace(shipped, llm=dataclasses.replace(shipped.llm, provider="vllm", base_url="http://localhost:8000/v1"))


def _vote_world(config: PolityConfig, n_voters: int, n_candidates: int) -> tuple[list[Citizen], list[Citizen]]:
    citizens = generate_population(config.citizens, n_voters, config.run.seed)
    parties = initialize_parties(citizens, n_candidates, config.run.seed)
    for citizen in citizens:
        citizen.party_affiliation = assign_party_affiliation(citizen, parties)
    nominees = []
    for party in parties:
        members = [c for c in citizens if c.party_affiliation == party.party_id]
        if members:
            nominees.append(max(members, key=lambda c: (c.ambition_score, -c.citizen_id)))
    for nominee in nominees:
        declare_candidacy(nominee)
    return citizens, sorted(nominees, key=lambda c: c.citizen_id)


def _chamber_member(cid: int, rep: int) -> Citizen:
    c = Citizen(
        citizen_id=cid,
        issue_positions=tuple((rep * 0.037 + cid * 0.019 + d * 0.013) % 1.0 for d in range(20)),
        issue_priorities=tuple(1.0 / 20 for _ in range(20)),
        blank_threshold=0.5,
        ambition_score=0.5,
        sortition_seat_until_tick=16,
        sortition_terms_served=1,
    )
    c.chamber_position = c.issue_positions
    return c


def _expected_ballot(voter: Citizen, candidates: list[Citizen]) -> tuple[int, list[int]]:
    """Ground truth for one voter, by the same logic _deterministic_vote_fallback
    uses: sincere ranking via simple_rules.build_ranking (ascending weighted_distance,
    blank spliced in at voter.blank_threshold). Returns (blank, ranking-as-cids), the
    same shape as a decoded VoteCastDecision, so a decision can be diffed against it
    directly."""
    ballot = build_ranking(voter, candidates)
    blank_index = ballot.index(BLANK_LABEL)
    if blank_index == 0:
        return 1, []
    return 0, [citizen_id_from_label(label) for label in ballot[:blank_index]]


def _measure_vote_cast(client: VllmJsonClient, config: PolityConfig, voters: list[Citizen], nominees: list[Citizen], chunk_size: int) -> dict:
    candidate_count = len(nominees)
    chunk = voters[:chunk_size]
    expected_cids = [v.citizen_id for v in chunk]
    system_prompt = build_system_prompt(chunk, nominees)
    user_prompt = build_user_prompt(chunk, nominees)
    prompt_tokens = _probe_prompt_tokens(config.llm.base_url, config.llm.model, system_prompt, user_prompt)
    max_tokens = _max_safe_tokens(prompt_tokens, floor=compute_max_tokens(chunk_size))
    start = time.perf_counter()
    try:
        raw = client.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=VOTE_CAST_JSON_SCHEMA,
            max_tokens=max_tokens,
            think=True,
        )
    except LlmError as exc:
        return {"chunk_size": chunk_size, "elapsed": time.perf_counter() - start, "ok": False, "detail": str(exc)[:200]}
    elapsed = time.perf_counter() - start
    try:
        decisions = decode_vote_batch(raw, expected_cids)
        for decision in decisions:
            validate_decision(decision, candidate_count, None)
    except LlmError as exc:
        return {"chunk_size": chunk_size, "elapsed": elapsed, "ok": False, "detail": str(exc).splitlines()[0][:200]}
    by_cid = {v.citizen_id: v for v in chunk}
    correct = 0
    for decision in decisions:
        voter = by_cid[decision.cid]
        expected_blank, expected_ranking = _expected_ballot(voter, list(nominees))
        actual_ranking = resolve_ranking_cids(decision, nominees) if decision.blank == 0 else []
        if decision.blank == expected_blank and actual_ranking == expected_ranking:
            correct += 1
    return {
        "chunk_size": chunk_size,
        "elapsed": elapsed,
        "ok": True,
        "detail": f"{correct}/{len(decisions)} correct vs ground truth",
    }


def _measure_chamber(client: VllmJsonClient, config: PolityConfig, chunk_size: int, rep: int) -> dict:
    members = [_chamber_member(900 + rep * 10 + i, rep) for i in range(chunk_size)]
    contexts = {m.citizen_id: ChamberContext(cid=m.citizen_id, ticks_left=12) for m in members}
    system_prompt = build_chamber_system_prompt(members, config)
    user_prompt = build_chamber_user_prompt(members, contexts)
    prompt_tokens = _probe_prompt_tokens(config.llm.base_url, config.llm.model, system_prompt, user_prompt)
    max_tokens = _max_safe_tokens(prompt_tokens, floor=compute_max_tokens(chunk_size))
    start = time.perf_counter()
    try:
        raw = client.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=CHAMBER_JSON_SCHEMA,
            max_tokens=max_tokens,
            think=True,
        )
    except LlmError as exc:
        return {"chunk_size": chunk_size, "elapsed": time.perf_counter() - start, "ok": False, "detail": str(exc)[:200]}
    elapsed = time.perf_counter() - start
    try:
        decisions = decode_chamber_batch(raw, [m.citizen_id for m in members])
        for decision in decisions:
            validate_chamber_decision(decision, config)
        motifs = [decision.motif for decision in decisions]
    except LlmError as exc:
        return {"chunk_size": chunk_size, "elapsed": elapsed, "ok": False, "detail": str(exc).splitlines()[0][:200]}
    sincere = sum(1 for m in motifs if m == int(ChamberMotif.SINCERE_POSITION))
    return {"chunk_size": chunk_size, "elapsed": elapsed, "ok": True, "detail": f"{len(decisions)} decoded, {sincere} sincere"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reps", type=int, default=2, help="repetitions per chunk size, per decision type")
    parser.add_argument("--chunk-sizes", type=int, nargs="+", default=list(_CHUNK_SIZES))
    parser.add_argument("--results", type=Path, default=None)
    args = parser.parse_args(argv)

    config = _vllm_config()
    lines: list[str] = []

    def log(line: str = "") -> None:
        print(line, flush=True)
        lines.append(line)

    log("# vLLM chunk-size throughput -- vote_cast and chamber_deliberation, scaled budgets\n")
    log(f"provider=vllm model={config.llm.model} reps={args.reps}\n")

    with VllmJsonClient.from_config(config.llm, seed=config.run.seed) as client:
        log("## vote_cast\n")
        log("| chunk_size | rep | elapsed(s) | s/citizen | ok | detail |")
        log("|---|---|---|---|---|---|")
        voters, nominees = _vote_world(config, n_voters=sum(c * args.reps for c in args.chunk_sizes) + 5, n_candidates=5)
        offset = 0
        for chunk_size in args.chunk_sizes:
            for rep in range(args.reps):
                chunk_voters = voters[offset:offset + chunk_size]
                offset += chunk_size
                result = _measure_vote_cast(client, config, chunk_voters, nominees, chunk_size)
                per_citizen = result["elapsed"] / chunk_size
                log(f"| {chunk_size} | {rep} | {result['elapsed']:.1f} | {per_citizen:.1f} | "
                    f"{'yes' if result['ok'] else '**NO**'} | {result['detail']} |")

        log("\n## chamber_deliberation\n")
        log("| chunk_size | rep | elapsed(s) | s/member | ok | detail |")
        log("|---|---|---|---|---|---|")
        for chunk_size in args.chunk_sizes:
            for rep in range(args.reps):
                result = _measure_chamber(client, config, chunk_size, rep)
                per_member = result["elapsed"] / chunk_size
                log(f"| {chunk_size} | {rep} | {result['elapsed']:.1f} | {per_member:.1f} | "
                    f"{'yes' if result['ok'] else '**NO**'} | {result['detail']} |")

    if args.results is not None:
        args.results.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nwrote {args.results}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
