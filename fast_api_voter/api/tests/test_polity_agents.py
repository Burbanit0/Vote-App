"""The agent tier (ADR-014): api/domain/polity/agents.py and the president agent's turn."""
from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from api.domain.polity.agents import (
    ISSUES,
    PRESIDENT_TURN,
    NomineeBriefing,
    nominee_system_prompt,
    nominee_user_prompt,
    AgentMemory,
    PresidentBriefing,
    agent_name,
    decide_turn,
    lean,
    steps_toward,
    persona,
    president_system_prompt,
    president_user_prompt,
    seat_weighted_median,
    turn_words,
    validate_turn,
)
from api.domain.polity.citizen import Citizen
from api.domain.polity.config import PolityConfigError, load_config, validate_config
from api.domain.polity import run_polity_simulation as engine
from api.domain.polity.journal import Journal, JournalEvent
from api.domain.polity.legislation import Bill, Legislature
from api.domain.polity.llm_behavior_engine import ResponseContext
from api.domain.polity.llm_client import LlmResponseError
from api.domain.polity.llm_schemas import IssueTarget, LeaderTurn, PositionShift
from api.domain.polity.parties import Party
from api.domain.polity.run_frames import load_run_frames
from api.domain.polity.run_polity_simulation import _agenda_closed, _agent_bill, _phase_leaders, _turn_moves, run_simulation
from api.tests.test_polity_run_simulation import _ElectingFakeLlmClient
from api.tests.polity_golden import golden_config

_CONFIG = load_config()
_N = len(ISSUES)


def _president(**kwargs: Any) -> Citizen:
    priorities = tuple(0.5 if d == 9 else 0.5 / (_N - 1) for d in range(_N))
    return Citizen(
        citizen_id=30, issue_positions=tuple(0.2 for _ in range(_N)), issue_priorities=priorities,
        blank_threshold=0.3, ambition_score=0.8, party_affiliation=2, **kwargs,
    )


def _turn(**kwargs: Any) -> dict[str, Any]:
    fields: dict[str, Any] = dict(rationale="why", positions=[], bill=[], speech="hello", note_to_self="", other_initiative="")
    return {**fields, **kwargs}


class _ScriptedClient:
    def __init__(self, *answers: dict[str, Any]) -> None:
        self._answers = [json.dumps(a) for a in answers]
        self.calls = 0

    def count_prompt_tokens(self, **kwargs: Any) -> int:
        return 1000

    def complete_json(self, **kwargs: Any) -> str:
        answer = self._answers[min(self.calls, len(self._answers) - 1)]
        self.calls += 1
        self.sampling = {key: kwargs[key] for key in ("temperature", "seed") if key in kwargs}
        return answer


# ── persona and prompts ───────────────────────────────────────────────────

def test_the_persona_names_what_the_citizen_cares_about_and_where_they_stand() -> None:
    text = persona(_president())
    assert agent_name(_president()) in text and "housing" in text.split("care most about:")[1].split(".")[0]
    assert f"{_N - 1} direct democracy (representative government / frequent referendums): 0.20, leaning to representative government" in text


@pytest.mark.parametrize("value,words", [
    (0.1, "strongly for low taxes"), (0.3, "leaning to low taxes"), (0.5, "in between"),
    (0.7, "leaning to high taxes"), (0.9, "strongly for high taxes"),
])
def test_a_lean_is_put_in_words_against_the_issue_s_poles(value: float, words: str) -> None:
    assert lean(0, value) == words


def test_the_system_prompt_states_the_rules_in_force_and_no_others() -> None:
    config = dataclasses.replace(_CONFIG, legislation=dataclasses.replace(_CONFIG.legislation, enabled=True))
    with_bills = president_system_prompt(_president(), config)
    assert "at most 2 terms" in with_bills and "propose one bill" in with_bills
    assert "propose one bill" not in president_system_prompt(_president(), _CONFIG)
    unlimited = dataclasses.replace(_CONFIG, institutions=dataclasses.replace(_CONFIG.institutions, president_term_limit=None))
    assert "no limit on terms" in president_system_prompt(_president(), unlimited)


def _briefing(**kwargs: Any) -> PresidentBriefing:
    fields: dict[str, Any] = dict(
        tick=9, ticks_per_year=4, context=ResponseContext(cid=30, legitimacy=0.4, mandate_dev=0.1, street=0.2, lame_duck=True, ticks_left=7),
        approval=0.55, agenda_closed=None, policy=(0.5,) * _N, public_median=(0.4,) * _N,
        assembly_median=(0.6,) * _N, pledge=(0.2,) * _N, stated=(0.3,) * _N,
    )
    return PresidentBriefing(**{**fields, **kwargs})


def test_the_briefing_shows_the_standing_the_agenda_and_every_issue() -> None:
    text = president_user_prompt(_briefing(), "MEMORY")
    assert "Tick 9 (year 2, quarter 2). Your term ends in 7 ticks; you cannot run again." in text
    assert "approval 0.55, legitimacy 0.40, street pressure 0.20, gap from your pledge 0.10" in text
    assert "The agenda is yours" in text and "MEMORY" in text
    assert "9 housing (the private market / public housing) | 0.50 | 0.30 | 0.20 | 0.40 | 0.60" in text
    quiet = president_user_prompt(_briefing(
        agenda_closed="no assembly has been elected yet", policy=None, assembly_median=None,
        context=ResponseContext(cid=30, legitimacy=None, mandate_dev=0.0, street=None, lame_duck=False, ticks_left=None),
    ), "")
    assert "No bill this tick: no assembly has been elected yet." in quiet and "no set end; you may run again" in quiet
    assert "legitimacy" not in quiet and "| - | 0.30 | 0.20 | 0.40 | -" in quiet


def test_the_assembly_median_counts_each_party_once_per_seat() -> None:
    parties = [Party(0, (0.1, 0.9)), Party(1, (0.5, 0.5)), Party(2, (0.9, 0.1))]
    assert seat_weighted_median(parties, {0: 60, 1: 20, 2: 20}) == (0.1, 0.9)
    assert seat_weighted_median(parties, {0: 30, 1: 20, 2: 50, 3: 0}) == (0.5, 0.1)  # exactly half at 0.1: the lower median


def test_a_nominee_campaigns_on_the_poll_under_the_campaign_s_rules() -> None:
    system = nominee_system_prompt(_president(), _CONFIG)
    assert "your party's nominee" in system and "up to 3 issues" in system and "leave \"bill\" empty" in system
    # Staying home is stated only where the rule can keep anyone home (OBS-042): a cost, and the utility vote.
    assert "may stay home" not in system  # polity_config.yaml's cost is 0
    costly = dataclasses.replace(_CONFIG, vote=dataclasses.replace(_CONFIG.vote, turnout_cost=0.15))
    assert "favourite is worth about as much as a blank ballot may stay home" in nominee_system_prompt(_president(), costly)
    model_votes = dataclasses.replace(costly, vote=dataclasses.replace(costly.vote, mode="llm"))
    assert "may stay home" not in nominee_system_prompt(_president(), model_votes)
    briefing = NomineeBriefing(
        tick=16, field=((30, 2), (7, None)), poll={30: 0.4, 7: 0.25}, blank=0.2, abstain=0.15,
        platform=(0.3,) * _N, public_median=(0.5,) * _N,
    )
    text = nominee_user_prompt(_president(), briefing)
    assert "- you (party 2): 40% of first choices" in text and "- citizen 7 (no party): 25% of first choices" in text
    assert "voting blank 20%, staying home 15%" in text and "9 housing (the private market / public housing) | 0.30 | 0.50" in text


# ── memory ────────────────────────────────────────────────────────────────

def _event(event_type: str, tick: int, payload: dict[str, Any], citizen_id: int | None = None) -> JournalEvent:
    return JournalEvent(run_id="r", event_id=tick, tick=tick, event_type=event_type, payload=payload, citizen_id=citizen_id)


_TURN_PAYLOAD = {"speech": "we build", "shifts": [{"dimension": 9, "delta": 0.1}], "bill": [{"dimension": 0, "delta": -0.1}],
                 "note_to_self": "watch taxes", "rationale": "", "other_initiative": ""}


def test_memory_keeps_the_public_record_and_each_agent_s_own() -> None:
    memory = AgentMemory(public_window=2)
    for event in (
        _event("pressure_action", 1, {"act": 3}, citizen_id=5),
        _event("bill_enacted", 2, {"bill_id": 1, "dimensions": [0, 9], "new_values": [0.1, 0.2]}),
        _event("recalled", 3, {"office": "president"}, citizen_id=7),
        _event("elected", 4, {"attempt": 1, "votes": {"citizen_30": 9}}, citizen_id=30),
        _event("legitimacy_updated", 4, {"legitimacy": 0.61, "ecart": 0.0, "mandate_strength": 0.6, "approval": 0.5}, citizen_id=30),
        _event("agent_turn", 4, _TURN_PAYLOAD, citizen_id=30),
    ):
        memory.observe(event)
    text = memory.recall(30)
    assert "pressure_action" not in text and "bill_enacted" not in text  # dropped, and pushed out of the window
    assert '- t3 recalled (citizen 7): {"office": "president"}' in text and "- t4 elected (citizen 30)" in text
    assert "- t4 legitimacy 0.61, approval 0.50" in text
    assert '- t4 you moved housing +0.10; bill taxation -0.10; note to self: "watch taxes"' in text
    assert "we build" not in text  # an agent's own past speeches are left out (OBS-028)
    assert memory.recall(8).endswith("Your recent record:\n- nothing yet")
    assert AgentMemory().recall(1).startswith("Recent public events:\n- none yet")


def test_memory_rebuilt_from_the_journal_matches_the_one_kept_live(tmp_path: Path) -> None:
    live = AgentMemory()
    with Journal(tmp_path / "events.jsonl", "r") as journal:
        journal.tap = live.observe
        journal.write(1, "bill_voted", {"bill_id": 1, "passed": 0}, citizen_id=None)
        journal.write(2, "agent_turn", {**_TURN_PAYLOAD, "bill": []}, citizen_id=30)
        journal.write(2, "legitimacy_updated", {"legitimacy": 0.5, "ecart": 0.1, "mandate_strength": 0.6}, citizen_id=30)
    rebuilt = AgentMemory()
    rebuilt.replay(tmp_path / "events.jsonl")
    rebuilt.replay(tmp_path / "missing.jsonl")
    assert rebuilt.recall(30) == live.recall(30) and "moved housing +0.10; note" in live.recall(30)


# ── validation and the turn ───────────────────────────────────────────────

def _target(dimension: int, target: float) -> IssueTarget:
    return IssueTarget(dimension=dimension, target=target)


@pytest.mark.behavior("LEG-04")
@pytest.mark.parametrize("positions,message", [
    ([_target(0, 0.1), _target(1, 0.1), _target(2, 0.1), _target(3, 0.1)], "4 issues, at most 3"),
    ([_target(0, 0.1), _target(0, 0.9)], "the same issue twice"),
    ([_target(_N, 0.1)], f"no issue {_N}"),
])
def test_a_turn_out_of_bounds_is_rejected(positions: list[IssueTarget], message: str) -> None:
    with pytest.raises(LlmResponseError, match=message):
        validate_turn(LeaderTurn(**_turn(positions=positions)), _CONFIG, max_positions=3, agenda_open=False)


def test_a_bill_is_checked_only_when_the_agenda_is_open() -> None:
    oversized = LeaderTurn(**_turn(bill=[_target(0, 0.9), _target(1, 0.9), _target(2, 0.9)]))
    validate_turn(oversized, _CONFIG, max_positions=3, agenda_open=False)
    with pytest.raises(LlmResponseError, match="bill: 3 issues, at most 2"):
        validate_turn(oversized, _CONFIG, max_positions=3, agenda_open=True)


@pytest.mark.behavior("LEG-04")
def test_the_kernel_steps_toward_each_target_by_at_most_the_bound() -> None:
    steps = steps_toward([_target(0, 1.0), _target(1, 0.9), _target(2, 0.1), _target(3, 0.5)], (0.5, 0.9, 0.2, 0.503), 0.3)
    # issue 1 is already there, and issue 3 only by the shown precision's rounding
    assert [(s.dimension, round(s.delta, 6)) for s in steps] == [(0, 0.3), (2, -0.1)]


def test_a_rejected_turn_is_replayed_and_an_exhausted_one_leaves_the_president_silent() -> None:
    config = dataclasses.replace(_CONFIG, llm=dataclasses.replace(_CONFIG.llm, enabled=True, max_batch_replays=1))
    good = _turn(bill=[{"dimension": 0, "target": 0.4}])
    bad = _turn(bill=[{"dimension": 0, "target": 0.4}, {"dimension": 1, "target": 0.4}, {"dimension": 2, "target": 0.4}])

    def decide(client: _ScriptedClient) -> Any:
        return decide_turn(_president(), decision_type=PRESIDENT_TURN, system_prompt="s", user_prompt="u", max_positions=3,  # type: ignore[arg-type]
                           agenda_open=True, config=config, client=client)

    recovered = decide(_ScriptedClient(bad, good))
    assert recovered.turn is not None and recovered.turn.bill[0].target == 0.4 and recovered.sampling_varied
    silent = decide(_ScriptedClient(bad))
    assert silent.turn is None and not silent.sampling_varied and silent.call_id


def test_a_turn_is_sampled_at_the_turn_temperature_with_a_seed_and_is_no_retry() -> None:
    config = dataclasses.replace(_CONFIG, llm=dataclasses.replace(_CONFIG.llm, enabled=True))
    for temperature, sampling in ((0.6, {"temperature": 0.6, "seed": 900_000_901}), (0.0, {})):
        client = _ScriptedClient(_turn())
        turned = dataclasses.replace(config, agents=dataclasses.replace(config.agents, turn_temperature=temperature))
        outcome = decide_turn(_president(), decision_type=PRESIDENT_TURN, system_prompt="s", user_prompt="u", max_positions=3,  # type: ignore[arg-type]
                              agenda_open=False, config=turned, client=client)
        assert client.sampling == sampling and outcome.turn is not None and not outcome.sampling_varied


def test_the_words_are_cut_to_their_limits() -> None:
    words = turn_words(LeaderTurn(**_turn(speech="x" * 500, rationale="y" * 400, note_to_self="z" * 300, other_initiative="w" * 300)))
    assert [len(words[k]) for k in ("speech", "rationale", "note_to_self", "other_initiative")] == [400, 300, 200, 200]
    assert set(turn_words(None).values()) == {""}


# ── config ────────────────────────────────────────────────────────────────

def test_the_president_agent_needs_the_model_and_the_named_issues() -> None:
    agent = dataclasses.replace(_CONFIG, agents=dataclasses.replace(_CONFIG.agents, president=True))
    with pytest.raises(PolityConfigError, match="llm.enabled"):
        validate_config(agent)
    with_llm = dataclasses.replace(agent, llm=dataclasses.replace(agent.llm, enabled=True))
    validate_config(with_llm)
    with pytest.raises(PolityConfigError, match="issue_count"):
        validate_config(dataclasses.replace(with_llm, citizens=dataclasses.replace(with_llm.citizens, issue_count=10)))


# ── the kernel's side of a turn ───────────────────────────────────────────

_AGENDA_CONFIG = dataclasses.replace(_CONFIG, legislation=dataclasses.replace(_CONFIG.legislation, enabled=True, bill_interval_ticks=2))


def _closed(legislature: Legislature | None, tick: int = 4) -> str | None:
    context = SimpleNamespace(config=_AGENDA_CONFIG, tick=tick)
    return _agenda_closed(context, SimpleNamespace(legislature=legislature), _president())  # type: ignore[arg-type]


def test_the_briefing_says_why_the_agenda_is_closed() -> None:
    seated = Legislature(policy=(0.5,) * _N, seats={2: 60, 3: 40}, coalition=(2,))
    bill = Bill(bill_id=1, agenda_setter="president", proposer=30, dimensions=(0,), proposal=(0.6,))
    assert _closed(None) == "legislation is not in force"
    assert _closed(Legislature(policy=(0.5,) * _N)) == "no assembly has been elected yet"
    assert _closed(dataclasses.replace(seated, suspended=bill)) == "a bill the chamber suspended comes back first"
    assert _closed(seated, tick=5) == "a bill comes every 2 ticks"
    assert _closed(dataclasses.replace(seated, coalition=(3,))) == "under cohabitation the government sets the agenda"
    assert _closed(seated) is None


def test_an_agent_bill_that_changes_nothing_is_no_bill() -> None:
    legislature = Legislature(policy=(1.0, 0.5))
    assert _agent_bill(legislature, _president(), []) is None
    assert _agent_bill(legislature, _president(), [PositionShift(dimension=0, delta=0.1)]) is None  # already at the bound
    bill = _agent_bill(legislature, _president(), [PositionShift(dimension=1, delta=0.1), PositionShift(dimension=0, delta=0.1)])
    assert bill is not None and (bill.dimensions, bill.proposal, bill.proposer) == ((1,), (0.6,), 30)


def test_a_failed_turn_moves_nothing_and_leaves_the_agenda_to_the_formula() -> None:
    assert _turn_moves(None, (0.5,) * _N, Legislature(policy=(0.5,) * _N), None, _CONFIG) == ([], None)


def test_no_turn_is_asked_without_a_seated_president() -> None:
    agent = dataclasses.replace(_CONFIG, agents=dataclasses.replace(_CONFIG.agents, president=True))
    for config in (agent, _CONFIG):
        context = SimpleNamespace(config=config, client=object(), memory=AgentMemory(), journal=None)
        _phase_leaders(context, SimpleNamespace(citizens=[_president()]))  # type: ignore[arg-type]  # holds no office


# ── a run with a president agent ──────────────────────────────────────────

class _AgentFakeClient(_ElectingFakeLlmClient):  # type: ignore[misc]
    """A stateless population, and a president who wants public housing (issue 9 at 1) and
    proposes it whenever the agenda is theirs; every third tick names an issue twice once.
    The speech carries a digest of the prompt, so a journal compares the prompts too."""

    def complete_json(self, **kwargs: Any) -> str:
        if kwargs["json_schema"].get("title") != "LeaderTurn":
            return str(super().complete_json(**kwargs))
        prompt = kwargs["user_prompt"]
        tick = int(re.match(r"Tick (\d+)", prompt).group(1))  # type: ignore[union-attr]
        twice = tick % 3 == 0 and "temperature" not in kwargs
        return json.dumps(_turn(
            positions=[{"dimension": 9, "target": 1.0}] * (2 if twice else 1),
            bill=[{"dimension": 9, "target": 1.0}] if "The agenda is yours" in prompt else [],
            speech=f"prompt {hashlib.sha256(prompt.encode()).hexdigest()[:12]}",
            other_initiative="abolish the chamber" if tick == 0 else "",
        ))


def _agent_run_config(output_dir: Path) -> Any:
    config = golden_config(output_dir, llm=True)
    # An assembly from tick 0 and a third year: the president holds the agenda at tick 10
    # (the government does before, under cohabitation).
    return dataclasses.replace(
        config,
        run=dataclasses.replace(config.run, duration_years=3),
        institutions=dataclasses.replace(config.institutions, assembly_offset_years=0),
        legislation=dataclasses.replace(config.legislation, enabled=True),
        agents=dataclasses.replace(config.agents, president=True, nominees=True),
        llm=dataclasses.replace(config.llm, max_batch_replays=1),
    )


def test_a_run_with_a_president_agent_journals_its_turns_and_its_bills(tmp_path: Path) -> None:
    journal = run_simulation(_agent_run_config(tmp_path), run_id="agent", llm_client=_AgentFakeClient())
    events = [json.loads(line) for line in journal.read_text().splitlines()]
    turns = [e for e in events if e["event_type"] == "agent_turn"]
    assert turns and not [e for e in events if e["event_type"] == "representative_response"]
    moves = [m for t in turns for m in t["payload"]["shifts"]]
    assert moves and all(m["dimension"] == 9 and 0 < m["delta"] <= 0.3 for m in moves)
    assert all(t["codebook_version"] for t in turns)
    assert turns[0]["payload"]["other_initiative"] == "abolish the chamber"
    assert any(t["payload"]["retry_sampling_varied"] for t in turns)
    agent_bills = [e for e in events if e["event_type"] == "bill_proposed" and e["payload"].get("drafted_by") == "agent"]
    assert agent_bills and all(b["payload"]["dimensions"] == [9] for b in agent_bills)
    assert len(agent_bills) == sum(1 for t in turns if t["payload"]["bill"])
    campaigns = [t for t in turns if t["payload"]["role"] == "nominee"]
    polls = [e for e in events if e["event_type"] == "vote_intention_poll"]
    assert campaigns and polls and not [e for e in events if e["event_type"] == "campaign_positioning"]
    assert {c["tick"] for c in campaigns} == {p["tick"] for p in polls}
    for poll in polls:
        assert sum(s["share"] for s in poll["payload"]["shares"]) + poll["payload"]["blank"] + poll["payload"]["abstain"] == pytest.approx(1.0)
    frames = load_run_frames(journal.parent)  # the explorer replays both roles' shifts
    assert len(frames.frames) == 13


class _Crash(Exception):
    pass


def test_a_president_agent_s_run_resumes_with_the_memory_it_had(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The memory is rebuilt from the journal on resume, so the resumed prompts -- whose digest
    each speech carries -- and with them the whole journal match the uninterrupted run."""
    uninterrupted = run_simulation(_agent_run_config(tmp_path / "a"), run_id="run", llm_client=_AgentFakeClient())
    real_phase = engine._run_accountability_phase

    def crash_at_tick_7(citizens: Any, config: Any, journal: Any, tick: int, llm_client: Any = None, **kwargs: Any) -> Any:
        if tick == 7:
            raise _Crash("killed mid-tick")
        return real_phase(citizens, config, journal, tick, llm_client, **kwargs)

    monkeypatch.setattr(engine, "_run_accountability_phase", crash_at_tick_7)
    with pytest.raises(_Crash):
        run_simulation(_agent_run_config(tmp_path / "b"), run_id="run", llm_client=_AgentFakeClient())
    monkeypatch.undo()
    resumed = run_simulation(_agent_run_config(tmp_path / "b"), run_id="run", resume=True, llm_client=_AgentFakeClient())
    assert resumed.read_bytes() == uninterrupted.read_bytes()
