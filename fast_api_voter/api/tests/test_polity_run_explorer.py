"""Run explorer data and notebook (S5.2). See api/domain/polity/run_explorer.py."""
from __future__ import annotations

import dataclasses
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

from api.domain.polity.run_explorer import (
    RunView,
    citizen_biography,
    citizen_census,
    cross_seed_rows,
    events_of_type,
    officeholder_at,
    run_choices,
    term_rows,
    tick_summary,
)
from api.domain.polity.run_polity_simulation import run_simulation
from api.domain.polity.run_registry import build_registry
from api.tests.test_polity_run_simulation import _config_with_legitimacy_enabled_and_guaranteed_winners

BACKEND = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    config = _config_with_legitimacy_enabled_and_guaranteed_winners(tmp_path_factory.mktemp("explorer") / "sweep_runs")
    config = dataclasses.replace(config, run=dataclasses.replace(config.run, duration_years=4, population_size=40))
    return run_simulation(config, run_id="explored").parent


def test_a_run_view_has_its_journal_census_and_terms(run_dir: Path) -> None:
    view = RunView.load(run_dir)
    assert view.run_id == "explored" and view.events and view.snapshots
    assert view.last_tick == view.ticks_planned
    rows = term_rows(view)
    assert rows and rows[0]["start_tick"] == 0
    assert all(row["ticks"] == row["end_tick"] - row["start_tick"] for row in rows)


def test_the_tick_summary_names_the_president_and_what_happened(run_dir: Path) -> None:
    view = RunView.load(run_dir)
    first = term_rows(view)[0]
    summary = tick_summary(view, 0)
    assert summary["president"] == officeholder_at(view, 0) == first["holder"]
    assert "elected" in [e["event_type"] for e in summary["institutional"]]
    assert sum(summary["events"].values()) == len([e for e in view.events if e["tick"] == 0])
    assert summary["llm_decisions"] == 0  # deterministic run
    assert officeholder_at(view, view.last_tick + 50) is None


def test_a_citizen_biography_covers_what_they_did_and_what_was_done_to_them(run_dir: Path) -> None:
    view = RunView.load(run_dir)
    president = term_rows(view)[0]["holder"]
    biography = citizen_biography(view, president)
    roles = {row["role"] for row in biography}
    assert "actor" in roles  # elected, legitimacy_updated, ...
    assert [row["tick"] for row in biography] == sorted(row["tick"] for row in biography)
    census = citizen_census(view, president)
    assert census and census[0]["year"] == 0
    assert citizen_biography(view, 10_000) == []
    assert events_of_type(view, ["elected"]) == [e for e in view.events if e["event_type"] == "elected"]


def test_the_cross_seed_panel_and_the_run_picker_read_the_registry(run_dir: Path) -> None:
    registry = build_registry([run_dir.parent])
    [row] = cross_seed_rows(registry, completed_only=False)
    assert (row["engine"], row["population"], row["runs"]) == ("deterministic", 40, 1)
    assert cross_seed_rows(registry) == []  # no digest, so not "completed"
    assert list(run_choices(registry).values()) == [str(run_dir)]


@pytest.mark.skipif(importlib.util.find_spec("marimo") is None, reason="marimo is a dev dependency")
def test_the_notebook_runs_headless_on_a_real_run(run_dir: Path) -> None:
    code = (
        "import sys; sys.path.insert(0, 'scripts'); import run_explorer; "
        "outputs, defs = run_explorer.app.run(); print(defs['view'].run_id, len(outputs))"
    )
    env = {**os.environ, "POLITY_RUN_ROOTS": str(run_dir.parent), "POLITY_EXPLORER_RUN": str(run_dir)}
    completed = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=180)
    assert completed.returncode == 0, completed.stderr[-2000:]
    assert completed.stdout.split()[:1] == ["explored"]


def test_biography_roles_and_a_damaged_or_missing_census(tmp_path: Path) -> None:
    from api.domain.polity.run_explorer import _read_snapshots

    events = [
        {"event_id": 1, "tick": 2, "event_type": "pressure_action", "citizen_id": 5, "payload": {"target": 9, "act": 3}},
        {"event_id": 2, "tick": 3, "event_type": "sortition_rotation", "citizen_id": None, "payload": {"seated": [9, 4], "vacated": []}},
        {"event_id": 3, "tick": 3, "event_type": "legitimacy_updated", "citizen_id": 4, "payload": {"legitimacy": 0.5}},
    ]
    view = RunView(run_dir=tmp_path, run_id="synthetic", events=events, snapshots=[], ticks_planned=4, last_tick=3, terms=())
    assert [(row["event_id"], row["role"]) for row in citizen_biography(view, 9)] == [(1, "target"), (2, "listed")]

    assert _read_snapshots(tmp_path / "missing.jsonl") == []
    census = tmp_path / "snapshots.jsonl"
    census.write_text('{"citizen_id": 9, "year": 0}\n{"citizen_id": 9, "ye', encoding="utf-8")
    assert _read_snapshots(census) == [{"citizen_id": 9, "year": 0}]
