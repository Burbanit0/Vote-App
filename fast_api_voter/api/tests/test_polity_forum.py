"""The forum (ADR-016, roadmap 3.1-3.2): the chamber and recent petition launchers post or stay silent."""
from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path
from typing import Any

import pytest

from api.domain.polity import run_polity_simulation as engine
from api.domain.polity.agents import (
    FEED_SIZE,
    FORUM_IDLE_TICKS,
    AgentMemory,
    decide_forum,
    forum_system_prompt,
    forum_user_prompt,
    forum_words,
)
from api.domain.polity.config import PolityConfigError, load_config, validate_config
from api.domain.polity.journal import JournalEvent
from api.domain.polity.llm_schemas import ForumTurn
from api.domain.polity.run_polity_simulation import run_simulation
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
    turn = {"rationale": "why", "post": "hello", "note_to_self": "n", "shift_issue": -1, "shift_direction": "none"}

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

    def __init__(self, shift: bool = False) -> None:
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
        return json.dumps({"rationale": "r", "post": f"hello from {cid}" if cid % 2 else "", "note_to_self": "", **shift})


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
