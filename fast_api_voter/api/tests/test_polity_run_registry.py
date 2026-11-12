"""Run registry (S5.1). See api/domain/polity/run_registry.py."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from api.domain.polity.run_polity_simulation import run_simulation
from api.domain.polity.run_registry import COLUMNS, build_registry, discover_runs, run_record
from api.tests.test_polity_run_simulation import _config_with_output_dir


def _write(path: Path, content: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")


def _flagship_layout(root: Path, run_id: str) -> Path:
    """<root>/<run_id>/run/<run_id>/, the flagship runner's layout."""
    run_dir = root / run_id / "run" / run_id
    run_dir.mkdir(parents=True)
    return run_dir


def test_a_journal_only_run_takes_its_shape_from_the_runners_outer_files(tmp_path: Path) -> None:
    run_dir = _flagship_layout(tmp_path, "old-run")
    _write(run_dir / "events.jsonl", '{"tick": 0}\n{"tick": 3}\n{"tick": 5}\n{"tick": 6, "torn')
    _write(run_dir / "run_metadata.json", {"run_id": "old-run", "llm_enabled": True, "llm_provider": "vllm", "llm_model": "qwen3:8b"})
    _write(tmp_path / "old-run" / "config.json", {"run": {"seed": 42, "ticks_per_year": 4, "duration_years": 2, "population_size": 100}})
    _write(tmp_path / "old-run" / "metrics.json", {"_meta": {"decisions_total": 77, "elapsed_seconds": 12.5}})

    record = run_record(run_dir)

    assert record["generation"] == "journal_only"
    assert (record["engine"], record["provider"], record["model"]) == ("llm", "vllm", "qwen3:8b")
    assert (record["population"], record["years"], record["seed"], record["ticks_planned"]) == (100, 2, 42, 8)
    assert record["ticks_reached"] == 5  # the torn final line is skipped, not fatal
    assert (record["decisions"], record["elapsed_seconds"]) == (77, 12.5)
    assert record["outcome"] is None and record["git_sha"] is None


def test_a_checkpointed_run_reports_its_outcome_and_llm_quality(tmp_path: Path) -> None:
    run_dir = _flagship_layout(tmp_path, "mid-run")
    _write(run_dir / "events.jsonl", '{"tick": 32}\n')
    _write(run_dir / "run_metadata.json", {"run_id": "mid-run", "llm_enabled": False})
    _write(run_dir / "checkpoint.json", {})
    _write(run_dir / "progress.json", {"tick": 32, "total_ticks": 32, "decisions_total": 0, "retry_count": 0, "fallback_count": 0})
    _write(run_dir / "digest.json", {
        "outcome": "crashed", "ticks": {"last_tick_journaled": 31}, "office_occupancy": 0.75,
        "llm_fallback_alerts": {"vote_cast": 0.2}, "elapsed_seconds": 99.0,
    })
    _write(run_dir / "llm_calls_summary.json", "not json at all")  # damaged: ignored, not fatal

    record = run_record(run_dir)

    assert (record["generation"], record["engine"], record["outcome"]) == ("checkpointed", "deterministic", "crashed")
    assert (record["ticks_reached"], record["ticks_planned"]) == (31, 32)
    assert (record["office_occupancy"], record["fallback_alerts"]) == (0.75, '{"vote_cast": 0.2}')
    assert record["llm_calls"] is None


def test_a_provenanced_run_carries_its_commit_and_shape(tmp_path: Path) -> None:
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(config, run=dataclasses.replace(config.run, duration_years=1, population_size=30, seed=9))
    journal = run_simulation(config, run_id="fresh")

    record = run_record(journal.parent)

    assert (record["generation"], record["engine"]) == ("provenanced", "deterministic")
    assert (record["population"], record["years"], record["seed"]) == (30, 1, 9)
    assert record["ticks_reached"] == record["ticks_planned"] == config.run.total_ticks
    assert record["events_bytes"] == journal.stat().st_size
    assert record["started_at"]


def test_the_registry_is_one_duckdb_table_over_every_root(tmp_path: Path) -> None:
    for name in ("b-run", "a-run"):
        run_dir = _flagship_layout(tmp_path / "flagship_runs", name)
        _write(run_dir / "events.jsonl", '{"tick": 1}\n')
    _write(tmp_path / "sweep_runs" / "notes" / "INVALID.md", "no journal here")

    roots = [tmp_path / "flagship_runs", tmp_path / "sweep_runs", tmp_path / "missing_runs"]
    assert [p.name for p in discover_runs(roots)] == ["a-run", "b-run"]
    con = build_registry(roots)
    assert [c[0] for c in con.execute("DESCRIBE runs").fetchall()] == [name for name, _ in COLUMNS]
    assert con.execute("SELECT run_id, ticks_reached FROM runs ORDER BY run_id").fetchall() == [("a-run", 1), ("b-run", 1)]
    assert build_registry([tmp_path / "missing_runs"]).execute("SELECT count(*) FROM runs").fetchone() == (0,)


def test_an_empty_or_unreadable_journal_has_no_last_tick(tmp_path: Path) -> None:
    run_dir = _flagship_layout(tmp_path, "empty")
    _write(run_dir / "events.jsonl", "")
    assert run_record(run_dir)["ticks_reached"] is None
    assert run_record(tmp_path / "nowhere")["ticks_reached"] is None
