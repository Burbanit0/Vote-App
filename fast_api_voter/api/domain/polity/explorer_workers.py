"""Workers for /api/v2/polity/* (the run explorer): each takes the explorer's context and
the request's parameters and returns `(body, http_status)`, the domain-worker contract
the routes lift into responses (api/core/worker_dispatch.py).

Bodies carry run keys and paths relative to a run root, never an absolute path. Map
coordinates are rounded to four decimals: the page draws them, it does not compute with
them, and a population-500 run's frames stay small.
"""
from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from api.domain.polity.codebook import motif_labels
from api.domain.polity.run_catalog import (
    DEFAULT_RUN_ROOT,
    CatalogEntry,
    LoadedRun,
    RunCache,
    RunRoot,
    find_run,
    list_runs,
    parse_roots,
)
from api.domain.polity.run_frames import NotExplorable, TickFrame

MAX_FRAME_SPAN = 40
XY_DECIMALS = 4

Body = tuple[dict[str, Any], int]


@dataclass(frozen=True)
class ExplorerContext:
    roots: tuple[RunRoot, ...]
    max_journal_bytes: int
    cache: RunCache


def explorer_roots(spec: str) -> tuple[RunRoot, ...]:
    """The configured roots, or the committed fixture run's when none are."""
    return parse_roots(spec) or (RunRoot(label="fixture", path=DEFAULT_RUN_ROOT),)


def _xy(point: Sequence[float]) -> list[float]:
    return [round(float(point[0]), XY_DECIMALS), round(float(point[1]), XY_DECIMALS)]


def list_polity_runs(context: ExplorerContext) -> Body:
    runs = []
    for entry in list_runs(context.roots, context.max_journal_bytes):
        record = entry.record
        runs.append({
            "key": entry.key, "label": entry.label, "relative_path": entry.relative_path, "run_id": str(record["run_id"]),
            **{field: record.get(field) for field in (
                "generation", "engine", "outcome", "population", "years", "seed", "ticks_reached", "ticks_planned")},
        })
    return {"runs": runs}, 200


class _Refused(Exception):
    def __init__(self, error: str, status: int) -> None:
        super().__init__(error)
        self.body: Body = ({"error": error}, status)


def _load(context: ExplorerContext, run_key: str) -> tuple[CatalogEntry, LoadedRun]:
    entry = find_run(context.roots, run_key, context.max_journal_bytes)
    if entry is None:
        raise _Refused("run not found", 404)
    try:
        return entry, context.cache.get(entry.run_dir)
    except NotExplorable as exc:
        raise _Refused(f"run cannot be explored: {exc.reason}", 400) from exc


def _plain(value: Any) -> Any:
    return dataclasses.asdict(value)


def _map(loaded: LoadedRun) -> dict[str, Any]:
    """Where citizens and parties sit, and each citizen's party."""
    projection = loaded.frames.projection
    census_zero = sorted((r for r in loaded.view.snapshots if r.get("year") == 0), key=lambda r: int(r["citizen_id"]))
    return {
        "projection": {
            "method": projection.method, "positions": projection.positions,
            "axes": [[_plain(weight) for weight in axis] for axis in projection.axes],
            "citizens": [{"year": year, "xy": [_xy(p) for p in xy]} for year, xy in sorted(projection.citizen_xy.items())],
        },
        "parties": [{"party_id": party_id, "xy": _xy(projection.point_xy(platform))} for party_id, platform in loaded.parties],
        "citizen_parties": [row.get("party_affiliation") for row in census_zero],
    }


def _story(loaded: LoadedRun) -> dict[str, Any]:
    """The terms, the institutional timeline and the curves."""
    macro = loaded.macro
    return {
        "terms": [_plain(term) for term in macro.terms],
        "timeline": [{**_plain(entry), "details": dict(entry.details)} for entry in macro.timeline],
        "standings": [{**_plain(s), "acts": list(s.acts)} for s in macro.standings],
        "elections": [_plain(e) for e in macro.elections],
        "legislative": [
            {"tick": p.tick, "blank_rate": p.blank_rate, "seats": [{"party_id": k, "seats": v} for k, v in sorted(p.seats.items())]}
            for p in macro.legislative
        ],
    }


def _overview(entry: CatalogEntry, loaded: LoadedRun) -> dict[str, Any]:
    frames = loaded.frames
    return {
        "key": entry.key, "label": entry.label, "run_id": frames.run_id, "population": frames.population,
        "ticks_per_year": frames.ticks_per_year, "last_tick": len(frames.frames) - 1,
        "last_checkpoint_tick": frames.last_checkpoint_tick, "vote_coverage": frames.vote_coverage,
        "unknown_event_types": list(frames.unknown_event_types),
        **_map(loaded), **_story(loaded),
        "motifs": [{"code": code, "label": label} for code, label in motif_labels().items()],
    }


def polity_run_overview(context: ExplorerContext, run_key: str) -> Body:
    try:
        entry, run = _load(context, run_key)
    except _Refused as refused:
        return refused.body
    return _overview(entry, run), 200


def _frame(frame: TickFrame) -> dict[str, Any]:
    president = frame.president
    return {
        "tick": frame.tick, "partial": frame.partial, "status": list(frame.status), "chamber": list(frame.chamber),
        "act": list(frame.act), "vote": list(frame.vote), "candidacy": list(frame.candidacy),
        "president": None if president is None else {
            "citizen_id": president.citizen_id, "xy": _xy(president.xy),
            "pledged_xy": _xy(president.pledged_xy) if president.pledged_xy is not None else None,
            "legitimacy": president.legitimacy, "ecart": president.ecart, "mandate_strength": president.mandate_strength,
            "lame_duck": president.lame_duck,
        },
    }


def polity_run_frames(context: ExplorerContext, run_key: str, from_tick: int, to_tick: int | None) -> Body:
    try:
        entry, run = _load(context, run_key)
    except _Refused as refused:
        return refused.body
    last = len(run.frames.frames) - 1
    end = min(from_tick + MAX_FRAME_SPAN - 1, last) if to_tick is None else to_tick
    if from_tick > last:
        return {"error": f"from_tick {from_tick} is past the run's last tick, {last}"}, 400
    if end < from_tick:
        return {"error": "to_tick is before from_tick"}, 400
    if end - from_tick + 1 > MAX_FRAME_SPAN:
        return {"error": f"at most {MAX_FRAME_SPAN} ticks per request"}, 400
    end = min(end, last)
    return {"key": entry.key, "from_tick": from_tick, "to_tick": end,
            "frames": [_frame(f) for f in run.frames.frames[from_tick:end + 1]]}, 200


def polity_citizen(context: ExplorerContext, run_key: str, citizen_id: int) -> Body:
    try:
        entry, run = _load(context, run_key)
    except _Refused as refused:
        return refused.body
    if citizen_id >= run.frames.population:
        return {"error": "citizen not found"}, 404
    biography = run.biography(citizen_id)
    return {
        "key": entry.key, "citizen_id": citizen_id,
        "sections": {section: [{**_plain(e), "details": dict(e.details)} for e in entries] for section, entries in biography.sections.items()},
        "received": [_plain(r) for r in biography.received],
        "census": [_plain(c) for c in biography.census],
    }, 200
