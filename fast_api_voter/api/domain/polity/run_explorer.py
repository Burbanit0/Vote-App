"""Data for the marimo run explorer (S5.2, scripts/run_explorer.py): one run read into
views a person can browse -- the state at a tick, the term timeline, one citizen's
biography -- and a panel comparing runs of the same shape across seeds.

Everything here is a pure function of files already on disk (events.jsonl,
snapshots.jsonl, the run registry), so the notebook stays a thin layer of widgets and
the logic is tested like the rest of the domain.
"""
from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

from api.domain.polity.events import INSTITUTIONAL_EVENT_TYPES, LLM_DECISION_EVENT_TYPES
from api.domain.polity.indexer import Term, segment_terms
from api.domain.polity.run_digest import read_journal_tolerant
from api.domain.polity.run_registry import run_record

_CITIZEN_LIST_KEYS = ("seated", "vacated", "contenders", "candidate_ids", "barred_candidate_ids", "ranking")


@dataclass(frozen=True)
class RunView:
    run_dir: Path
    run_id: str
    events: list[dict[str, Any]]
    snapshots: list[dict[str, Any]]
    ticks_planned: int | None
    last_tick: int
    terms: tuple[Term, ...]

    @classmethod
    def load(cls, run_dir: Path) -> RunView:
        events, _skipped = read_journal_tolerant(run_dir / "events.jsonl")
        last_tick = max((e["tick"] for e in events), default=0)
        record = run_record(run_dir)
        return cls(
            run_dir=run_dir,
            run_id=str(record["run_id"]),
            events=events,
            snapshots=_read_snapshots(run_dir / "snapshots.jsonl"),
            ticks_planned=record["ticks_planned"],
            last_tick=last_tick,
            terms=segment_terms(events, last_tick),
        )


def _read_snapshots(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue  # a torn final row from an interrupted write
    return rows


def term_rows(view: RunView) -> list[dict[str, Any]]:
    """The presidency, term by term."""
    return [
        {
            "holder": term.holder_id,
            "start_tick": term.start_tick,
            "end_tick": term.end_tick,
            "ticks": term.end_tick - term.start_tick,
            "ended_by": term.ended_by,
            "mandate_strength": term.mandate_strength,
            "lame_duck": term.lame_duck,
        }
        for term in view.terms
    ]


def officeholder_at(view: RunView, tick: int) -> int | None:
    """The president holding office at `tick` (a term covers [start, end))."""
    return next((t.holder_id for t in view.terms if t.start_tick <= tick < t.end_tick), None)


def tick_summary(view: RunView, tick: int) -> dict[str, Any]:
    """What the polity looked like at one tick: who governed, with what standing, and
    what happened."""
    at_tick = [e for e in view.events if e["tick"] == tick]
    holder = officeholder_at(view, tick)
    return {
        "tick": tick,
        "president": holder,
        "legitimacy": _holder_legitimacy(at_tick, holder),
        "events": dict(sorted(Counter(e["event_type"] for e in at_tick).items())),
        "institutional": _institutional_entries(at_tick),
        "llm_decisions": sum(1 for e in at_tick if _is_model_decision(e)),
        "llm_fallbacks": sum(1 for e in at_tick if (e.get("payload") or {}).get("llm_fallback")),
    }


def _holder_legitimacy(events: Sequence[Mapping[str, Any]], holder: int | None) -> float | None:
    updates = [e for e in events if e["event_type"] == "legitimacy_updated" and e.get("citizen_id") == holder]
    return updates[0]["payload"].get("legitimacy") if updates else None


def _institutional_entries(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"event_id": e.get("event_id"), "event_type": e["event_type"], "citizen_id": e.get("citizen_id"), "payload": e["payload"]}
        for e in events
        if e["event_type"] in INSTITUTIONAL_EVENT_TYPES
    ]


def _is_model_decision(event: Mapping[str, Any]) -> bool:
    return event["event_type"] in LLM_DECISION_EVENT_TYPES and bool(event.get("codebook_version"))


def _role_in(event: Mapping[str, Any], citizen_id: int) -> str | None:
    payload = event.get("payload") or {}
    if event.get("citizen_id") == citizen_id:
        return "actor"
    if payload.get("target") == citizen_id:
        return "target"
    if any(isinstance(payload.get(key), list) and citizen_id in payload[key] for key in _CITIZEN_LIST_KEYS):
        return "listed"
    return None


def citizen_biography(view: RunView, citizen_id: int) -> list[dict[str, Any]]:
    """Every event this citizen acted in, was targeted by, or was named in, in order."""
    rows = []
    for event in view.events:
        role = _role_in(event, citizen_id)
        if role is not None:
            rows.append({
                "tick": event["tick"],
                "event_id": event.get("event_id"),
                "event_type": event["event_type"],
                "role": role,
                "motif": event.get("motif"),
                "payload": json.dumps(event.get("payload"), sort_keys=True),
            })
    return rows


def citizen_census(view: RunView, citizen_id: int) -> list[dict[str, Any]]:
    """The citizen's yearly snapshot rows: role, office, party, salience."""
    return [
        {key: row.get(key) for key in ("year", "tick", "role", "office", "party_affiliation", "event_salience")}
        for row in view.snapshots
        if row.get("citizen_id") == citizen_id
    ]


def cross_seed_rows(registry: duckdb.DuckDBPyConnection, *, completed_only: bool = True) -> list[dict[str, Any]]:
    """Runs of the same shape (engine, population, years) compared across seeds."""
    result = registry.execute(
        "SELECT engine, population, years, count(*) AS runs, count(DISTINCT seed) AS seeds, "
        "round(avg(office_occupancy), 4) AS occupancy_mean, round(min(office_occupancy), 4) AS occupancy_min, "
        "round(max(office_occupancy), 4) AS occupancy_max, sum(fallbacks) AS fallbacks, "
        "round(avg(elapsed_seconds) / 3600, 2) AS hours_mean "
        "FROM runs WHERE NOT ? OR outcome = 'completed' "
        "GROUP BY engine, population, years ORDER BY population, years, engine",
        [completed_only],
    )
    columns = [column[0] for column in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


def run_choices(registry: duckdb.DuckDBPyConnection) -> dict[str, str]:
    """run label -> run directory, for a picker."""
    rows = registry.execute("SELECT run_id, run_dir, generation, outcome FROM runs ORDER BY run_dir").fetchall()
    return {f"{run_id} ({generation}, {outcome or 'no digest'}) -- {run_dir}": run_dir for run_id, run_dir, generation, outcome in rows}


def events_of_type(view: RunView, event_types: Sequence[str]) -> list[dict[str, Any]]:
    wanted = set(event_types)
    return [e for e in view.events if e["event_type"] in wanted]
