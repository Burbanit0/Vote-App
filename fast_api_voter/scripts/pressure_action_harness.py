"""
scripts/pressure_action_harness.py

Phase 1 instrumentation for plan-pressure-action-resolution.md §1 -- shared by every Phase 2 test
script, built once here rather than duplicated per test. Reuses the project's own existing
llm_test_harness (registration/trial/storage/report) rather than inventing a new logging system,
exactly what §1.3 asked for ("SQLite via le harnais existant").

Captures what production's own extractors throw away (llm_test_harness/README.md's own
documented pitfall, "le raisonnement n'est PAS dans message.content"): the FULL raw response body
(message.reasoning, finish_reason/done_reason, token counts), not just decoded content -- and the
EXACT serialized request body actually sent (post json.dumps), the same technique that caught the
§3.4 sort_keys alphabetization bug. Both are dumped in full, never reconstructed from what the
caller assumed was sent.

llm_test_harness's own trial schema (ok/finish_reason/truncated/decoded_tokens/detail) is scoped
to call-level RELIABILITY, not decision-content correctness -- deliberately not extended here
(a schema migration for one experiment's needs would touch shared harness code used by other
investigations). The rich per-decision fields §1.3 asks for (self_gap, blank_threshold, ratio,
mandate_dev, neighbors_acting, ticks_to_election, act, motif, full reasoning text, actual JSON
field order, variant label) are JSON-encoded into `detail`, queryable via SQLite's own
json_extract() without touching storage.py's schema.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from api.domain.polity.accountability import self_gap  # noqa: E402
from api.domain.polity.citizen import Citizen, generate_population  # noqa: E402
from api.domain.polity.config import PolityConfig  # noqa: E402
from api.domain.polity.llm_client import OllamaJsonClient, _post_with_transport_retry, _THINK_TAG_RE  # noqa: E402
from api.domain.polity.simple_rules import declare_candidacy  # noqa: E402
from llm_test_harness import trial  # noqa: E402

POPULATION_SIZE = 190
HOLDER_CID = 5
MANDATE_DEV = 0.0
TICKS_TO_ELECTION = 15
ACTING_CODES = {1, 2, 3}
ACT_NAMES = {0: "NOTHING", 1: "SIGN_PETITION", 2: "LAUNCH_PETITION", 3: "MOBILIZE", 4: "WAIT_FOR_ELECTION"}


def harvest_unambiguous_citizens(config: PolityConfig) -> tuple[Citizen, list[tuple[Citizen, float, bool]]]:
    """Same deterministic construction as every prior remediation script this session --
    self_gap/blank_threshold are pure functions of citizen data, no LLM needed. holder=cid5 via
    declare_candidacy (unshifted, unbiased by any campaign_positioning LLM run -- see
    plan-pressure-action-remediation.md §3.1's own verification of this)."""
    population = list(generate_population(config.citizens, POPULATION_SIZE, config.run.seed))
    holder = next(c for c in population if c.citizen_id == HOLDER_CID)
    declare_candidacy(holder)
    cases = []
    for citizen in population:
        if citizen.citizen_id == holder.citizen_id or citizen.blank_threshold <= 0:
            continue
        gap = self_gap(citizen, holder)
        ratio = gap / citizen.blank_threshold
        if ratio < 0.5:
            cases.append((citizen, gap, False))
        elif ratio > 1.5:
            cases.append((citizen, gap, True))
    return holder, cases


@dataclass(frozen=True)
class RawCallResult:
    """Everything a diagnostic needs, nothing pre-interpreted. request_body_sent is the exact
    bytes-equivalent string that went on the wire (post json.dumps(sort_keys=True) -- the same
    serialization production uses, bugs included, not a cleaned-up reconstruction). response_body
    is the FULL parsed JSON response, not just extracted content -- message.reasoning included,
    captured even when done_reason != "stop" (unlike _extract_native_content, which raises and
    discards it)."""

    request_body_sent: str
    response_body: dict[str, Any] | None
    response_status: int
    transport_error: str | None
    done_reason: str | None
    content: str | None
    reasoning: str | None
    field_order: list[str] | None
    """Actual top-level key order of the first element of the decoded decisions array, as it
    appears in the raw JSON text (not the parsed dict, which does not preserve wire order once
    round-tripped through some JSON parsers) -- what caught the §3.4 sort_keys bug."""


def raw_pressure_call(
    client: OllamaJsonClient, system_prompt: str, user_prompt: str, json_schema: dict[str, Any] | None,
    max_tokens: int, temperature: float | None = None,
) -> RawCallResult:
    """Native /api/chat, think=False (production path), bypassing complete_json/
    _extract_native_content entirely so a truncation or any other non-"stop" done_reason does not
    discard the response -- captures everything regardless of outcome. Mirrors
    OllamaJsonClient._complete_json_native_no_think's exact request shape (same body, same
    sort_keys=True serialization) so what's captured is what production would actually send, not
    an idealized reconstruction.

    `json_schema=None` (plan-pressure-action-resolution.md §2.3): omits the `format` field
    entirely -- free-form generation, no grammar-constrained decoding -- rather than sending an
    empty/null format, which Ollama could plausibly treat differently than the field's total
    absence. The caller's own prompt must ask for JSON in prose when using this mode; parsing is
    the caller's responsibility (a lenient extraction, not the strict decode_*_batch functions,
    which assume grammar-constrained output)."""
    native_base = client._base_url.removesuffix("/v1")  # noqa: SLF001 -- exploratory harness, documented reuse
    effective_temperature = temperature if temperature is not None else client._temperature  # noqa: SLF001
    body: dict[str, Any] = {
        "model": client._model,  # noqa: SLF001
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "think": False,
        "options": {"temperature": effective_temperature, "seed": client._seed, "num_predict": max_tokens},  # noqa: SLF001
    }
    if json_schema is not None:
        body["format"] = json_schema
    payload = json.dumps(body, sort_keys=True, separators=(",", ":"))

    try:
        response = _post_with_transport_retry(client._client, f"{native_base}/api/chat", payload)  # noqa: SLF001
    except Exception as exc:  # noqa: BLE001 -- transport failure itself is a result to record, not to hide
        return RawCallResult(
            request_body_sent=payload, response_body=None, response_status=-1,
            transport_error=str(exc), done_reason=None, content=None, reasoning=None, field_order=None,
        )

    try:
        response_body = response.json()
    except ValueError:
        return RawCallResult(
            request_body_sent=payload, response_body=None, response_status=response.status_code,
            transport_error=f"response was not valid JSON: {response.text[:500]!r}",
            done_reason=None, content=None, reasoning=None, field_order=None,
        )

    message = response_body.get("message", {}) if isinstance(response_body, dict) else {}
    content = message.get("content") if isinstance(message, dict) else None
    reasoning = message.get("reasoning") if isinstance(message, dict) else None
    done_reason = response_body.get("done_reason") if isinstance(response_body, dict) else None

    field_order = None
    if isinstance(content, str):
        stripped = _THINK_TAG_RE.sub("", content).strip()
        try:
            parsed = json.loads(stripped)
            first_decision = parsed.get("decisions", [None])[0]
            if isinstance(first_decision, dict):
                field_order = list(first_decision.keys())
        except (json.JSONDecodeError, AttributeError, IndexError):
            pass

    return RawCallResult(
        request_body_sent=payload, response_body=response_body, response_status=response.status_code,
        transport_error=None, done_reason=done_reason, content=content, reasoning=reasoning,
        field_order=field_order,
    )


def to_trial_result(raw: RawCallResult, extra: dict[str, Any]) -> trial.TrialResult:
    """Maps a RawCallResult onto the harness's own reliability-scoped TrialResult (ok/
    finish_reason/truncated/decoded_tokens), with everything else (the rich §1.3 fields, plus the
    caller-supplied `extra` -- self_gap, ratio, act, motif, variant label, etc.) JSON-encoded into
    `detail`, queryable via SQLite's json_extract() without a schema migration."""
    ok = raw.transport_error is None and raw.done_reason == "stop"
    usage = raw.response_body.get("eval_count") if raw.response_body else None
    detail = {
        "request_body_sent": raw.request_body_sent,
        "response_body": raw.response_body,
        "content": raw.content,
        "reasoning": raw.reasoning,
        "reasoning_chars": len(raw.reasoning) if raw.reasoning else 0,
        "field_order": raw.field_order,
        "transport_error": raw.transport_error,
        **extra,
    }
    return trial.TrialResult(
        ok=ok,
        finish_reason=raw.done_reason,
        truncated=(raw.done_reason is not None and raw.done_reason != "stop"),
        decoded_tokens=usage,
        detail=json.dumps(detail, sort_keys=True, default=str),
    )
