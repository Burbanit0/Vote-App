"""Lot 8 — run_polity_simulation.py: orchestration + the reproducibility test.

Contracts (dev-plan-v0-worktree.md §3-4, Lot 8):
- Integration: a full 30-year run completes without error and produces a
  non-empty journal.
- Transversal, "the test that matters more than the others": two full runs
  with the same seed produce byte-identical journals.
"""
import dataclasses
import json

import pytest

from api.domain.polity.config import PolityConfig, load_config
from api.domain.polity.run_polity_simulation import run_simulation


def _config_with_output_dir(output_dir) -> PolityConfig:
    config = load_config()
    return dataclasses.replace(config, journal=dataclasses.replace(config.journal, output_dir=str(output_dir)))


def _events(journal_path):
    return [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]


def test_full_run_completes_and_produces_a_non_empty_journal(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    assert journal_path.is_file()
    lines = journal_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) > 0
    for line in lines:
        json.loads(line)  # every line is valid, complete JSON


def test_election_counts_match_the_calendar(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    events = _events(journal_path)
    presidential_outcomes = [e for e in events if e["event_type"] in ("elected", "election_no_winner")]
    legislative_results = [e for e in events if e["event_type"] == "legislative_result"]
    assert len(presidential_outcomes) == 8
    assert len(legislative_results) == 8


def test_every_legislative_result_allocates_all_seats(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    config = load_config()
    for event in _events(journal_path):
        if event["event_type"] == "legislative_result":
            assert sum(event["payload"]["seats"].values()) == config.institutions.assembly_seats


def test_two_runs_with_the_same_seed_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(_config_with_output_dir(tmp_path / "a"), run_id="same-run-id")
    path_b = run_simulation(_config_with_output_dir(tmp_path / "b"), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


def test_different_seed_produces_a_different_journal(tmp_path):
    config_a = _config_with_output_dir(tmp_path / "a")
    config_b = _config_with_output_dir(tmp_path / "b")
    config_b = dataclasses.replace(config_b, run=dataclasses.replace(config_b.run, seed=999))
    path_a = run_simulation(config_a, run_id="r")
    path_b = run_simulation(config_b, run_id="r")
    assert path_a.read_bytes() != path_b.read_bytes()


def _config_with_rupture_enabled(output_dir) -> PolityConfig:
    config = _config_with_output_dir(output_dir)
    return dataclasses.replace(
        config,
        candidacy=dataclasses.replace(
            config.candidacy,
            rupture_path_enabled=True,
            rupture_base_probability=0.05,
            rupture_signature_ratio=0.01,
        ),
    )


def test_rupture_path_produces_a_rupture_candidacy_event(tmp_path):
    journal_path = run_simulation(_config_with_rupture_enabled(tmp_path), run_id="rupture")
    events = _events(journal_path)
    rupture_events = [
        e for e in events if e["event_type"] == "candidacy_declared" and e["payload"].get("path") == "rupture"
    ]
    assert len(rupture_events) > 0


def test_two_runs_with_rupture_enabled_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(_config_with_rupture_enabled(tmp_path / "a"), run_id="same-run-id")
    path_b = run_simulation(_config_with_rupture_enabled(tmp_path / "b"), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


def test_unsupported_presidential_method_raises_before_any_work(tmp_path):
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(
        config, institutions=dataclasses.replace(config.institutions, presidential_method="star")
    )
    with pytest.raises(NotImplementedError, match="star"):
        run_simulation(config, run_id="r")
    assert not (tmp_path / "r").exists()
