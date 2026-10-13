"""The referendum on a ratified voting-method change (ADR-020, roadmap 4.3)."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

from api.domain.polity import run_polity_simulation as engine
from api.domain.polity.amendments import referendum_count
from api.domain.polity.config import ARTICLES
from api.domain.polity.run_polity_simulation import run_simulation
from api.tests.test_polity_agents import _agent_run_config
from api.tests.test_polity_amendments import _amending, _ChamberClient, _of

_BALLOTS = [["A", "B", "C"]] * 4 + [["B", "C", "A"]] * 3 + [["C", "B", "A"]] * 2


def test_the_ballots_are_recounted_under_both_methods() -> None:
    assert referendum_count(_BALLOTS, "plurality", "borda") == (5, 4)  # A wins the plurality, B the Borda count
    assert referendum_count(_BALLOTS, "plurality", "plurality") is None
    assert "constitution.referendum" in ARTICLES


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str, counted: tuple[int, int] | None) -> tuple[Path, list[dict[str, Any]]]:
    config = _amending(_agent_run_config(tmp_path))
    config = dataclasses.replace(config, constitution=dataclasses.replace(config.constitution, referendum=mode))
    monkeypatch.setattr(engine, "referendum_count", lambda *_: counted)
    journal = run_simulation(config, run_id="referendum", llm_client=_ChamberClient("yes"))
    return journal, [json.loads(line) for line in journal.read_text().splitlines()]


@pytest.mark.parametrize(("mode", "counted", "held", "amended"), [
    ("never", (1, 10**6), None, True),
    ("always", None, None, True),
    ("always", (5, 3), "required", True),
    ("always", (3, 5), "required", False),
    ("petition", (1, 10**6), "petition", False),
    ("petition", (5, 0), None, True),
])
def test_the_citizens_confirm_or_overturn_what_the_chamber_ratified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str, counted: tuple[int, int] | None, held: str | None, amended: bool,
) -> None:
    journal, events = _run(tmp_path, monkeypatch, mode, counted)
    referendums = _of(events, "referendum_held")
    assert bool(_of(events, "constitution_amended")) == amended
    if held is None:
        assert not referendums
    else:
        payload = referendums[0]["payload"]
        assert counted is not None
        assert (payload["trigger"], payload["yes"], payload["no"], payload["passed"]) == (held, *counted, int(amended))
        assert _of(events, "amendment_resolved")[0]["payload"]["ratified"] == int(amended)
    assert json.loads((journal.parent / "checkpoint.json").read_text())["last_ballots"]


def test_the_referendum_is_a_new_vote_on_todays_opinions(tmp_path: Path) -> None:
    """ADR-029: the citizens vote now, each for the method whose winner they prefer today -- not a recount of the
    last election's ballots."""
    import numpy as np

    from api.domain.polity.citizen import Citizen
    from api.domain.polity.config import load_config
    from api.domain.polity.constitution import Proposal
    from api.domain.polity.journal import Journal
    from api.domain.polity.tick_state import TickState

    def citizen(cid: int, at: float) -> Citizen:
        return Citizen(citizen_id=cid, issue_positions=(at,), issue_priorities=(1.0,), blank_threshold=0.5, ambition_score=0.1)

    a, b, c = citizen(1, 0.2), citizen(2, 0.52), citizen(3, 0.8)
    last = [["citizen_1", "citizen_2", "citizen_3"]] * 5 + [["citizen_2", "citizen_3", "citizen_1"]] * 4
    assert referendum_count(last, "plurality", "borda") == (4, 5)  # recounted, the change to Borda would lose
    # Opinion has since moved: today the plurality still elects 1, the Borda count 2, and most rank 2 above 1.
    voters = [citizen(10 + i, x) for i, x in enumerate((0.1,) * 4 + (0.55,) * 2 + (0.9,) * 3)]
    state = TickState(citizens=[a, b, c, *voters], parties=[], rupture_rng=np.random.default_rng(0),
                      events_rng=np.random.default_rng(0), sortition_rng=np.random.default_rng(0), last_ballots=last)
    config = load_config()
    config = dataclasses.replace(config, constitution=dataclasses.replace(config.constitution, referendum="always"),
                                 institutions=dataclasses.replace(config.institutions, presidential_method="plurality"))
    proposal = Proposal(article="institutions.presidential_method", value="borda", proposer=1, tick=4, threshold=0.6, reason="")
    with Journal(tmp_path / "e.jsonl", "run") as journal:
        context = engine.TickContext(tick=5, config=config, journal=journal, client=None, clock=None, graph=None,  # type: ignore[arg-type]
                                     snapshots_path=tmp_path / "s.jsonl", election=None)
        assert engine._referendum(context, state, proposal)
    [held] = _of([json.loads(line) for line in (tmp_path / "e.jsonl").read_text().splitlines()], "referendum_held")
    assert (held["payload"]["yes"], held["payload"]["no"]) == (7, 5)  # every engaged citizen, the candidates included
