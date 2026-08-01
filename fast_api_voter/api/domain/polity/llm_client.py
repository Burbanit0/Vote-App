"""
api.domain.polity.llm_client — sync HTTP transport to a local Ollama
instance, v2 increment 1.

Sync httpx.Client only, never async. A batch call is a single request/
response; there is no intra-batch concurrency to justify async, and the
existing scripts/check_llm_batching_determinism.py is async specifically
to fire deliberately-concurrent requests and prove they diverge (§15bis.5)
-- that pattern must not leak into production code, which must keep
exactly one request in flight at a time to preserve the reproducibility
that protocol already proved: temperature=0 + a pinned model + serialized
calls, confirmed empirically in llm_batching_determinism_results.md.

Ollama's OpenAI-compatible endpoint cannot handle Pydantic's nested
$defs/$ref schemas -- confirmed in ollama_structured_output_results.md
(Finding A): sent as-is, every request silently consumed the whole token
budget with zero visible content. This module dereferences (inlines) any
schema before sending it, so every caller is protected automatically
rather than having to remember to do it themselves.

No caching here (§4.2 deferred to a later increment, per the approved
plan): correctness comes from temperature=0 + pinned model + serialization,
not from a cache. The request body is still built as canonical
(sort_keys, compact separators) bytes so a cache key can be added later
without touching prompt construction.
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
from api.domain.polity.llm_schemas import VoteCastBatch, VoteCastDecision

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
    batch-alignment rule (wrong count or cid order). NOT retried: at
    temperature=0 with a pinned seed, replaying a bad request is a
    guaranteed no-op (confirmed by llm_batching_determinism_results.md's
    sequential-determinism result) -- it would burn CPU time to reproduce
    the identical failure, never fix it."""


class LlmClientProtocol(Protocol):
    def complete_json(
        self, *, system_prompt: str, user_prompt: str, json_schema: dict[str, Any], max_tokens: int
    ) -> str: ...


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


class OllamaJsonClient:
    """Ollama's OpenAI-compatible endpoint (`llm.base_url`, already ending
    in `/v1`). One instance per run, reused across every batch call."""

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
    def from_config(cls, llm: LlmConfig, *, seed: int, timeout: float = 300.0) -> OllamaJsonClient:
        return cls(llm.base_url, llm.model, llm.temperature, seed, timeout)

    def complete_json(
        self, *, system_prompt: str, user_prompt: str, json_schema: dict[str, Any], max_tokens: int
    ) -> str:
        """Retries only a transport failure, up to _TRANSPORT_RETRY_ATTEMPTS
        total attempts, no backoff (no concurrency to jitter against -- see
        module docstring). A response-level failure (bad schema, truncated
        generation) propagates immediately, unretried -- see LlmResponseError."""
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

        last_transport_error: LlmTransportError | None = None
        for _ in range(_TRANSPORT_RETRY_ATTEMPTS):
            try:
                response = self._client.post(
                    f"{self._base_url}/chat/completions",
                    content=payload,
                    headers={"Content-Type": "application/json"},
                )
            except httpx.HTTPError as exc:
                last_transport_error = LlmTransportError(f"request to {self._base_url} failed: {exc}")
                continue
            if response.status_code != 200:
                last_transport_error = LlmTransportError(
                    f"HTTP {response.status_code} from {self._base_url}: {response.text[:500]}"
                )
                continue
            return _extract_content(response)

        assert last_transport_error is not None  # loop runs at least once
        raise last_transport_error

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> OllamaJsonClient:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self.close()


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
