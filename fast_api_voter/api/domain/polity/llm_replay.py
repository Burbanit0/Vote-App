"""Replay client (S0.6): answers a run's LLM requests from its llm_calls.jsonl.

Given the same config and seed, a run replayed from its own call log sends the
same requests in the same order, so it gets the same answers and writes the same
journal -- without a GPU and without the model. That makes a run's decisions
reproducible after the fact whatever the server did (a sampled retry, a
batch-composition effect), and lets engine changes that should not alter
decisions be checked against a real run.

Loud by design: a request the log does not hold raises UnrecordedRequestError
instead of being answered approximately. A recorded failure is replayed as the
same failure -- a truncated generation raises LlmResponseError again, so the
engine retries exactly as it did.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from api.domain.polity.llm_call_log import CALL_LOG_FILENAME, read_calls, request_sha256
from api.domain.polity.llm_client import LlmResponseError, LlmTransportError

_REPLAYABLE_ERRORS: dict[str, type[Exception]] = {
    "LlmResponseError": LlmResponseError,
    "LlmTransportError": LlmTransportError,
}


class UnrecordedRequestError(RuntimeError):
    """The replayed run sent a request its call log does not hold (or holds fewer
    times than it was sent): the code, config or seed differ from the recorded run."""


class ReplayClient:
    def __init__(self, calls: Iterable[dict[str, Any]]) -> None:
        self._answers: dict[tuple[str, str], deque[dict[str, Any]]] = {}
        for call in calls:
            if call.get("kind") == "warm_up":
                continue  # an injected client is never warmed up, so no replay asks for these
            key = (_endpoint(call.get("kind")), str(call["request_sha256"]))
            self._answers.setdefault(key, deque()).append(call)
        self.served = 0

    @classmethod
    def from_run_dir(cls, run_dir: Path) -> ReplayClient:
        return cls(read_calls(run_dir / CALL_LOG_FILENAME))

    @property
    def unserved(self) -> int:
        """Recorded calls no request has consumed yet."""
        return sum(len(answers) for answers in self._answers.values())

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
        call = self._next("complete_json", request_hash)
        _raise_recorded_error(call)
        if not isinstance(call.get("content"), str):
            raise UnrecordedRequestError(f"call {call.get('call_id')} was recorded without content to replay")
        return str(call["content"])

    def count_prompt_tokens(self, **kwargs: Any) -> int:
        request_hash = request_sha256(
            system_prompt=kwargs["system_prompt"],
            user_prompt=kwargs["user_prompt"],
            json_schema=None,
            max_tokens=None,
            think=kwargs.get("think", True),
        )
        call = self._next("count_prompt_tokens", request_hash)
        _raise_recorded_error(call)
        if not isinstance(call.get("prompt_tokens"), int):
            raise UnrecordedRequestError(f"budget probe {call.get('call_id')} was recorded without prompt_tokens")
        return int(call["prompt_tokens"])

    def _next(self, endpoint: str, request_hash: str) -> dict[str, Any]:
        answers = self._answers.get((endpoint, request_hash))
        if not answers:
            raise UnrecordedRequestError(
                f"no recorded {endpoint} answer left for request {request_hash[:16]} -- the replayed run "
                "diverged from the recorded one (different code, config or seed)"
            )
        self.served += 1
        return answers.popleft()


def _endpoint(kind: Any) -> str:
    return "count_prompt_tokens" if kind == "budget_probe" else "complete_json"


def _raise_recorded_error(call: dict[str, Any]) -> None:
    error = call.get("error")
    if not error:
        return
    type_name, _, message = str(error).partition(": ")
    error_type = _REPLAYABLE_ERRORS.get(type_name)
    if error_type is None:
        raise UnrecordedRequestError(f"call {call.get('call_id')} failed with {error!r}, which replay cannot reproduce")
    raise error_type(message)
