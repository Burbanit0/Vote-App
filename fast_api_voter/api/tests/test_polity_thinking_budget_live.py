"""scripts/thinking_budget_live.py: the sample, the arms, the scoring and the pre-registered verdict, with a fake model."""

from __future__ import annotations

import importlib.util
import json
import random
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx
import pytest

from api.domain.polity.llm_call_log import CALL_LOG_FILENAME, PROMPT_LOG_FILENAME, PromptLogWriter, record_http_response

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def _load() -> ModuleType:
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("thinking_budget_live", SCRIPTS / "thinking_budget_live.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["thinking_budget_live"] = module
    spec.loader.exec_module(module)
    return module


tb = _load()

# voter 1: candidate 2 is the nearest acceptable; voter 2: nobody acceptable (the rule says blank); voter 3: candidate 1
VOTERS = [{"cid": 1, "distances": [0.5, 0.2], "blank_threshold": 0.4}, {"cid": 2, "distances": [0.9, 0.8], "blank_threshold": 0.4},
          {"cid": 3, "distances": [0.1, 0.3], "blank_threshold": 0.4}]
RIGHT = {"decisions": [{"cid": 1, "blank": 0, "ranking": [2]}, {"cid": 2, "blank": 1, "ranking": []}, {"cid": 3, "blank": 0, "ranking": [1]}]}
BLANKED = {"decisions": [{"cid": 1, "blank": 1, "ranking": []}, {"cid": 2, "blank": 1, "ranking": []}, {"cid": 3, "blank": 0, "ranking": [2]}]}
CHAMBER = {"decisions": [{"cid": 1, "motif": 702, "shifts": [{"dimension": 0, "delta": 0.01}]}, {"cid": 2, "motif": 701, "shifts": []}]}


def _case(case_id: int, decision_type: str = "vote_cast", **extra: Any) -> dict[str, Any]:
    user = json.dumps({"voters": VOTERS}) if decision_type == "vote_cast" else "{}"
    return {"case_id": case_id, "run": "r", "call_id": f"c{case_id}", "decision_type": decision_type, "units": [1, 2, 3], "system": "rule",
            "user": user, "schema": {"title": "x"}, "max_tokens": 5000, "think": True, "temperature": None, "seed": None,
            "original_budget": 2048, "original_reasoning_tokens": 2048, "original_at_budget": True, **extra}


class FakeModel:
    """Answers by the budget it is sent: cut at 2048 (blanks against the rule), right at 4096 and above."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def complete_json(self, **kwargs: Any) -> str:
        self.calls.append(kwargs)
        budget = (kwargs.get("extra_body") or {}).get("thinking_token_budget")
        vote = kwargs["user_prompt"] != "{}"
        content = json.dumps((BLANKED if budget == 2048 else RIGHT) if vote else CHAMBER)
        reasoning = {2048: 2048, 4096: 3000, 8192: 3200, None: 5000}[budget]
        body = {"choices": [{"finish_reason": "stop", "message": {"content": content, "reasoning": "r"}}],
                "usage": {"completion_tokens": reasoning + 50, "completion_tokens_details": {"reasoning_tokens": reasoning}}}
        record_http_response(httpx.Response(200, json=body))
        return content


def _run_all(out: Path, cases: list[dict[str, Any]], model: FakeModel) -> None:
    (out / tb.CASES_FILE).write_text("".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8")
    for budget in tb.ARMS:
        tb.run_arm(model, cases, budget, out / f"arm-{tb.arm_name(budget)}", workers=2)


def test_the_vote_outcomes_follow_the_rule_per_voter() -> None:
    case = _case(0)
    assert tb.vote_outcomes(case, json.dumps(RIGHT)) == {1: (False, False), 3: (False, False)}  # voter 2: the rule says blank
    assert tb.vote_outcomes(case, json.dumps(BLANKED)) == {1: (True, True), 3: (False, True)}  # blank against the rule; wrong first choice
    assert tb.vote_outcomes(case, "{oops") == {1: (True, True), 3: (True, True)}  # an answer that does not parse is wrong everywhere
    assert tb.vote_outcomes(case, None) == tb.vote_outcomes(case, "[]")


def test_the_chamber_outcome_counts_units_with_a_shift() -> None:
    assert tb.chamber_outcome(json.dumps(CHAMBER)) == (2, 1)
    assert tb.chamber_outcome("{oops") is None and tb.chamber_outcome(json.dumps({"decisions": "x"})) is None


def test_the_arms_send_the_logged_bytes_with_only_the_budget_changed(tmp_path: Path) -> None:
    model = FakeModel()
    case = _case(0, temperature=0.3, seed=7)
    tb.run_arm(model, [case], 4096, tmp_path / "a", workers=1)
    tb.run_arm(model, [_case(1)], None, tmp_path / "b", workers=1)
    sent = model.calls
    assert sent[0]["extra_body"] == {"thinking_token_budget": 4096} and sent[-1]["extra_body"] is None
    assert (sent[0]["temperature"], sent[0]["seed"]) == (0.3, 7) and "temperature" not in sent[-1] and "seed" not in sent[-1]
    assert all(call["system_prompt"] == "rule" and call["max_tokens"] == 5000 and call["think"] for call in sent)


def test_an_arm_resumes_and_repeats_votes_twice_and_chamber_three_times(tmp_path: Path) -> None:
    model = FakeModel()
    cases = [_case(0), _case(1, "chamber_deliberation")]
    tb.run_arm(model, cases, 2048, tmp_path, workers=2)
    assert len(model.calls) == 2 + 3
    tb.run_arm(model, cases, 2048, tmp_path, workers=2)  # everything is in the call log: nothing is sent again
    assert len(model.calls) == 5
    assert {(c["unit_ids"][0], c["attempt"]) for c in tb.read_calls(tmp_path / CALL_LOG_FILENAME)} == {(0, 0), (0, 1), (1, 0), (1, 1), (1, 2)}


def test_an_answer_the_client_rejects_is_logged_and_scored_wrong(tmp_path: Path) -> None:
    class Rejecting(FakeModel):
        def complete_json(self, **kwargs: Any) -> str:
            raise tb.LlmResponseError("no valid JSON")

    cases = [_case(0)]
    tb.run_arm(Rejecting(), cases, 2048, tmp_path, workers=1)
    arm = tb.load_arm(tmp_path.parent, None) or {}
    logged = {(c["unit_ids"][0], c["attempt"]): c for c in tb.read_calls(tmp_path / CALL_LOG_FILENAME)}
    assert len(logged) == 2 and all(c.get("error") for c in logged.values()) and arm == {}
    table = tb.unit_table(cases, logged)
    assert table and all(outcome == (True, True) for outcome in table.values())


def test_mcnemar_pairs_units_and_the_noise_floor_compares_repeats() -> None:
    base = {("a", 0, 1): (True, True), ("a", 0, 2): (True, False), ("a", 0, 3): (False, False), ("a", 0, 4): (True, True)}
    other = {("a", 0, 1): (False, False), ("a", 0, 2): (False, False), ("a", 0, 3): (False, False), ("a", 0, 9): (True, True)}
    fixed, broken, p = tb.mcnemar(base, other, 1)
    assert (fixed, broken, p) == (1, 0, 1.0)  # one discordant pair, exact two-sided p = 1.0
    fixed, broken, p = tb.mcnemar(base, other, 0)
    assert (fixed, broken) == (2, 0) and p == pytest.approx(0.5)
    assert tb.mcnemar({}, {}, 0) == (0, 0, 1.0)
    cases = [_case(0)]
    calls = {(0, 0): {"content": json.dumps(RIGHT)}, (0, 1): {"content": json.dumps(BLANKED)}}
    assert tb.noise_floor(cases, calls) == pytest.approx(1.0)  # both units differ between the two repeats
    assert tb.noise_floor(cases, {(0, 0): {"content": json.dumps(RIGHT)}}) is None


def test_the_verdict_is_the_smallest_budget_within_two_points_of_none_at_lower_cost() -> None:
    reasoning = {2048: 2048.0, 4096: 3000.0, 8192: 3200.0, None: 5000.0}
    assert tb.verdict({2048: 0.30, 4096: 0.05, 8192: 0.04, None: 0.04}, reasoning).startswith("candidate budget 4096")
    assert tb.verdict({2048: 0.30, 4096: 0.20, 8192: 0.04, None: 0.04}, reasoning).startswith("candidate budget 8192")
    assert tb.verdict({2048: 0.05, 4096: 0.05, 8192: 0.04, None: 0.04}, reasoning).startswith("keep 2048")
    assert tb.verdict({2048: 0.30, 4096: 0.20, 8192: 0.10, None: 0.05}, reasoning).startswith("no tested budget")
    assert tb.verdict({2048: 0.05, 4096: 0.05, 8192: 0.04, None: 0.04}, {2048: 9000.0, 4096: 6000.0, 8192: 5500.0, None: 5000.0}).startswith("no tested budget")  # none is the cheapest


def test_sampling_draws_the_at_budget_calls_with_their_prompts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run = tmp_path / "run"
    run.mkdir()
    writer = PromptLogWriter(run / PROMPT_LOG_FILENAME)
    calls = []
    for i in range(6):
        cut = i < 4
        call_id = f"v{i}"
        writer.write(call_id, system_prompt="rule", user_prompt=json.dumps({"voters": VOTERS}), json_schema={"title": "t"})
        calls.append({"call_id": call_id, "kind": "decision", "decision_type": "vote_cast", "tick": 0, "attempt": 0, "unit_ids": [1],
                      "think": True, "max_tokens": 9, "temperature": None, "seed": None, "reasoning_tokens": 2048 if cut else 100,
                      "extra_body": {"thinking_token_budget": 2048}})
    writer.write("noprompt", system_prompt="rule", user_prompt="{}", json_schema=None)
    calls.append({**calls[0], "call_id": "missing"})  # a call whose prompt was never kept
    (run / CALL_LOG_FILENAME).write_text("".join(json.dumps(c) + "\n" for c in calls), encoding="utf-8")
    writer.close()
    monkeypatch.setattr(tb, "VOTE_AT", 2)
    monkeypatch.setattr(tb, "VOTE_UNDER", 1)
    monkeypatch.setattr(tb, "CHAMBER_AT", 1)
    cases = tb.sample_cases("p500-x", run, random.Random(1))
    assert sorted(c["original_at_budget"] for c in cases) == [False, True, True]
    assert all(c["system"] == "rule" and c["schema"] == {"title": "t"} and c["original_budget"] == 2048 for c in cases)
    assert len(tb.sample_cases("baseline", run, random.Random(1))) == 6  # the baseline keeps every vote call that has a prompt


def test_the_whole_experiment_on_a_fake_model_reaches_the_pre_registered_verdict(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cases = [_case(i) for i in range(6)] + [_case(10, "chamber_deliberation"), _case(11, "vote_cast", original_at_budget=False, original_reasoning_tokens=100)]
    _run_all(tmp_path, cases, FakeModel())
    assert tb.report(tmp_path) == 0
    text = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "candidate budget 4096" in text
    assert "| 2048 | " in text and "| none | " in text and "## Chamber" in text and "## Cases that ended under the budget" in text
    assert "rejected" in text  # 2048 blanks every time: the exact test is significant after Holm across the six
    assert capsys.readouterr().out.startswith("# Thinking budget on live prompts")


def test_a_noisy_2048_arm_leaves_the_verdict_unresolved(tmp_path: Path) -> None:
    class Flaky(FakeModel):
        def complete_json(self, **kwargs: Any) -> str:
            self.calls.append(kwargs)
            content = json.dumps(RIGHT if len(self.calls) % 2 else BLANKED)  # alternates between repeats
            record_http_response(httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": content}}]}))
            return content

    cases = [_case(i) for i in range(3)]
    (tmp_path / tb.CASES_FILE).write_text("".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8")
    for budget in tb.ARMS:
        tb.run_arm(Flaky(), cases, budget, tmp_path / f"arm-{tb.arm_name(budget)}", workers=1)
    tb.report(tmp_path)
    assert "unresolved: the 2048 arm's own repeats disagree" in (tmp_path / "report.md").read_text(encoding="utf-8")


def test_the_report_says_when_it_cannot_decide(tmp_path: Path) -> None:
    (tmp_path / tb.CASES_FILE).write_text(json.dumps(_case(0)) + "\n", encoding="utf-8")
    tb.report(tmp_path)
    assert "not decidable" in (tmp_path / "report.md").read_text(encoding="utf-8")


def test_the_cli_dispatches_to_the_three_commands(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(tb, "sample", lambda out: seen.append("sample") or 0)
    monkeypatch.setattr(tb, "run", lambda out: seen.append("run") or 0)
    monkeypatch.setattr(tb, "report", lambda out: seen.append("report") or 0)
    for command in ("sample", "run", "report"):
        assert tb.main([command, "--out", str(tmp_path)]) == 0
    assert seen == ["sample", "run", "report"]
