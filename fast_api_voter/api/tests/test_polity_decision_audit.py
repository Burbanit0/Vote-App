"""decision_audit.py: a run's decisions scored against the kernel's own rules, from the run's own files."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from api.domain.polity import decision_audit as audit
from api.domain.polity.config import PressureMenuConfig, load_config
from api.domain.polity.llm_call_log import CALL_LOG_FILENAME, PROMPT_LOG_FILENAME, PromptLogWriter
from api.domain.polity.simple_rules import PressureAct, deterministic_pressure_action

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
FIXTURE_RUN = Path(__file__).resolve().parents[2] / "polity_fixtures" / "runs" / "explorer-fixture"


def _script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _call(call_id: str, decision_type: str, *, think: bool = False, reasoning_tokens: int = 0, budget: int | None = None,
          attempt: int = 0, finish: str = "stop", reasoning: str = "", content: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"call_id": call_id, "kind": "decision", "decision_type": decision_type, "tick": 0, "attempt": attempt,
            "think": think, "reasoning_tokens": reasoning_tokens, "finish_reason": finish, "reasoning": reasoning,
            "extra_body": {"thinking_token_budget": budget} if budget else None, "content": json.dumps(content or {})}


def test_a_call_is_at_the_budget_when_its_reasoning_reached_it() -> None:
    assert audit.at_budget(_call("a", "vote_cast", think=True, reasoning_tokens=2047, budget=2048))
    assert audit.at_budget(_call("a", "vote_cast", think=True, reasoning_tokens=2048, budget=2048))
    assert not audit.at_budget(_call("a", "vote_cast", think=True, reasoning_tokens=1500, budget=2048))
    assert not audit.at_budget(_call("a", "vote_cast", think=True, reasoning_tokens=5000))  # no budget sent


def test_type_stats_count_retries_truncations_budget_and_format_search_per_type() -> None:
    calls = [
        _call("1", "chamber_deliberation", think=True, reasoning_tokens=2048, budget=2048),
        _call("2", "chamber_deliberation", think=True, reasoning_tokens=900, budget=2048, attempt=1, finish="length",
              reasoning="Need JSON schema: rationale, post"),
        _call("3", "pressure_action"),
        {"kind": "warm_up", "decision_type": None},
    ]
    stats = audit.type_stats(calls)
    chamber = stats["chamber_deliberation"]
    assert (chamber.calls, chamber.retried, chamber.truncated, chamber.thinking, chamber.at_budget, chamber.format_search) == (2, 1, 1, 2, 1, 1)
    assert stats["pressure_action"].thinking == 0 and set(stats) == {"chamber_deliberation", "pressure_action"}


def test_the_vote_rule_is_blank_only_when_no_candidate_is_within_the_threshold() -> None:
    assert audit.vote_rule({"distances": [0.5, 0.2, 0.3], "blank_threshold": 0.4}) == (False, 2)
    assert audit.vote_rule({"distances": [0.5, 0.6], "blank_threshold": 0.4}) == (True, None)
    assert audit.vote_rule({"distances": [], "blank_threshold": 0.4}) == (True, None)
    assert audit.vote_rule({"distances": [0.1]}) == (True, None)  # no threshold: nothing is acceptable


def test_a_vote_is_scored_against_the_rule() -> None:
    voters = {1: {"distances": [0.5, 0.2], "blank_threshold": 0.4}, 2: {"distances": [0.9, 0.8], "blank_threshold": 0.4},
              3: {"distances": [0.1, 0.3], "blank_threshold": 0.4}, 4: {"distances": [0.2, 0.1], "blank_threshold": 0.4}}
    decisions = [
        {"cid": 1, "blank": 0, "ranking": [2]},       # right
        {"cid": 2, "blank": 1, "ranking": []},         # blank, rule agrees
        {"cid": 3, "blank": 1, "ranking": []},         # blank though candidates were acceptable
        {"cid": 4, "blank": 0, "ranking": [1, 2]},     # first choice is not the nearest (2)
        {"cid": 99, "blank": 0, "ranking": [1]},       # not in the prompt: ignored
    ]
    score = audit.VoteScore()
    audit.score_vote(score, voters, decisions)
    assert (score.units, score.rule_blank, score.model_blank, score.blank_though_acceptable) == (4, 1, 2, 1)
    assert (score.ranked, score.first_choice_right) == (2, 1)


def _write_run(root: Path, calls: list[dict[str, Any]], events: list[dict[str, Any]] | None = None, *, prompts: bool = True,
               anger: float = 0.0) -> Path:
    run = root / "run"
    run.mkdir()
    (run / CALL_LOG_FILENAME).write_text("".join(json.dumps(c) + "\n" for c in calls), encoding="utf-8")
    (run / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events or []), encoding="utf-8")
    (run / "config.json").write_text(json.dumps({"emotions": {"mobilization_anger": anger}}), encoding="utf-8")
    if prompts:
        writer = PromptLogWriter(run / PROMPT_LOG_FILENAME)
        request = {"voters": [{"cid": 1, "distances": [0.5, 0.2], "blank_threshold": 0.4},
                              {"cid": 2, "distances": [0.1, 0.3], "blank_threshold": 0.4}]}
        writer.write("v-cut", system_prompt="rule", user_prompt=json.dumps(request), json_schema=None)
        writer.write("v-done", system_prompt="rule", user_prompt=json.dumps(request), json_schema=None)
        writer.write("other", system_prompt="rule", user_prompt="{}", json_schema=None)
        writer.close()
    return run


def _vote_calls() -> list[dict[str, Any]]:
    cut = {"decisions": [{"cid": 1, "blank": 0, "ranking": [2]}, {"cid": 2, "blank": 1, "ranking": []}]}
    done = {"decisions": [{"cid": 1, "blank": 0, "ranking": [2]}, {"cid": 2, "blank": 0, "ranking": [1]}]}
    return [
        _call("v-cut", "vote_cast", think=True, reasoning_tokens=2048, budget=2048, content=cut),
        _call("v-done", "vote_cast", think=True, reasoning_tokens=700, budget=2048, content=done),
        _call("v-cut", "vote_cast", think=True, reasoning_tokens=700, budget=2048, attempt=1, content=cut),  # a retry is not scored
    ]


def test_votes_are_scored_by_budget_state_from_the_logged_prompts(tmp_path: Path) -> None:
    run = _write_run(tmp_path, _vote_calls())
    scores = audit.audit_run(run).vote
    assert scores is not None
    assert (scores[audit.AT_BUDGET].units, scores[audit.AT_BUDGET].blank_though_acceptable) == (2, 1)
    assert (scores[audit.UNDER_BUDGET].units, scores[audit.UNDER_BUDGET].blank_though_acceptable) == (2, 0)
    assert scores[audit.UNDER_BUDGET].first_choice_right == scores[audit.UNDER_BUDGET].ranked == 2


def test_answers_of_an_unexpected_shape_are_unscored_not_fatal(tmp_path: Path) -> None:
    run = tmp_path / "odd"
    run.mkdir()
    writer = PromptLogWriter(run / PROMPT_LOG_FILENAME)
    good = json.dumps({"voters": [{"cid": 1, "distances": [0.1], "blank_threshold": 0.4}]})
    for call_id, user in (("list", good), ("null", good), ("novoters", "{}"), ("badvoter", json.dumps({"voters": [3]})),
                          ("ok", good), ("garbage", good)):
        writer.write(call_id, system_prompt="rule", user_prompt=user, json_schema=None)
    writer.close()
    calls = [{**_call("list", "vote_cast", think=True), "content": "[1, 2]"}, {**_call("null", "vote_cast", think=True), "content": "null"},
             _call("novoters", "vote_cast", think=True, content={"decisions": []}),
             _call("badvoter", "vote_cast", think=True, content={"decisions": []}),
             _call("ok", "vote_cast", think=True, content={"decisions": [{"cid": 1, "blank": 0, "ranking": [1]}, "stray", {"cid": 7}]}),
             {**_call("garbage", "vote_cast", think=True), "content": None}]
    (run / CALL_LOG_FILENAME).write_text("".join(json.dumps(c) + "\n" for c in calls), encoding="utf-8")
    result = audit.audit_run(run)
    assert result.vote is not None and result.vote[audit.UNDER_BUDGET].units == 1  # only the real decision of "ok"
    assert result.vote_unscored == 5
    assert "left unscored" in "\n".join(audit.render_audit({"odd": result}))


def test_a_torn_prompt_sidecar_leaves_every_vote_unscored(tmp_path: Path) -> None:
    run = _write_run(tmp_path, _vote_calls())
    with (run / PROMPT_LOG_FILENAME).open("a", encoding="utf-8") as sidecar:
        sidecar.write('{"call_id": "torn')
    result = audit.audit_run(run)
    assert result.vote is not None and all(v.units == 0 for v in result.vote.values()) and result.vote_unscored == 2


def test_fallbacks_are_reported_by_the_journals_own_event_type(tmp_path: Path) -> None:
    run = _write_run(tmp_path, [_call("a", "president_turn", think=True)], [
        {"event_type": "agent_turn", "payload": {"llm_fallback": 1}}, {"event_type": "agent_turn", "payload": {"llm_fallback": 0}}])
    text = "\n".join(audit.render_audit({"r": audit.audit_run(run)}))
    assert "| r | agent_turn | 2 | 50% (1) |" in text and "| r | president_turn | 1 |" in text
    clean = _write_run(tmp_path / "clean", [_call("a", "president_turn")], [{"event_type": "agent_turn", "payload": {"llm_fallback": 0}}]) \
        if (tmp_path / "clean").mkdir() is None else tmp_path
    assert "no journaled decision fell back" in "\n".join(audit.render_audit({"c": audit.audit_run(clean)}))


def test_a_run_without_prompts_is_audited_without_the_vote(tmp_path: Path) -> None:
    run = _write_run(tmp_path, _vote_calls(), prompts=False)
    result = audit.audit_run(run)
    assert result.vote is None and result.types["vote_cast"].calls == 3
    assert any("not scored" in line for line in audit.render_audit({"r": result}))


def test_a_vote_whose_prompt_or_answer_cannot_be_read_is_skipped(tmp_path: Path) -> None:
    run = _write_run(tmp_path, [_call("other", "vote_cast", think=True, content={"decisions": []}),
                                _call("missing", "vote_cast", think=True), {**_call("v-done", "vote_cast", think=True), "content": "{oops"}])
    scores = audit.audit_run(run).vote
    assert scores is not None and all(s.units == 0 for s in scores.values())
    assert [line for line in audit.render_audit({"r": audit.audit_run(run)}) if line.startswith("| r | ") and "budget" in line] == []


def test_the_pressure_rule_is_the_kernels_for_every_context() -> None:
    config = load_config()
    menu = PressureMenuConfig(electoral_only=False, petition_enabled=False, mobilization_enabled=True)
    for gap, threshold, anger, mobilization in [(0.3, 0.4, 0.0, 0.0), (0.4, 0.4, 0.0, 0.0), (0.5, 0.4, 0.0, 0.0),
                                                (0.3, 0.4, 0.5, 0.5), (0.2, 0.4, 0.9, 0.5), (0.39, 0.4, None, 0.7)]:
        citizen = SimpleNamespace(blank_threshold=threshold)
        scale = 1.0 - mobilization * (anger or 0.0)
        kernel = deterministic_pressure_action(citizen, gap, menu, tolerance_scale=scale)  # type: ignore[arg-type]
        context = {"self_gap": gap, "blank_threshold": threshold, "anger": anger}
        assert audit.rule_acts(context, mobilization) == (kernel != PressureAct.NOTHING)
    assert config.emotions.mobilization_anger >= 0.0


def test_events_give_the_fallback_share_and_the_pressure_agreement(tmp_path: Path) -> None:
    def pressure(act: int, gap: float, fallback: int = 0) -> dict[str, Any]:
        return {"event_type": "pressure_action", "payload": {"act": act, "llm_fallback": fallback,
                                                             "ctx": {"self_gap": gap, "blank_threshold": 0.4, "anger": 0.0}}}
    events = [pressure(0, 0.1), pressure(3, 0.9), pressure(0, 0.9, fallback=1), pressure(3, 0.1),
              {"event_type": "elected", "payload": {}}]
    run = _write_run(tmp_path, [], events, prompts=False)
    result = audit.audit_run(run)
    assert result.pressure is not None
    # the fallback (the rule applied to itself) is counted apart, not compared
    assert (result.pressure.units, result.pressure.rule_acts, result.pressure.model_acts, result.pressure.agree) == (3, 1, 2, 2)
    assert result.pressure.fallbacks == 1
    assert (result.journaled["pressure_action"], result.fallbacks["pressure_action"]) == (4, 1)


def test_a_torn_last_line_is_skipped_and_a_run_without_a_call_log_is_empty(tmp_path: Path) -> None:
    run = tmp_path / "torn"
    run.mkdir()
    (run / "events.jsonl").write_text('{"event_type": "elected", "payload": {}}\n\n{"event_type": "pre', encoding="utf-8")  # a blank line, a torn one
    result = audit.audit_run(run)
    assert result.types == {} and result.vote is None and result.pressure is None and result.journaled == {}


def test_a_run_with_a_call_log_and_no_journal_is_audited_for_its_calls(tmp_path: Path) -> None:
    run = tmp_path / "calls-only"
    run.mkdir()
    (run / CALL_LOG_FILENAME).write_text(json.dumps(_call("p", "pressure_action")) + "\n", encoding="utf-8")
    result = audit.audit_run(run)
    assert result.types["pressure_action"].calls == 1 and result.pressure is None and not result.journaled


def test_the_report_reads_as_tables_per_question(tmp_path: Path) -> None:
    run = _write_run(tmp_path, _vote_calls() + [_call("p", "pressure_action")], [
        {"event_type": "pressure_action", "payload": {"act": 0, "ctx": {"self_gap": 0.1, "blank_threshold": 0.4}}}])
    text = "\n".join(audit.render_audit({"seed 1": audit.audit_run(run)}))
    assert "| seed 1 | vote_cast | 3 | 33% | 0% | 3 | 33% | 0% |" in text
    assert "| seed 1 | at budget | 2 | 0% | 50% | 50% | 1/1 |" in text
    assert "| seed 1 | 1 | 1 | 0% | 0% | 100% | 0 |" in text


def test_the_cli_audits_every_run_under_a_root(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cli = _script("audit_decisions")
    assert cli.main([]) == 2
    assert cli.main([str(tmp_path)]) == 1
    _write_run(tmp_path, _vote_calls())
    assert cli.main([str(tmp_path)]) == 0
    assert "| run | decision |" in capsys.readouterr().out


def test_runs_that_share_a_directory_name_are_labelled_by_their_path(tmp_path: Path) -> None:
    cli = _script("audit_decisions")
    a, b, c = tmp_path / "full" / "run" / "x", tmp_path / "replay" / "run" / "x", tmp_path / "full" / "run" / "y"
    labels = cli.labelled([a, b, c])
    assert labels[c] == "y" and labels[a] != labels[b] and labels[a].endswith("full/run/x") and labels[b].endswith("replay/run/x")


def test_the_sweep_summary_carries_the_audit_only_when_a_run_has_decisions(tmp_path: Path) -> None:
    sweep = _script("run_polity_seed_sweep")
    for run_id in ("seed1", "seed2"):
        run_dir = tmp_path / f"sweep-1y-p10-{run_id}" / "run" / f"sweep-1y-p10-{run_id}"
        run_dir.mkdir(parents=True)
        (run_dir / "digest.json").write_text(json.dumps({"outcome": "completed", "office_occupancy": 0.9}), encoding="utf-8")
        (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    assert "## Decision audit" not in sweep._write_sweep_summary(tmp_path, 1, 10, [1, 2]).read_text(encoding="utf-8")
    run = tmp_path / "sweep-1y-p10-seed1" / "run" / "sweep-1y-p10-seed1"
    (run / CALL_LOG_FILENAME).write_text(json.dumps(_call("p", "pressure_action")) + "\n", encoding="utf-8")
    text = sweep._write_sweep_summary(tmp_path, 1, 10, [1, 2]).read_text(encoding="utf-8")
    assert "## Decision audit" in text and "| seed 1 | pressure_action | 1 |" in text


def test_the_nominations_of_a_party_dissolved_before_the_checkpoint_do_not_crash_the_election_report() -> None:
    observations = _script("check_observations")
    events = [json.loads(line) for line in (FIXTURE_RUN / "events.jsonl").read_text().splitlines()]
    nomination = next(e for e in events if e["event_type"] == "party_nomination_choice")
    gone = {**nomination, "payload": {**nomination["payload"], "party_id": 99}}  # at the first election, like the others
    before = len(observations._nomination_rows(FIXTURE_RUN, events))
    assert len(observations._nomination_rows(FIXTURE_RUN, [gone, *events])) == before  # an initial party since dissolved: skipped
    founded = {"event_type": "party_founded", "tick": 0, "payload": {"party_id": 99, "platform": [0.5] * 20, "members": 5}}
    assert len(observations._nomination_rows(FIXTURE_RUN, [founded, gone, *events])) == before + 1  # its platform is in the journal


def test_an_llm_run_keeps_its_prompts_unless_the_caller_opted_out(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    flagship = _script("run_polity_flagship")
    seen: list[str | None] = []
    monkeypatch.setattr(flagship, "run_flagship", lambda **_: seen.append(os.environ.get("POLITY_LOG_PROMPTS")))
    monkeypatch.setattr(flagship.signal, "signal", lambda *_: None)
    out = ["--output-dir", str(tmp_path), "--years", "1", "--population", "10", "--seats", "3"]
    monkeypatch.setenv("POLITY_LOG_PROMPTS", "x")  # recorded, so the teardown restores "absent" whatever main() sets
    monkeypatch.delenv("POLITY_LOG_PROMPTS")
    flagship.main(["--engine", "deterministic", *out])
    flagship.main(["--engine", "llm", *out])
    monkeypatch.setenv("POLITY_LOG_PROMPTS", "0")
    flagship.main(["--engine", "llm", *out])
    assert seen == [None, "1", "0"]


def test_the_committed_fixture_run_is_audited_end_to_end() -> None:
    """The explorer fixture has a journal and no call log: its pressure decisions are audited, the rest says so."""
    result = audit.audit_run(FIXTURE_RUN)
    assert result.types == {} and result.vote is None
    assert result.pressure is not None and result.pressure.units > 0 and 0 <= result.pressure.agree <= result.pressure.units
    text = "\n".join(audit.render_audit({"explorer-fixture": result}))
    assert "| explorer-fixture | " in text and "not scored" in text
    assert _script("audit_decisions").main([str(FIXTURE_RUN)]) == 0
