"""
api.domain.polity.run_digest — a structured account of what a run did,
written on EVERY ending: completed, crashed, or interrupted.

**Why this exists.** `viz_export.export_run` and the runner's own
`metrics.json` are written at run_polity_flagship.py:402-412, *after* the
try/finally that wraps `run_simulation` -- so an exception, a KeyboardInterrupt
or a SIGTERM skips both entirely. Measured, not assumed: at the time this
module was written, only 3 of the 8 directories under scripts/flagship_runs/
had a `viz_export.json`. The other five runs really happened, are sitting in
`events.jsonl`, and nothing reads them. This module is what those five runs
were missing.

**It is deliberately not a second metrics source.** §16.2's standing rule
("les métriques du §10 deviennent des vues dérivées, pas une seconde source de
vérité à maintenir") applies here exactly as it does to viz_export.py: terms
come from `indexer.segment_terms`, the institutional projection reuses
viz_export's own `_INSTITUTIONAL_EVENT_TYPES`, the unverified-decision labels
come from `viz_export.export_metadata`, and the wall-clock/retry/fallback
tallies are read from `progress.json` rather than recomputed. What IS new here
is only the per-year shaping a narrative needs, which nothing else produces.

**Two hard constraints the failure path imposes, both load-bearing:**

1. `indexer.read_journal` *raises* on a malformed line, by design ("a
   truncated tail from an aborted run must be loud, never silently skipped").
   A truncated tail is precisely the state a hard kill leaves, so this module
   cannot use it -- `read_journal_tolerant` below skips such a line the way
   run_polity_flagship._count_llm_decisions already does, and **reports how
   many it skipped** as a digest field. Loud, but not fatal: refusing to
   describe a crashed run because it crashed would defeat the purpose.
2. Nothing here may call `index_run`/`export_run`. `viz_export.py:175` does
   `list(read_journal(...))` over the whole journal and `index_run` walks it
   again; that is fine after a clean run and a bad idea inside a SIGTERM
   handler racing a shutdown. On the success path those richer artifacts
   already exist beside this one, so the digest names them instead.

**What it cannot do:** nothing survives SIGKILL or a power cut -- no in-process
mechanism can. That gap is covered outside this module, by a catch-up scan that
notices a run directory whose journal has no digest.
"""
from __future__ import annotations

import dataclasses
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from api.domain.polity.codebook import PressureAct
from api.domain.polity.config import PolityConfig
from api.domain.polity.indexer import segment_terms
from api.domain.polity.metrics import office_occupancy
from api.domain.polity.events import ALL_EVENT_TYPES as REGISTERED_EVENT_TYPES
from api.domain.polity.viz_export import _INSTITUTIONAL_EVENT_TYPES, export_metadata

DIGEST_FILENAME = "digest.json"
ATTEMPTS_FILENAME = "digest.jsonl"

ALL_EVENT_TYPES: frozenset[str] = REGISTERED_EVENT_TYPES
"""Every event_type the simulation can journal -- events.py's registry (S3.3), which
the write sites construct, so it cannot miss one the way the grep this set used to
be built from missed `election_no_winner` (a ternary branch).

The digest reports a count for EVERY one of these per year, including zeros.
That is the point: a reader must be able to tell "this did not happen" apart
from "nobody looked", and a silently absent key cannot express the difference."""

_PRESSURE_ACT_NAMES: Mapping[int, str] = {act.value: act.name for act in PressureAct}


def read_journal_tolerant(path: Path) -> tuple[list[dict[str, Any]], int]:
    """`indexer.read_journal`'s forgiving twin -- see this module's docstring
    for why the strict one cannot be used here. Returns the parsed events and
    the number of unparseable lines skipped, so the caller can report the
    damage rather than hide it. A journal killed mid-write can only ever
    truncate its final line (`journal.py` flushes every write), so a count
    above 1 means something stranger than an interrupted run and is worth
    surfacing in the digest."""
    events: list[dict[str, Any]] = []
    skipped = 0
    if not path.is_file():
        return events, skipped
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                skipped += 1
    return events, skipped


def _year_of(tick: int, ticks_per_year: int) -> int:
    return tick // ticks_per_year


def event_counts_by_year(
    events: list[dict[str, Any]], ticks_per_year: int
) -> dict[str, dict[str, int]]:
    """year -> event_type -> count, with all 30 types present at every year.
    See ALL_EVENT_TYPES on why the zeros are written out rather than omitted.
    An event_type absent from ALL_EVENT_TYPES is still counted (never dropped)
    -- if the simulation gains a new one and this constant is not updated, the
    digest must show it rather than silently lose it."""
    per_year: dict[int, Counter[str]] = defaultdict(Counter)
    for event in events:
        per_year[_year_of(event["tick"], ticks_per_year)][event["event_type"]] += 1
    out: dict[str, dict[str, int]] = {}
    for year in _year_span(events, ticks_per_year):
        seen = per_year.get(year, Counter())
        known = {event_type: seen.get(event_type, 0) for event_type in sorted(ALL_EVENT_TYPES)}
        unknown = {k: v for k, v in sorted(seen.items()) if k not in ALL_EVENT_TYPES}
        out[str(year)] = {**known, **unknown}
    return out


def _year_span(events: list[dict[str, Any]], ticks_per_year: int) -> range:
    """Every year from 0 to the last one the run actually reached — including
    years in which nothing whatsoever happened.

    A silent year must appear as a row of zeros rather than vanish from the
    map: an absent key cannot distinguish "this society had a quiet year" from
    "this year was never simulated", and a reader of a crashed run needs
    exactly that distinction. Bounded by the last tick JOURNALED, never by the
    planned total, so an interrupted run does not sprout empty years it never
    lived through."""
    if not events:
        return range(0)
    return range(_year_of(max(e["tick"] for e in events), ticks_per_year) + 1)


def population_impact_by_year(
    events: list[dict[str, Any]], config: PolityConfig
) -> list[dict[str, Any]]:
    """The per-year series a narrative actually needs, none of which exists
    anywhere else: nothing in this codebase computes a population-level
    aggregate during or after a run (`metrics.mean_legitimacy` averages the
    *officeholder's* legitimacy within a tick -- ordinary citizens have no
    legitimacy field at all). Everything below is derived from real journaled
    events; no synthetic "satisfaction index" is invented here.

    `pressure.acts_decided` is deliberately named: `pressure_action.payload.act`
    is the act the citizen DECIDED, before `applicable_pressure_act` gating --
    a LAUNCH_PETITION that was not launchable is silently downgraded to a
    signature, and the only record of what actually happened is the
    petition_launched/petition_signed event that follows. Both are reported so
    the gap is visible instead of being quietly averaged away."""
    ticks_per_year = config.run.ticks_per_year
    population = config.run.population_size
    per_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        per_year[_year_of(event["tick"], ticks_per_year)].append(event)

    series = []
    for year in _year_span(events, ticks_per_year):
        # A year with no events still gets a row -- see _year_span.
        year_events = per_year.get(year, [])
        ticks = [e["tick"] for e in year_events] or [year * ticks_per_year]
        by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event in year_events:
            by_type[event["event_type"]].append(event)
        series.append({
            "year": year,
            "tick_range": [min(ticks), max(ticks)],
            "candidacy": _candidacy_impact(by_type, population),
            "pressure": _pressure_impact(by_type, population),
            "petitions": _petition_impact(by_type),
            "votes": _vote_impact(by_type),
            "reactions": _reaction_impact(by_type),
            "llm_quality": {
                "fallbacks": sum(1 for e in year_events if e["payload"].get("llm_fallback")),
                "retries": sum(1 for e in year_events if e["payload"].get("retry_sampling_varied")),
            },
        })
    return series


EventsByType = Mapping[str, list[dict[str, Any]]]


def _candidacy_impact(by_type: EventsByType, population: int) -> dict[str, Any]:
    considered = by_type.get("candidacy_considered", [])
    declared_llm = sum(1 for e in considered if e["payload"].get("outcome") == 1)
    return {
        # `considered` exists only on the LLM path; on a deterministic
        # run it is 0 and every rate below is None rather than 0.0 --
        # indexer.py's own "0.0 is a claim, None says this run does not
        # track that" rule.
        "considered": len(considered),
        "declared": declared_llm,
        "declined": len(considered) - declared_llm,
        "declared_rate_of_considered": _ratio(declared_llm, len(considered)),
        "declared_rate_of_population": _ratio(declared_llm, population) if considered else None,
        "declared_events": len(by_type.get("candidacy_declared", [])),
    }


def _pressure_impact(by_type: EventsByType, population: int) -> dict[str, Any]:
    pressure = by_type.get("pressure_action", [])
    acts = Counter(_PRESSURE_ACT_NAMES.get(e["payload"].get("act"), "UNKNOWN") for e in pressure)
    return {
        "consulted": len(pressure),
        "acts_decided": dict(sorted(acts.items())),
        "inaction_rate": _ratio(acts.get("NOTHING", 0), len(pressure)),
        "consulted_rate_of_population": _ratio(len(pressure), population) if pressure else None,
    }


def _petition_impact(by_type: EventsByType) -> dict[str, Any]:
    signed = by_type.get("petition_signed", [])
    launched = by_type.get("petition_launched", [])
    ratios = [
        e["payload"]["signed_ratio"]
        for e in (*signed, *launched)
        if e["payload"].get("signed_ratio") is not None
    ]
    return {
        "launched": len(launched),
        "signed": len(signed),
        "expired": len(by_type.get("petition_expired", [])),
        "peak_signed_ratio": max(ratios) if ratios else None,
        "confidence_votes": len(by_type.get("confidence_vote_triggered", [])),
    }


def _vote_impact(by_type: EventsByType) -> dict[str, Any]:
    ballots = by_type.get("vote_cast", [])
    blanks = sum(1 for e in ballots if e["payload"].get("blank"))
    return {"ballots": len(ballots), "blank": blanks, "blank_rate": _ratio(blanks, len(ballots))}


def _reaction_impact(by_type: EventsByType) -> dict[str, Any]:
    reactions = by_type.get("reaction_to_event", [])
    deltas = [e["payload"].get("salience_delta", 0.0) for e in reactions]
    return {"count": len(reactions), "mean_salience_delta": (sum(deltas) / len(deltas)) if deltas else None}


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


FALLBACK_ALERT_THRESHOLD = 0.10
"""Track C2 (2026-09-11, lets-build-a-solid-spicy-otter.md): Stage 3's own
overall fallback rate was 0.26% -- reassuring on its face -- while
`party_nomination_choice` alone fell back 67% of the time (10/15). An
aggregate-only number cannot distinguish "healthy run" from "one decision
type quietly broken"; per-type rates can. 10% is a first cut, not a
measured optimum: comfortably above the occasional single-chunk fallback
this project's own retry/fallback design already treats as normal and
harmless (a transient decode failure that recovers via
`_deterministic_*_fallback`), comfortably below the 67% that actually
happened. Revisit with real multi-seed data (Track D) once one exists --
this is a pre-registered bar in the same spirit as B3's <5% candidacy
bar, not a value derived from a distribution nobody has measured yet."""


def llm_fallback_rates(decisions_by_type: Mapping[str, int], fallback_by_type: Mapping[str, int]) -> dict[str, float]:
    """Per-type fallback rate -- `progress.json`'s own `decisions_by_type`/
    `fallback_by_type`, never recomputed from the journal (this module's own
    "not a second source of truth" rule, see module docstring). A type with
    zero decisions this run is OMITTED, not given a 0.0 -- indexer.py's own
    "0.0 is a claim, absent is untracked" convention, since a rate over zero
    decisions is not a real measurement of anything."""
    return {
        event_type: rate
        for event_type, count in decisions_by_type.items()
        if count and (rate := _ratio(fallback_by_type.get(event_type, 0), count)) is not None
    }


def llm_fallback_alerts(fallback_rates: Mapping[str, float], *, threshold: float = FALLBACK_ALERT_THRESHOLD) -> dict[str, float]:
    """Which decision types exceeded the alert threshold this run, and by
    how much -- a dict (not just a list of names) so the digest itself
    carries the number that tripped the alert, not just its verdict. Empty,
    not absent, when nothing is flagged: a reader must be able to tell
    "checked, all clear" from "the check never ran"."""
    return {event_type: rate for event_type, rate in sorted(fallback_rates.items()) if rate > threshold}


def legitimacy_trajectory(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every `legitimacy_updated` event, in order -- the officeholder's own
    standing over time, which is the closest thing this simulation has to "how
    the term was going". One per presided tick, so a 120-tick run yields at
    most 120 rows: small enough to carry whole rather than summarize."""
    return [
        {
            "tick": e["tick"],
            "citizen_id": e.get("citizen_id"),
            "legitimacy": e["payload"].get("legitimacy"),
            "mandate_strength": e["payload"].get("mandate_strength"),
            "ecart": e["payload"].get("ecart"),
        }
        for e in events
        if e["event_type"] == "legitimacy_updated"
    ]


def institutional_timeline(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """viz_export's own curated projection, reused rather than re-listed --
    one definition of "what institutionally happened", not two that can drift.
    Note `coalition_failed` carries three different payload shapes and
    `elected`/`election_no_winner` have conditional keys, so the payload is
    passed through whole rather than reshaped into a fixed schema here.

    `event_id` (S5.3) is what a TIMELINE.md claim anchors to, so
    scripts/check_timeline_claims.py can check the claim against the journal."""
    return [
        {
            "event_id": e.get("event_id"),
            "tick": e["tick"],
            "event_type": e["event_type"],
            "citizen_id": e.get("citizen_id"),
            "payload": e["payload"],
        }
        for e in events
        if e["event_type"] in _INSTITUTIONAL_EVENT_TYPES
    ]


def _read_json(path: Path) -> dict[str, Any] | None:
    """progress.json/checkpoint.json are written atomically (temp + os.replace)
    so a torn read is not a concern -- but on a run killed before its first
    checkpoint they simply do not exist yet, which is not an error."""
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def build_digest(
    journal_path: Path,
    config: PolityConfig,
    *,
    run_id: str,
    outcome: str,
    resume: bool,
    elapsed_seconds: float | None = None,
    error: BaseException | None = None,
) -> dict[str, Any]:
    """`outcome` is one of "completed" / "crashed" / "interrupted" -- the three
    ways a run actually ends. It is passed in rather than inferred: only the
    caller knows whether `run_simulation` returned or raised, and guessing from
    the journal alone ("did it reach the last tick?") would mislabel a run that
    was stopped deliberately."""
    events, skipped_lines = read_journal_tolerant(journal_path)
    ticks_seen = [e["tick"] for e in events]
    last_tick = max(ticks_seen) if ticks_seen else None
    progress = _read_json(journal_path.with_name("progress.json"))
    checkpoint = _read_json(journal_path.with_name("checkpoint.json"))
    # See "terms"/"office_occupancy" below for why this is computed once,
    # here, rather than inline in each of those two places.
    terms = segment_terms(events, last_tick or 0)

    return {
        "run_id": run_id,
        "outcome": outcome,
        "error": None if error is None else {"type": type(error).__name__, "message": str(error)},
        "resumed_attempt": resume,
        "elapsed_seconds": None if elapsed_seconds is None else round(elapsed_seconds, 1),
        "ticks": {
            # The config total is what was ASKED for; last_tick is what was
            # reached. On a crash the two differ, and that difference is the
            # single most important fact about the run.
            "planned_total": config.run.ticks_per_year * config.run.duration_years,
            "last_tick_journaled": last_tick,
            "last_checkpoint_tick": (checkpoint or {}).get("tick"),
            "ticks_per_year": config.run.ticks_per_year,
        },
        "shape": _run_shape(config),
        "journal": {
            "total_events": len(events),
            "malformed_lines_skipped": skipped_lines,
            "path": str(journal_path),
        },
        # segment_terms is given the last tick actually journaled, NOT the
        # planned total: its own contract is that "the run's own end closes
        # whatever term is still open", and for an interrupted run the real end
        # is where it stopped. Passing the planned total would silently extend
        # a term the run never actually lived through. Called once, here, and
        # reused for office_occupancy below -- never a second, potentially
        # divergent call over the same events.
        "terms": [dataclasses.asdict(term) for term in terms],
        # Track A5 (2026-09-11): the same metrics.office_occupancy formula
        # RunMetrics carries, computed here too because digest.json is what
        # an interrupted or still-running attempt actually has -- metrics.json
        # only exists on a clean completion (index_after_run), and this is the
        # number that would have caught the 2026-09-11 misdiagnosis on sight
        # (a run that looks "stuck" with a long-vacant presidency is instead
        # just a run with low office_occupancy, a fact this makes visible
        # without reading the journal by hand). Engine-agnostic like the
        # metric itself -- see that function's own docstring.
        "office_occupancy": office_occupancy(
            sum(term.end_tick - term.start_tick for term in terms),
            last_tick or 0,
        ),
        "institutional_timeline": institutional_timeline(events),
        "event_counts_by_year": event_counts_by_year(events, config.run.ticks_per_year),
        "population_impact_by_year": population_impact_by_year(events, config),
        "legitimacy_trajectory": legitimacy_trajectory(events),
        **_llm_quality(progress),
        # Carried through so a narrator flags these rather than presenting them
        # as findings -- see viz_export.export_metadata's own docstring.
        "metadata": export_metadata(config),
        "sibling_artifacts": _sibling_artifacts(journal_path),
    }


def _llm_quality(progress: dict[str, Any] | None) -> dict[str, Any]:
    """The digest's LLM decision counts, retries and fallbacks, from progress.json."""
    if progress is None:
        # `null`, NOT `{}`, when progress.json itself is missing (2026-09-13):
        # llm_fallback_alerts' own docstring promises a reader can tell "checked, all
        # clear" from "the check never ran", and `{}` on both paths broke exactly that
        # promise on the one path where it matters most -- a run killed before its
        # first checkpoint, i.e. a crash. A deterministic run still yields `{}`:
        # progress.json exists, it just has no LLM decisions to rate, which IS
        # "checked, nothing to flag".
        return {
            "llm_decisions": {}, "llm_retries": None, "llm_fallbacks": None,
            "llm_fallback_rates": None, "llm_fallback_alerts": None,
        }
    decisions_by_type = progress.get("decisions_by_type", {})
    fallback_rates = llm_fallback_rates(decisions_by_type, progress.get("fallback_by_type", {}))
    return {
        "llm_decisions": decisions_by_type,
        "llm_retries": progress.get("retry_count"),
        "llm_fallbacks": progress.get("fallback_count"),
        # Track C2 (2026-09-11): the aggregate above hid Stage 3's real problem
        # (0.26% overall, 67% on one type) -- per-type rates plus an explicit alert
        # make that impossible to miss silently again.
        "llm_fallback_rates": fallback_rates,
        "llm_fallback_alerts": llm_fallback_alerts(fallback_rates),
    }


def _run_shape(config: PolityConfig) -> dict[str, Any]:
    return {
        "population_size": config.run.population_size,
        "duration_years": config.run.duration_years,
        "llm_enabled": config.llm.enabled,
        "llm_provider": config.llm.provider,
        "llm_model": config.llm.model,
        "sortition_seats": config.sortition_chamber.seats if config.sortition_chamber.enabled else None,
        "pressure_menu": {
            "electoral_only": config.pressure_menu.electoral_only,
            "petition_enabled": config.pressure_menu.petition_enabled,
            "mobilization_enabled": config.pressure_menu.mobilization_enabled,
        },
    }


def _sibling_artifacts(journal_path: Path) -> list[str]:
    if not journal_path.parent.is_dir():
        return []
    return sorted(p.name for p in journal_path.parent.iterdir() if p.is_file())


def write_digest(
    journal_path: Path,
    config: PolityConfig,
    *,
    run_id: str,
    outcome: str,
    resume: bool,
    elapsed_seconds: float | None = None,
    error: BaseException | None = None,
) -> Path:
    """Writes both artifacts, beside `events.jsonl` (the same directory
    `viz_export.json`/`progress.json`/`snapshots.jsonl` live in -- NOT the
    runner's outer bookkeeping directory; that mix-up is already documented at
    run_polity_flagship.py:407-411).

    Two files, deliberately:

    - `digest.jsonl` is APPENDED, one line per attempt. A run interrupted at
      tick 16 and resumed to completion must not lose the record that the first
      attempt died -- the same reason `config.json` is not rewritten on resume
      (run_polity_flagship.py:336-344) and `replays.log` is opened in append
      mode (:349).
    - `digest.json` holds the latest attempt only and is overwritten freely,
      the `run_metadata.json` pattern: a derived description of current state,
      cheap to regenerate, with no history to protect.
    """
    digest = build_digest(
        journal_path, config, run_id=run_id, outcome=outcome,
        resume=resume, elapsed_seconds=elapsed_seconds, error=error,
    )
    digest_path = journal_path.with_name(DIGEST_FILENAME)
    attempts_path = journal_path.with_name(ATTEMPTS_FILENAME)
    digest_path.parent.mkdir(parents=True, exist_ok=True)
    digest_path.write_text(json.dumps(digest, indent=2, default=str), encoding="utf-8")
    with attempts_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(digest, sort_keys=True, default=str) + "\n")
    return digest_path
