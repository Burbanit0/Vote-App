"""Live smoke test against a real local vLLM instance — v4 vLLM switch
(§15bis.6).

Opt-in only, never runs in CI. Written when no GPU/vLLM server had ever been
available in this project's environment; a GPU host with `vllm-polity`
(docker-compose.llm.yml) running qwen3:8b has existed since, and every claim
below has since been exercised live against it (see e.g.
check_pressure_shipped_wiring_results.md and the other scripts/check_*.py
files this session used the same way) -- set POLITY_VLLM_LIVE=1 to run this
file itself against it. Everything else about VllmJsonClient (request/
response shape via httpx.MockTransport) is unit-tested offline in
test_polity_llm_client.py -- this file is what actually confirms or refutes
the claims in VllmJsonClient's own docstring end to end, through pytest
rather than a one-off script.

Kept as its own file rather than a parametrization of test_polity_llm_live.py
(the Ollama live suite): that file's module-scoped fixture, its 49-line
historical wall-clock docstring, and its per-decision-type sweep are all
Ollama-specific, and parametrizing it across two providers would double an
already multi-hour CPU suite for the provider people actually have today.

Setup (once a GPU host exists):
    docker compose -f docker-compose.llm.yml up -d
    POLITY_VLLM_LIVE=1 POLITY_VLLM_URL=http://localhost:8000/v1 \\
        python -m pytest api/tests/test_polity_vllm_live.py -o addopts="" -v

Tests are ordered so the cheapest disproof runs first: does the server even
answer as the configured model, before spending minutes on a full batch.

test_think_true_actually_produces_reasoning is the single most important
test in this file (see VllmJsonClient's docstring, "R1"): if
--reasoning-parser qwen3 is missing from the server's launch flags, vLLM's
structured-output grammar can silently make `enable_thinking: true` a
no-op, which is exactly the failure mode decide_campaign_positioning's own
docstring already recorded once under a different name (think=False's
100%-reproducible degenerate batch on real production data).
"""
import dataclasses
import json
import os

import httpx
import pytest

from api.domain.polity.citizen import Citizen, Office, Role
from api.domain.polity.codebook import PressureMotif
from api.domain.polity.config import load_config
from api.domain.polity.journal import Journal
from api.domain.polity.llm_behavior_engine import (
    _VOTE_THINK_TOKEN_ALLOWANCE,
    PressureContext,
    _dynamic_max_tokens,
    _vote_cast_chunk_size,
    build_system_prompt,
    build_user_prompt,
    compute_max_tokens,
    decide_pressure_actions,
    menu_acts,
)
from api.domain.polity.llm_client import VllmJsonClient, _inline_refs, decode_vote_batch
from api.domain.polity.llm_schemas import VOTE_CAST_JSON_SCHEMA, VoteCastBatch
from api.domain.polity.run_polity_simulation import _run_accountability_phase, run_simulation
from api.domain.polity.simple_rules import declare_candidacy

pytestmark = pytest.mark.skipif(
    os.getenv("POLITY_VLLM_LIVE") != "1",
    reason="requires a live vLLM instance serving qwen3:8b; set POLITY_VLLM_LIVE=1",
)

_VLLM_URL = os.getenv("POLITY_VLLM_URL", "http://localhost:8000/v1")


def _citizen(cid, dims):
    positions = tuple((cid * 0.037 + i * 0.017) % 1.0 for i in range(dims))
    priorities = tuple(1.0 / dims for _ in range(dims))
    return Citizen(citizen_id=cid, issue_positions=positions, issue_priorities=priorities, blank_threshold=0.5,
                   ambition_score=0.5)


def _candidate(cid, dims):
    c = _citizen(1000 + cid, dims)
    declare_candidacy(c)
    return c


def _vllm_config():
    config = load_config()
    return dataclasses.replace(config, llm=dataclasses.replace(config.llm, provider="vllm", base_url=_VLLM_URL))


@pytest.fixture(scope="module")
def client():
    with VllmJsonClient.from_config(_vllm_config().llm, seed=42) as client:
        yield client


def test_vllm_serves_the_configured_model_id():
    """Proves --served-model-name qwen3:8b was actually used at launch --
    the vLLM deployment plan's D-4 (see docker-compose.llm.yml) requires
    it, since llm.model's pinning rule rejects a bare HF repo id."""
    response = httpx.get(f"{_VLLM_URL}/models", timeout=10.0)
    response.raise_for_status()
    ids = {m["id"] for m in response.json()["data"]}
    assert "qwen3:8b" in ids


def test_structured_output_is_honored_on_a_full_size_vote_batch(client):
    """Mirrors test_polity_llm_live.py's Ollama equivalent -- the first
    question is simply whether vLLM's response_format/json_schema honors
    this project's real, $ref-bearing schema at all.

    Correction, 2026-09-10, in two steps -- both confirmed live, not
    assumed. Step 1: the original call sized max_tokens via plain
    compute_max_tokens(chunk_size), with no reasoning allowance --
    think=True defaults on, and cast_votes (the real production call
    site) NEVER sizes a think=True call that way, always adding
    _dynamic_max_tokens's own probe-and-maximize budget. Fixed that, and
    it STILL failed identically (finish_reason='length'), with real
    prompt_tokens=8830 and a maximized budget of 7254 -- ample room, not
    a sizing problem. Step 2, the actual root cause: `config.llm.
    max_batch_size` (25) citizens in ONE unchunked call is a shape
    cast_votes NEVER sends -- production always chunks at
    _vote_cast_chunk_size(config) (3 on vLLM), specifically because an
    oversized batch is documented elsewhere in this module (build_
    system_prompt's own docstring) to trigger a real, non-convergent
    "Mode A" reasoning loop that burns the entire budget re-quoting the
    prompt's own ranking rule without ever emitting JSON. This test's own
    10 candidates (crossing the >6 truncation threshold, §3.6.1) at 25
    unchunked citizens was exactly that trigger -- a test-harness shape
    mismatch, not a real vLLM or cast_votes issue (cast_votes was never
    at risk; it never sends this shape). Fixed by testing at cast_votes's
    own real chunk size instead, which still exercises the same $ref
    schema and the same >6-candidate truncation path the 2026-09-10
    truncation-limit fix (246da0b) specifically targets -- just at the
    batch size that actually ships."""
    config = load_config()
    dims = config.citizens.issue_count
    citizens = [_citizen(i, dims) for i in range(_vote_cast_chunk_size(config))]
    candidates = [_candidate(i, dims) for i in range(10)]
    system_prompt = build_system_prompt(citizens, candidates)
    user_prompt = build_user_prompt(citizens, candidates)

    raw = client.complete_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        json_schema=VOTE_CAST_JSON_SCHEMA,
        max_tokens=_dynamic_max_tokens(
            client, config, system_prompt=system_prompt, user_prompt=user_prompt,
            chunk_size=len(citizens), flat_allowance=_VOTE_THINK_TOKEN_ALLOWANCE,
        ),
        think=True,
    )
    decisions = decode_vote_batch(raw, expected_cids=[c.citizen_id for c in citizens])
    assert len(decisions) == len(citizens)


def test_raw_ref_schema_is_accepted_without_inlining():
    """Answers VllmJsonClient's own open question (D-3): does vLLM's
    guided-decoding backend resolve nested $defs/$ref itself, unlike
    Ollama (ollama_structured_output_results.md, Finding A)? Sends the
    schema WITHOUT _inline_refs, via raw httpx rather than the client --
    if this passes, _inline_refs's call site in VllmJsonClient could later
    be dropped; this test does not do that on its own."""
    assert "$defs" in VOTE_CAST_JSON_SCHEMA  # sanity: this schema actually has nested refs
    body = {
        "model": "qwen3:8b",
        "messages": [
            {"role": "system", "content": "Return decisions=[] only."},
            {"role": "user", "content": "{}"},
        ],
        "temperature": 0.0,
        "seed": 42,
        "max_tokens": 64,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "polity_decision_batch", "strict": True, "schema": VOTE_CAST_JSON_SCHEMA},
        },
    }
    response = httpx.post(f"{_VLLM_URL}/chat/completions", json=body, timeout=60.0)
    response.raise_for_status()


def test_think_false_returns_clean_json_without_reasoning(client):
    config = load_config()
    dims = config.citizens.issue_count
    citizens = [_citizen(i, dims) for i in range(20)]
    candidates = [_candidate(i, dims) for i in range(5)]

    raw = client.complete_json(
        system_prompt=build_system_prompt(citizens, candidates),
        user_prompt=build_user_prompt(citizens, candidates),
        json_schema=VOTE_CAST_JSON_SCHEMA,
        max_tokens=compute_max_tokens(20),
        think=False,
    )
    batch = VoteCastBatch.model_validate_json(raw)
    assert [d.cid for d in batch.decisions] == [c.citizen_id for c in citizens]


def test_think_true_actually_produces_reasoning():
    """The R1 detector -- see this file's module docstring and
    VllmJsonClient's own docstring. Goes through raw httpx rather than the
    client: surfacing `reasoning_content` through LlmClientProtocol would
    be production surface added purely for this one test. Asserts
    reasoning is present via EITHER the --reasoning-parser shape
    (message.reasoning_content, non-empty) OR an inline <think> block in
    message.content -- whichever the server's actual launch flags produce
    -- so this test only passes if reasoning genuinely happened somewhere
    in the response, not merely that the request didn't error."""
    body = {
        "model": "qwen3:8b",
        "messages": [
            {"role": "system", "content": "Think step by step before answering. Return decisions=[] only."},
            {"role": "user", "content": "{}"},
        ],
        "temperature": 0.0,
        "seed": 42,
        "max_tokens": 512,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": True},
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "polity_decision_batch", "strict": True, "schema": _inline_refs(VOTE_CAST_JSON_SCHEMA),
            },
        },
    }
    response = httpx.post(f"{_VLLM_URL}/chat/completions", json=body, timeout=60.0)
    response.raise_for_status()
    message = response.json()["choices"][0]["message"]
    # vLLM v0.28.0's --reasoning-parser qwen3 names this field `reasoning`, not the
    # `reasoning_content` this test originally checked (a name from the v4 switch's
    # written-but-unverified docs, pre-dating any live vLLM response) -- confirmed
    # live 2026-09-05 via a raw probe against this exact server.
    reasoning_content = message.get("reasoning") or ""
    has_inline_think_block = "<think>" in (message.get("content") or "")
    assert reasoning_content.strip() or has_inline_think_block, (
        "enable_thinking=True produced no visible reasoning anywhere in the response -- "
        "the server is likely missing --reasoning-parser qwen3 (see docker-compose.llm.yml); "
        "think=True is a silent no-op under this configuration (VllmJsonClient docstring, R1)"
    )


def test_ten_identical_sequential_requests_are_byte_identical(client):
    """§15bis.5 point 2, against a live vLLM server, sequential (not
    concurrent) calls -- the cheap half of the determinism protocol that
    doesn't need check_vllm_batching_determinism.py's deliberate
    concurrency. Ollama already failed this exact test
    (ollama_structured_output_results.md, Finding D); whether vLLM does
    too is unmeasured."""
    config = load_config()
    dims = config.citizens.issue_count
    citizens = [_citizen(i, dims) for i in range(20)]
    candidates = [_candidate(i, dims) for i in range(5)]
    kwargs = dict(
        system_prompt=build_system_prompt(citizens, candidates),
        user_prompt=build_user_prompt(citizens, candidates),
        json_schema=VOTE_CAST_JSON_SCHEMA,
        max_tokens=compute_max_tokens(20),
        think=False,
    )
    responses = [client.complete_json(**kwargs) for _ in range(10)]
    assert len(set(responses)) == 1, "sequential identical requests diverged -- see llm_client.py's module docstring"


def test_a_short_live_run_produces_a_valid_journal(tmp_path):
    config = _vllm_config()
    config = dataclasses.replace(config, journal=dataclasses.replace(config.journal, output_dir=str(tmp_path)))
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))
    config = dataclasses.replace(config, candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.1))
    config = dataclasses.replace(config, run=dataclasses.replace(config.run, duration_years=4))

    journal_path = run_simulation(config, run_id="vllm-live-smoke")

    lines = journal_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) > 0
    for line in lines:
        json.loads(line)  # every line is valid, complete JSON


def test_two_short_live_runs_with_the_same_seed_are_byte_identical(tmp_path):
    """The actual §15bis.4c question, end to end: does a real production
    run reproduce under vLLM the way it does under Ollama's FakeLlmClient
    tests? Expected to be the first test in this file to fail if vLLM's
    continuous-batching scheduler causes kernel-reduction-order
    nondeterminism across runs (the design doc's own threat model,
    §15bis.4c) -- see check_vllm_batching_determinism.py for the isolated
    version of this question."""
    config = _vllm_config()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))
    config = dataclasses.replace(config, candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.1))
    config = dataclasses.replace(config, run=dataclasses.replace(config.run, duration_years=4))

    config_a = dataclasses.replace(config, journal=dataclasses.replace(config.journal, output_dir=str(tmp_path / "a")))
    config_b = dataclasses.replace(config, journal=dataclasses.replace(config.journal, output_dir=str(tmp_path / "b")))
    path_a = run_simulation(config_a, run_id="same-run-id")
    path_b = run_simulation(config_b, run_id="same-run-id")

    assert path_a.read_bytes() == path_b.read_bytes()


# ── pressure_action (v4 Lot 7, calibrated + shipped Phase E 2026-09-10) ──────
#
# NOT a copy-paste of test_polity_llm_live.py's own pressure_action tests --
# think=False decisions route through OllamaJsonClient's Ollama-only native
# /api/chat endpoint there, which vLLM does not serve (confirmed live,
# 2026-09-10: running that file's pressure_action tests against the shipped
# vllm-polity server 404s at exactly that call, unrelated to anything in this
# session's own change -- a pre-existing gap between that file's Ollama-only
# fixture and the provider this project has shipped since §15bis.6). This
# file's own `client` fixture already uses VllmJsonClient, so these are new
# tests, not a parametrization.

def _pressure_context(cid, target, legal):
    # Same alternating-availability shape as test_polity_llm_live.py's own
    # helper of the same name -- kept structurally identical since it isn't
    # provider-specific, only self_gap/blank_threshold (below) differ.
    if cid % 2 == 0:
        available = legal
        petition_open = True
        expires_at = 14
    else:
        available = tuple(a for a in legal if a not in (1, 2))
        petition_open = False
        expires_at = None
    return PressureContext(
        cid=cid, target=target, self_gap=0.6, mandate_dev=0.3, ticks_to_election=9,
        available=available, petition_open=petition_open, petition_expires_at_tick=expires_at,
        already_signed=False,
    )


def test_decide_pressure_actions_against_the_real_client(client):
    """decide_pressure_actions now ships calibrated (PRESSURE_THRESHOLD_SIGNAL,
    polity-decision-contracts.md Phase E), chunked one citizen per call
    regardless of config.llm.max_batch_size -- so 10 consulted citizens means
    10 real HTTP calls here, not one or two chunked ones."""
    config = _vllm_config()
    config = dataclasses.replace(
        config,
        llm=dataclasses.replace(config.llm, enabled=True),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True),
    )
    target = 9200
    consulted = [_citizen(3200 + i, 1) for i in range(10)]
    legal = menu_acts(config.pressure_menu)
    contexts = {c.citizen_id: _pressure_context(c.citizen_id, target, legal) for c in consulted}

    outcome = decide_pressure_actions(consulted, contexts, config, client)

    assert [d.cid for d in outcome.decisions] == [c.citizen_id for c in consulted]
    assert all(d.act in legal for d in outcome.decisions)


def test_pressure_action_wiring_against_the_real_client_in_a_live_tick(client, tmp_path):
    """The vLLM twin of test_polity_llm_live.py's own dt=10 wiring test:
    proves run_polity_simulation.py's OWN wiring (the gate, the frozen
    PressureContext, applicable_pressure_act, the journal write) against a
    real client and a real tick -- not decide_pressure_actions in isolation.
    Same hand-built holder/population shape as that file's own version
    (base_threshold=0.0 guarantees consultation)."""
    config = _vllm_config()
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))
    config = dataclasses.replace(config, legitimacy=dataclasses.replace(config.legitimacy, enabled=True))
    config = dataclasses.replace(
        config,
        awakening=dataclasses.replace(config.awakening, enabled=True, modulation_amplitude=0.0),
        pressure_menu=dataclasses.replace(
            config.pressure_menu, electoral_only=False, petition_enabled=True, mobilization_enabled=True
        ),
        petition=dataclasses.replace(config.petition, enabled=True),
    )
    dims = config.citizens.issue_count
    holder = Citizen(
        citizen_id=1,
        issue_positions=tuple(0.5 for _ in range(dims)),
        issue_priorities=tuple(1.0 / dims for _ in range(dims)),
        blank_threshold=0.5,
        ambition_score=0.5,
        role=Role.ELECTED,
        office=Office.PRESIDENT,
        term_end_tick=16,
        mandates_served=1,
        legitimacy_capital=0.5,
        mandate_strength=0.5,
    )
    holder.pledged_platform = holder.issue_positions
    holder.revealed_position = holder.issue_positions
    consulted = [
        Citizen(
            citizen_id=100 + i,
            issue_positions=tuple(0.0 for _ in range(dims)),
            issue_priorities=tuple(1.0 / dims for _ in range(dims)),
            blank_threshold=0.0,
            ambition_score=0.5,
            base_threshold=0.0,
        )
        for i in range(3)
    ]

    journal_path = tmp_path / "dt10-vllm-live.jsonl"
    with Journal(journal_path, run_id="dt10-vllm-live") as journal:
        _run_accountability_phase([holder] + consulted, config, journal, tick=0, llm_client=client)

    events = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    pressure_events = [e for e in events if e["event_type"] == "pressure_action"]
    assert len(pressure_events) == len(consulted)
    legal = menu_acts(config.pressure_menu)
    for e in pressure_events:
        assert e["payload"]["target"] == holder.citizen_id
        assert e["payload"]["act"] in legal
        assert e["motif"] in {str(m.value) for m in PressureMotif}
        assert e["codebook_version"] == config.llm.codebook_version
