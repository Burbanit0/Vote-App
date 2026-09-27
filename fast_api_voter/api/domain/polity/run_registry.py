"""Run registry (S5.1): every simulation run on disk as one row of a DuckDB table, so
"which runs exist, what shape, how did they end" is one query instead of a walk through
directories with different contents.

Runs come in three generations, and a row is built from whatever its run has:

- `journal_only` -- events.jsonl and a thin run_metadata.json (LLM provider and model
  only); shape from the runner's outer config.json / metrics.json when present.
- `checkpointed` -- adds checkpoint.json, progress.json and (Track C) digest.json.
- `provenanced` -- S0.4's run_metadata.json (commit, server, run shape) and, for LLM
  runs, S0.5's llm_calls.jsonl.

Each field is read from the best source that has it, in order; a field no source has is
null. A file that is missing or unreadable is treated as absent, never as an error --
a registry that crashes on one damaged run lists none.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

from api.domain.polity.explorer_paths import inside

COLUMNS: tuple[tuple[str, str], ...] = (
    ("run_id", "VARCHAR"),
    ("run_dir", "VARCHAR"),
    ("generation", "VARCHAR"),
    ("outcome", "VARCHAR"),
    ("engine", "VARCHAR"),
    ("provider", "VARCHAR"),
    ("model", "VARCHAR"),
    ("population", "INTEGER"),
    ("years", "INTEGER"),
    ("seed", "BIGINT"),
    ("sortition_seats", "INTEGER"),
    ("ticks_planned", "INTEGER"),
    ("ticks_reached", "INTEGER"),
    ("decisions", "BIGINT"),
    ("retries", "BIGINT"),
    ("fallbacks", "BIGINT"),
    ("fallback_alerts", "VARCHAR"),
    ("office_occupancy", "DOUBLE"),
    ("elapsed_seconds", "DOUBLE"),
    ("started_at", "VARCHAR"),
    ("git_sha", "VARCHAR"),
    ("git_dirty", "BOOLEAN"),
    ("vllm_version", "VARCHAR"),
    ("served_model_revision", "VARCHAR"),
    ("llm_calls", "BIGINT"),
    ("llm_calls_bytes", "BIGINT"),
    ("events_bytes", "BIGINT"),
)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _first(*values: Any) -> Any:
    return next((value for value in values if value is not None), None)


def _last_journaled_tick(journal: Path) -> int | None:
    """The last line's tick, read from the end of the file -- a p500 journal is
    hundreds of megabytes, and only its last complete line is needed."""
    try:
        with journal.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(size - 65536, 0))
            lines = [line for line in handle.read().splitlines() if line.strip()]
    except OSError:
        return None
    for line in reversed(lines):
        try:
            tick = json.loads(line).get("tick")
        except ValueError:
            continue  # a torn final line from an interrupted write
        return tick if isinstance(tick, int) else None
    return None


@dataclass(frozen=True)
class _RunFiles:
    """Every JSON source a run directory (and the runner's outer directory) can hold."""

    run_dir: Path
    metadata: dict[str, Any]
    progress: dict[str, Any]
    digest: dict[str, Any]
    run_config: dict[str, Any]
    meta: dict[str, Any]
    call_summary: dict[str, Any]

    @classmethod
    def read(cls, run_dir: Path, confine: Path | None = None) -> _RunFiles:
        """Every JSON source of `run_dir`. With `confine`, a file that resolves outside
        that root reads as absent, and the runner's outer directory is skipped when it
        sits outside it -- the explorer serves roots it does not own (see
        api/domain/polity/explorer_paths.py)."""
        def read_json(path: Path) -> dict[str, Any]:
            return _read_json(path) if confine is None or inside(path, confine) else {}

        outer = run_dir.parent.parent if run_dir.parent.name == "run" else None
        if outer is not None and confine is not None and not inside(outer, confine):
            outer = None
        inner_config = read_json(run_dir / "config.json")
        outer_config = read_json(outer / "config.json") if outer is not None else {}
        metrics = read_json(outer / "metrics.json") if outer is not None else {}
        return cls(
            run_dir=run_dir,
            metadata=read_json(run_dir / "run_metadata.json"),
            progress=read_json(run_dir / "progress.json"),
            digest=read_json(run_dir / "digest.json"),
            run_config=dict((inner_config or outer_config).get("run") or {}),
            meta=dict(metrics.get("_meta") or {}),
            call_summary=read_json(run_dir / "llm_calls_summary.json"),
        )

    def generation(self) -> str:
        if "git_sha" in self.metadata:
            return "provenanced"
        if self.progress or (self.run_dir / "checkpoint.json").exists():
            return "checkpointed"
        return "journal_only"

    def engine(self) -> str | None:
        llm_enabled = self.metadata.get("llm_enabled")
        engine = _first(
            self.metadata.get("engine"),
            None if llm_enabled is None else ("llm" if llm_enabled else "deterministic"),
            self.meta.get("engine"),
        )
        return None if engine is None else str(engine)

    def shape(self) -> dict[str, Any]:
        years = _first(self.metadata.get("duration_years"), self.run_config.get("duration_years"), self.meta.get("duration_years"))
        ticks_per_year = _first(self.metadata.get("ticks_per_year"), self.run_config.get("ticks_per_year"))
        return {
            "population": _first(self.metadata.get("population_size"), self.run_config.get("population_size"), self.meta.get("population_size")),
            "years": years,
            "seed": _first(self.metadata.get("seed"), self.run_config.get("seed"), self.meta.get("seed")),
            "sortition_seats": _first(self.metadata.get("sortition_seats"), self.meta.get("sortition_seats")),
            "ticks_planned": _first(
                self.metadata.get("total_ticks"), self.progress.get("total_ticks"),
                years * ticks_per_year if years is not None and ticks_per_year is not None else None,
            ),
        }

    def outcome_fields(self, journal: Path) -> dict[str, Any]:
        ticks = self.digest.get("ticks") or {}
        alerts = self.digest.get("llm_fallback_alerts")
        return {
            "outcome": self.digest.get("outcome"),
            "ticks_reached": _first(ticks.get("last_tick_journaled"), self.progress.get("tick"), _last_journaled_tick(journal)),
            "decisions": _first(self.progress.get("decisions_total"), self.meta.get("decisions_total")),
            "retries": _first(self.progress.get("retry_count"), self.digest.get("llm_retries")),
            "fallbacks": _first(self.progress.get("fallback_count"), self.digest.get("llm_fallbacks")),
            "fallback_alerts": None if alerts is None else json.dumps(alerts, sort_keys=True),
            "office_occupancy": self.digest.get("office_occupancy"),
            "elapsed_seconds": _first(
                self.digest.get("elapsed_seconds"), self.meta.get("elapsed_seconds"),
                self.progress.get("wall_clock_elapsed_seconds"),
            ),
        }


def run_record(run_dir: Path, confine: Path | None = None) -> dict[str, Any]:
    """One registry row for the run whose journal is `run_dir/events.jsonl`.

    `confine` is the root the run was found under: files resolving outside it are not
    read (the explorer passes it; the registry CLI, reading roots it owns, does not).
    """
    files = _RunFiles.read(run_dir, confine)
    journal = run_dir / "events.jsonl"
    metadata = files.metadata
    return {
        "run_id": _first(metadata.get("run_id"), files.meta.get("run_id"), run_dir.name),
        "run_dir": str(run_dir),
        "generation": files.generation(),
        "engine": files.engine(),
        "provider": _first(metadata.get("llm_provider"), files.meta.get("provider")),
        "model": _first(metadata.get("llm_model"), files.meta.get("model")),
        **files.shape(),
        **files.outcome_fields(journal),
        "started_at": metadata.get("started_at"),
        "git_sha": metadata.get("git_sha"),
        "git_dirty": metadata.get("git_dirty"),
        "vllm_version": metadata.get("vllm_version"),
        "served_model_revision": metadata.get("served_model_revision"),
        "llm_calls": files.call_summary.get("calls"),
        "llm_calls_bytes": files.call_summary.get("bytes"),
        "events_bytes": journal.stat().st_size if journal.exists() else None,
    }


def discover_runs(roots: Iterable[Path]) -> list[Path]:
    """Every directory under `roots` holding an events.jsonl, sorted by path."""
    found = {journal.parent for root in roots if root.is_dir() for journal in root.rglob("events.jsonl")}
    return sorted(found)


def build_registry(roots: Iterable[Path], connection: duckdb.DuckDBPyConnection | None = None) -> duckdb.DuckDBPyConnection:
    """A DuckDB connection (in memory unless one is given) with a `runs` table."""
    con = connection if connection is not None else duckdb.connect()
    con.execute("DROP TABLE IF EXISTS runs")
    con.execute("CREATE TABLE runs (" + ", ".join(f"{name} {kind}" for name, kind in COLUMNS) + ")")
    # DuckDB's table API, not an INSERT statement built as a string: bandit (B608) flags
    # any formatted SQL, placeholders only or not, and the API needs no SQL at all.
    table = con.table("runs")
    for run_dir in discover_runs(roots):
        table.insert(_row(run_record(run_dir)))
    return con


def _row(record: Mapping[str, Any]) -> list[Any]:
    return [record.get(name) for name, _ in COLUMNS]
