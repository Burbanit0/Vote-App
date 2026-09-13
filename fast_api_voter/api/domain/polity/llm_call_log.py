"""Per-call LLM log (S0.5): `llm_calls.jsonl` beside `events.jsonl`, one line per
request a run sends -- decisions, retries, token-budget probes, warm-up.

The journal records what the polity did; this records what it cost and what the
model actually said, reasoning included, so a run's time can be attributed and
its decisions audited or replayed (S0.6) without re-running the model.

A call's id is derived from its request (`llm_call_id`), not from a counter:
ids must be the same on every run of the same seed, because LLM-derived events
journal them and the journal's bytes are what reproducibility is asserted over,
and chunks run concurrently. Two byte-identical requests therefore share an id
and get one line each; a reader pairs an event with its call by (id, tick).

Writing never fails a run -- the same contract as run_digest: the first write
error is logged and the log disables itself.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any

import httpx

from api.domain.polity import llm_schemas

_logger = logging.getLogger(__name__)

CALL_LOG_FILENAME = "llm_calls.jsonl"
CALL_LOG_SUMMARY_FILENAME = "llm_calls_summary.json"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


_DECISION_TYPE_BY_SCHEMA = {
    _canonical(llm_schemas.VOTE_CAST_JSON_SCHEMA): "vote_cast",
    _canonical(llm_schemas.CANDIDACY_JSON_SCHEMA): "candidacy_considered",
    _canonical(llm_schemas.PARTY_NOMINATION_JSON_SCHEMA): "party_nomination_choice",
    _canonical(llm_schemas.POSITIONING_JSON_SCHEMA): "campaign_positioning",
    _canonical(llm_schemas.RESPONSE_JSON_SCHEMA): "representative_response",
    _canonical(llm_schemas.PRESSURE_JSON_SCHEMA): "pressure_action",
    _canonical(llm_schemas.REACTION_JSON_SCHEMA): "reaction_to_event",
    _canonical(llm_schemas.CHAMBER_JSON_SCHEMA): "chamber_deliberation",
    _canonical(llm_schemas.COALITION_JSON_SCHEMA): "coalition_decision",
}


def decision_type_for_schema(json_schema: dict[str, Any] | None) -> str:
    """Which decision type a complete_json request belongs to, read off its JSON
    schema -- the one request field every decision type sets differently."""
    return _DECISION_TYPE_BY_SCHEMA.get(_canonical(json_schema), "unknown_schema")


def request_sha256(
    *,
    system_prompt: str,
    user_prompt: str,
    json_schema: dict[str, Any] | None,
    max_tokens: int | None,
    think: bool = True,
    temperature: float | None = None,
    seed: int | None = None,
) -> str:
    """sha256 of a request as the engine issues it: complete_json's arguments,
    with temperature/seed null when the client's own configured value applies."""
    request = {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "json_schema": json_schema,
        "max_tokens": max_tokens,
        "think": think,
        "temperature": temperature,
        "seed": seed,
    }
    return hashlib.sha256(_canonical(request).encode("utf-8")).hexdigest()


def llm_call_id(request_hash: str) -> str:
    return request_hash[:16]


@dataclass(frozen=True)
class CallContext:
    """What the engine knows about a call that its arguments do not say."""

    kind: str
    decision_type: str | None
    unit_ids: tuple[int, ...] | None
    attempt: int | None


_current_context: ContextVar[CallContext | None] = ContextVar("llm_call_context", default=None)


@contextmanager
def call_context(
    *, kind: str = "decision", decision_type: str | None, unit_ids: Sequence[int] | None = None, attempt: int | None = None,
) -> Iterator[None]:
    """Set in the thread that makes the call, around the call -- chunk workers
    run on pool threads, which do not see a context set by the caller's thread."""
    token = _current_context.set(
        CallContext(kind, decision_type, tuple(unit_ids) if unit_ids is not None else None, attempt)
    )
    try:
        yield
    finally:
        _current_context.reset(token)


_in_flight = threading.local()


def record_http_response(response: httpx.Response) -> None:
    """Called by the real clients with every response body they receive. Fills
    the calling thread's in-flight log record, if a CallLoggingClient opened one;
    a no-op otherwise, and never raises."""
    record = getattr(_in_flight, "record", None)
    if record is None:
        return
    try:
        body = response.json()
    except ValueError:
        return
    record.update(response_fields(body))


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _first_choice(body: dict[str, Any]) -> dict[str, Any]:
    choices = body.get("choices")
    return _as_dict(choices[0]) if isinstance(choices, list) and choices else {}


def response_fields(body: Any) -> dict[str, Any]:
    """Token counts, finish reason, reasoning and content from an OpenAI-compatible
    body (vLLM: reasoning in `message.reasoning`) or Ollama's native /api/chat body
    (`message.thinking`, `eval_count`, `done_reason`). Absent fields stay absent."""
    body = _as_dict(body)
    usage = _as_dict(body.get("usage"))
    choice = _first_choice(body)
    message = _as_dict(choice.get("message")) or _as_dict(body.get("message"))
    reasoning = message.get("reasoning") or message.get("reasoning_content") or message.get("thinking")
    fields = {
        "prompt_tokens": _as_int(usage.get("prompt_tokens", body.get("prompt_eval_count"))),
        "completion_tokens": _as_int(usage.get("completion_tokens", body.get("eval_count"))),
        "reasoning_tokens": _as_int(_as_dict(usage.get("completion_tokens_details")).get("reasoning_tokens")),
        "cached_tokens": _as_int(_as_dict(usage.get("prompt_tokens_details")).get("cached_tokens")),
        "finish_reason": choice.get("finish_reason", body.get("done_reason")),
        "reasoning": reasoning if isinstance(reasoning, str) else None,
        "content": message.get("content") if isinstance(message.get("content"), str) else None,
    }
    return {key: value for key, value in fields.items() if value is not None}


class CallLogWriter:
    """Appends records under a lock, flushing each line so a crashed run keeps
    every call it made. Times its own work, and writes the totals to
    llm_calls_summary.json on close."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.calls = 0
        self.writer_seconds = 0.0
        self.writer_seconds_max = 0.0
        self._handle: Any = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._handle = path.open("a", encoding="utf-8")
        except OSError as exc:
            _logger.warning("LLM call log disabled, cannot open %s: %s", path, exc)

    def write(self, record: dict[str, Any]) -> None:
        start = time.perf_counter()
        with self._lock:
            if self._handle is None:
                return
            try:
                self._handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
                self._handle.flush()
            except (OSError, TypeError, ValueError) as exc:
                _logger.warning("LLM call log disabled after a write error on %s: %s", self.path, exc)
                self._handle = None
                return
            elapsed = time.perf_counter() - start
            self.calls += 1
            self.writer_seconds += elapsed
            self.writer_seconds_max = max(self.writer_seconds_max, elapsed)

    def summary(self) -> dict[str, Any]:
        return {
            "calls": self.calls,
            "bytes": self.path.stat().st_size if self.path.exists() else 0,
            "writer_seconds": round(self.writer_seconds, 6),
            "writer_ms_mean": round(1000 * self.writer_seconds / self.calls, 3) if self.calls else None,
            "writer_ms_max": round(1000 * self.writer_seconds_max, 3),
        }

    def close(self) -> None:
        with self._lock:
            if self._handle is not None:
                self._handle.close()
                self._handle = None
        try:
            (self.path.parent / CALL_LOG_SUMMARY_FILENAME).write_text(json.dumps(self.summary(), indent=2), encoding="utf-8")
        except OSError as exc:
            _logger.warning("LLM call log summary not written: %s", exc)

    def __enter__(self) -> CallLogWriter:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None,
    ) -> None:
        self.close()


class CallLoggingClient:
    """Wraps any client (real, fake, replay) and logs each call it forwards.
    Arguments are forwarded exactly as given -- never adding temperature=None or
    seed=None -- so clients whose signatures predate those parameters still work."""

    def __init__(self, inner: Any, writer: CallLogWriter, tick_source: Callable[[], int | None]) -> None:
        self._inner = inner
        self._writer = writer
        self._tick_source = tick_source

    def complete_json(self, **kwargs: Any) -> str:
        request_hash = request_sha256(
            system_prompt=kwargs["system_prompt"],
            user_prompt=kwargs["user_prompt"],
            json_schema=kwargs["json_schema"],
            max_tokens=kwargs["max_tokens"],
            think=kwargs.get("think", True),
            temperature=kwargs.get("temperature"),
            seed=kwargs.get("seed"),
        )
        record = self._open_record(request_hash, kwargs, fallback_decision_type=decision_type_for_schema(kwargs["json_schema"]))

        def call() -> str:
            result = str(self._inner.complete_json(**kwargs))
            record.setdefault("content", result)  # a client with no HTTP body to report (a fake, a replay)
            return result

        return str(self._forward(record, call))

    def count_prompt_tokens(self, **kwargs: Any) -> int:
        request_hash = request_sha256(
            system_prompt=kwargs["system_prompt"],
            user_prompt=kwargs["user_prompt"],
            json_schema=None,
            max_tokens=None,
            think=kwargs.get("think", True),
        )
        record = self._open_record(request_hash, kwargs, fallback_decision_type=None, kind="budget_probe")
        return int(self._forward(record, lambda: int(self._inner.count_prompt_tokens(**kwargs))))

    def _open_record(
        self, request_hash: str, kwargs: dict[str, Any], *, fallback_decision_type: str | None, kind: str | None = None,
    ) -> dict[str, Any]:
        context = _current_context.get()
        return {
            "call_id": llm_call_id(request_hash),
            "request_sha256": request_hash,
            "kind": kind or (context.kind if context is not None else "decision"),
            "decision_type": context.decision_type if context is not None else fallback_decision_type,
            "tick": self._tick_source(),
            "unit_ids": list(context.unit_ids) if context is not None and context.unit_ids is not None else None,
            "attempt": context.attempt if context is not None else None,
            "think": kwargs.get("think", True),
            "max_tokens": kwargs.get("max_tokens"),
            "temperature": kwargs.get("temperature"),
            "seed": kwargs.get("seed"),
        }

    def _forward(self, record: dict[str, Any], call: Callable[[], Any]) -> Any:
        record["started_at"] = time.time()
        start = time.perf_counter()
        _in_flight.record = record
        try:
            result = call()
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
            raise
        else:
            return result
        finally:
            _in_flight.record = None
            record["latency_ms"] = round(1000 * (time.perf_counter() - start), 3)
            self._writer.write(record)


@contextmanager
def call_logged(client: Any, path: Path | None, tick_source: Callable[[], int | None]) -> Iterator[Any]:
    """`client` wrapped with a log at `path`, or `client` itself when `path` is None."""
    if path is None:
        yield client
        return
    with CallLogWriter(path) as writer:
        yield CallLoggingClient(client, writer, tick_source)
