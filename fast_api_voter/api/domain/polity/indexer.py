"""
api.domain.polity.indexer — the journal-replay module named (but not built)
since v0: journal.py's own docstring already pointed here ("Replaying it
into a queryable store is indexer.py's job — not part of the v0 lot
breakdown"), and metrics.py's own docstring has said the same since v0
("an indexer that replays the raw journal into these shapes is indexer.py's
job"). v4 Lot 8 is the first lot that actually needs it.

This module READS a journal, ONCE, and assembles the observations §10's
rows are computed from -- it contains no formula of its own. Every actual
computation (a mean, a ratio, a distribution) lives in metrics.py, exactly
as that module's own docstring already specified; this module's only job is
event-type knowledge, tick/term bookkeeping, and calling into metrics.py
with the right slice of the journal. It is NOT §16.6's DuckDB compaction or
codebook decoding -- both live in compaction.py (v4 storage lot); this is a
metrics reducer over a JSONL file, nothing more.

`index_events` (an Iterable of already-parsed event dicts) is the real
function; `index_run` (a Path) is four lines that stream a JSONL file into
it. This shape exists for the tests: every indexer unit test hand-builds a
small list of event dicts, no tmp_path, no Journal, no run -- the same
direct-call register this project's hand-built-citizen tests have used
since Lot 2.

A metric whose governing config flag is off is `None` in the returned
RunMetrics, never an empty collection or a 0.0 -- Lot 6's rule ("0.0 is a
claim, None says this run does not track that"), applied here to "this run
was not asked to compute that".

Two rows deserve a specific warning, because a naive reading of the journal
produces a WRONG number for both:

- mandate_deviation: `mandate_deviation_recorded` is journaled only above
  `mandate.deviation_log_threshold` (§16.3's anti-saturation rule) -- its
  mean is therefore left-censored and rises as drift FALLS. The uncensored
  series is `representative_response.payload.ctx.mandate_dev`, journaled
  every presided tick since Lot 6 (pre-decision, one tick lagged) -- this
  indexer prefers it whenever it exists and only falls back to the censored
  series when dt=6 never ran (config.llm.enabled=False), flagging which one
  it used (`mandate_deviation_source`) plus a coverage ratio so a reader
  never mistakes a partial series for a complete one.
- petition_success_rate: §7bis.4a's "aboutie" means the petition reached
  its threshold and forced a confidence vote (`confidence_vote_triggered ÷
  petition_launched`) -- NOT the fraction of triggered votes that actually
  recall the officeholder. That second, genuinely distinct number is
  `petition_removal_rate` (`recalled[trigger=confidence_vote] ÷
  confidence_vote_triggered`), reported alongside it under its own name so
  the two are never conflated.

The two shipped calibration scripts (calibrate_awakening.py,
calibrate_petition.py) are deliberately NOT refactored onto this module --
their own committed results docs (awakening_calibration_results.md,
petition_calibration_results.md) are evidence whose provenance is the code
as it stood when they were produced, and several Lot 4/5/7 judgment calls
cite specific numbers from them. Re-deriving those numbers through new code
in the palier's last lot risks a silent discrepancy for zero benefit -- the
duplication is deliberate and frozen.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

from api.domain.polity.config import PolityConfig
from api.domain.polity.metrics import (
    blank_vote_rate,
    cohabitation_rate as _cohabitation_rate_fn,
    coalition_lifespans,
    effective_number_of_parties,
    inaction_rate as _inaction_rate_fn,
    is_cohabitation,
    lame_duck_deviation_delta as _lame_duck_deviation_delta_fn,
    mean_legitimacy as _mean_legitimacy_fn,
    petition_success_rate as _petition_success_rate_fn,
    pressure_lever_mix as _pressure_lever_mix_fn,
    recall_frequency as _recall_frequency_fn,
    stance_distribution as _stance_distribution_fn,
)

_PRESIDENT_ELECTION_EVENTS = ("elected", "election_no_winner", "election_invalidated")


@dataclass(frozen=True)
class Term:
    """One continuous presidential term, from the journal's own record --
    opens at `elected`, closes at `recalled` (either trigger) or the next
    presidential election, whichever comes first; the run's own end closes
    whatever term is still open. `end_tick` is exclusive EXCEPT for a
    same-tick election recall (Lot 3's own reachable pathological case),
    where start_tick == end_tick and both bounds are read inclusively by
    every consumer in this module -- a zero-length term is still a real
    term, not a non-event."""

    holder_id: int
    start_tick: int
    end_tick: int
    lame_duck: bool
    mandate_strength: float | None
    ended_by: str  # "legitimacy_floor" | "confidence_vote" | "election" | "run_end"


@dataclass(frozen=True)
class RunMetrics:
    """§10's table, one bundle per indexed run. Every field is `None` when
    its governing config section/flag is off -- see this module's own
    docstring."""

    run_id: str
    total_ticks: int
    terms: tuple[Term, ...]

    # v0 rows (gated on their own already-shipped metrics.* flags)
    effective_parties: tuple[tuple[int, float], ...] | None
    cohabitation_rate: float | None
    coalition_lifespans: tuple[int, ...] | None
    blank_vote_rate: tuple[tuple[int, float], ...] | None

    # implied by legitimacy.enabled (no dedicated metrics.* flag of their own)
    mean_legitimacy: tuple[tuple[int, float], ...] | None
    recalls_by_trigger: dict[str, int] | None
    recalls_per_term: float | None

    # v4 Lot 8's six newly-gated rows
    mandate_deviation: tuple[tuple[int, float], ...] | None
    mandate_deviation_source: str | None  # "ctx" (uncensored) | "recorded" (censored)
    mandate_deviation_coverage: float | None
    lame_duck_deviation_delta: float | None
    inaction_rate: tuple[tuple[int, float], ...] | None
    pressure_lever_mix: dict[int, float] | None
    pressure_lever_counts: dict[int, int] | None
    petition_downgrades: int | None
    petition_success_rate: float | None
    petition_removal_rate: float | None
    stance_distribution: dict[int, float] | None


def read_journal(path: Path) -> Iterator[dict[str, Any]]:
    """Streams one JSONL journal file, one parsed event dict per line. A
    malformed line raises with its line number -- a truncated tail from an
    aborted run must be loud, never silently skipped."""
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: malformed journal line: {exc}") from exc


def segment_terms(events: Sequence[Mapping[str, Any]], total_ticks: int) -> tuple[Term, ...]:
    """One pass over the journal's own election/recall events -- see
    RunMetrics's own docstring for why this exists as a single tested
    function rather than N divergent per-metric readers of "what is a
    term"."""
    closed: list[tuple[int, int, int, str]] = []
    open_holder: int | None = None
    open_start: int | None = None

    for event in events:
        event_type = event["event_type"]
        tick = event["tick"]
        if event_type in _PRESIDENT_ELECTION_EVENTS:
            if open_holder is not None:
                assert open_start is not None
                closed.append((open_holder, open_start, tick, "election"))
                open_holder = None
                open_start = None
            if event_type == "elected":
                open_holder = event["citizen_id"]
                open_start = tick
        elif event_type == "recalled" and open_holder is not None and event["citizen_id"] == open_holder:
            assert open_start is not None
            closed.append((open_holder, open_start, tick, event["payload"]["trigger"]))
            open_holder = None
            open_start = None

    if open_holder is not None:
        assert open_start is not None
        closed.append((open_holder, open_start, total_ticks, "run_end"))

    terms = []
    for holder_id, start, end, ended_by in closed:
        lame_duck = False
        mandate_strength_value: float | None = None
        for event in events:
            if event["tick"] < start or event["tick"] > end:
                continue
            if event["event_type"] == "mandate_pledge_declared" and event["citizen_id"] == holder_id and event["tick"] == start:
                lame_duck = bool(event["payload"]["lame_duck"])
            if (
                mandate_strength_value is None
                and event["event_type"] == "legitimacy_updated"
                and event["citizen_id"] == holder_id
            ):
                mandate_strength_value = event["payload"]["mandate_strength"]
        terms.append(
            Term(
                holder_id=holder_id, start_tick=start, end_tick=end,
                lame_duck=lame_duck, mandate_strength=mandate_strength_value, ended_by=ended_by,
            )
        )
    return tuple(terms)


def _party_id_at_term_start(events: Sequence[Mapping[str, Any]], holder_id: int, start_tick: int) -> int | None:
    for event in events:
        if (
            event["event_type"] == "candidacy_declared"
            and event["citizen_id"] == holder_id
            and event["tick"] == start_tick
        ):
            party_id = event["payload"].get("party_id")
            return int(party_id) if party_id is not None else None
    return None


def _coalition_at_or_before(events: Sequence[Mapping[str, Any]], tick: int) -> list[int] | None:
    coalition: list[int] | None = None
    for event in events:
        if event["tick"] > tick:
            break
        if event["event_type"] in ("coalition_formed", "coalition_failed"):
            payload_coalition = event["payload"]["coalition"]
            coalition = [int(pid) for pid in payload_coalition] if payload_coalition is not None else None
    return coalition


def index_events(events: Iterable[Mapping[str, Any]], config: PolityConfig, *, run_id: str = "") -> RunMetrics:
    """The real function -- see this module's own docstring for the
    Iterable-taking-core / Path-wrapper split and why it's shaped that way
    for tests. Unknown event types are ignored by construction (nothing
    below matches them); a malformed line is read_journal's problem, not
    this function's -- it only ever sees already-parsed dicts."""
    events = list(events)
    total_ticks = config.run.total_ticks
    terms = segment_terms(events, total_ticks)

    # ── v0 rows ────────────────────────────────────────────────────────
    effective_parties = None
    if config.metrics.effective_parties:
        pairs = []
        for event in events:
            if event["event_type"] == "legislative_result":
                seats = {int(pid): count for pid, count in event["payload"]["seats"].items()}
                pairs.append((event["tick"], effective_number_of_parties(seats)))
        effective_parties = tuple(pairs)

    cohabitation = None
    if config.metrics.cohabitation_rate:
        # One observation per completed presidential term (equal-weighted,
        # per cohabitation_rate's own documented contract) -- the party in
        # office and the governing coalition both taken as of the term's
        # own start tick.
        observations = []
        for term in terms:
            party_id = _party_id_at_term_start(events, term.holder_id, term.start_tick)
            coalition = _coalition_at_or_before(events, term.start_tick)
            observations.append(is_cohabitation(party_id, coalition))
        cohabitation = _cohabitation_rate_fn(observations)

    coalition_lifespan = None
    if config.metrics.coalition_lifespan:
        coalition_events = [
            (event["tick"], [int(pid) for pid in event["payload"]["coalition"]] if event["payload"]["coalition"] is not None else None)
            for event in events
            if event["event_type"] in ("coalition_formed", "coalition_failed")
        ]
        coalition_lifespan = tuple(coalition_lifespans(coalition_events, total_ticks))

    blank_rate = None
    legislative_events = [e for e in events if e["event_type"] == "legislative_result"]
    if legislative_events:
        pairs = []
        for event in legislative_events:
            blank_count = event["payload"]["blank_count"]
            total_votes = blank_count + sum(event["payload"]["votes"].values())
            pairs.append((event["tick"], blank_vote_rate(blank_count, int(total_votes))))
        blank_rate = tuple(pairs)

    # ── implied by legitimacy.enabled ─────────────────────────────────
    mean_legitimacy = None
    recalls_by_trigger: dict[str, int] | None = None
    recalls_per_term = None
    if config.legitimacy.enabled:
        legitimacy_by_tick: dict[int, list[float]] = {}
        for event in events:
            if event["event_type"] == "legitimacy_updated":
                legitimacy_by_tick.setdefault(event["tick"], []).append(event["payload"]["legitimacy"])
        mean_legitimacy = tuple(
            (tick, _mean_legitimacy_fn(values)) for tick, values in sorted(legitimacy_by_tick.items())
        )
        recalls_by_trigger = {}
        for event in events:
            if event["event_type"] == "recalled":
                trigger = event["payload"]["trigger"]
                recalls_by_trigger[trigger] = recalls_by_trigger.get(trigger, 0) + 1
        total_recalls = sum(recalls_by_trigger.values())
        recalls_per_term = _recall_frequency_fn(total_recalls, len(terms))

    # ── mandate deviation series (v4 Lot 8, the censoring trap) ───────
    mandate_deviation = None
    mandate_deviation_source = None
    mandate_deviation_coverage = None
    # (tick, citizen_id, value) -- keeps citizen_id so lame_duck_deviation_delta
    # can filter by HOLDER, not just tick range: a shared election-boundary
    # tick can carry one event for the outgoing holder and one for the
    # incoming one, and term ranges are read end-tick-inclusive (the
    # same-tick-recall case needs that), so tick range alone is ambiguous
    # exactly at that boundary.
    deviation_by_holder: list[tuple[int, int, float]] = []
    if config.metrics.mandate_deviation:
        ctx_series = [
            (event["tick"], event["citizen_id"], event["payload"]["ctx"]["mandate_dev"])
            for event in events
            if event["event_type"] == "representative_response"
        ]
        recorded_count = sum(1 for event in events if event["event_type"] == "mandate_deviation_recorded")
        if ctx_series:
            mandate_deviation = tuple((tick, dev) for tick, _cid, dev in ctx_series)
            mandate_deviation_source = "ctx"
            mandate_deviation_coverage = recorded_count / len(ctx_series)
            deviation_by_holder = ctx_series
        else:
            recorded_series = [
                (event["tick"], event["citizen_id"], event["payload"]["deviation"])
                for event in events
                if event["event_type"] == "mandate_deviation_recorded"
            ]
            mandate_deviation = tuple((tick, dev) for tick, _cid, dev in recorded_series)
            mandate_deviation_source = "recorded"
            # No dt=6 ctx series exists to give an exact presided-tick count
            # -- approximated from term length, the same quantity Lot 6
            # proved is >= 1 and never 0 for a sitting holder.
            presided_estimate = sum(term.end_tick - term.start_tick for term in terms)
            mandate_deviation_coverage = recorded_count / presided_estimate if presided_estimate > 0 else None
            deviation_by_holder = recorded_series

    lame_duck_delta = None
    if config.metrics.lame_duck_deviation_delta and mandate_deviation is not None:
        lame_duck_means: list[float] = []
        eligible_means: list[float] = []
        for term in terms:
            values = [
                dev for tick, cid, dev in deviation_by_holder
                if cid == term.holder_id and term.start_tick <= tick <= term.end_tick
            ]
            if not values:
                continue
            mean_value = sum(values) / len(values)
            (lame_duck_means if term.lame_duck else eligible_means).append(mean_value)
        lame_duck_delta = _lame_duck_deviation_delta_fn(lame_duck_means, eligible_means)

    # ── pressure_action-derived rows ──────────────────────────────────
    inaction_rate = None
    pressure_lever_mix = None
    pressure_lever_counts = None
    petition_downgrades = None
    if config.metrics.inaction_rate or config.metrics.pressure_lever_mix:
        acts_by_tick: dict[int, list[int]] = {}
        all_acts: list[int] = []
        for event in events:
            if event["event_type"] == "pressure_action":
                act = event["payload"]["act"]
                acts_by_tick.setdefault(event["tick"], []).append(act)
                all_acts.append(act)
        if config.metrics.inaction_rate:
            inaction_rate = tuple(
                (tick, _inaction_rate_fn(sum(1 for a in acts if a == 0), len(acts)))
                for tick, acts in sorted(acts_by_tick.items())
            )
        if config.metrics.pressure_lever_mix:
            pressure_lever_mix = _pressure_lever_mix_fn(all_acts)
            pressure_lever_counts = {act: all_acts.count(act) for act in range(5)}
            downgrades = 0
            for i, event in enumerate(events):
                if (
                    event["event_type"] == "pressure_action"
                    and event["payload"]["act"] == 2
                    and i + 1 < len(events)
                    and events[i + 1]["event_type"] == "petition_signed"
                    and events[i + 1]["citizen_id"] == event["citizen_id"]
                ):
                    downgrades += 1
            petition_downgrades = downgrades

    petition_success = None
    petition_removal = None
    if config.metrics.petition_success_rate:
        launched = sum(1 for e in events if e["event_type"] == "petition_launched")
        triggered = sum(1 for e in events if e["event_type"] == "confidence_vote_triggered")
        removed = sum(
            1 for e in events if e["event_type"] == "recalled" and e["payload"]["trigger"] == "confidence_vote"
        )
        petition_success = _petition_success_rate_fn(triggered, launched)
        petition_removal = (removed / triggered) if triggered > 0 else None

    stance_dist = None
    if config.metrics.stance_distribution:
        stances = [
            event["payload"]["stance"] for event in events if event["event_type"] == "representative_response"
        ]
        stance_dist = _stance_distribution_fn(stances)

    return RunMetrics(
        run_id=run_id,
        total_ticks=total_ticks,
        terms=terms,
        effective_parties=effective_parties,
        cohabitation_rate=cohabitation,
        coalition_lifespans=coalition_lifespan,
        blank_vote_rate=blank_rate,
        mean_legitimacy=mean_legitimacy,
        recalls_by_trigger=recalls_by_trigger,
        recalls_per_term=recalls_per_term,
        mandate_deviation=mandate_deviation,
        mandate_deviation_source=mandate_deviation_source,
        mandate_deviation_coverage=mandate_deviation_coverage,
        lame_duck_deviation_delta=lame_duck_delta,
        inaction_rate=inaction_rate,
        pressure_lever_mix=pressure_lever_mix,
        pressure_lever_counts=pressure_lever_counts,
        petition_downgrades=petition_downgrades,
        petition_success_rate=petition_success,
        petition_removal_rate=petition_removal,
        stance_distribution=stance_dist,
    )


def index_run(path: Path, config: PolityConfig) -> RunMetrics:
    """Four lines: streams `path` into index_events. `run_id` is taken from
    the first event, matching every event in a single journal file
    (Journal writes exactly one run_id per file)."""
    events = list(read_journal(path))
    run_id = events[0]["run_id"] if events else ""
    return index_events(events, config, run_id=run_id)
