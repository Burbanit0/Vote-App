"""The bake-off runner (S2.2). See api/domain/polity/bakeoff_runner.py."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from api.domain.polity import bakeoff_runner as br
from api.domain.polity.bakeoff_cases import LOGPROB_GATE_FAMILY, CaseBank
from api.domain.polity.llm_call_log import CALL_LOG_FILENAME, read_calls
from api.domain.polity.llm_client import TokenLogprob
from api.domain.polity.llm_replay import ReplayClient
from api.tests.polity_bakeoff_fixtures import CHOSEN_DIGIT_PROBABILITY, LogprobFakeClient, reference_bank, reference_config
from api.tests.test_polity_run_simulation import _ElectingFakeLlmClient

SMALL_FAMILIES = ("response_sweep", "candidacy_p500")


def _small_bank(*families: str) -> CaseBank:
    bank = reference_bank()
    keep = {*families, LOGPROB_GATE_FAMILY}
    return CaseBank(reference=bank.reference, cases=tuple(c for c in bank.cases if c.family in keep))


def _run(bank: CaseBank, client: Any, session_dir: Path, **kwargs: Any) -> list[dict[str, Any]]:
    br.run_session(bank, client, reference_config(), session_dir, metadata={"label": session_dir.name}, **kwargs)
    return br.read_results(session_dir / br.RESULTS_FILENAME)


def test_a_session_asks_every_case_reads_logprobs_and_reruns_a_tenth(tmp_path: Path) -> None:
    bank = reference_bank()
    results = _run(bank, LogprobFakeClient(), tmp_path / "fake")

    main = [r for r in results if r["pass"] == "main"]
    reruns = [r for r in results if r["pass"] == "rerun"]
    scored = [c for c in bank.cases if c.family != LOGPROB_GATE_FAMILY]
    assert len(main) == len(bank.cases) and all(r["valid"] and r["error"] is None for r in main)
    assert [r["case_id"] for r in reruns] == [c.case_id for c in br.rerun_selection(scored, br.DEFAULT_RERUN_FRACTION)]

    gates = json.loads((tmp_path / "fake" / br.GATES_FILENAME).read_text())
    assert gates["logprobs_available"] is True and gates["logprob_aligned"] is True
    assert gates["think"] == {"think_true_reasoning_tokens": None, "think_false_reasoning_tokens": None, "passed": None}
    response = next(r for r in main if r["family"] == "response_sweep")
    assert list(response["probabilities"].values()) == [CHOSEN_DIGIT_PROBABILITY]  # the fake concedes: P(stance=1) read back
    chamber = next(r for r in main if r["family"] == "chamber_poles")
    assert set(chamber["probabilities"].values()) == {CHOSEN_DIGIT_PROBABILITY}  # the fake answers 702: the "2" at offset 2
    assert json.loads((tmp_path / "fake" / br.SESSION_FILENAME).read_text())["bank_sha256"] == bank.content_sha256

    logged = read_calls(tmp_path / "fake" / CALL_LOG_FILENAME)
    assert {r["kind"] for r in logged} == {"warm_up", "decision", "budget_probe"}
    assert all(r.get("content") for r in logged if r["kind"] == "decision")
    assert response["call"]["call_id"] and response["content_sha256"]


def test_a_session_resumes_without_asking_a_case_twice(tmp_path: Path) -> None:
    bank = _small_bank(*SMALL_FAMILIES)
    client = LogprobFakeClient()
    first = _run(bank, client, tmp_path / "s", warm_up=False)
    asked = client.calls
    again = _run(bank, client, tmp_path / "s", warm_up=False)
    assert client.calls == asked and len(again) == len(first)


class _MisalignedLogprobs(_ElectingFakeLlmClient):  # type: ignore[misc]
    def complete_json_with_logprobs(self, **kwargs: Any) -> tuple[str, list[TokenLogprob]]:
        return str(self.complete_json(**kwargs)), [TokenLogprob(token="?", logprob=0.0, alternatives={"?": 0.0})]


def test_logprobs_that_do_not_align_on_the_gate_are_not_read_anywhere(tmp_path: Path) -> None:
    results = _run(_small_bank(*SMALL_FAMILIES), _MisalignedLogprobs(), tmp_path / "s", warm_up=False)
    gate = [r for r in results if r["family"] == LOGPROB_GATE_FAMILY]
    assert all(r["valid"] and r["error"].startswith("LogprobAlignmentError") for r in gate)
    assert json.loads((tmp_path / "s" / br.GATES_FILENAME).read_text())["logprob_aligned"] is False
    assert all(r["probabilities"] is None and r["error"] is None for r in results if r["family"] == "response_sweep")


class _Garbage(_ElectingFakeLlmClient):  # type: ignore[misc]
    def complete_json(self, **kwargs: Any) -> str:
        return "not a decision batch"


def test_an_answer_production_would_reject_is_an_invalid_result_not_a_crash(tmp_path: Path) -> None:
    results = _run(_small_bank("candidacy_p500"), _Garbage(), tmp_path / "s", warm_up=False, rerun_fraction=0.0)
    assert results and all(not r["valid"] and r["error"].startswith("LlmResponseError") and r["answers"] == {} for r in results)
    assert json.loads((tmp_path / "s" / br.GATES_FILENAME).read_text()) == {"logprobs_available": False, "logprob_aligned": None}


def test_a_session_replayed_from_its_call_log_gets_the_same_answers(tmp_path: Path) -> None:
    bank = _small_bank(*SMALL_FAMILIES)
    recorded = _run(bank, _ElectingFakeLlmClient(), tmp_path / "live", warm_up=False, rerun_fraction=0.0)
    partial = CaseBank(reference=bank.reference, cases=bank.cases[:-1])
    _run(partial, _ElectingFakeLlmClient(), tmp_path / "partial", warm_up=False, rerun_fraction=0.0)

    replayed = _run(bank, ReplayClient(read_calls(tmp_path / "partial" / CALL_LOG_FILENAME)), tmp_path / "replay",
                    warm_up=False, rerun_fraction=0.0)
    answers = {r["case_id"]: r["answers"] for r in recorded}
    assert all(r["answers"] == answers[r["case_id"]] for r in replayed[:-1])
    assert not replayed[-1]["valid"] and replayed[-1]["error"].startswith("UnrecordedRequestError")


def test_the_thinking_gate_reads_reasoning_tokens_off_the_warm_up_calls() -> None:
    def warm_ups(on: int | None, off: int | None) -> list[dict[str, Any]]:
        return [{"kind": "warm_up", "think": True, "reasoning_tokens": on}, {"kind": "warm_up", "think": False, "reasoning_tokens": off},
                {"kind": "decision", "think": False, "reasoning_tokens": 5}]

    assert br.think_gate(warm_ups(340, 0))["passed"] is True
    assert br.think_gate(warm_ups(340, 12))["passed"] is False
    assert br.think_gate(warm_ups(0, 0))["passed"] is False
    assert br.think_gate(warm_ups(None, 0))["passed"] is None


def test_the_rerun_tenth_is_fixed_by_case_id() -> None:
    cases = list(reference_bank().cases)
    chosen = br.rerun_selection(cases, 0.1)
    assert chosen == sorted(cases, key=lambda c: c.case_id)[::10]
    assert br.rerun_selection(cases, 0.0) == [] and br.rerun_selection([], 0.1) == []
    assert br.gate_aligned([], cases) is None
