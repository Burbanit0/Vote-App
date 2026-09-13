"""Runs one model through the bake-off (S2.2): warm-up and the thinking gate, the
logprob alignment gate, every case in the bank, then a re-run of a tenth of them.

Everything the model returns lands in the session directory: `llm_calls.jsonl` (the
S0.5 call log, so time attribution and replay work on a bake-off session as on a run),
`results.jsonl` (one line per answered case: validity, each unit's answer, and the
probability read off the logprobs where the case names a field), and `gates.json`.
Scoring is `bakeoff_scorecard`'s job; this module only asks and records.

A session resumes: cases already in `results.jsonl` are not asked again.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any

from api.domain.polity.bakeoff_bank import LOGPROB_GATE_FAMILY, Case, CaseBank
from api.domain.polity.bakeoff_cases import resolve_max_tokens
from api.domain.polity.bakeoff_controls import canonical_content
from api.domain.polity.config import PolityConfig
from api.domain.polity.llm_call_log import CALL_LOG_FILENAME, CallLoggingClient, CallLogWriter, call_context
from api.domain.polity.llm_client import (
    LlmClientProtocol,
    LlmResponseError,
    decode_candidacy_batch,
    decode_chamber_batch,
    decode_coalition_batch,
    decode_party_nomination_batch,
    decode_positioning_batch,
    decode_pressure_batch,
    decode_reaction_batch,
    decode_response_batch,
    decode_vote_batch,
)
from api.domain.polity.llm_logprob_instrumentation import (
    LogprobAlignmentError,
    binary_probability,
    candidate_probability,
    locate_decision_field_logprobs,
)
from api.domain.polity.llm_behavior_engine import truncation_limit
from api.domain.polity.llm_replay import UnrecordedRequestError
from api.domain.polity.llm_schemas import vote_cast_json_schema
from api.domain.polity.run_polity_simulation import _warm_up_llm_client

RESULTS_FILENAME = "results.jsonl"
GATES_FILENAME = "gates.json"
SESSION_FILENAME = "session.json"
DEFAULT_RERUN_FRACTION = 0.1

_DECODERS: dict[str, Callable[[str, Sequence[int]], Sequence[Any]]] = {
    "vote_cast": decode_vote_batch,
    "candidacy_considered": decode_candidacy_batch,
    "party_nomination_choice": decode_party_nomination_batch,
    "campaign_positioning": decode_positioning_batch,
    "representative_response": decode_response_batch,
    "pressure_action": decode_pressure_batch,
    "reaction_to_event": decode_reaction_batch,
    "chamber_deliberation": decode_chamber_batch,
    "coalition_decision": decode_coalition_batch,
}

_PARTY_UNITS = frozenset({"party_nomination_choice", "coalition_decision"})


def _vote_grammar_schema(case: Case, schema: dict[str, Any]) -> dict[str, Any]:
    """S1.2's grammar for a vote_cast case, bounded by its own field's ranking limit; any
    other case keeps the bank's schema."""
    if case.decision_type != "vote_cast":
        return schema
    candidates = len(json.loads(case.user_prompt)["candidates"])
    limit = truncation_limit(candidates)
    return vote_cast_json_schema(limit if limit is not None else candidates)


ARMS: dict[str, Callable[[Case, dict[str, Any]], dict[str, Any]]] = {
    "vote_grammar": _vote_grammar_schema,
}
"""Schema arms for an A/B on the same frozen cases: a session run with an arm sends each
case the arm's schema instead of the bank's. Two sessions of one model, with and without
an arm, are the A/B the scorecard's paired tests compare."""


def _vote_answer(d: Any) -> Any:
    return "blank" if d.blank else (d.ranking[0] if d.ranking else None)


def _shifts(d: Any) -> list[list[float]]:
    return sorted([s.dimension, s.delta] for s in d.shifts)


_ANSWERS: dict[str, Callable[[Any], Any]] = {
    "vote_cast": _vote_answer,
    "candidacy_considered": lambda d: d.outcome,
    "party_nomination_choice": lambda d: d.winner_position,
    "campaign_positioning": lambda d: [d.motif, _shifts(d)],
    "representative_response": lambda d: d.stance,
    "pressure_action": lambda d: d.act,
    "reaction_to_event": lambda d: [d.salience_delta, d.motif],
    "chamber_deliberation": lambda d: [d.motif, len(d.shifts)],
    "coalition_decision": lambda d: d.action,
}


def unit_key(decision_type: str) -> str:
    return "party_id" if decision_type in _PARTY_UNITS else "cid"


def decode_answers(case: Case, content: str) -> dict[str, Any]:
    """Each unit's answer, keyed by its id as a string, in canonical codes (a code-permuted
    case's answer is mapped back first). Raises LlmResponseError when the content is not a
    valid batch for the case's units -- exactly what production rejects."""
    decisions = _DECODERS[case.decision_type](canonical_content(case, content), list(case.unit_ids))
    key = unit_key(case.decision_type)
    extract = _ANSWERS[case.decision_type]
    return {str(getattr(d, key)): extract(d) for d in decisions}


def read_probabilities(case: Case, content: str, tokens: Sequence[Any]) -> dict[str, float]:
    """P(labels["value"]) at labels["field"] for each unit. Raises LogprobAlignmentError
    when the field's tokens cannot be located."""
    labels = case.labels
    probes = locate_decision_field_logprobs(
        content, tokens, field=labels["field"], cid_field=unit_key(case.decision_type),
        value_char_offset=int(labels.get("value_char_offset", 0)),
    )
    if labels.get("reading") == "binary":
        return {str(p.cid): binary_probability(p.token, true_value="1", false_value="0") for p in probes}
    return {str(p.cid): candidate_probability(p.token, labels["value"]) for p in probes}


class RecordingWriter(CallLogWriter):
    """The call log, also kept in memory so each result can carry its own call's cost."""

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.records: list[dict[str, Any]] = []

    def write(self, record: dict[str, Any]) -> None:
        super().write(record)
        self.records.append(record)

    def __enter__(self) -> RecordingWriter:
        return self


_CALL_FIELDS = ("call_id", "request_sha256", "latency_ms", "prompt_tokens", "completion_tokens",
                "reasoning_tokens", "cached_tokens", "finish_reason")


def _call_summary(record: dict[str, Any] | None) -> dict[str, Any]:
    return {key: record.get(key) for key in _CALL_FIELDS} if record is not None else {}


def _ask(client: Any, case: Case, config: PolityConfig, schema: dict[str, Any], use_logprobs: bool) -> tuple[str, Any]:
    max_tokens = resolve_max_tokens(case, client, config)
    request = {"system_prompt": case.system_prompt, "user_prompt": case.user_prompt, "json_schema": schema,
               "max_tokens": max_tokens, "think": case.think}
    if use_logprobs:
        content, tokens = client.complete_json_with_logprobs(**request)
        return str(content), tokens
    return str(client.complete_json(**request)), None


def _content_sha256(content: str | None) -> str | None:
    return hashlib.sha256(content.encode("utf-8")).hexdigest() if content is not None else None


def run_case(
    case: Case, client: Any, writer: RecordingWriter, config: PolityConfig, schema: dict[str, Any],
    *, pass_name: str, use_logprobs: bool,
) -> dict[str, Any]:
    """Ask one case and record what came back. A response the engine would reject is a
    result (invalid), not an error; a request a replayed log does not hold is recorded too."""
    result: dict[str, Any] = {"case_id": case.case_id, "family": case.family, "decision_type": case.decision_type,
                              "pass": pass_name, "valid": False, "error": None, "answers": {}, "probabilities": None}
    content: str | None = None
    first_record = len(writer.records)
    try:
        with call_context(kind="decision", decision_type=case.decision_type, unit_ids=case.unit_ids, attempt=0):
            content, tokens = _ask(client, case, config, schema, use_logprobs)
        result["answers"] = decode_answers(case, content)
        result["valid"] = True
        if tokens is not None and case.labels.get("value") is not None:
            result["probabilities"] = read_probabilities(case, content, tokens)
    except (LlmResponseError, UnrecordedRequestError, LogprobAlignmentError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["content_sha256"] = _content_sha256(content)
    decision_calls = [r for r in writer.records[first_record:] if r.get("kind") == "decision"]
    result["call"] = _call_summary(decision_calls[-1] if decision_calls else None)
    return result


def rerun_selection(cases: Sequence[Case], fraction: float) -> list[Case]:
    """A fixed, content-chosen subset: every k-th case by id, k = 1/fraction, at least one."""
    if not cases or fraction <= 0:
        return []
    step = max(1, round(1 / fraction))
    return sorted(cases, key=lambda c: c.case_id)[::step]


def think_gate(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """think=False must produce no reasoning tokens and think=True some, read off the
    warm-up calls. None where the server did not report reasoning tokens."""
    by_think = {r.get("think"): r.get("reasoning_tokens") for r in records if r.get("kind") == "warm_up"}
    on, off = by_think.get(True), by_think.get(False)
    passed = None if on is None or off is None else bool(off == 0 and on > 0)
    return {"think_true_reasoning_tokens": on, "think_false_reasoning_tokens": off, "passed": passed}


def read_results(results_path: Path) -> list[dict[str, Any]]:
    if not results_path.is_file():
        return []
    return [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _append(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def gate_aligned(results: Sequence[dict[str, Any]], cases: Sequence[Case]) -> bool | None:
    """Whether every gate unit got a probability; None before the gate has run."""
    gate_results = [r for r in results if r["family"] == LOGPROB_GATE_FAMILY and r["pass"] == "main"]
    if not gate_results:
        return None
    units = sum(len(c.unit_ids) for c in cases)
    return sum(len(r["probabilities"] or {}) for r in gate_results) == units


def schema_resolver(bank: CaseBank, arm: str | None) -> Callable[[Case], dict[str, Any]]:
    """The schema each case is sent with: the bank's, or the arm's."""
    if arm is None:
        return lambda case: bank.schemas[case.decision_type]
    schema_arm = ARMS[arm]
    return lambda case: schema_arm(case, bank.schemas[case.decision_type])


def run_session(
    bank: CaseBank,
    client: LlmClientProtocol,
    config: PolityConfig,
    session_dir: Path,
    *,
    metadata: dict[str, Any],
    families: Iterable[str] | None = None,
    warm_up: bool = True,
    rerun_fraction: float = DEFAULT_RERUN_FRACTION,
    arm: str | None = None,
) -> Path:
    """One model's session. `client` is the model's own (or a replay); `config.llm`
    names the model, so token budgets follow its profile. `arm` names an entry of ARMS."""
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / SESSION_FILENAME).write_text(
        json.dumps({**metadata, "bank_sha256": bank.content_sha256, "arm": arm}, indent=2, sort_keys=True)
    )
    schema_for = schema_resolver(bank, arm)

    results_path = session_dir / RESULTS_FILENAME
    done = {(r["case_id"], r["pass"]) for r in read_results(results_path)}
    logprobs = callable(getattr(client, "complete_json_with_logprobs", None))
    selected = set(bank.families() if families is None else families) | {LOGPROB_GATE_FAMILY}
    gate_cases = [c for c in bank.cases if c.family == LOGPROB_GATE_FAMILY]
    cases = [c for c in bank.cases if c.family in selected and c.family != LOGPROB_GATE_FAMILY]

    with RecordingWriter(session_dir / CALL_LOG_FILENAME) as writer:
        logged = CallLoggingClient(client, writer, tick_source=lambda: None)
        gates: dict[str, Any] = {"logprobs_available": logprobs}
        if warm_up:
            _warm_up_llm_client(logged)
            gates["think"] = think_gate(writer.records)

        def ask_all(batch: Sequence[Case], pass_name: str, use_logprobs: bool) -> list[dict[str, Any]]:
            answered = []
            for case in batch:
                if (case.case_id, pass_name) in done:
                    continue
                result = run_case(case, logged, writer, config, schema_for(case), pass_name=pass_name, use_logprobs=use_logprobs)
                _append(results_path, result)
                answered.append(result)
            return answered

        ask_all(gate_cases, "main", logprobs)
        gates["logprob_aligned"] = gate_aligned(read_results(results_path), gate_cases) if logprobs else None
        use_logprobs = bool(gates["logprob_aligned"])
        ask_all(cases, "main", use_logprobs)
        ask_all(rerun_selection(cases, rerun_fraction), "rerun", use_logprobs)
    (session_dir / GATES_FILENAME).write_text(json.dumps(gates, indent=2, sort_keys=True))
    return session_dir
