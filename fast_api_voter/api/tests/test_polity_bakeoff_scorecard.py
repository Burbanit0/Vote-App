"""The bake-off scorecard and its Markdown (S2.2). See api/domain/polity/bakeoff_scorecard.py
and bakeoff_report.py. Sessions here are written by hand, so every number has a known answer."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from api.domain.polity import bakeoff_scorecard as sc
from api.domain.polity.bakeoff_cases import LOGPROB_GATE_FAMILY, Case, CaseBank, make_case
from api.domain.polity.bakeoff_report import family_summary, render_markdown
from api.domain.polity.bakeoff_runner import GATES_FILENAME, RESULTS_FILENAME, SESSION_FILENAME


def _case(family: str, decision_type: str, units: list[int], labels: dict[str, Any]) -> Case:
    return make_case(family=family, decision_type=decision_type, system_prompt=family, user_prompt=json.dumps(labels, sort_keys=True),
                     think=False, budget={"rule": "fixed", "max_tokens": 10}, unit_ids=units, labels=labels)


CANDIDACY = _case("candidacy_p500", "candidacy_considered", [0, 1, 2, 3], {"kind": "truth", "truth": {"0": 1, "1": 0, "2": 1, "3": 0}})
PRESSURE = _case("pressure_act", "pressure_action", [5, 6], {"kind": "truth", "truth": {"5": True, "6": False}, "match": "acts"})
GATE = _case(LOGPROB_GATE_FAMILY, "vote_cast", [7, 8, 9], {"kind": "truth", "truth": {"7": "blank", "8": 2, "9": 1}, "field": "blank", "value": "1", "reading": "binary"})
RESPONSE = [_case("response_sweep", "representative_response", [60 + i], {"kind": "contrast", "group": "pressure", "t": t, "units": [60 + i], "field": "stance", "value": "1"})
            for i, t in enumerate((0.0, 0.5, 1.0))]
COALITION = [_case("coalition_diagonal", "coalition_decision", [1, 2], {"kind": "contrast", "group": "join_to_decline", "t": t, "units": [unit], "field": "action", "value": "1"})
             for t, unit in ((0.0, 1), (1.0, 2))]
REACTION = [_case("reaction_scandal", "reaction_to_event", [3], {"kind": "contrast", "group": "prior_salience", "t": t, "units": [3], "field": None, "value": None})
            for t in (0.0, 1.0)]
NOMINATION = [_case("nomination_permutation", "party_nomination_choice", [0, 1],
                    {"kind": "permutation", "pair": "seed1", "rendering": rendering, "units": [0, 1], "listed": listed})
              for rendering, listed in (("original", {"0": {"1": 10, "2": 11, "3": 12}, "1": {"1": 20, "2": 21}}),
                                        ("renumbered", {"0": {"1": 12, "2": 11, "3": 10}, "1": {"1": 21, "2": 20}}))]
BANK = CaseBank(reference={"provider": "vllm", "model": "qwen3:8b", "seed": 42, "max_batch_size": 25},
                cases=(CANDIDACY, PRESSURE, GATE, *RESPONSE, *COALITION, *REACTION, *NOMINATION))


def _result(case: Case, answers: dict[str, Any], *, valid: bool = True, p: dict[str, float] | None = None, pass_name: str = "main",
            content: str | None = "c", call: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"case_id": case.case_id, "family": case.family, "decision_type": case.decision_type, "pass": pass_name, "valid": valid,
            "error": None if valid else "LlmResponseError: bad", "answers": answers if valid else {}, "probabilities": p,
            "content_sha256": content, "call": call if call is not None else {"latency_ms": 2000.0, "prompt_tokens": 100,
                                                                              "completion_tokens": 20, "reasoning_tokens": None, "finish_reason": "stop"}}


def _control_results(**overrides: Any) -> list[dict[str, Any]]:
    response_p = overrides.get("response_p", (0.12, 0.99, 1.0))
    return [
        _result(CANDIDACY, {"0": 1, "1": 1, "2": 1, "3": 0}, call={"latency_ms": 1000.0, "finish_reason": "length"}),
        _result(PRESSURE, {"5": 2, "6": 0}),
        _result(GATE, {"7": "blank", "8": 2, "9": 1}, p={"7": 0.98, "8": 0.05, "9": 0.6}),
        *(_result(case, {str(case.unit_ids[0]): 1 if p > 0.5 else 3}, p={str(case.unit_ids[0]): p}) for case, p in zip(RESPONSE, response_p)),
        _result(COALITION[0], {"1": 1, "2": 1}, p={"1": 0.99, "2": 0.97}),
        _result(COALITION[1], {"1": 1, "2": 1}, p={"1": 0.99, "2": 0.96}),
        _result(REACTION[0], {"3": [0.2, 401]}),
        _result(REACTION[1], {"3": [0.15, 401]}),
        _result(NOMINATION[0], {"0": 3, "1": 1}),
        _result(NOMINATION[1], {"0": 1, "1": 1}),
        _result(CANDIDACY, {"0": 1, "1": 1, "2": 1, "3": 1}, pass_name="rerun", content="different"),
        _result(PRESSURE, {"5": 2, "6": 0}, pass_name="rerun"),
    ]


def _session(label: str, results: list[dict[str, Any]], gates: dict[str, Any] | None = None) -> sc.Session:
    return sc.Session(label=label, metadata={"label": label, "provider": "vllm", "model": label, "bank_sha256": BANK.content_sha256},
                      gates=gates if gates is not None else {"think": {"think_true_reasoning_tokens": 300, "think_false_reasoning_tokens": 0, "passed": True},
                                                             "logprobs_available": True},
                      results=results)


def test_a_session_is_scored_per_decision_type() -> None:
    scored = sc.score_session(BANK, _session("control", _control_results()))
    types = scored["decision_types"]

    candidacy = types["candidacy_considered"]
    assert candidacy["families"]["candidacy_p500"]["accuracy"]["successes"] == 3
    assert candidacy["families"]["candidacy_p500"]["answers"] == {"0": 1, "1": 3}
    assert candidacy["cost"] == {"requests": 1, "latency_s_mean": 1.0, "prompt_tokens_mean": None, "completion_tokens_mean": None,
                                 "reasoning_tokens_mean": None, "truncated": 1}
    assert types["pressure_action"]["families"]["pressure_act"]["accuracy"]["successes"] == 2  # act 2 counts as acting

    pressure = types["representative_response"]["families"]["response_sweep"]["groups"]["pressure"]
    assert pressure["p_by_t"] == {"0.0": 0.12, "0.5": 0.99, "1.0": 1.0}
    assert (pressure["separation"], pressure["flat"], pressure["distinct_answers"]) == (pytest.approx(0.88), False, 2)
    join = types["coalition_decision"]["families"]["coalition_diagonal"]["groups"]["join_to_decline"]
    assert join["p_by_t"] == {"0.0": 0.99, "1.0": 0.96} and join["flat"] is True
    reaction = types["reaction_to_event"]["families"]["reaction_scandal"]["groups"]["prior_salience"]
    assert (reaction["p_by_t"], reaction["flat"], reaction["distinct_answers"]) == (None, None, 2)

    nomination = types["party_nomination_choice"]["families"]["nomination_permutation"]
    # party 0 follows the candidate (citizen 12, listed third then first); party 1 follows the position (first both times)
    assert nomination["same_candidate"]["successes"] == 1 and nomination["same_candidate"]["trials"] == 2
    assert nomination["same_listed_position"]["successes"] == 1
    assert nomination["last_listed_position"]["successes"] == 1 and nomination["last_listed_position"]["trials"] == 4

    assert scored["gates"]["logprob"] == {"units": 3, "aligned": 3, "threshold_call_correct": 2, "separation": pytest.approx(0.98 - 0.325),
                                          "passed": True}
    assert scored["noise_floor"]["reruns"] == 2
    assert scored["noise_floor"]["identical_output"]["successes"] == 1  # candidacy's re-run differs, pressure's does not
    assert scored["noise_floor"]["unit_agreement"]["successes"] == 5 and scored["bank_matches"] is True  # 3 of 4 candidacy units, 2 of 2


def test_invalid_answers_count_as_wrong_and_unread_gates_are_unmeasured() -> None:
    results = [_result(CANDIDACY, {}, valid=False), _result(GATE, {"7": "blank", "8": 2, "9": 1})]
    scored = sc.score_session(BANK, _session("s", results, gates={}))
    assert scored["decision_types"]["candidacy_considered"]["validity"]["successes"] == 0
    assert scored["decision_types"]["candidacy_considered"]["families"]["candidacy_p500"]["accuracy"]["successes"] == 0
    assert scored["gates"]["logprob"]["passed"] is None and scored["gates"]["think"] is None


def test_paired_tests_compare_every_model_with_the_control_and_all_of_them_together() -> None:
    control = _session("control", _control_results())
    assert sc.compare_sessions(BANK, [control], "control") == {}

    worse = _control_results()
    worse[0] = _result(CANDIDACY, {"0": 0, "1": 1, "2": 0, "3": 1})
    two = sc.compare_sessions(BANK, [control, _session("worse", worse)], "control")
    accuracy = two["accuracy/candidacy_p500: worse vs control"]
    assert (accuracy["first_only"], accuracy["second_only"], accuracy["n"]) == (0, 3, 4)
    assert accuracy["p_value"] == pytest.approx(0.25) and accuracy["p_holm"] >= accuracy["p_value"]
    assert "validity/candidacy_considered: worse vs control" in two

    missing_pressure = [r for r in _control_results() if r["family"] != "pressure_act"]
    sessions = [control, _session("worse", worse), _session("partial", missing_pressure)]
    three = sc.compare_sessions(BANK, sessions, "control")
    assert three["accuracy/candidacy_p500: all models"]["test"] == "cochrans_q"
    assert not any(name.startswith("accuracy/pressure_act") for name in three)  # only cases every model answered are paired
    assert "Cochran's Q = " in render_markdown(sc.scorecard(BANK, sessions, control="control"))


def _acceptance_session(declared: int, correct: int, response_p: tuple[float, ...]) -> dict[str, Any]:
    scored = sc.score_session(BANK, _session("control", _control_results(response_p=response_p)))
    candidacy = scored["decision_types"]["candidacy_considered"]["families"]["candidacy_p500"]
    candidacy["answers"] = {"0": 500 - declared, "1": declared}
    candidacy["accuracy"] = {"successes": correct, "trials": 500}
    return scored


def test_acceptance_reads_the_known_qwen_numbers_on_the_control() -> None:
    passing = sc.acceptance(_acceptance_session(202, 318, (0.12, 0.99, 1.0)))
    assert [c["passed"] for c in passing] == [True, True, True, True]
    failing = sc.acceptance(_acceptance_session(390, 208, (0.9, 0.5, 1.0)))
    assert [c["passed"] for c in failing] == [False, False, True, False]

    unmeasured = sc.score_session(BANK, _session("control", [_result(c, {str(c.unit_ids[0]): 1}) for c in RESPONSE]))
    assert sc.acceptance(unmeasured) == [{"check": "representative_response flat under pressure, silent without",
                                          "expected": "spread(t>0) < 0.10 and P(t=0) < 0.5", "observed": None, "passed": None}]


def test_sessions_load_from_disk_and_the_scorecard_renders(tmp_path: Path) -> None:
    for label, results in (("control", _control_results()), ("other", _control_results())):
        directory = tmp_path / label
        directory.mkdir()
        (directory / RESULTS_FILENAME).write_text("\n".join(json.dumps(r) for r in results) + "\n")
        (directory / GATES_FILENAME).write_text(json.dumps({"logprobs_available": True}))
        if label == "control":
            (directory / SESSION_FILENAME).write_text(json.dumps({"label": "control", "bank_sha256": BANK.content_sha256}))
    (tmp_path / "not-a-session").mkdir()

    sessions = sc.discover_sessions(tmp_path)
    assert [s.label for s in sessions] == ["control", "other"]
    card = sc.scorecard(BANK, sessions)
    assert card["control"] == "control" and card["comparisons"] and card["acceptance"]

    markdown = render_markdown(card)
    assert markdown.startswith("# Model bake-off scorecard")
    assert "## representative_response" in markdown and "McNemar exact" in markdown and "Cochran" not in markdown
    assert "| control | ?/? | – | yes | not run | yes: 3/3 aligned, 2 correct, separation +0.655 |" in markdown
    lonely = render_markdown(sc.scorecard(BANK, sessions[:1]))
    assert "One session: nothing to compare." in lonely


def test_family_summaries_cover_every_kind() -> None:
    scored = sc.score_session(BANK, _session("s", _control_results()))
    families = {f: fs for t in scored["decision_types"].values() for f, fs in t["families"].items()}
    assert family_summary("candidacy_p500", families["candidacy_p500"]).startswith("candidacy_p500: accuracy 3/4 = 75.0%")
    assert "separation +0.880 (moves)" in family_summary("response_sweep", families["response_sweep"])
    assert family_summary("reaction_scandal", families["reaction_scandal"]) == "reaction_scandal/prior_salience: 2 distinct answer(s) over 2 levels"
    assert "same candidate 1/2" in family_summary("nomination_permutation", families["nomination_permutation"])
    card = sc.scorecard(BANK, [_session("s", _control_results(), gates={})])
    assert "| s | vllm/s | – | yes | not run | yes: 3/3" in render_markdown(card)
    empty = sc.scorecard(BANK, [_session("e", [], gates={"think": {"think_true_reasoning_tokens": 1, "think_false_reasoning_tokens": 0, "passed": True}})])
    assert "yes (on 1, off 0) | unmeasured |" in render_markdown(empty)
