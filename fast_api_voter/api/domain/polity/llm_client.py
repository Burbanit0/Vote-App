"""
api.domain.polity.llm_client — sync HTTP transport to a local Ollama or
vLLM instance, v2 increment 1 (Ollama); v4 vLLM switch (§15bis.6) adds
VllmJsonClient.

vLLM status: VllmJsonClient below is implemented against vLLM's documented
OpenAI-compatible surface and Qwen3's documented `enable_thinking` chat-
template flag -- it has never been executed against a live vLLM server (no
GPU has been available in this project). Every claim in OllamaJsonClient's
own docstring is backed by a committed live results doc; no claim in
VllmJsonClient's docstring is. §15bis.5's determinism-under-batching
protocol has been run against Ollama only (llm_batching_determinism_results.md)
and has never been run against vLLM. `polity_config.yaml` ships
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
import re
from types import TracebackType
from typing import Any, Protocol, Sequence

import httpx
from pydantic import ValidationError

from api.domain.polity.config import LlmConfig
from api.domain.polity.llm_schemas import (
    CandidacyBatch,
    CandidacyDecision,
    CoalitionBatch,
    CoalitionDecision,
    PartyNominationBatch,
    PartyNominationDecision,
    PositioningBatch,
    PositioningDecision,
    PressureBatch,
    PressureDecision,
    ResponseBatch,
    ResponseDecision,
    VoteCastBatch,
    VoteCastDecision,
)

_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_TRANSPORT_RETRY_ATTEMPTS = 3  # 1 initial + 2 retries -- see module docstring on why


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
    ) -> str: ...


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
    batch size -- party_nomination_choice now also uses think=False."""

    def __init__(
        self,
        base_url: str,
        model: str,
        temperature: float,
        seed: int,
        timeout: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._temperature = temperature
        self._seed = seed
        self._client = httpx.Client(timeout=timeout, transport=transport)

    @classmethod
    def from_config(cls, llm: LlmConfig, *, seed: int, timeout: float = 600.0) -> OllamaJsonClient:
        """600s default: a live consolidation run measured a real full-size
        (25-citizen) batch completing at 294.64s -- already within seconds
        of the previous 300s default, with no margin for Qwen3's variable
        <think> reasoning length. 600s gives real headroom without masking
        a genuinely hung request."""
        return cls(llm.base_url, llm.model, llm.temperature, seed, timeout)

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        max_tokens: int,
        think: bool = True,
    ) -> str:
        """Retries only a transport failure, up to _TRANSPORT_RETRY_ATTEMPTS
        total attempts, no backoff (no concurrency to jitter against -- see
        module docstring). A response-level failure (bad schema, truncated
        generation) propagates immediately, unretried -- see LlmResponseError.

        `think` defaults to True (vote_cast's existing, unchanged behavior)
        -- see the class docstring for why `think=False` needs an entirely
        different endpoint/request shape, not just one extra body field."""
        if think:
            return self._complete_json_openai_compat(system_prompt, user_prompt, json_schema, max_tokens)
        return self._complete_json_native_no_think(system_prompt, user_prompt, json_schema, max_tokens)

    def _complete_json_openai_compat(
        self, system_prompt: str, user_prompt: str, json_schema: dict[str, Any], max_tokens: int
    ) -> str:
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self._temperature,
            "seed": self._seed,
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
        self, system_prompt: str, user_prompt: str, json_schema: dict[str, Any], max_tokens: int
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
            "options": {"temperature": self._temperature, "seed": self._seed, "num_predict": max_tokens},
        }
        payload = json.dumps(body, sort_keys=True, separators=(",", ":"))
        response = _post_with_transport_retry(self._client, f"{native_base}/api/chat", payload)
        return _extract_native_content(response)

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
    template, not against a live vLLM response. No GPU has been available
    in this project. `polity_config.yaml` ships `provider: ollama` as the
    default for exactly this reason.

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
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._temperature = temperature
        self._seed = seed
        self._client = httpx.Client(timeout=timeout, transport=transport)

    @classmethod
    def from_config(cls, llm: LlmConfig, *, seed: int, timeout: float = 600.0) -> VllmJsonClient:
        """Same 600s default as OllamaJsonClient.from_config -- no live
        vLLM measurement exists yet to justify a different one; re-measure
        once a GPU host is available (see the vLLM switch plan)."""
        return cls(llm.base_url, llm.model, llm.temperature, seed, timeout)

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        max_tokens: int,
        think: bool = True,
    ) -> str:
        """Retries only a transport failure, exactly like OllamaJsonClient
        -- see _post_with_transport_retry. A response-level failure
        propagates immediately, unretried -- see LlmResponseError."""
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self._temperature,
            "seed": self._seed,
            "max_tokens": max_tokens,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": think},
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "polity_decision_batch", "strict": True, "schema": _inline_refs(json_schema)},
            },
        }
        payload = json.dumps(body, sort_keys=True, separators=(",", ":"))
        response = _post_with_transport_retry(self._client, f"{self._base_url}/chat/completions", payload)
        return _extract_content(response)

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


def _extract_content(response: httpx.Response) -> str:
    """response.json() is Any -- walk it with explicit isinstance checks
    rather than indexing blindly, so a surprise shape raises a named error
    instead of an opaque KeyError three frames from here."""
    try:
        body = response.json()
    except ValueError as exc:
        raise LlmResponseError(f"response was not valid JSON: {exc}") from exc

    if not isinstance(body, dict):
        raise LlmResponseError(f"expected a JSON object, got {type(body).__name__}")
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LlmResponseError(f"expected a non-empty 'choices' list, got {choices!r}")
    choice = choices[0]
    if not isinstance(choice, dict):
        raise LlmResponseError(f"expected choices[0] to be an object, got {type(choice).__name__}")

    finish_reason = choice.get("finish_reason")
    if finish_reason != "stop":
        raise LlmResponseError(f"generation did not finish cleanly: finish_reason={finish_reason!r}")

    message = choice.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise LlmResponseError(f"expected choices[0].message.content to be a string, got {message!r}")

    return str(message["content"])


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


def decode_vote_batch(raw: str, expected_cids: Sequence[int]) -> list[VoteCastDecision]:
    """Enforces design doc §3.6.0's hard rule: response contains exactly
    one element per cid sent, in the same order. A count or order mismatch
    is a full-batch failure -- never a partial/silent correction, which
    would make a cid<->decision misalignment undetectable and break
    reproducibility (§4). Concrete to VoteCastBatch for now -- this
    increment has exactly one decision type; generalize when a second one
    is actually built, not before."""
    stripped = _THINK_TAG_RE.sub("", raw).strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LlmResponseError(f"response is not valid JSON after stripping reasoning tags: {exc}") from exc

    try:
        batch = VoteCastBatch.model_validate(parsed)
    except ValidationError as exc:
        raise LlmResponseError(f"batch failed schema validation: {exc}") from exc

    got_cids = [decision.cid for decision in batch.decisions]
    if got_cids != list(expected_cids):
        raise LlmResponseError(
            f"batch misaligned with the request: expected cids {list(expected_cids)}, got {got_cids}"
        )

    return batch.decisions


def decode_party_nomination_batch(raw: str, expected_party_ids: Sequence[int]) -> list[PartyNominationDecision]:
    """Same contract as decode_vote_batch/decode_candidacy_batch, specialized
    to PartyNominationBatch and keyed on `party_id` instead of `cid` -- the
    decision unit here is a contested party, not a citizen. This is the
    third near-identical decode function (decode_vote_batch's own comment
    flagged this as the point to "revisit genericizing... if the duplication
    cost is clearly worth paying"): kept duplicated anyway, since the prior
    generic `type[T]` attempt concretely failed mypy-strict typing and
    nothing about that has changed."""
    stripped = _THINK_TAG_RE.sub("", raw).strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LlmResponseError(f"response is not valid JSON after stripping reasoning tags: {exc}") from exc

    try:
        batch = PartyNominationBatch.model_validate(parsed)
    except ValidationError as exc:
        raise LlmResponseError(f"batch failed schema validation: {exc}") from exc

    got_party_ids = [decision.party_id for decision in batch.decisions]
    if got_party_ids != list(expected_party_ids):
        raise LlmResponseError(
            f"batch misaligned with the request: expected party_ids {list(expected_party_ids)}, "
            f"got {got_party_ids}"
        )

    return batch.decisions


def decode_positioning_batch(raw: str, expected_cids: Sequence[int]) -> list[PositioningDecision]:
    """Same contract as decode_vote_batch/decode_candidacy_batch, specialized
    to PositioningBatch -- keyed on `cid` (the nominee), same as those two,
    unlike decode_party_nomination_batch's `party_id` key. A fourth
    near-identical decode function, kept duplicated for the same reason as
    the third: the prior generic `type[T]` attempt concretely failed
    mypy-strict typing, and nothing about that has changed."""
    stripped = _THINK_TAG_RE.sub("", raw).strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LlmResponseError(f"response is not valid JSON after stripping reasoning tags: {exc}") from exc

    try:
        batch = PositioningBatch.model_validate(parsed)
    except ValidationError as exc:
        raise LlmResponseError(f"batch failed schema validation: {exc}") from exc

    got_cids = [decision.cid for decision in batch.decisions]
    if got_cids != list(expected_cids):
        raise LlmResponseError(
            f"batch misaligned with the request: expected cids {list(expected_cids)}, got {got_cids}"
        )

    return batch.decisions


def decode_response_batch(raw: str, expected_cids: Sequence[int]) -> list[ResponseDecision]:
    """Same contract as decode_vote_batch/decode_candidacy_batch/
    decode_positioning_batch, specialized to ResponseBatch -- keyed on `cid`
    (the officeholder), v4 Lot 6 (dt=6). A sixth near-identical decode
    function, kept duplicated for the same reason as the third, fourth and
    fifth: the prior generic `type[T]` attempt concretely failed
    mypy-strict typing, and nothing about that has changed."""
    stripped = _THINK_TAG_RE.sub("", raw).strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LlmResponseError(f"response is not valid JSON after stripping reasoning tags: {exc}") from exc

    try:
        batch = ResponseBatch.model_validate(parsed)
    except ValidationError as exc:
        raise LlmResponseError(f"batch failed schema validation: {exc}") from exc

    got_cids = [decision.cid for decision in batch.decisions]
    if got_cids != list(expected_cids):
        raise LlmResponseError(
            f"batch misaligned with the request: expected cids {list(expected_cids)}, got {got_cids}"
        )

    return batch.decisions


def decode_pressure_batch(raw: str, expected_cids: Sequence[int]) -> list[PressureDecision]:
    """Same contract as decode_vote_batch/decode_candidacy_batch/
    decode_positioning_batch/decode_response_batch, specialized to
    PressureBatch -- keyed on `cid` (the consulted citizen), v4 Lot 7
    (dt=10). A seventh near-identical decode function, kept duplicated for
    the same reason as the third through sixth: the prior generic `type[T]`
    attempt concretely failed mypy-strict typing, and nothing about that
    has changed.

    Unlike every prior decode function, `expected_cids` here is a
    variable-size, CHUNKED cohort (decide_pressure_actions calls this once
    per chunk_voters chunk, not once per tick) -- a misalignment costs a
    whole chunk, not a whole tick's consultation."""
    stripped = _THINK_TAG_RE.sub("", raw).strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LlmResponseError(f"response is not valid JSON after stripping reasoning tags: {exc}") from exc

    try:
        batch = PressureBatch.model_validate(parsed)
    except ValidationError as exc:
        raise LlmResponseError(f"batch failed schema validation: {exc}") from exc

    got_cids = [decision.cid for decision in batch.decisions]
    if got_cids != list(expected_cids):
        raise LlmResponseError(
            f"batch misaligned with the request: expected cids {list(expected_cids)}, got {got_cids}"
        )

    return batch.decisions


def decode_coalition_batch(raw: str, expected_party_ids: Sequence[int]) -> list[CoalitionDecision]:
    """Same contract as decode_party_nomination_batch — keyed on `party_id`,
    not `cid`. A fifth near-identical decode function, kept duplicated for
    the same reason as the third and fourth: the prior generic `type[T]`
    attempt concretely failed mypy-strict typing, and nothing about that has
    changed."""
    stripped = _THINK_TAG_RE.sub("", raw).strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LlmResponseError(f"response is not valid JSON after stripping reasoning tags: {exc}") from exc

    try:
        batch = CoalitionBatch.model_validate(parsed)
    except ValidationError as exc:
        raise LlmResponseError(f"batch failed schema validation: {exc}") from exc

    got_party_ids = [decision.party_id for decision in batch.decisions]
    if got_party_ids != list(expected_party_ids):
        raise LlmResponseError(
            f"batch misaligned with the request: expected party_ids {list(expected_party_ids)}, "
            f"got {got_party_ids}"
        )

    return batch.decisions


def decode_candidacy_batch(raw: str, expected_cids: Sequence[int]) -> list[CandidacyDecision]:
    """Same contract as decode_vote_batch, specialized to CandidacyBatch —
    the second decision type this project actually builds. Deliberately
    duplicated rather than generalized: decode_vote_batch's own comment
    anticipated this moment, but a prior generic `type[T]` attempt didn't
    type-check cleanly (return type conflated batch vs. decision types).
    Revisit genericizing both only if a third decision type makes the
    duplication cost clearly worth paying."""
    stripped = _THINK_TAG_RE.sub("", raw).strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LlmResponseError(f"response is not valid JSON after stripping reasoning tags: {exc}") from exc

    try:
        batch = CandidacyBatch.model_validate(parsed)
    except ValidationError as exc:
        raise LlmResponseError(f"batch failed schema validation: {exc}") from exc

    got_cids = [decision.cid for decision in batch.decisions]
    if got_cids != list(expected_cids):
        raise LlmResponseError(
            f"batch misaligned with the request: expected cids {list(expected_cids)}, got {got_cids}"
        )

    return batch.decisions
