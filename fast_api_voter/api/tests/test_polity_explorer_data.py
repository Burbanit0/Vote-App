"""The run explorer's macro series, citizen biographies and run catalog (B2):
api/domain/polity/run_macro.py, explorer_biography.py and run_catalog.py."""
from __future__ import annotations

import json
import os
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from api.domain.polity.codebook import PressureAct, motif_labels
from api.domain.polity.events import INSTITUTIONAL_EVENT_TYPES
from api.domain.polity.explorer_biography import RATIONALE_LIMIT, SECTIONS, build_biography
from api.domain.polity.indexer import segment_terms
from api.domain.polity.run_catalog import (
    RunCache,
    RunRoot,
    RunRootsError,
    find_run,
    list_runs,
    load_run,
    parse_roots,
    run_key,
)
from api.domain.polity.run_explorer import RunView
from api.domain.polity.run_frames import load_run_frames
from api.domain.polity.run_macro import build_macro
from api.tests.polity_explorer_fixtures import explorer_runs

UNLIMITED = 10**9


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return explorer_runs(tmp_path_factory.mktemp("explorer"))


def _events(run_dir: Path) -> list[dict[str, Any]]:
    return RunView.load(run_dir).events


# ── macro ─────────────────────────────────────────────────────────────────

def test_the_standing_series_agrees_with_the_replayed_frames(runs: dict[str, Path]) -> None:
    for name in ("staggered", "invalidated", "deterministic"):
        view = RunView.load(runs[name])
        macro = build_macro(view.events, 40, view.last_tick)
        frames = load_run_frames(runs[name])
        assert [s.tick for s in macro.standings] == [f.tick for f in frames.frames]
        assert [s.president for s in macro.standings] == [f.president.citizen_id if f.president else None for f in frames.frames]
        for standing, frame in zip(macro.standings, frames.frames):
            acts = Counter(a for a in frame.act if a >= 0)
            assert standing.acts == tuple(acts.get(int(act), 0) for act in PressureAct)


def test_a_standing_carries_the_holder_s_reading_of_that_tick(runs: dict[str, Path]) -> None:
    view = RunView.load(runs["staggered"])
    macro = build_macro(view.events, 40, view.last_tick)
    readings = {(e["tick"], e["citizen_id"]): e["payload"] for e in view.events if e["event_type"] == "legitimacy_updated"}
    checked = 0
    for standing in macro.standings:
        reading = readings.get((standing.tick, standing.president))
        if reading is not None:
            assert (standing.legitimacy, standing.ecart, standing.mandate_strength) == (
                reading["legitimacy"], reading["ecart"], reading["mandate_strength"])
            checked += 1
        elif standing.president is None:
            assert standing.legitimacy is None
    assert checked >= 3


def test_elections_carry_turnout_and_a_blank_share_with_its_source(runs: dict[str, Path]) -> None:
    def elections(name: str) -> tuple[Any, ...]:
        view = RunView.load(runs[name])
        return build_macro(view.events, 40, view.last_tick).elections

    staggered = elections("staggered")
    assert {e.outcome for e in staggered} == {"elected"} and all(e.winner is not None for e in staggered)
    assert all((e.blank_source, e.turnout) == ("ballots", 1.0) and e.blank_share == 0.0 for e in staggered)  # the fake never votes blank

    invalidated = elections("invalidated")
    checks = [e for e in invalidated if e.outcome == "invalidated"]
    assert checks and all(e.blank_source == "invalidation_check" and e.blank_share == 1.0 and e.turnout is None for e in checks)
    assert all(e.winner is None for e in invalidated)
    assert any(e.forced and e.outcome == "no_winner" and e.blank_source == "ballots" for e in invalidated)

    assert {e.blank_source for e in elections("audited")} == {"audit_sample"}
    assert {(e.blank_source, e.blank_share) for e in elections("deterministic")} == {(None, None)}


def test_turnout_counts_abstainers_and_an_empty_field_holds_no_vote() -> None:
    events = [
        {"tick": 0, "event_type": "elected", "citizen_id": 3, "payload": {"office": "president", "abstained": 10}},
        {"tick": 4, "event_type": "election_no_winner", "citizen_id": None, "payload": {"office": "president", "reason": "no_candidates"}},
        {"tick": 5, "event_type": "election_invalidated", "citizen_id": None,
         "payload": {"office": "president", "blank_share": None, "threshold": 0.5, "attempt": 1, "candidate_ids": [],
                     "barred_candidate_ids": [], "next_attempt_tick": 6}},
        {"tick": 8, "event_type": "legislative_result", "citizen_id": None, "payload": {"seats": {}, "votes": {}, "blank_count": 0}},
        {"tick": 8, "event_type": "legislative_result", "citizen_id": None,
         "payload": {"seats": {"0": 3, "1": 2}, "votes": {"0": 30.0, "1": 20.0}, "blank_count": 50}},
    ]
    macro = build_macro(events, 40, 8)
    assert [(e.outcome, e.turnout, e.blank_share) for e in macro.elections] == [
        ("elected", 0.75, None), ("no_winner", None, None), ("invalidated", None, None)]
    assert [(p.seats, p.blank_rate) for p in macro.legislative] == [({}, None), ({0: 3, 1: 2}, 0.5)]


def test_terms_and_the_timeline_lay_out_the_institutional_story(runs: dict[str, Path]) -> None:
    view = RunView.load(runs["staggered"])
    macro = build_macro(view.events, 40, view.last_tick)
    assert [(t.holder, t.start_tick, t.end_tick, t.ended_by) for t in macro.terms] == [
        (t.holder_id, t.start_tick, t.end_tick, t.ended_by) for t in segment_terms(view.events, view.last_tick)]
    expected = [e for e in view.events if e["event_type"] in INSTITUTIONAL_EVENT_TYPES | {"sortition_rotation"}]
    assert [(t.tick, t.event_type) for t in macro.timeline] == [(e["tick"], e["event_type"]) for e in expected]
    rotation = next(t for t in macro.timeline if t.event_type == "sortition_rotation")
    assert "seated" not in rotation.details and "pool_relaxed" in rotation.details  # scalars only
    assert any(t.event_type == "recalled" for t in macro.timeline)


# ── biography ─────────────────────────────────────────────────────────────

def test_a_president_s_biography_sorts_their_story_and_counts_the_pressure_on_them(runs: dict[str, Path]) -> None:
    view = RunView.load(runs["staggered"])
    president = next(e["citizen_id"] for e in view.events if e["event_type"] == "elected")
    biography = build_biography(view, president)
    assert tuple(biography.sections) == SECTIONS
    assert any(entry.event_type == "elected" for entry in biography.sections["roles"])
    assert any(entry.event_type == "candidacy_declared" for entry in biography.sections["candidacies"])
    assert all(entry.event_type == "vote_cast" and entry.role == "actor" for entry in biography.sections["votes"])
    decoded = [entry for section in biography.sections.values() for entry in section if entry.motif is not None]
    assert decoded and all(entry.motif_label == motif_labels()[entry.motif] for entry in decoded)
    assert all(isinstance(v, int | float | str | bool) or v is None for s in biography.sections.values() for e in s for v in e.details.values())

    named: Counter[tuple[int, str, int | None]] = Counter()
    for e in view.events:
        payload, actor = e.get("payload") or {}, e.get("citizen_id")
        if e["event_type"] in ("pressure_action", "petition_signed") and payload.get("target") == president and actor != president:
            named[(e["tick"], e["event_type"], payload.get("act"))] += 1
        elif e["event_type"] == "vote_cast" and president in payload["ranking"] and actor != president:
            named[(e["tick"], "vote_cast", payload["ranking"].index(president))] += 1
    assert Counter({(r.tick, r.event_type, r.code): r.count for r in biography.received}) == named
    assert {"pressure_action", "vote_cast"} <= {kind for _, kind, _ in named}
    assert [c.year for c in biography.census] == [0, 1, 2, 3]


def test_a_rationale_is_cut_short_and_an_unknown_motif_stays_undecoded(runs: dict[str, Path], tmp_path: Path) -> None:
    run_dir = Path(shutil.copytree(runs["deterministic"], tmp_path / "run"))
    long_reason = "because " * 100
    with (run_dir / "events.jsonl").open("a") as handle:
        for event_id, (motif, rationale, event_type) in enumerate(
            [("104", long_reason, "vote_cast"), ("not-a-code", "short", "scandal_occurred"), (None, None, "future_event")], start=10**6,
        ):
            handle.write(json.dumps({"event_id": event_id, "tick": 12, "citizen_id": 2, "event_type": event_type, "motif": motif,
                                     "rationale": rationale, "payload": {"blank": 0, "ranking": [1]}}) + "\n")
    biography = build_biography(RunView.load(run_dir), 2)
    [vote] = [e for e in biography.sections["votes"] if e.tick == 12]
    assert vote.rationale is not None and len(vote.rationale) == RATIONALE_LIMIT and vote.rationale.endswith("…")
    assert (vote.motif, vote.motif_label) == (104, motif_labels()[104])
    others = [e for e in biography.sections["other"] if e.tick == 12]
    assert [(e.event_type, e.motif, e.rationale) for e in others] == [("scandal_occurred", None, "short"), ("future_event", None, None)]


# ── catalog ───────────────────────────────────────────────────────────────

def test_run_roots_are_label_path_pairs() -> None:
    assert parse_roots(" p500=/data/p500, fixture=/srv/fixture ,") == (
        RunRoot("p500", Path("/data/p500")), RunRoot("fixture", Path("/srv/fixture")))
    assert parse_roots("") == ()
    for bad in ("/no/label", "bad label=/x", "a=", "a=/x,a=/y"):
        with pytest.raises(RunRootsError):
            parse_roots(bad)
    assert run_key("p500", "seed2/run") == run_key("p500", "seed2/run") != run_key("fixture", "seed2/run")


def _root_with(runs: dict[str, Path], tmp_path: Path, names: list[str]) -> Path:
    root = tmp_path / "root"
    for name in names:
        shutil.copytree(runs[name], root / "batch" / name)
    return root


def test_the_catalog_lists_explorable_runs_under_their_keys(runs: dict[str, Path], tmp_path: Path) -> None:
    root = _root_with(runs, tmp_path, ["staggered", "deterministic"])
    (root / "no-census").mkdir()
    shutil.copy(runs["staggered"] / "events.jsonl", root / "no-census" / "events.jsonl")
    shutil.copy(runs["staggered"] / "config.json", root / "no-census" / "config.json")
    roots = [RunRoot("lab", root)]

    entries = list_runs(roots, UNLIMITED)
    assert [(e.relative_path, e.key) for e in entries] == [
        ("batch/deterministic", run_key("lab", "batch/deterministic")), ("batch/staggered", run_key("lab", "batch/staggered"))]
    assert entries[1].record["run_id"] == "staggered"
    small = (root / "batch" / "deterministic" / "events.jsonl").stat().st_size
    assert [e.relative_path for e in list_runs(roots, small)] == ["batch/deterministic"]  # the larger journal is left out

    assert find_run(roots, entries[1].key, UNLIMITED) == entries[1]
    assert find_run(roots, "0" * 16, UNLIMITED) is None
    assert find_run(roots, "../../etc/passwd", UNLIMITED) is None


def test_the_catalog_does_not_follow_a_symlink_out_of_its_root(runs: dict[str, Path], tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = Path(shutil.copytree(runs["deterministic"], tmp_path / "outside"))
    os.symlink(outside, root / "linked-run", target_is_directory=True)
    half = root / "half-linked"
    shutil.copytree(runs["deterministic"], half)
    (half / "events.jsonl").unlink()
    os.symlink(outside / "events.jsonl", half / "events.jsonl")
    listed = list_runs([RunRoot("lab", root)], UNLIMITED)
    assert [e.relative_path for e in listed] == []


def test_a_loaded_run_is_cached_until_its_journal_changes(runs: dict[str, Path], tmp_path: Path) -> None:
    root = _root_with(runs, tmp_path, ["staggered", "deterministic", "audited"])
    cache = RunCache(capacity=2)
    staggered = root / "batch" / "staggered"
    first = cache.get(staggered)
    assert cache.get(staggered) is first and len(cache) == 1
    assert first.biography(first.frames.frames[0].president.citizen_id).census  # type: ignore[union-attr]

    with (staggered / "events.jsonl").open("a") as handle:
        handle.write("\n")
    assert cache.get(staggered) is not first

    cache.get(root / "batch" / "deterministic")
    cache.get(root / "batch" / "audited")
    assert len(cache) == 2 and cache.get(root / "batch" / "audited") is cache.get(root / "batch" / "audited")


def test_a_loaded_run_holds_frames_and_macro_of_the_same_run(runs: dict[str, Path]) -> None:
    loaded = load_run(runs["audited"])
    assert loaded.frames.run_id == loaded.view.run_id == "audited"
    assert len(loaded.macro.standings) == len(loaded.frames.frames)
