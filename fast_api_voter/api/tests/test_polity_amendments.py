"""The amendment procedure (ADR-015, roadmap 2.2-2.3): the president proposes, the chamber votes."""
from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

from api.domain.polity import run_polity_simulation as engine
from api.domain.polity.agents import (
    ballot_system_prompt,
    ballot_user_prompt,
    ballot_words,
    decide_ballot,
    decide_turn,
    president_system_prompt,
    proposer_line,
    amendment_consequence,
    ballot_proposer_text,
    validate_turn,
    PRESIDENT_TURN,
)
from api.domain.polity.amendments import (
    articles_text,
    constitution_text,
    proposal_closed,
    ratified,
    validate_amendment,
    value_text,
)
from api.domain.polity.checkpoint import _constitution_from_dict, _constitution_to_dict
from api.domain.polity.config import (
    _DEFAULT_CONFIG_PATH,
    PolityConfigError,
    amended,
    broken_rule,
    load_config,
    validate_config,
)
from api.domain.polity.constitution import Constitution, Proposal, amend, close_proposal, propose, threshold_for
from api.domain.polity.llm_client import LlmResponseError
from api.domain.polity.llm_schemas import AMENDING_LEADER_TURN_JSON_SCHEMA, AmendingLeaderTurn, AmendmentBallot, AmendmentProposal
from api.domain.polity.run_polity_simulation import run_simulation
from api.tests.test_polity_agents import _AgentFakeClient, _agent_run_config, _president, _ScriptedClient, _turn

_CONFIG = load_config()
_METHOD = "institutions.presidential_method"
_PROPOSAL = Proposal(article=_METHOD, value="borda", proposer=30, tick=3, threshold=0.6, reason="fairer")


def _amending(config: Any) -> Any:
    return dataclasses.replace(
        config, llm=dataclasses.replace(config.llm, enabled=True),
        agents=dataclasses.replace(config.agents, president=True, amendments=True),
        sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True),
    )


# ── the procedure is an article; entrenchment raises it ───────────────────

def test_an_entrenched_article_needs_more_than_the_general_threshold() -> None:
    assert threshold_for(_CONFIG, "legitimacy.recall_floor") == 0.5
    assert threshold_for(_CONFIG, _METHOD) == 0.6
    assert threshold_for(_CONFIG, "constitution.amendment_threshold") == 0.75
    stricter = amended(_CONFIG, "constitution.amendment_threshold", 0.7)
    assert (threshold_for(stricter, "legitimacy.recall_floor"), threshold_for(stricter, _METHOD)) == (0.7, 0.7)


def test_a_pending_proposal_is_cleared_by_its_resolution_and_survives_a_checkpoint() -> None:
    pending = propose(amend(None, "legitimacy.recall_floor", 0.1), _PROPOSAL)
    assert pending.pending == _PROPOSAL and pending.version == 1
    assert _constitution_from_dict(json.loads(json.dumps(_constitution_to_dict(pending)))) == pending
    assert "pending" not in _constitution_to_dict(Constitution())
    assert close_proposal(pending) == Constitution(1, {"legitimacy.recall_floor": 0.1})
    assert close_proposal(propose(None, _PROPOSAL)) is None
    assert amend(pending, _METHOD, "borda") == Constitution(2, {"legitimacy.recall_floor": 0.1, _METHOD: "borda"})


def _load(tmp_path: Path, **constitution: Any) -> Any:
    data = yaml.safe_load(_DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    data["constitution"].update(constitution)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return load_config(path)


@pytest.mark.parametrize("constitution,message", [
    ({"entrenched": {"run.seed": 0.6}}, "not an amendable article"),
    ({"entrenched": {_METHOD: 0.95}}, "not a threshold"),
    ({"amendment_threshold": 0.3}, "amendment_threshold"),
])
def test_an_entrenchment_the_constitution_cannot_hold_is_refused(tmp_path: Path, constitution: Any, message: str) -> None:
    with pytest.raises(PolityConfigError, match=message):
        _load(tmp_path, **constitution)


def test_a_config_file_states_the_entrenchment() -> None:
    assert _CONFIG.constitution.entrenched == {_METHOD: 0.6, "constitution.amendment_threshold": 0.75}


def test_amending_needs_the_president_the_chamber_and_the_model() -> None:
    proposing = dataclasses.replace(_CONFIG, agents=dataclasses.replace(_CONFIG.agents, amendments=True))
    with pytest.raises(PolityConfigError, match="llm.enabled"):
        validate_config(proposing)
    with_llm = dataclasses.replace(proposing, llm=dataclasses.replace(proposing.llm, enabled=True))
    with pytest.raises(PolityConfigError, match="requires 'agents.president'"):
        validate_config(with_llm)
    validate_config(_amending(_CONFIG))
    assert broken_rule(_amending(_CONFIG)) is None and broken_rule(with_llm) is not None


# ── what needs no agent ───────────────────────────────────────────────────

@pytest.mark.parametrize("proposal,message", [
    (AmendmentProposal(article="run.seed", value=1, reason="r"), "not an article"),
    (AmendmentProposal(article=_METHOD, value="star", reason="r"), "not a value"),
    (AmendmentProposal(article=_METHOD, value="two_round", reason="r"), r'already "two_round"'),
])
def test_a_proposal_the_articles_refuse_is_an_error(proposal: AmendmentProposal, message: str) -> None:
    with pytest.raises(LlmResponseError, match=message):
        validate_amendment(proposal, _CONFIG)


@pytest.mark.parametrize(
    ("article", "written", "value"),
    [
        ("institutions.president_term_limit", "null", None),  # the term limit the log asks to abolish
        ("institutions.electoral_threshold", "0.03", 0.03),
        ("institutions.presidential_method", "borda", "borda"),  # a string article keeps its string
        ("institutions.president_term_limit", "nonsense", "nonsense"),  # left alone, so validate_amendment refuses it
    ],
)
def test_a_value_the_model_quoted_is_read_as_the_json_literal_the_article_wants(
    article: str, written: str, value: Any,
) -> None:
    assert AmendmentProposal(article=article, value=written, reason="r").value == value


def test_a_proposal_that_breaks_the_rules_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    validate_amendment(AmendmentProposal(article=_METHOD, value="borda", reason="r"), _CONFIG)
    monkeypatch.setattr("api.domain.polity.config._CONFIG_RULES", (
        lambda c: "no borda here" if c.institutions.presidential_method == "borda" else None,
    ))
    with pytest.raises(LlmResponseError, match=r"would not hold \(no borda here\)"):
        validate_amendment(AmendmentProposal(article=_METHOD, value="borda", reason="r"), _CONFIG)


def test_a_member_who_does_not_vote_counts_against() -> None:
    assert [ratified(y, 10, 0.5) for y in (5, 6)] == [False, True]
    assert ratified(3, 4, 0.75) is False and ratified(4, 4, 0.75) is True


def test_the_texts_tell_the_articles_the_thresholds_and_whether_one_can_be_proposed() -> None:
    assert (value_text(None), value_text("two_round"), value_text(0.5)) == ("null", '"two_round"', "0.5")
    text = articles_text(_CONFIG)
    assert "1, 2, 3, null" in text and "a number from 0.5 to 0.9" in text and '"kemeny_young"' in text
    assert proposal_closed(None, 0) == "no chamber has been drawn yet" and proposal_closed(None, 30) is None
    pending = propose(None, _PROPOSAL)
    assert 'yet to vote on changing institutions.presidential_method to "borda"' in str(proposal_closed(pending, 30))
    open_text = constitution_text(amended(_CONFIG, _METHOD, "borda"), None, 30)
    assert f"{_METHOD}: \"borda\" (amending it needs more than 60% of the chamber's 30 members)" in open_text
    assert open_text.endswith("You may propose an amendment this tick.")
    assert "No amendment can be proposed this tick: the chamber is yet to vote" in constitution_text(_CONFIG, pending, 30)


# ── the agents ────────────────────────────────────────────────────────────

def test_the_president_is_told_the_articles_only_where_the_polity_can_amend() -> None:
    assert "amended" not in president_system_prompt(_president(), _CONFIG)
    prompt = president_system_prompt(_president(), _amending(_CONFIG))
    assert articles_text(_CONFIG) in prompt and "one amendment in a turn" in prompt


def test_the_amending_turn_carries_the_proposal_and_is_checked_against_the_articles() -> None:
    assert "amendment" in AMENDING_LEADER_TURN_JSON_SCHEMA["properties"]
    turn = AmendingLeaderTurn(**_turn(amendment={"article": _METHOD, "value": "borda", "reason": "r"}))
    validate_turn(turn, _CONFIG, max_positions=3, agenda_open=False)
    bad = AmendingLeaderTurn(**_turn(amendment={"article": _METHOD, "value": "star", "reason": "r"}))
    with pytest.raises(LlmResponseError, match="not a value"):
        validate_turn(bad, _CONFIG, max_positions=3, agenda_open=False)
    config = _amending(_CONFIG)
    client = _ScriptedClient(_turn(amendment={"article": _METHOD, "value": "borda", "reason": "r"}))
    outcome = decide_turn(_president(), decision_type=PRESIDENT_TURN, system_prompt="s", user_prompt="u", max_positions=3,  # type: ignore[arg-type]
                          agenda_open=False, config=config, client=client)
    assert isinstance(outcome.turn, AmendingLeaderTurn) and outcome.turn.amendment is not None


def test_a_ballot_shows_the_proposal_the_threshold_and_what_the_member_remembers() -> None:
    system = ballot_system_prompt(_president(), _amending(_CONFIG))
    assert "drawn by lot" in system and articles_text(_CONFIG) in system
    user = ballot_user_prompt(_PROPOSAL, tick=4, old="two_round", members=30, memory="MEMORY")
    assert 'from "two_round" to "borda"' in user and "more than 60% of the 30 members" in user and "fairer" in user and "MEMORY" in user


def test_a_ballot_tells_the_member_who_asks_in_facts_and_not_whether_it_serves_them() -> None:
    president = dataclasses.replace(_president(), party_affiliation=2)
    line = proposer_line(president, approval=0.35, ticks_left=4, lame_duck=True)
    assert line == "The president belongs to party 2; their approval is 35%, with 4 ticks left in their term, and they cannot run again."
    user = ballot_user_prompt(_PROPOSAL, tick=4, old="two_round", members=30, memory="", proposer=line)
    assert line in user and "benefit" not in user
    assert line not in ballot_user_prompt(_PROPOSAL, tick=4, old="two_round", members=30, memory="")


_TERM = "institutions.president_term_limit"


def _proposal(article: str, value: Any) -> Proposal:
    return Proposal(article=article, value=value, proposer=30, tick=3, threshold=0.5, reason="continuity")


@pytest.mark.parametrize(
    ("article", "served", "old", "new", "shown"),
    [
        # The case OBS-038 measured: a president who has served their two terms asks for a third.
        (_TERM, 2, 2, 3, True),
        (_TERM, 2, 2, None, True),  # abolishing the limit lifts the bar too (and OBS-033 made it reachable)
        (_TERM, 1, 2, 3, False),  # not yet barred, so the change gains them nothing now
        (_TERM, 2, 2, 1, False),  # tightening the limit binds them no less
        (_TERM, 0, None, 2, False),  # introducing a limit where there was none
        ("legitimacy.recall_floor", 1, 0.3, 0.1, True),  # a lower floor shields the sitting president
        ("legitimacy.recall_floor", 1, 0.1, 0.3, False),
        ("petition.signature_threshold", 1, 0.25, 0.4, True),  # a higher bar shields them from petitions
        ("petition.signature_threshold", 1, 0.25, 0.15, False),
        ("institutions.presidential_method", 2, "two_round", "borda", False),  # no rule the proposer is bound by
    ],
)
def test_the_ballot_names_a_change_that_would_loosen_a_rule_binding_its_proposer(
    article: str, served: int, old: Any, new: Any, shown: bool,
) -> None:
    president = dataclasses.replace(_president(), mandates_served=served)
    line = amendment_consequence(_proposal(article, new), president, old)
    assert bool(line) is shown
    # A consequence, never advice (C4): it says what would follow, not how to vote.
    assert not any(advice in line.lower() for advice in ("should", "vote yes", "vote no", "reject", "oppose", "beware"))


def test_the_ballot_s_proposer_text_is_the_standing_then_any_self_interest() -> None:
    # One composer for the kernel and the neutrality harness, so the harness cannot measure a
    # ballot the runs no longer show (it had drifted once already, before this function existed).
    barred = dataclasses.replace(_president(), mandates_served=2)
    standing = proposer_line(barred, approval=0.4, ticks_left=1, lame_duck=True)
    third_term = _proposal(_TERM, 3)
    assert ballot_proposer_text(barred, third_term, 2, approval=0.4, ticks_left=1, lame_duck=True) == (
        f"{standing}\n{amendment_consequence(third_term, barred, 2)}"
    )
    method = _proposal("institutions.presidential_method", "borda")
    assert ballot_proposer_text(barred, method, "two_round", approval=0.4, ticks_left=1, lame_duck=True) == standing


def test_a_ballot_is_a_decision_and_a_failed_one_is_no_vote() -> None:
    config = _amending(dataclasses.replace(_CONFIG, llm=dataclasses.replace(_CONFIG.llm, max_batch_replays=0)))
    ballot = {"rationale": "why", "vote": "yes", "statement": "aye", "note_to_self": "n"}

    def cast(client: Any) -> Any:
        return decide_ballot(_president(), system_prompt="s", user_prompt="u", config=config, client=client)

    yes = cast(_ScriptedClient(ballot))
    assert yes.turn is not None and yes.turn.vote == "yes"
    assert ballot_words(yes.turn) == {"statement": "aye", "rationale": "why", "note_to_self": "n"}
    lost = cast(_ScriptedClient({"vote": "maybe"}))
    assert lost.turn is None and set(ballot_words(lost.turn).values()) == {""}
    assert AmendmentBallot(**ballot).vote == "yes"


# ── a run ─────────────────────────────────────────────────────────────────

class _ChamberClient(_AgentFakeClient):
    """A president who proposes Borda for as long as the method is two-round; a chamber that
    votes `vote`, or answers nothing usable when `vote` is None."""

    def __init__(self, vote: str | None) -> None:
        self.vote = vote

    def complete_json(self, **kwargs: Any) -> str:
        title, prompt = kwargs["json_schema"].get("title"), kwargs["user_prompt"]
        if title == "AmendmentBallot":
            if self.vote is None:
                return "not json"
            return json.dumps({"rationale": "r", "vote": self.vote, "statement": f"I say {self.vote}", "note_to_self": ""})
        if title != "AmendingLeaderTurn":
            return super().complete_json(**kwargs)
        proposing = "You may propose an amendment this tick" in prompt and f'{_METHOD}: "two_round"' in prompt
        return json.dumps(_turn(amendment={"article": _METHOD, "value": "borda", "reason": "fairer"} if proposing else None))


def _run(tmp_path: Path, vote: str | None) -> tuple[Path, list[dict[str, Any]]]:
    config = _amending(_agent_run_config(tmp_path))
    journal = run_simulation(config, run_id="amend", llm_client=_ChamberClient(vote))
    return journal, [json.loads(line) for line in journal.read_text().splitlines()]


def _of(events: list[dict[str, Any]], event_type: str) -> list[dict[str, Any]]:
    return [e for e in events if e["event_type"] == event_type]


def test_a_chamber_that_votes_yes_ratifies_the_amendment_and_the_next_election_uses_it(tmp_path: Path) -> None:
    journal, events = _run(tmp_path, "yes")
    [proposed] = _of(events, "amendment_proposed")
    assert (proposed["payload"]["article"], proposed["payload"]["value"], proposed["payload"]["old"], proposed["payload"]["threshold"]) == (
        _METHOD, "borda", "two_round", 0.6,
    )
    [resolved] = _of(events, "amendment_resolved")
    members = resolved["payload"]["members"]
    assert resolved["tick"] == proposed["tick"] + 1
    assert (resolved["payload"]["yes"], resolved["payload"]["ratified"]) == (members, 1) and members > 0
    votes = _of(events, "amendment_vote")
    assert len(votes) == members and {v["payload"]["statement"] for v in votes} == {"I say yes"}
    assert all(v["payload"]["llm_call_id"] and not v["payload"]["llm_fallback"] for v in votes)
    [amendment] = _of(events, "constitution_amended")
    assert (amendment["payload"]["source"], amendment["payload"]["new"], amendment["payload"]["version"]) == ("vote", "borda", 1)
    assert json.loads((journal.parent / "checkpoint.json").read_text())["constitution"] == {"version": 1, "values": {_METHOD: "borda"}}


def test_a_chamber_that_votes_no_or_not_at_all_leaves_the_constitution_and_is_asked_again(tmp_path: Path) -> None:
    for vote in ("no", None):
        journal, events = _run(tmp_path / str(vote), vote)
        resolved = _of(events, "amendment_resolved")
        assert len(resolved) > 1 and len(resolved) == len(_of(events, "amendment_proposed")) - 1  # the last is still pending
        assert {r["payload"]["ratified"] for r in resolved} == {0} and not _of(events, "constitution_amended")
        assert {v["payload"]["vote"] for v in _of(events, "amendment_vote")} == {vote or "none"}
        kept = json.loads((journal.parent / "checkpoint.json").read_text())["constitution"]
        assert (kept["version"], kept["values"]) == (0, {})
    assert {v["payload"]["llm_fallback"] for v in _of(events, "amendment_vote")} == {1}


class _Crash(Exception):
    pass


def test_a_run_resumes_across_a_pending_proposal_and_the_vote_after_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    uninterrupted, events = _run(tmp_path / "a", "yes")
    [proposed] = _of(events, "amendment_proposed")
    real_phase = engine._run_accountability_phase

    def crash(citizens: Any, config: Any, journal: Any, tick: int, llm_client: Any = None, **kwargs: Any) -> Any:
        if tick == proposed["tick"] + 1:  # the tick that resolves it: the checkpoint holds the pending proposal
            raise _Crash("killed mid-tick")
        return real_phase(citizens, config, journal, tick, llm_client, **kwargs)

    monkeypatch.setattr(engine, "_run_accountability_phase", crash)
    with pytest.raises(_Crash):
        run_simulation(_amending(_agent_run_config(tmp_path / "b")), run_id="amend", llm_client=_ChamberClient("yes"))
    assert json.loads((tmp_path / "b" / "amend" / "checkpoint.json").read_text())["constitution"]["pending"]["article"] == _METHOD
    monkeypatch.undo()
    resumed = run_simulation(_amending(_agent_run_config(tmp_path / "b")), run_id="amend", resume=True, llm_client=_ChamberClient("yes"))
    assert resumed.read_bytes() == uninterrupted.read_bytes()


def test_a_proposal_made_while_another_is_pending_or_with_no_chamber_is_dropped(tmp_path: Path) -> None:
    config = _amending(_CONFIG)
    journal = SimpleNamespace(events=[], write_event=lambda **kw: journal.events.append(kw))
    turn = AmendingLeaderTurn(**_turn(amendment={"article": _METHOD, "value": "borda", "reason": "r"}))
    state = SimpleNamespace(constitution=propose(None, _PROPOSAL), citizens=[])
    context = SimpleNamespace(tick=4, config=config, journal=journal)
    engine._open_proposal(context, state, _president(), turn)  # type: ignore[arg-type]
    assert state.constitution == propose(None, _PROPOSAL) and not journal.events
    state.constitution = None
    engine._open_proposal(context, state, _president(), turn)  # type: ignore[arg-type]
    assert state.constitution is None and not journal.events
    engine._open_proposal(context, state, _president(), AmendingLeaderTurn(**_turn()))  # type: ignore[arg-type]
    assert not journal.events
    assert re.fullmatch(r"[a-z_]+", "amendment_proposed")
