"""
api.domain.polity.llm_client — sync HTTP transport to a local Ollama or
vLLM instance, v2 increment 1 (Ollama); v4 vLLM switch (§15bis.6) adds
VllmJsonClient.

vLLM status: VllmJsonClient below is implemented against vLLM's documented
OpenAI-compatible surface and Qwen3's documented `enable_thinking` chat-
template flag -- it has never been executed against a live vLLM server. A
GPU (RTX 5070 Ti) became available in this project's environment on
2026-08-17 and has since been used to validate OllamaJsonClient on real
GPU inference (llm_batching_determinism_results_gpu.md) -- but no vLLM
server has ever been stood up on it, so every claim in VllmJsonClient's
docstring remains unverified for that reason specifically, not for lack
of a GPU. Every claim in OllamaJsonClient's own docstring is backed by a
committed live results doc; no claim in VllmJsonClient's docstring is.
§15bis.5's determinism-under-batching protocol has been run against
Ollama on both CPU (llm_batching_determinism_results.md, 2026-07-31) and
GPU (llm_batching_determinism_results_gpu.md, 2026-08-17) -- both FAIL the
same way (batched calls diverge, sequential calls don't) on either
backend. It has never been run against vLLM. `polity_config.yaml` ships
`provider: ollama` as the default for exactly this reason -- see that
file's own comment block for the switch procedure and its caveats.

Sync httpx.Client only, never async. A batch call is a single request/
response; there is no intra-batch concurrency to justify async, and the
existing scripts/check_llm_batching_determinism.py is async specifically
to fire deliberately-concurrent requests and prove they diverge (§15bis.5)
-- that pattern must not leak into production code, which must keep
exactly one request in flight at a time: concurrent batching provably
breaks reproducibility outright (llm_batching_determinism_results.md),
serialized calls just avoid making a bad problem worse.

Serialized calls at temperature=0 with a pinned model are NOT a
reproducibility guarantee on their own, despite this project's earlier
assumption: ollama_structured_output_results.md's live consolidation pass
found two textually identical requests (same prompts, same seed) produce
different decisions on a real run. Most likely cause is non-deterministic
floating-point reduction order in multi-threaded CPU inference (llama.cpp,
which Ollama runs on) -- a known limitation of such backends, not
something fixable at this layer. True cross-run reproducibility, if a
future increment needs it for a controlled comparison, is the response
cache's job (§4.2, deferred): replay a pinned response, don't expect the
live model to regenerate it.

Ollama's OpenAI-compatible endpoint cannot handle Pydantic's nested
$defs/$ref schemas -- confirmed in ollama_structured_output_results.md
(Finding A): sent as-is, every request silently consumed the whole token
budget with zero visible content. This module dereferences (inlines) any
schema before sending it, so every caller is protected automatically
rather than having to remember to do it themselves.

No caching here (§4.2 deferred to a later increment, per the approved
plan). The request body is still built as canonical (sort_keys, compact
separators) bytes so a cache key can be added later without touching
prompt construction.
"""
from __future__ import annotations

import copy
import json
import logging
import re
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Callable, Protocol, Sequence, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from api.domain.polity.config import LlmConfig
from api.domain.polity.llm_call_log import record_http_response
from api.domain.polity.model_profiles import QWEN3_THINKING, ThinkingControl, model_profile
from api.domain.polity.llm_schemas import (
    CandidacyBatch,
    CandidacyDecision,
    ChamberBatch,
    ChamberDecision,
    CoalitionBatch,
    CoalitionDecision,
    PartyNominationBatch,
    PartyNominationDecision,
    PositioningBatch,
    PositioningDecision,
    PressureBatch,
    PressureDecision,
    ReactionBatch,
    ReactionDecision,
    ResponseBatch,
    ResponseDecision,
    VoteCastBatch,
    VoteCastDecision,
)

_logger = logging.getLogger(__name__)

_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_TRANSPORT_RETRY_ATTEMPTS = 3  # 1 initial + 2 retries -- see module docstring on why

_RECYCLE_WARM_UP_SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}
"""Deliberately a near-duplicate of run_polity_simulation._WARM_UP_SCHEMA,
not an import of it -- llm_client.py has no dependency on
run_polity_simulation.py, and this trivial throwaway shape is not worth
introducing one for. Used only by OllamaJsonClient._recycle's own re-warm
calls, never to decode a real decision. The OUTPUT stays trivial on
purpose -- see _RECYCLE_WARM_UP_USER_PROMPT for why the INPUT does not."""

_RECYCLE_WARM_UP_USER_PROMPT = json.dumps(
    {"padding": [round(i * 0.0001, 4) for i in range(1400)]}, separators=(",", ":")
)
"""Inert filler, sized to approximate a real production prompt's rough
character count (~6000, measured against a real campaign_positioning
user_prompt) -- NOT a semantically real prompt, just large. Verified live
(bug 4 investigation, 2026-08-20) that this specific size/shape avoids the
failure _RECYCLE_WARM_UP_SCHEMA's own docstring describes; a first
implementation used a tiny `"{}"` stub here and made a live 5-call
sequence WORSE (2/5 vs the normal baseline), not better."""

_RECYCLE_WARM_UP_MAX_TOKENS = 1500
"""Generous relative to the trivial `{"ok": bool}` output this schema
asks for -- large budget alone was already tested and found insufficient
on its own (a warm-up that finishes cleanly at this same budget still
broke the next call, when its prompt was still the tiny stub); kept
generous here anyway so a real `<think>` pass over the padding above
never gets starved for an unrelated reason."""


class LlmError(RuntimeError):
    """Base for every error this module raises."""


class LlmTransportError(LlmError):
    """Network/HTTP failure -- genuinely transient, safe to retry the
    byte-identical request (temperature=0 + pinned seed means the retry
    reproduces the same request, not a different attempt)."""


class LlmResponseError(LlmError):
    """The response is malformed, schema-invalid, or violates §3.6.0's
    batch-alignment rule (wrong count or cid order). NOT retried: this
    project previously assumed a retry here was a "guaranteed no-op" at
    temperature=0 with a pinned seed -- ollama_structured_output_results.md's
    determinism finding shows that's not actually true, a retry could
    occasionally "succeed" by luck. It stays unretried anyway: a malformed
    or misaligned response is a real problem to investigate, and silently
    laundering it through a lucky retry would hide that instead of
    surfacing it."""


class LlmClientProtocol(Protocol):
    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        max_tokens: int,
        think: bool = True,
        temperature: float | None = None,
        seed: int | None = None,
    ) -> str: ...

    # Prefill-only probe (`max_tokens=1`) returning the real token count of
    # (system_prompt, user_prompt) as the backend's own chat template
    # tokenizes it -- added for llm_behavior_engine._dynamic_max_tokens
    # (2026-09-08, check_vllm_chunk_size_throughput_results.md). See each
    # implementation's own docstring below for the verified-vs-unverified
    # split (VllmJsonClient.count_prompt_tokens / OllamaJsonClient.count_
    # prompt_tokens) -- this stub carries no doc of its own, matching
    # complete_json's own convention on this Protocol.
    def count_prompt_tokens(self, *, system_prompt: str, user_prompt: str, think: bool = True) -> int: ...


SUPPORTED_PROVIDERS = frozenset({"ollama", "vllm"})
"""Providers with an actual client in this module. config._LLM_PROVIDERS is
deliberately wider ({"ollama", "vllm", "api"}): that set says which values
are spellable in llm.provider, this one says which are implemented. "api"
(hosted inference) is out of scope by decision (§12: local self-hosting),
not merely unbuilt yet."""


def unsupported_provider_error(provider: str) -> NotImplementedError:
    """Single message, two raise sites (llm_behavior_engine._check_supported
    at first-decision time, build_json_client at run start) -- keeping the
    text in one place means the two can't drift apart. Must keep the
    substring "provider": every _check_supported test asserts
    pytest.raises(NotImplementedError, match="provider")."""
    return NotImplementedError(
        f"llm.provider {provider!r} has no client in this codebase -- implemented: "
        f"{', '.join(sorted(SUPPORTED_PROVIDERS))} ('vllm' added in v4, §15bis.6). "
        "'api' is out of scope by design (§12), not merely unbuilt."
    )


def _inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """See module docstring / ollama_structured_output_results.md Finding A.
    One-level-deep $ref substitution -- adequate for this project's
    decision schemas, not a general-purpose JSON Schema resolver."""
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


def _post_with_transport_retry(client: httpx.Client, url: str, payload: str) -> httpx.Response:
    """Shared by every complete_json path (Ollama's two, vLLM's one):
    retries only a transport failure (network error / non-200), up to
    _TRANSPORT_RETRY_ATTEMPTS total attempts, no backoff -- see the module
    docstring on why there's no concurrency to jitter against. A
    response-level failure (bad schema, truncated generation) is the
    caller's problem via the returned Response; this function never raises
    LlmResponseError."""
    last_transport_error: LlmTransportError | None = None
    for _ in range(_TRANSPORT_RETRY_ATTEMPTS):
        try:
            response = client.post(url, content=payload, headers={"Content-Type": "application/json"})
        except httpx.HTTPError as exc:
            last_transport_error = LlmTransportError(f"request to {url} failed: {exc}")
            continue
        if response.status_code != 200:
            last_transport_error = LlmTransportError(f"HTTP {response.status_code} from {url}: {response.text[:500]}")
            continue
        # Every path that receives a model response passes here, so this one line
        # gives the per-call log (llm_call_log.py) tokens, finish reason and reasoning
        # for all of them, including responses the caller then rejects.
        record_http_response(response)
        return response

    assert last_transport_error is not None  # loop runs at least once
    raise last_transport_error


class OllamaJsonClient:
    """Ollama's OpenAI-compatible endpoint (`llm.base_url`, already ending
    in `/v1`). One instance per run, reused across every batch call.

    `think=False` (v2 increment 2) switches to Ollama's *native* `/api/chat`
    endpoint entirely, not just a body flag on the OpenAI-compat one --
    empirically required. A live investigation (increment 2's candidacy
    task) found that `think: false` on `/v1/chat/completions` combined with
    `response_format` (structured/strict JSON) is silently ignored: the
    model still burns the *entire* token budget on invisible `<think>`
    reasoning, `finish_reason='length'`, zero visible content, regardless of
    budget size (confirmed up to 6144 tokens). The native endpoint's own
    `think`+`format` combination has no such bug and is dramatically faster
    (~35s vs 4+ min for a 20-citizen batch) since no reasoning tokens are
    spent at all. `think=True` (vote_cast, unchanged since increment 1)
    keeps using the OpenAI-compat path exactly as shipped -- this is a
    per-call transport choice, not a behavior change to the vote path.

    v2 increment 3 (party_nomination_choice) initially tried think=True on
    the theory that its small batches (a handful of contested parties, not
    tens of citizens) would sidestep candidacy's bug. A live run disproved
    that: think=True hit the identical finish_reason='length' failure
    regardless of batch size (ollama_structured_output_results.md Finding
    E). The bug tracks the *prompt's* subjective/comparative framing, not
    batch size -- party_nomination_choice now also uses think=False.

    `recycle_after_n_calls` (bug 4 investigation, 2026-08-19/20): llama.cpp's
    own prompt-cache pool has a measured, finite capacity on this project's
    container (~8 prompts under a large think=True budget, bounded by the
    server's own 8192 MiB cache memory limit). A batched harness experiment
    (4 independent cold-restart sessions, identical content/order each time)
    found the SAME rank-by-rank failure pattern reproduced exactly across
    all 4 -- deterministic, not stochastic -- and a direct correlation
    between the cache's own reported occupancy and finish_reason='length'
    truncation: 0 failures across 24 calls at cache<7, versus a 40-50%
    failure rate once the pool is at or near its observed capacity (ratio
    >=2x, the pre-registered decision criterion). A separate, complementary
    finding narrows the likely mechanism: the specific PROMPT immediately
    preceding a call matters, not just how many prior calls happened -- a
    tiny, structurally dissimilar prompt (this project's own warm-up
    stub) reliably breaks the very next real call (12/12 across two
    independent tests, one with a generously-budgeted, cleanly-finishing
    warm-up), while a realistically-sized prior prompt does not (6/6
    clean). Both readings point the same way: a poor-quality partial
    match against a dissimilar cache entry is the likely proximate cause,
    and a bigger/more-crowded pool raises the odds of hitting one.

    This field forces a Ollama model unload+reload -- via `keep_alive: 0`
    on the native endpoint, confirmed directly to reset "cache state" to 0
    prompts exactly like a full container restart, without the container-
    restart's own cost (no lost TCP connection, no container process
    respawn) -- every `recycle_after_n_calls` complete_json calls,
    preemptively (before the call that would push the pool near its
    observed risk zone, not after). Shipped null (disabled): the measured
    capacity/threshold above is calibrated for ONE prompt shape
    (campaign_positioning, think=True, large token budget) against ONE
    container's own memory configuration -- not proven to generalize to
    every decision type's own prompt size, so this stays an opt-in,
    explicitly-enabled mitigation, not a new default. See
    llm_batching_determinism_results_gpu.md for the full investigation."""

    def __init__(
        self,
        base_url: str,
        model: str,
        temperature: float,
        seed: int,
        timeout: float,
        transport: httpx.BaseTransport | None = None,
        recycle_after_n_calls: int | None = None,
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._temperature = temperature
        self._seed = seed
        self._client = httpx.Client(timeout=timeout, transport=transport)
        self._recycle_after_n_calls = recycle_after_n_calls
        self._calls_since_recycle = 0

    @classmethod
    def from_config(cls, llm: LlmConfig, *, seed: int, timeout: float = 600.0) -> OllamaJsonClient:
        """600s default: a live consolidation run measured a real full-size
        (25-citizen) batch completing at 294.64s -- already within seconds
        of the previous 300s default, with no margin for Qwen3's variable
        <think> reasoning length. 600s gives real headroom without masking
        a genuinely hung request."""
        return cls(
            llm.base_url, llm.model, llm.temperature, seed, timeout,
            recycle_after_n_calls=llm.recycle_after_n_calls,
        )

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        max_tokens: int,
        think: bool = True,
        temperature: float | None = None,
        seed: int | None = None,
    ) -> str:
        """Retries only a transport failure, up to _TRANSPORT_RETRY_ATTEMPTS
        total attempts, no backoff (no concurrency to jitter against -- see
        module docstring). A response-level failure (bad schema, truncated
        generation) propagates immediately, unretried -- see LlmResponseError.

        `think` defaults to True (vote_cast's existing, unchanged behavior)
        -- see the class docstring for why `think=False` needs an entirely
        different endpoint/request shape, not just one extra body field.

        `temperature`/`seed`, when given, override `self._temperature`/
        `self._seed` (the client's own, config-derived values) for THIS call
        only -- every other call on this same client instance is unaffected.
        `None` (the default, and every call site's own default) preserves
        this client's configured values exactly, unchanged behavior. This
        exists for exactly one, deliberate, documented exception to the
        project's own determinism requirement (config._parse_llm's
        "temperature=0 is a hard determinism requirement" rule, which
        governs the CONFIGURED value only, not a per-call override this
        narrow) -- see llm_behavior_engine._complete_and_decode_with_replay's
        own `retry_temperature`/`retry_seed_base` parameters and
        cache_recycle_chunk_size_tension_findings.md /
        check_vllm_vote_cast_retry_is_inert_results.md for the one call site
        that uses them. `seed` joined `temperature` here for a reason
        `temperature` alone doesn't cover on Ollama either: this module's own
        docstring already records that temperature=0 + a pinned seed is not
        a reproducibility guarantee on this backend, so the ORIGINAL seed was
        never a strong lock to begin with -- overriding it on retry is a
        smaller step here than it is for VllmJsonClient, where the pinned
        seed is normally binding (see that class's own finding). This
        mechanism itself is general (any caller could pass either override);
        the fact that only one call site does is a policy choice made at
        that call site, not something enforced here.

        Recycles BEFORE this call, not after, when `recycle_after_n_calls`
        is set and the counter has reached it -- preemptive, so the cache
        pool never actually enters the observed risk zone (see class
        docstring); a reactive recycle-after would let exactly the call
        this mitigation exists to protect run against an already-crowded
        pool. The counter resets on recycle and is never incremented by
        the recycle's own internal calls (see _recycle)."""
        effective_temperature = temperature if temperature is not None else self._temperature
        effective_seed = seed if seed is not None else self._seed
        if self._recycle_after_n_calls is not None and self._calls_since_recycle >= self._recycle_after_n_calls:
            self._recycle()
        try:
            if think:
                return self._complete_json_openai_compat(
                    system_prompt, user_prompt, json_schema, max_tokens, effective_temperature, effective_seed
                )
            return self._complete_json_native_no_think(
                system_prompt, user_prompt, json_schema, max_tokens, effective_temperature, effective_seed
            )
        finally:
            self._calls_since_recycle += 1

    def _complete_json_openai_compat(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        max_tokens: int,
        temperature: float,
        seed: int,
    ) -> str:
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "seed": seed,
            "max_tokens": max_tokens,
            "stream": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "polity_decision_batch", "strict": True, "schema": _inline_refs(json_schema)},
            },
        }
        payload = json.dumps(body, sort_keys=True, separators=(",", ":"))
        response = _post_with_transport_retry(self._client, f"{self._base_url}/chat/completions", payload)
        return _extract_content(response)

    def _complete_json_native_no_think(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        max_tokens: int,
        temperature: float,
        seed: int,
    ) -> str:
        # `self._base_url` is documented as ending in `/v1` (the
        # OpenAI-compat convention) -- the native endpoint lives one level
        # up, at plain `/api/chat`, not `/v1/api/chat`.
        native_base = self._base_url.removesuffix("/v1")
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "think": False,
            "format": _inline_refs(json_schema),
            "options": {"temperature": temperature, "seed": seed, "num_predict": max_tokens},
        }
        payload = json.dumps(body, sort_keys=True, separators=(",", ":"))
        response = _post_with_transport_retry(self._client, f"{native_base}/api/chat", payload)
        return _extract_native_content(response)

    def count_prompt_tokens(self, *, system_prompt: str, user_prompt: str, think: bool = True) -> int:
        """UNVERIFIED against a live Ollama server, unlike VllmJsonClient's
        own implementation -- this project's LLM investigation since the vLLM
        switch (§15bis.6) has not touched Ollama at all, and this method is
        never actually called against one in production: llm_behavior_engine.
        _dynamic_max_tokens only invokes count_prompt_tokens behind a
        `config.llm.provider == "vllm"` gate. Implemented anyway so
        LlmClientProtocol has one real implementation per client rather than
        a stub that would raise if ever reached, on the same OpenAI-compat
        `/v1/chat/completions` shape `_complete_json_openai_compat` already
        uses (Ollama's `usage.prompt_tokens` field is a standard part of that
        same compat surface) -- but ollama_structured_output_results.md's own
        finding that "temperature=0 + a pinned seed is not a reproducibility
        guarantee on this backend" is reason enough not to assume this probe
        is safe to actually wire into a chunk-size decision for Ollama
        without first measuring it the way VllmJsonClient's own version was
        measured. `think` intentionally does not route to the native
        `think=False` endpoint the way complete_json does -- a max_tokens=1
        probe on either endpoint returns the same usage.prompt_tokens for the
        same input, so the extra complexity of a second code path here would
        buy nothing."""
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self._temperature,
            "seed": self._seed,
            "max_tokens": 1,
            "stream": False,
        }
        payload = json.dumps(body, sort_keys=True, separators=(",", ":"))
        response = _post_with_transport_retry(self._client, f"{self._base_url}/chat/completions", payload)
        return _extract_prompt_tokens(response)

    def _recycle(self) -> None:
        """Forces a model unload (`keep_alive: 0` on the native endpoint,
        verified directly against a live container to reset "cache state"
        to 0 prompts, the same effect as a full container restart) then
        re-warms both endpoint shapes with one throwaway call each.

        The re-warm prompt is deliberately NOT the tiny `"{}"` stub
        _warm_up_llm_client uses (run_polity_simulation.py) -- a first
        implementation reused that exact shape and, verified live, made
        things WORSE: recycling every 2 calls dropped a 5-call sequence
        from its normal reliability to 2/5 successes, because the call
        immediately following a trivial warm-up prompt is itself the
        already-documented failure mode this investigation found (12/12
        across two independent tests: a tiny, structurally dissimilar
        prior prompt reliably breaks the next real call, regardless of
        whether the tiny prompt's own generation succeeded or failed).
        _RECYCLE_WARM_UP_USER_PROMPT pads the input to a size closer to a
        real production prompt (verified live: 6/6 clean when the prior
        prompt was actually production-sized) while keeping a trivial
        output schema -- the model never has to reason hard about the
        padding, only acknowledge it. This is a SIZE-only approximation
        of "realistic shape", not a full reproduction of a real decision
        prompt's structure; whether size alone is sufficient or the
        output schema's own complexity also matters was not separately
        isolated and remains open.

        Calls the private _complete_json_* methods directly, never
        self.complete_json -- going through the public entry point would
        re-check _calls_since_recycle against the call this method is
        itself issuing, before the counter below has been reset, which
        would recurse.

        Best-effort throughout, matching _warm_up_llm_client's own
        contract: every step is logged and swallowed, never allowed to
        raise out of the real call it exists to protect. The counter
        resets unconditionally at the end, even if every step above
        failed -- the unload attempt is what actually matters for the
        cache pool, and a failed re-warm just means the next real call
        pays bug 2's cold-start cost instead of a clean one, not that the
        recycle itself didn't happen."""
        try:
            self._force_unload()
        except Exception as exc:  # noqa: BLE001
            _logger.warning("LLM recycle: force-unload failed, continuing anyway: %s", exc)
        for think in (True, False):
            try:
                if think:
                    self._complete_json_openai_compat(
                        "Reply with the required JSON object.", _RECYCLE_WARM_UP_USER_PROMPT,
                        _RECYCLE_WARM_UP_SCHEMA, _RECYCLE_WARM_UP_MAX_TOKENS, self._temperature, self._seed,
                    )
                else:
                    self._complete_json_native_no_think(
                        "Reply with the required JSON object.", _RECYCLE_WARM_UP_USER_PROMPT,
                        _RECYCLE_WARM_UP_SCHEMA, _RECYCLE_WARM_UP_MAX_TOKENS, self._temperature, self._seed,
                    )
            except Exception as exc:  # noqa: BLE001
                _logger.warning("LLM recycle: re-warm call (think=%s) failed, continuing anyway: %s", think, exc)
        self._calls_since_recycle = 0

    def _force_unload(self) -> None:
        """POSTs `keep_alive: 0` to the native endpoint -- confirmed live
        (bug 4 investigation) to return `done_reason: "unload"` and make
        `ollama ps` report no running model, with the very next real
        call's own "cache state" log line starting back at 0 prompts."""
        native_base = self._base_url.removesuffix("/v1")
        body = {"model": self._model, "keep_alive": 0}
        payload = json.dumps(body, sort_keys=True, separators=(",", ":"))
        self._client.post(
            f"{native_base}/api/chat", content=payload, headers={"Content-Type": "application/json"}
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> OllamaJsonClient:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self.close()


class VllmJsonClient:
    """vLLM's OpenAI-compatible endpoint (`llm.base_url`, ending in `/v1`,
    e.g. `http://localhost:8000/v1`). One instance per run, reused across
    every batch call -- same lifecycle contract as OllamaJsonClient.

    UNVERIFIED (v4 vLLM switch, §15bis.6): everything below is written
    against vLLM's documented request surface and Qwen3's documented chat
    template, not against a live vLLM response. A GPU has been available
    in this project's environment since 2026-08-17 and has been used with
    Ollama (see the module docstring above), but no vLLM server has ever
    been stood up on it -- the claims below remain unverified for that
    reason, not for lack of a GPU. `polity_config.yaml` ships
    `provider: ollama` as the default for exactly this reason.

    Single endpoint for both think modes, unlike OllamaJsonClient. Ollama's
    `/api/chat` detour exists to route around a *measured Ollama bug*:
    `think: false` combined with `response_format` on `/v1/chat/completions`
    is silently ignored there, burning the whole token budget on invisible
    reasoning (ollama_structured_output_results.md, Finding E). vLLM has no
    equivalent native endpoint and no such bug on record -- Qwen3's
    thinking mode is controlled by a chat-template argument,
    `chat_template_kwargs: {"enable_thinking": ...}`, sent as part of the
    normal OpenAI-compatible request body (per vLLM's documented
    extra_body/chat_template_kwargs support and Qwen3's own
    `enable_thinking` template flag). Sent unconditionally for both
    think=True and think=False, so the request body is a total function of
    the call arguments rather than depending on a hidden server-side
    default.

    Structural risk, not yet resolvable without a live server: with
    `response_format` active, vLLM's structured-output backend constrains
    generation from the first token. If the server is not launched with
    `--reasoning-parser qwen3` (see docker-compose.llm.yml), that grammar
    constraint may make `enable_thinking: true` a SILENT no-op -- no
    `<think>` content, no error, just an immediate, unreasoned JSON answer.
    That would matter here: decide_campaign_positioning's own docstring
    records that `think=False` produced a 100%-reproducible degenerate
    batch on real production data, which is exactly the failure mode this
    risk could reintroduce under a different name. A live test
    (test_polity_vllm_live.py::test_think_true_actually_produces_reasoning)
    is written to detect this once a GPU host exists; nothing in this
    codebase can detect it today.

    `_inline_refs` is applied here too even though vLLM's guided-decoding
    backends (e.g. xgrammar) may handle nested $defs/$ref natively --
    keeping the dereferencing is semantics-preserving and removes any
    dependence on an unverified claim. `seed` is sent for parity with
    OllamaJsonClient, but at temperature=0 sampling is already argmax; it
    does nothing about §15bis.4c's batch-composition nondeterminism, which
    is a kernel floating-point reduction order property, not a sampling
    one -- see check_vllm_batching_determinism.py, never yet run."""

    def __init__(
        self,
        base_url: str,
        model: str,
        temperature: float,
        seed: int,
        timeout: float,
        transport: httpx.BaseTransport | None = None,
        thinking: ThinkingControl = QWEN3_THINKING,
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._temperature = temperature
        self._seed = seed
        self._client = httpx.Client(timeout=timeout, transport=transport)
        # How this model's reasoning is switched (S2.3, model_profiles.py). The default
        # is Qwen3's, which every request sent before model profiles existed used.
        self._thinking = thinking

    @classmethod
    def from_config(cls, llm: LlmConfig, *, seed: int, timeout: float = 600.0) -> VllmJsonClient:
        """Same 600s default as OllamaJsonClient.from_config -- no live
        vLLM measurement exists yet to justify a different one; re-measure
        once a GPU host is available (see the vLLM switch plan)."""
        return cls(
            llm.base_url, llm.model, llm.temperature, seed, timeout,
            thinking=model_profile(llm.provider, llm.model).thinking,
        )

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        max_tokens: int,
        think: bool = True,
        temperature: float | None = None,
        seed: int | None = None,
    ) -> str:
        """Retries only a transport failure, exactly like OllamaJsonClient
        -- see _post_with_transport_retry. A response-level failure
        propagates immediately, unretried -- see LlmResponseError.

        `temperature`/`seed` mirror OllamaJsonClient's own per-call override
        (None preserves this client's configured value). `seed` is no longer
        inert here the way the class docstring above once assumed: it
        overrides `self._seed`, which -- unlike Ollama's -- IS a strong lock
        on this backend at temperature=0 (see the class docstring's own
        `check_vllm_batching_determinism.py` result). `cast_votes`'s
        `retry_seed_base` is the one call site that uses it, for exactly the
        finding `check_vllm_vote_cast_retry_is_inert_results.md` measured: a
        `blank`/`ranking`-incoherent decision at temperature=0 is
        deterministic on this backend, so an identical retry (same seed) only
        reproduces it -- `_VOTE_CAST_RETRY_TEMPERATURE` alone was not enough
        here, unlike on Ollama, because vLLM's pinned seed still constrains
        the retry at the RETRY temperature too."""
        body = self._chat_body(
            system_prompt, user_prompt, max_tokens=max_tokens, think=think, temperature=temperature, seed=seed,
            json_schema=json_schema,
        )
        return _extract_content(self._post_chat(body))

    def count_prompt_tokens(self, *, system_prompt: str, user_prompt: str, think: bool = True) -> int:
        """VERIFIED live (2026-09-08, GPU, check_vllm_chunk_size_throughput_
        results.md): a `max_tokens=1` request against the real production
        prompt builders returns `usage.prompt_tokens` matching the real
        tokenized size at every chunk size measured (1/2/3/5), not an
        estimate -- this is what makes llm_behavior_engine._dynamic_max_tokens
        safe to size against `--max-model-len` (docker-compose.llm.yml)
        precisely rather than guessing a flat allowance the way the naive
        first attempt at this fix did (a chunk_size-scaled allowance guess
        both contradicted compute_max_tokens's own flat-addend convention and
        exceeded the ceiling outright once chunk_size>=3, a real 19716-token
        request rejected outright).

        `chat_template_kwargs: {"enable_thinking": think}` is sent exactly
        as complete_json sends it, so the probed prompt is byte-identical
        (via the chat template) to what the real call will send -- a probe
        under a different `think` value could plausibly tokenize differently
        (Qwen3's template may alter its own preamble based on the flag) and
        would silently mis-size the real call's budget. temperature/seed are
        this client's own configured values (never overridden here): they do
        not affect prompt tokenization, only sampling, but are included for
        the same reason complete_json always includes them -- a total
        function of the call arguments, no hidden server-side default.
        `response_format` is deliberately omitted: xgrammar-style structured
        output constrains GENERATION via logit masking, not the prompt sent
        to the model, so it should not affect `usage.prompt_tokens` -- this
        specific equivalence (probe vs. real-call prompt_tokens) was not
        separately isolated in the live investigation and remains an
        assumption, not a measured claim, though it follows directly from
        how vLLM's structured-output backends are documented to work."""
        body = self._chat_body(system_prompt, user_prompt, max_tokens=1, think=think, temperature=None, seed=None)
        return _extract_prompt_tokens(self._post_chat(body))

    def complete_with_logprobs(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        top_logprobs: int = 10,
        think: bool = False,
        temperature: float | None = None,
        seed: int | None = None,
    ) -> tuple[str, list[TokenLogprob]]:
        """plan-llm-protocol-and-theory-program.md §5.C: a diagnostic
        capability, deliberately NOT wired into any decide_* entry point yet
        -- this reads a decision's own confidence, it does not decide
        anything. VERIFIED live (2026-09-09) that vLLM 0.28.0 returns real,
        calibrated-looking logprobs for a trivial forced-choice probe
        (P(yes)=0.962 vs P(no)=0.038); NOT yet verified against a real
        production, xgrammar-constrained decision schema, where the token
        whose probability actually matters (e.g. an `"act":` field's value,
        deep inside structured JSON) is not necessarily the FIRST generated
        token the way it is for a bare forced-choice probe -- locating that
        token inside a real completion's own token sequence is a real,
        separate problem this method does not attempt to solve, only
        exposes the raw material (`TokenLogprob`, one entry per generated
        position) for a caller to solve it against.

        No `json_schema`/`response_format` here, unlike complete_json --
        the first live use case (§5.C: read P(act) for a decision this
        project has already reduced to a forced binary choice in its own
        prompt wording) does not need structured output, and xgrammar's
        logit masking would only complicate reading a raw token
        probability for no benefit. A schema-constrained variant, if one
        is ever needed, is a distinct method, not a parameter here --
        same reasoning complete_json/count_prompt_tokens already apply
        (each call shape stays a total function of its own arguments, no
        hidden per-caller branching).

        2026-09-10 update: that schema-constrained variant now exists --
        see `complete_json_with_logprobs` below, added to attack this
        method's own "NOT yet verified" gap above (the real, xgrammar-
        constrained, `think=True` decision shape) rather than adding a
        branch here.

        `think` defaults to False, unlike complete_json/count_prompt_tokens
        -- a logprobs probe is normally a short, direct forced-choice
        question (see this method's own module-level design note), and a
        `<think>` block would sit between the prompt and the actual answer
        token, consuming `max_tokens` on reasoning this diagnostic does not
        currently parse out. Overridable per call for a future use case
        that does want it.

        `temperature`/`seed` mirror every other method on this class (None
        preserves the client's own configured values) -- included for the
        same reason count_prompt_tokens documents: a total function of the
        call arguments, no hidden server-side default."""
        body = self._chat_body(
            system_prompt, user_prompt, max_tokens=max_tokens, think=think, temperature=temperature, seed=seed,
            top_logprobs=top_logprobs,
        )
        return _extract_content_and_logprobs(self._post_chat(body))

    def complete_json_with_logprobs(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        max_tokens: int,
        top_logprobs: int = 10,
        think: bool = True,
        temperature: float | None = None,
        seed: int | None = None,
    ) -> tuple[str, list[TokenLogprob]]:
        """plan-llm-protocol-and-theory-program.md §5.C's "real hard
        problem": complete_with_logprobs's own docstring names it and
        deliberately does not attack it -- a real production decision is
        xgrammar-constrained (`response_format`) and, for every decide_*
        caller that matters here, generated under `think=True`, neither of
        which that method's own trivial forced-choice probe exercises.
        This is that call shape instead: complete_json's own body
        (`response_format` with `_inline_refs(json_schema)`, same
        `strict: True` schema envelope) plus `logprobs`/`top_logprobs`,
        so the SAME completion a decide_* function would have decoded is
        also returned with its own per-token log-probabilities attached.

        A distinct method rather than a parameter on either complete_json
        or complete_with_logprobs, same discipline both already apply:
        each call shape stays a total function of its own arguments, no
        hidden per-caller branching. `think` defaults to True here (unlike
        complete_with_logprobs's own False default) because this method's
        whole reason to exist is exercising the REAL production shape,
        where every current vote_cast/chamber caller sends think=True --
        a caller wanting the untouched, no-reasoning shape should still
        reach for complete_with_logprobs instead of overriding this
        default down.

        Locating the field-relevant token inside the returned
        (raw_text, tokens) pair -- e.g. `content` is the reasoning-
        parser-stripped final JSON, but `tokens` covers the FULL raw
        generation including any `<think>...</think>` block, so a naive
        cumulative-offset walk against `content` misaligns under
        think=True -- is llm_logprob_instrumentation.py's job, not this
        method's; see that module's own docstring for the fix (locate
        `content` as a substring of the reconstructed raw token stream,
        then work in that raw offset space)."""
        body = self._chat_body(
            system_prompt, user_prompt, max_tokens=max_tokens, think=think, temperature=temperature, seed=seed,
            json_schema=json_schema, top_logprobs=top_logprobs,
        )
        return _extract_content_and_logprobs(self._post_chat(body))

    def _chat_body(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int,
        think: bool,
        temperature: float | None,
        seed: int | None,
        json_schema: dict[str, Any] | None = None,
        top_logprobs: int | None = None,
    ) -> dict[str, Any]:
        """The request body every call on this client sends: a total function of the
        call's arguments, with temperature/seed falling back to the client's own
        configured values, the model profile's thinking switch, and -- when asked --
        a strict JSON-schema response format and token logprobs."""
        body: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature if temperature is not None else self._temperature,
            "seed": seed if seed is not None else self._seed,
            "max_tokens": max_tokens,
            "stream": False,
            **self._thinking.request_fields(think),
        }
        if json_schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "polity_decision_batch", "strict": True, "schema": _inline_refs(json_schema)},
            }
        if top_logprobs is not None:
            body["logprobs"] = True
            body["top_logprobs"] = top_logprobs
        return body

    def _post_chat(self, body: dict[str, Any]) -> httpx.Response:
        payload = json.dumps(body, sort_keys=True, separators=(",", ":"))
        return _post_with_transport_retry(self._client, f"{self._base_url}/chat/completions", payload)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> VllmJsonClient:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self.close()


def build_json_client(
    llm: LlmConfig, *, seed: int, timeout: float = 600.0
) -> OllamaJsonClient | VllmJsonClient:
    """The single seam that turns `llm.provider` into a concrete client --
    used by run_polity_simulation._llm_client_scope (the only production
    caller) and by any test that wants the real dispatch behavior. Raises
    unsupported_provider_error for anything not in SUPPORTED_PROVIDERS,
    the same error (same message) llm_behavior_engine._check_supported
    raises at first-decision time -- this is the earlier, cheaper failure
    point: a run with `provider: api` now fails at run start rather than at
    the first LLM call."""
    if llm.provider == "ollama":
        return OllamaJsonClient.from_config(llm, seed=seed, timeout=timeout)
    if llm.provider == "vllm":
        return VllmJsonClient.from_config(llm, seed=seed, timeout=timeout)
    raise unsupported_provider_error(llm.provider)


def _response_body(response: httpx.Response) -> dict[str, Any]:
    """response.json() is Any -- walk it with explicit isinstance checks rather than
    indexing blindly, so a surprise shape raises a named error instead of an opaque
    KeyError three frames from here."""
    try:
        body = response.json()
    except ValueError as exc:
        raise LlmResponseError(f"response was not valid JSON: {exc}") from exc
    if not isinstance(body, dict):
        raise LlmResponseError(f"expected a JSON object, got {type(body).__name__}")
    return body


def _first_choice(body: dict[str, Any]) -> dict[str, Any]:
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LlmResponseError(f"expected a non-empty 'choices' list, got {choices!r}")
    choice = choices[0]
    if not isinstance(choice, dict):
        raise LlmResponseError(f"expected choices[0] to be an object, got {type(choice).__name__}")
    return choice


def _message_content(choice: dict[str, Any]) -> str:
    message = choice.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise LlmResponseError(f"expected choices[0].message.content to be a string, got {message!r}")
    return str(message["content"])


def _extract_content(response: httpx.Response) -> str:
    # finish_reason before content, always: a truncated generation can come back with
    # no content at all (everything still in reasoning), and it must be reported as the
    # truncation it is -- replays.log and llm_calls.jsonl are read for that text.
    choice = _first_choice(_response_body(response))
    finish_reason = choice.get("finish_reason")
    if finish_reason != "stop":
        raise LlmResponseError(f"generation did not finish cleanly: finish_reason={finish_reason!r}")
    return _message_content(choice)


def _extract_prompt_tokens(response: httpx.Response) -> int:
    """Shared by both count_prompt_tokens implementations -- the OpenAI-
    compat `usage.prompt_tokens` field, present on the response regardless
    of `finish_reason` (a max_tokens=1 probe always finishes at 'length',
    never 'stop', so this deliberately does NOT go through _extract_content,
    which would raise on exactly that)."""
    usage = _response_body(response).get("usage")
    if not isinstance(usage, dict) or not isinstance(usage.get("prompt_tokens"), int):
        raise LlmResponseError(f"expected usage.prompt_tokens to be an int, got {usage!r}")
    return int(usage["prompt_tokens"])


@dataclass(frozen=True)
class TokenLogprob:
    """One generated token, its own log-probability, and the alternatives
    the server considered at that same position -- vLLM's own OpenAI-compat
    `choices[0].logprobs.content[i]` shape (`token`/`logprob`/`top_logprobs`),
    reshaped into a plain dataclass so a caller never touches raw response
    JSON. `alternatives` is `{token: logprob}`, always including this position's
    own chosen token (vLLM includes it in `top_logprobs` too) -- so
    `alternatives[token] == logprob` always holds, and a caller wanting
    P(a specific candidate token), chosen or not, reads one dict."""

    token: str
    logprob: float
    alternatives: dict[str, float]


def _extract_content_and_logprobs(response: httpx.Response) -> tuple[str, list[TokenLogprob]]:
    """VERIFIED live (2026-09-09): vLLM 0.28.0's `/v1/chat/completions`
    returns `logprobs.content`, one entry per generated token, when the
    request carries `logprobs: true` -- confirmed against a real trivial
    yes/no probe (P(yes)=0.962, P(no)=0.038, read directly off this shape).

    Deliberately does NOT require `finish_reason == 'stop'` the way
    _extract_content does: plan-llm-protocol-and-theory-program.md §5.C's
    whole point is reading the probability of a SPECIFIC early token (often
    the first), so a tiny `max_tokens` budget legitimately ends in 'length'
    on every call -- that is the expected, common case here, not a failure
    mode to reject. Both 'stop' and 'length' are accepted; anything else
    (e.g. a content filter) is not, since this project has never seen or
    reasoned about what those would mean for the returned logprobs."""
    choice = _first_choice(_response_body(response))
    finish_reason = choice.get("finish_reason")
    if finish_reason not in ("stop", "length"):
        raise LlmResponseError(f"generation did not finish as expected: finish_reason={finish_reason!r}")
    content = _message_content(choice)
    logprobs_obj = choice.get("logprobs")
    if not isinstance(logprobs_obj, dict) or not isinstance(logprobs_obj.get("content"), list):
        raise LlmResponseError(
            f"expected choices[0].logprobs.content to be a list -- was `logprobs: true` sent? got {logprobs_obj!r}"
        )
    return content, [_token_logprob(entry) for entry in logprobs_obj["content"]]


def _token_logprob(entry: Any) -> TokenLogprob:
    if not isinstance(entry, dict) or not isinstance(entry.get("token"), str) \
            or not isinstance(entry.get("logprob"), (int, float)):
        raise LlmResponseError(f"malformed logprobs.content entry: {entry!r}")
    alternatives: dict[str, float] = {}
    top = entry.get("top_logprobs")
    for alt in top if isinstance(top, list) else []:
        if isinstance(alt, dict) and isinstance(alt.get("token"), str) and isinstance(alt.get("logprob"), (int, float)):
            alternatives[alt["token"]] = float(alt["logprob"])
    alternatives.setdefault(entry["token"], float(entry["logprob"]))
    return TokenLogprob(token=entry["token"], logprob=float(entry["logprob"]), alternatives=alternatives)


def _extract_native_content(response: httpx.Response) -> str:
    """Ollama's native /api/chat response shape -- no `choices` list, a
    single top-level `message` object, and `done_reason` instead of
    `finish_reason`. See OllamaJsonClient's class docstring for why
    think=False needs this entirely separate endpoint/shape."""
    try:
        body = response.json()
    except ValueError as exc:
        raise LlmResponseError(f"response was not valid JSON: {exc}") from exc

    if not isinstance(body, dict):
        raise LlmResponseError(f"expected a JSON object, got {type(body).__name__}")

    done_reason = body.get("done_reason")
    if done_reason != "stop":
        raise LlmResponseError(f"generation did not finish cleanly: done_reason={done_reason!r}")

    message = body.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise LlmResponseError(f"expected message.content to be a string, got {message!r}")

    return str(message["content"])


class _HasCid(Protocol):
    @property
    def cid(self) -> int: ...


class _HasPartyId(Protocol):
    @property
    def party_id(self) -> int: ...


def _cid(decision: _HasCid) -> int:
    return decision.cid


def _party_id(decision: _HasPartyId) -> int:
    return decision.party_id


_BatchT = TypeVar("_BatchT", bound=BaseModel)
_DecisionT = TypeVar("_DecisionT")


def _decode_batch(
    raw: str,
    batch_model: type[_BatchT],
    *,
    decisions: Callable[[_BatchT], list[_DecisionT]],
    unit: Callable[[_DecisionT], int],
    unit_label: str,
    expected_units: Sequence[int],
) -> list[_DecisionT]:
    """Every decode_*_batch below is this, for one batch model and one unit key.

    Enforces design doc §3.6.0's hard rule: the response holds exactly one
    decision per unit sent (citizen or party), in the same order. A count or
    order mismatch is a full-batch failure -- never a partial or silent
    correction, which would make a unit<->decision misalignment undetectable and
    break reproducibility (§4).

    Nine copies of this body existed until S3.1 (plan-polity-build-order.md);
    each carried a note that a generic `type[T]` version had failed mypy-strict.
    It failed because one type variable stood for both the batch and its
    decisions; two, with the decision list and the unit key passed as functions,
    type-check."""
    stripped = _THINK_TAG_RE.sub("", raw).strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LlmResponseError(f"response is not valid JSON after stripping reasoning tags: {exc}") from exc
    except RecursionError as exc:
        # json.loads' recursive-descent parser overflows the C stack on
        # pathologically deep nesting (confirmed: ~1e5 nested `[` from a fresh
        # interpreter) *before* reaching JSONDecodeError's own checks -- an LLM
        # stuck in a degenerate repetition loop can emit exactly this shape.
        # Found fuzzing decode_vote_batch with atheris (Lot 9,
        # PLAN_SOLIDITE_TECHNIQUE.md).
        raise LlmResponseError(f"response is too deeply nested to parse as JSON: {exc}") from exc

    try:
        batch = batch_model.model_validate(parsed)
    except ValidationError as exc:
        raise LlmResponseError(f"batch failed schema validation: {exc}") from exc

    batch_decisions = decisions(batch)
    got_units = [unit(decision) for decision in batch_decisions]
    if got_units != list(expected_units):
        raise LlmResponseError(
            f"batch misaligned with the request: expected {unit_label} {list(expected_units)}, got {got_units}"
        )
    return batch_decisions


# One typed accessor per batch model, not a lambda: through a lambda mypy stops
# checking the decision type against `unit`, so a wrong key (party_id on a
# citizen decision) type-checked. Named, the whole call is checked.

def _vote_decisions(batch: VoteCastBatch) -> list[VoteCastDecision]:
    return batch.decisions


def _party_nomination_decisions(batch: PartyNominationBatch) -> list[PartyNominationDecision]:
    return batch.decisions


def _positioning_decisions(batch: PositioningBatch) -> list[PositioningDecision]:
    return batch.decisions


def _response_decisions(batch: ResponseBatch) -> list[ResponseDecision]:
    return batch.decisions


def _pressure_decisions(batch: PressureBatch) -> list[PressureDecision]:
    return batch.decisions


def _reaction_decisions(batch: ReactionBatch) -> list[ReactionDecision]:
    return batch.decisions


def _chamber_decisions(batch: ChamberBatch) -> list[ChamberDecision]:
    return batch.decisions


def _coalition_decisions(batch: CoalitionBatch) -> list[CoalitionDecision]:
    return batch.decisions


def _candidacy_decisions(batch: CandidacyBatch) -> list[CandidacyDecision]:
    return batch.decisions

def decode_vote_batch(raw: str, expected_cids: Sequence[int]) -> list[VoteCastDecision]:
    """vote_cast, one decision per voter (cid)."""
    return _decode_batch(
        raw, VoteCastBatch, decisions=_vote_decisions, unit=_cid, unit_label="cids",
        expected_units=expected_cids,
    )


def decode_party_nomination_batch(raw: str, expected_party_ids: Sequence[int]) -> list[PartyNominationDecision]:
    """party_nomination_choice, one decision per contested party (party_id)."""
    return _decode_batch(
        raw, PartyNominationBatch, decisions=_party_nomination_decisions, unit=_party_id, unit_label="party_ids",
        expected_units=expected_party_ids,
    )


def decode_positioning_batch(raw: str, expected_cids: Sequence[int]) -> list[PositioningDecision]:
    """campaign_positioning, one decision per nominee (cid)."""
    return _decode_batch(
        raw, PositioningBatch, decisions=_positioning_decisions, unit=_cid, unit_label="cids",
        expected_units=expected_cids,
    )


def decode_response_batch(raw: str, expected_cids: Sequence[int]) -> list[ResponseDecision]:
    """representative_response, one decision per officeholder (cid)."""
    return _decode_batch(
        raw, ResponseBatch, decisions=_response_decisions, unit=_cid, unit_label="cids",
        expected_units=expected_cids,
    )


def decode_pressure_batch(raw: str, expected_cids: Sequence[int]) -> list[PressureDecision]:
    """pressure_action, one decision per consulted citizen (cid). Called once per
    chunk, so a misalignment costs a chunk, not a tick's consultation."""
    return _decode_batch(
        raw, PressureBatch, decisions=_pressure_decisions, unit=_cid, unit_label="cids",
        expected_units=expected_cids,
    )


def decode_reaction_batch(raw: str, expected_cids: Sequence[int]) -> list[ReactionDecision]:
    """reaction_to_event, one decision per reacting citizen (cid), once per chunk."""
    return _decode_batch(
        raw, ReactionBatch, decisions=_reaction_decisions, unit=_cid, unit_label="cids",
        expected_units=expected_cids,
    )


def decode_chamber_batch(raw: str, expected_cids: Sequence[int]) -> list[ChamberDecision]:
    """chamber_deliberation, one decision per seated member (cid), once per chunk
    at llm_behavior_engine._chamber_chunk_size -- a single call of 30 members
    was measured to drop all but the last 6 decisions."""
    return _decode_batch(
        raw, ChamberBatch, decisions=_chamber_decisions, unit=_cid, unit_label="cids",
        expected_units=expected_cids,
    )


def decode_coalition_batch(raw: str, expected_party_ids: Sequence[int]) -> list[CoalitionDecision]:
    """coalition_decision, one decision per responding party (party_id)."""
    return _decode_batch(
        raw, CoalitionBatch, decisions=_coalition_decisions, unit=_party_id, unit_label="party_ids",
        expected_units=expected_party_ids,
    )


def decode_candidacy_batch(raw: str, expected_cids: Sequence[int]) -> list[CandidacyDecision]:
    """candidacy_considered, one decision per citizen considered (cid)."""
    return _decode_batch(
        raw, CandidacyBatch, decisions=_candidacy_decisions, unit=_cid, unit_label="cids",
        expected_units=expected_cids,
    )
