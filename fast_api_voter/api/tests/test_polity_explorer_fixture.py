"""The run explorer's committed fixture run (B3): polity_fixtures/runs/explorer-fixture,
written by scripts/gen_polity_explorer_fixture.py. It is not regenerated here (its floats
can differ in the last bits across BLAS builds); these tests pin what it is instead."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from api.domain.polity.checkpoint import config_hash
from api.domain.polity.codebook import PressureAct
from api.domain.polity.run_catalog import RunRoot, list_runs, load_run, run_key
from api.tests.polity_explorer_fixtures import (
    FIXTURE_MANIFEST,
    FIXTURE_ROOT,
    FIXTURE_RUN_ID,
    file_digests,
    fixture_config,
    replay_mismatches,
)

RUN_DIR = FIXTURE_ROOT / FIXTURE_RUN_ID


def _manifest() -> dict[str, object]:
    manifest: dict[str, object] = json.loads((RUN_DIR / FIXTURE_MANIFEST).read_text(encoding="utf-8"))
    return manifest


def test_the_fixture_files_are_the_ones_its_manifest_records(tmp_path: Path) -> None:
    manifest = _manifest()
    assert manifest["files"] == file_digests(RUN_DIR), "regenerate with scripts/gen_polity_explorer_fixture.py"
    assert manifest["config_hash"] == config_hash(fixture_config(tmp_path)), "the fixture's config changed without a regeneration"
    assert set(file_digests(RUN_DIR)) == {"checkpoint.json", "config.json", "events.jsonl", "progress.json", "run_metadata.json", "snapshots.jsonl"}


def test_the_fixture_replays_and_holds_no_machine_path() -> None:
    assert replay_mismatches(RUN_DIR) == []
    for path in RUN_DIR.iterdir():
        text = path.read_text(encoding="utf-8")
        assert "/tmp/" not in text and "/home/" not in text, path.name


def test_the_fixture_is_the_one_run_its_root_lists() -> None:
    [entry] = list_runs([RunRoot("fixture", FIXTURE_ROOT)], max_journal_bytes=1_000_000)
    assert (entry.relative_path, entry.key, entry.record["run_id"]) == (FIXTURE_RUN_ID, run_key("fixture", FIXTURE_RUN_ID), FIXTURE_RUN_ID)


def test_the_fixture_holds_what_the_explorer_pages_show() -> None:
    loaded = load_run(RUN_DIR)
    events = loaded.view.events
    kinds = Counter(e["event_type"] for e in events)
    assert kinds["elected"] >= 3 and kinds["recalled"] >= 1 and kinds["snap_election_triggered"] >= 1
    assert kinds["petition_launched"] >= 1 and kinds["sortition_rotation"] >= 1 and kinds["nomination_lost"] >= 1
    assert {int(e["payload"]["act"]) for e in events if e["event_type"] == "pressure_action"} == {int(a) for a in PressureAct}
    assert any(e["payload"]["blank"] for e in events if e["event_type"] == "vote_cast")
    assert not any(e["payload"].get("llm_fallback") for e in events)
    assert loaded.frames.vote_coverage == "all" and loaded.frames.projection.method == "latent"
    assert len(loaded.frames.frames) == 13 and not any(frame.partial for frame in loaded.frames.frames)
    assert any(frame.president is None for frame in loaded.frames.frames)  # between a recall and its snap election
