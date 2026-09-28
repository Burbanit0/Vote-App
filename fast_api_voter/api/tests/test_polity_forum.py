"""The forum (ADR-016, roadmap 3.1-3.2): the chamber and recent petition launchers post or stay silent."""
from __future__ import annotations

import dataclasses
import json
import re
from types import SimpleNamespace
from pathlib import Path
from typing import Any

import pytest

from api.domain.polity import run_polity_simulation as engine
from api.domain.polity.citizen import generate_population
from api.domain.polity.agents import (
    FEED_SIZE,
    FORUM_IDLE_TICKS,
    AgentMemory,
    decide_forum,
    forum_system_prompt,
    forum_user_prompt,
    forum_words,
    party_roll,
)
from api.domain.polity.config import PolityConfigError, load_config, validate_config
from api.domain.polity.journal import JournalEvent
from api.domain.polity.llm_schemas import ForumTurn
from api.domain.polity.parties import initialize_parties
from api.domain.polity.run_polity_simulation import run_simulation
from api.domain.polity.simple_rules import apply_party_move, assign_party_affiliation, dissolve_small_parties
from api.tests.test_polity_agents import _AgentFakeClient, _agent_run_config, _president, _ScriptedClient

_CONFIG = load_config()


def _event(tick: int, citizen_id: int | None, event_type: str, **payload: Any) -> JournalEvent:
    return JournalEvent(run_id="r", event_id=0, tick=tick, citizen_id=citizen_id, event_type=event_type, payload=payload)


def _forum(config: Any) -> Any:
    return dataclasses.replace(
        config, llm=dataclasses.replace(config.llm, enabled=True), agents=dataclasses.replace(config.agents, forum=True),
        sortition_chamber=dataclasses.replace(config.sortition_chamber, enabled=True),
    )


def test_the_forum_needs_the_model() -> None:
    with pytest.raises(PolityConfigError, match="agents.forum"):
        validate_config(dataclasses.replace(_CONFIG, agents=dataclasses.replace(_CONFIG.agents, forum=True)))
    validate_config(_forum(_CONFIG))


def test_a_citizen_reads_the_officeholders_and_their_authors_and_never_their_own_posts() -> None:
    memory = AgentMemory()
    for event in (
        _event(1, 5, "forum_post", post="from a neighbour", rationale="", note_to_self=""),
        _event(1, 6, "forum_post", post="from a stranger", rationale="", note_to_self=""),
        _event(2, 7, "forum_post", post="my own", rationale="", note_to_self=""),
        _event(2, 8, "forum_post", post="", rationale="", note_to_self=""),
        _event(2, 30, "agent_turn", role="president", speech="a speech", shifts=[], bill=[], note_to_self=""),
    ):
        memory.observe(event)
    feed = memory.feed(7, frozenset({5, 7, 8}))
    assert 't1 citizen 5: "from a neighbour"' in feed and 't2 the president: "a speech"' in feed
    assert "stranger" not in feed and "my own" not in feed and "citizen 8" not in feed
    assert memory.feed(7, frozenset()).count("\n") == 1 and "nothing yet" in AgentMemory().feed(7, frozenset({5}))
    assert "you posted" in memory.recall(7) and "you kept silent" in memory.recall(8)
    for tick in range(3, 3 + 2 * FEED_SIZE):
        memory.observe(_event(tick, 5, "forum_post", post=f"post {tick}", rationale="", note_to_self=""))
    assert memory.feed(7, frozenset({5})).count("\n") == FEED_SIZE


def test_a_petition_launcher_speaks_for_a_few_ticks_the_latest_first() -> None:
    memory = AgentMemory()
    for tick, cid in ((2, 9), (5, 4), (5, 3)):
        memory.observe(_event(tick, cid, "petition_launched", target=1, signatures=1, signed_ratio=0.1, expires_at_tick=9))
    assert memory.recent_petitioners(6) == [3, 4, 9]
    assert memory.recent_petitioners(2 + FORUM_IDLE_TICKS) == [3, 4]


def test_a_turn_is_a_post_or_silence_and_a_failed_one_is_silence() -> None:
    config = _forum(dataclasses.replace(_CONFIG, llm=dataclasses.replace(_CONFIG.llm, max_batch_replays=0)))
    turn = {"rationale": "why", "post": "hello", "note_to_self": "n", "shift_issue": -1, "shift_direction": "none", "party_move": "none", "party_id": -1}

    def say(client: Any) -> Any:
        return decide_forum(_president(), system_prompt="s", user_prompt="u", config=config, client=client)

    said = say(_ScriptedClient(turn))
    assert said.turn is not None and forum_words(said.turn) == {k: turn[k] for k in ("rationale", "post", "note_to_self")}
    lost = say(_ScriptedClient({"post": 3}))
    assert lost.turn is None and set(forum_words(lost.turn).values()) == {""}
    assert say(_ScriptedClient({**turn, "shift_direction": "high"})).turn is None  # a shift with no issue is retried, then lost
    assert ForumTurn(**turn).post == "hello"
    assert "silent" in forum_system_prompt(_president(), config)
    assert "You sit in the citizens' chamber" in forum_user_prompt(tick=3, member=True, feed="FEED", memory="MEMORY")
    assert "chamber" not in forum_user_prompt(tick=3, member=False, feed="FEED", memory="MEMORY")


class _ForumClient(_AgentFakeClient):
    """Every odd citizen posts `hello from <id>`, every even one stays silent; every forum prompt is kept."""

    def __init__(self, shift: bool = False, party: str = "none") -> None:
        self.party = party
        self.prompts: list[tuple[int, str]] = []
        self.systems: list[tuple[int, str]] = []
        self.shift = shift

    def complete_json(self, **kwargs: Any) -> str:
        if kwargs["json_schema"].get("title") != "ForumTurn":
            return super().complete_json(**kwargs)
        cid = int(re.search(r"\(citizen (\d+)\)", kwargs["system_prompt"]).group(1))  # type: ignore[union-attr]
        self.prompts.append((cid, kwargs["user_prompt"]))
        self.systems.append((cid, kwargs["system_prompt"]))
        shift = {"shift_issue": 5, "shift_direction": "high"} if self.shift and cid % 2 else {"shift_issue": -1, "shift_direction": "none"}
        move = {"party_move": self.party if cid % 2 else "none", "party_id": 0 if self.party == "join" else -1}
        return json.dumps({"rationale": "r", "post": f"hello from {cid}" if cid % 2 else "", "note_to_self": "", **shift, **move})


def _run(tmp_path: Path, client: _ForumClient | None = None) -> tuple[Path, list[dict[str, Any]], _ForumClient]:
    client = client or _ForumClient()
    config = _forum(_agent_run_config(tmp_path))
    journal = run_simulation(config, run_id="forum", llm_client=client)
    return journal, [json.loads(line) for line in journal.read_text().splitlines()], client


def test_the_chamber_talks_and_no_one_reads_their_own_post_or_a_post_of_the_same_tick(tmp_path: Path) -> None:
    _, events, client = _run(tmp_path)
    posts = [e for e in events if e["event_type"] == "forum_post"]
    ticks = {e["tick"] for e in posts}
    assert posts and len(ticks) > 2 and {e["citizen_id"] % 2 == 1 for e in posts if e["payload"]["post"]} == {True}
    assert {e["payload"]["post"] for e in posts if e["citizen_id"] % 2 == 0} == {""}
    assert all(e["payload"]["llm_call_id"] and not e["payload"]["llm_fallback"] for e in posts)
    assert len({e["citizen_id"] for e in posts if e["tick"] == min(ticks)}) <= _forum(_CONFIG).agents.forum_size
    assert all(f"citizen {cid}: " not in prompt for cid, prompt in client.prompts)
    assert any("hello from" in prompt for _, prompt in client.prompts)
    assert not [prompt for _, prompt in client.prompts if "Tick 0." in prompt and "hello from" in prompt]


class _Crash(Exception):
    pass


def test_a_run_resumes_with_the_forum_it_had(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    uninterrupted, events, _ = _run(tmp_path / "a")
    real_phase = engine._run_accountability_phase

    def crash(citizens: Any, config: Any, journal: Any, tick: int, llm_client: Any = None, **kwargs: Any) -> Any:
        if tick == 6:
            raise _Crash("killed mid-tick")
        return real_phase(citizens, config, journal, tick, llm_client, **kwargs)

    monkeypatch.setattr(engine, "_run_accountability_phase", crash)
    with pytest.raises(_Crash):
        run_simulation(_forum(_agent_run_config(tmp_path / "b")), run_id="forum", llm_client=_ForumClient())
    monkeypatch.undo()
    resumed = run_simulation(_forum(_agent_run_config(tmp_path / "b")), run_id="forum", resume=True, llm_client=_ForumClient())
    assert resumed.read_bytes() == uninterrupted.read_bytes()


def _moving(config: Any) -> Any:
    return dataclasses.replace(
        config, agents=dataclasses.replace(config.agents, stance_step=0.25), dynamics=dataclasses.replace(config.dynamics, enabled=True),
    )


def test_stance_step_needs_the_forum_and_the_dynamics() -> None:
    for config in (_moving(_CONFIG), dataclasses.replace(_forum(_CONFIG), agents=dataclasses.replace(_forum(_CONFIG).agents, stance_step=0.25))):
        with pytest.raises(PolityConfigError, match="stance_step"):
            validate_config(config)
    validate_config(_moving(_forum(_CONFIG)))
    assert "genuinely changed your mind" in forum_system_prompt(_president(), _moving(_forum(_CONFIG)))
    assert "genuinely" not in forum_system_prompt(_president(), _forum(_CONFIG))


def test_a_citizen_who_changes_their_mind_stays_moved(tmp_path: Path) -> None:
    client = _ForumClient(shift=True)
    journal = run_simulation(_moving(_forum(_agent_run_config(tmp_path))), run_id="mind", llm_client=client)
    posts = [json.loads(line) for line in journal.read_text().splitlines() if '"forum_post"' in line]
    assert {(e["citizen_id"] % 2, e["payload"]["shift_issue"], e["payload"]["shift_logit"]) for e in posts} == {(1, 5, 0.25), (0, -1, 0.0)}

    def position(system: str) -> float:
        return float(re.search(r"- 5 [^:]+: (\d\.\d+)", system).group(1))  # type: ignore[union-attr]

    by_citizen: dict[int, list[float]] = {}
    for cid, system in client.systems:
        by_citizen.setdefault(cid, []).append(position(system))
    moved = [seen for cid, seen in by_citizen.items() if cid % 2 and len(seen) > 1]
    assert moved and all(seen == sorted(seen) and seen[-1] > seen[0] for seen in moved)
    assert all(len(set(seen)) == 1 for cid, seen in by_citizen.items() if cid % 2 == 0)


def _polity(n: int = 100) -> tuple[list[Any], list[Any]]:
    citizens = generate_population(_CONFIG.citizens, n, seed=3)
    parties = initialize_parties(citizens, 5, seed=3)
    for citizen in citizens:
        citizen.party_affiliation = assign_party_affiliation(citizen, parties)
    return citizens, parties


def _size(citizens: list[Any], party_id: int) -> int:
    return sum(1 for c in citizens if c.party_affiliation == party_id)


def test_a_citizen_joins_leaves_and_founds() -> None:
    citizens, parties = _polity()
    parties_cfg = dataclasses.replace(_CONFIG.parties, birth_enabled=True)
    citizen = citizens[0]
    other = next(p.party_id for p in parties if p.party_id != citizen.party_affiliation)
    assert apply_party_move(citizen, "join", 99, citizens, parties, parties_cfg) == ""
    assert apply_party_move(citizen, "join", citizen.party_affiliation, citizens, parties, parties_cfg) == ""
    assert apply_party_move(citizen, "join", other, citizens, parties, parties_cfg) == f"join {other}" and citizen.party_affiliation == other
    assert apply_party_move(citizen, "leave", -1, citizens, parties, parties_cfg) == "leave" and citizen.party_affiliation is None
    assert apply_party_move(citizen, "leave", -1, citizens, parties, parties_cfg) == ""
    assert apply_party_move(citizen, "none", -1, citizens, parties, parties_cfg) == ""

    assert apply_party_move(citizen, "found", -1, citizens, parties, _CONFIG.parties) == ""  # birth is off
    assert apply_party_move(citizen, "found", -1, citizens, parties, dataclasses.replace(parties_cfg, founding_ratio=1.0)) == ""
    assert len(parties) == 5
    founder = next(c for c in citizens if c.party_affiliation is not None and apply_party_move(c, "found", -1, citizens, parties, parties_cfg))
    assert parties[-1].party_id == 5 and parties[-1].platform == founder.issue_positions and founder.party_affiliation == 5
    assert _size(citizens, 5) >= 0.05 * len(citizens)


def test_a_party_too_small_to_keep_is_dissolved_and_its_members_go_to_the_nearest() -> None:
    citizens, parties = _polity()
    config = dataclasses.replace(_CONFIG.parties, death_enabled=True, founding_ratio=0.1)
    assert dissolve_small_parties(citizens, parties, _CONFIG.parties) == []  # death is off
    assert dissolve_small_parties(citizens, parties, config) == []  # every party is above half the ratio
    small, seated = parties[0].party_id, parties[1].party_id
    for party_id in (small, seated):
        for citizen in [c for c in citizens if c.party_affiliation == party_id][2:]:
            citizen.party_affiliation = parties[2].party_id
    independent = next(c for c in citizens if c.party_affiliation == parties[2].party_id)
    independent.party_affiliation = None
    assert dissolve_small_parties(citizens, parties, config, seated={seated}) == [(small, 2)]
    assert small not in {p.party_id for p in parties} and _size(citizens, small) == 0 and independent.party_affiliation is None
    assert all(c.party_affiliation is None or c.party_affiliation in {p.party_id for p in parties} for c in citizens)
    lone, rest = parties[:1], [c for c in citizens if c.party_affiliation is not None]
    assert dissolve_small_parties(rest[:1], lone, dataclasses.replace(config, founding_ratio=0.3)) == []  # the last party stays


def test_party_moves_need_the_forum_and_show_the_parties() -> None:
    with pytest.raises(PolityConfigError, match="party_moves"):
        validate_config(dataclasses.replace(_CONFIG, agents=dataclasses.replace(_CONFIG.agents, party_moves=True)))
    config = _forum(_CONFIG)
    moving = dataclasses.replace(config, agents=dataclasses.replace(config.agents, party_moves=True))
    validate_config(moving)
    assert "change party" in forum_system_prompt(_president(), moving) and "change party" not in forum_system_prompt(_president(), config)
    citizens, parties = _polity()
    roll = party_roll(parties, citizens)
    assert roll.count("- party ") == 5 and "% of citizens" in roll
    assert forum_user_prompt(tick=3, member=False, feed="FEED", memory="M", roll=roll).startswith("Tick 3.\n\nThe parties:")
    with pytest.raises(ValueError, match="party_id"):
        ForumTurn(rationale="", post="", note_to_self="", shift_issue=-1, shift_direction="none", party_move="join", party_id=-1)


def test_a_founder_starts_a_party_that_the_run_keeps(tmp_path: Path) -> None:
    config = _forum(_agent_run_config(tmp_path))
    config = dataclasses.replace(
        config, agents=dataclasses.replace(config.agents, party_moves=True), parties=dataclasses.replace(config.parties, birth_enabled=True),
    )
    journal = run_simulation(config, run_id="founder", llm_client=_ForumClient(party="found"))
    events = [json.loads(line) for line in journal.read_text().splitlines()]
    founded = [e for e in events if e["event_type"] == "party_founded"]
    assert founded and founded[0]["payload"]["party_id"] == config.parties.initial_count and founded[0]["payload"]["members"] > 0
    posts = [e["payload"]["party_move"] for e in events if e["event_type"] == "forum_post"]
    assert any(move.startswith("found ") for move in posts) and set(posts) >= {""}


def test_a_party_move_is_journaled_and_a_dissolution_too() -> None:
    citizens, parties = _polity()
    config = dataclasses.replace(
        _forum(_CONFIG), parties=dataclasses.replace(_CONFIG.parties, death_enabled=True, founding_ratio=0.1),
        agents=dataclasses.replace(_forum(_CONFIG).agents, party_moves=True),
    )
    written: list[Any] = []
    context = SimpleNamespace(config=config, tick=4, journal=SimpleNamespace(write_event=lambda **kw: written.append(kw["event"])))
    state = SimpleNamespace(citizens=citizens, parties=parties, legislature=SimpleNamespace(seats={p.party_id: 20 for p in parties[1:]}))
    turn = ForumTurn(rationale="", post="", note_to_self="", shift_issue=-1, shift_direction="none", party_move="leave", party_id=-1)
    first, second = parties[0].party_id, parties[1].party_id
    for citizen in [c for c in citizens if c.party_affiliation == first][:-1]:
        citizen.party_affiliation = second
    lone = next(c for c in citizens if c.party_affiliation == first)
    assert engine._apply_party_move(context, state, lone, turn) == "leave"
    assert [(type(e).__name__, e.party_id) for e in written] == [("PartyDissolved", first)] and first not in {p.party_id for p in parties}
    assert engine._apply_party_move(context, state, lone, turn) == "" and engine._apply_party_move(context, state, lone, None) == ""
