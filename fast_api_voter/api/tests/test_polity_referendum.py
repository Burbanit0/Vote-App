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
