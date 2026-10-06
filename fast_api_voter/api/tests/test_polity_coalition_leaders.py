"""Coalition talks between party leaders (ADR-019, roadmap 4.2): a leader answers the formateur, round after round."""
from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path
from typing import Any

import pytest

from api.domain.polity.agents import (
    AgentMemory,
    coalition_system_prompt,
    coalition_user_prompt,
    coalition_words,
    party_leader,
)
from api.domain.polity.citizen import Citizen
from api.domain.polity.config import PolityConfigError, load_config, validate_config
from api.domain.polity.journal import JournalEvent
from api.domain.polity.llm_schemas import LeaderCoalitionTurn
from api.domain.polity.run_polity_simulation import run_simulation
from api.tests.test_polity_agents import _AgentFakeClient, _agent_run_config, _president

_CONFIG = load_config()


def _coalition(config: Any) -> Any:
    return dataclasses.replace(
        config, llm=dataclasses.replace(config.llm, enabled=True), agents=dataclasses.replace(config.agents, coalition=True),
    )


def test_the_leaders_need_the_model() -> None:
    with pytest.raises(PolityConfigError, match="agents.coalition"):
        validate_config(dataclasses.replace(_CONFIG, agents=dataclasses.replace(_CONFIG.agents, coalition=True)))
    validate_config(_coalition(_CONFIG))


@pytest.mark.behavior("PAR-01")
def test_a_party_is_led_by_its_most_ambitious_member_and_no_one_leads_two() -> None:
    def member(cid: int, party: int | None, ambition: float) -> Citizen:
        return dataclasses.replace(_president(), citizen_id=cid, party_affiliation=party, ambition_score=ambition)

    citizens = [member(0, 1, 0.5), member(1, 1, 0.9), member(2, 1, 0.9), member(3, 2, 0.1), member(4, None, 0.7)]
    assert party_leader(1, citizens).citizen_id == 1  # the tie goes to the lower id
    assert party_leader(2, citizens).citizen_id == 3
    assert party_leader(9, citizens).citizen_id == 1  # a party with no member: the most ambitious citizen
    assert party_leader(9, citizens, taken={1, 2}).citizen_id == 4


def test_a_leader_is_told_where_the_formateur_differs_and_what_the_others_said() -> None:
    platforms = {1: tuple([0.5] * 20), 2: (1.0, *[0.5] * 19)}
    args: dict[str, Any] = dict(
        tick=3, party_id=1, initiator=2, platforms=platforms, seats={1: 10, 2: 30}, threshold=25.0, memory="MEMORY",
    )
    first = coalition_user_prompt(**args, round_number=1, provisional=None, others="")
    assert "Tick 3, round 1" in first and "party 2, with 30 seats" in first and "you in between, they strongly for" in first
    assert "other leaders said" not in first and first.endswith("MEMORY\n\nYour turn.")
    assert "other leaders said:\n- party 3" in coalition_user_prompt(**args, round_number=2, provisional=30, others="- party 3")
    system = coalition_system_prompt(_president(), 1, _CONFIG)
    assert "You lead party 1" in system and f"after {_CONFIG.parties.coalition_max_negotiation_rounds} rounds" in system
    turn = LeaderCoalitionTurn(rationale="r", join="yes", statement="s" * 999, note_to_self="n")
    assert len(coalition_words(turn)["statement"]) < 999 and set(coalition_words(None).values()) == {""}


def test_a_leader_remembers_the_talks_they_took_part_in() -> None:
    memory = AgentMemory()
    memory.observe(JournalEvent(
        run_id="r", event_id=0, tick=4, citizen_id=7, event_type="coalition_decision",
        payload={"round": 2, "action": 2, "note_to_self": "never again"},
    ))
    assert 'round 2 of the coalition talks you declined; note to self: "never again"' in memory.recall(7)


class _LeaderClient(_AgentFakeClient):
    """Even parties join at once; odd parties decline until they see the coalition stand somewhere."""

    def __init__(self, broken: bool = False, mute_after_round_1: bool = False) -> None:
        self.prompts: list[str] = []
        self.broken = broken
        self.mute = mute_after_round_1

    def complete_json(self, **kwargs: Any) -> str:
        title = kwargs["json_schema"].get("title")
        assert title != "CoalitionBatch"
        if title != "LeaderCoalitionTurn":
            return super().complete_json(**kwargs)
        if self.broken or (self.mute and "round 1." not in kwargs["user_prompt"]):
            return "{}"
        party = int(re.search(r"You lead party (\d+)", kwargs["system_prompt"]).group(1))  # type: ignore[union-attr]
        self.prompts.append(kwargs["user_prompt"])
        joins = party % 2 == 0 or "The coalition now stands at" in kwargs["user_prompt"]
        return json.dumps({"rationale": "r", "join": "yes" if joins else "no", "statement": f"party {party} speaks", "note_to_self": "n"})


def _run(tmp_path: Path, client: _LeaderClient) -> list[dict[str, Any]]:
    config = _coalition(_agent_run_config(tmp_path))
    journal = run_simulation(config, run_id="talks", llm_client=client)
    return [json.loads(line) for line in journal.read_text().splitlines()]


def test_the_leaders_negotiate_and_the_talks_are_journaled(tmp_path: Path) -> None:
    client = _LeaderClient()
    events = _run(tmp_path, client)
    decisions = [e for e in events if e["event_type"] == "coalition_decision"]
    assert decisions and all(e["citizen_id"] == e["payload"]["leader"] for e in decisions)
    assert all(e["payload"]["statement"] == f"party {e['payload']['party_id']} speaks" and e["payload"]["llm_call_id"] for e in decisions)
    assert all(not e["payload"]["llm_fallback"] and not e.get("motif") for e in decisions)
    assert max(e["payload"]["round"] for e in decisions) >= 2  # an odd party changed its answer after round 1
    assert any("party 2 speaks" in p or "party 4 speaks" in p for p in client.prompts)
    assert [e for e in events if e["event_type"] in ("coalition_formed", "coalition_failed")]


def test_a_leader_who_never_answers_declines(tmp_path: Path) -> None:
    events = _run(tmp_path, _LeaderClient(broken=True))
    decisions = [e for e in events if e["event_type"] == "coalition_decision"]
    assert decisions and {e["payload"]["action"] for e in decisions} == {2} and all(e["payload"]["llm_fallback"] for e in decisions)
    assert {e["payload"]["round"] for e in decisions} == {1, 2}  # round 2 confirms the fixed point


def test_a_leader_who_goes_quiet_keeps_their_answer(tmp_path: Path) -> None:
    events = _run(tmp_path, _LeaderClient(mute_after_round_1=True))
    quiet = [e["payload"] for e in events if e["event_type"] == "coalition_decision" and e["payload"]["round"] == 2]
    assert quiet and all(p["llm_fallback"] for p in quiet)
    assert {p["action"] for p in quiet if p["party_id"] % 2 == 0} == {1} and {p["action"] for p in quiet if p["party_id"] % 2} == {2}
