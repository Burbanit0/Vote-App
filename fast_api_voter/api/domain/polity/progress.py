"""
api.domain.polity.progress — per-tick live status (Phase 4,
plan-flagship-30y-run.md).

Turns a multi-day sequential run (Phase 2's own conclusion: this simulator
does not run concurrent) from an opaque black box into something watchable:
`progress.json`, rewritten atomically after every tick, is a live status
snapshot an operator -- or a future UI, per the design doc's own §16.1 "hot
regime" -- can read at any moment without touching the journal or
interrupting the run.

`ProgressTracker` owns the cumulative counters (decisions by type, retry
count, fallback count) and the rolling tick-duration window across the whole
run's lifetime. It is constructed ONCE per `run_simulation` invocation --
fresh or resumed -- never per tick. Cumulative counts stay correct across a
resume for free, with no fresh/resume branch: `record_tick`'s own journal
scan reads from a running byte offset that starts at 0, so the very FIRST
call after a resume naturally reads everything the truncated file already
holds (the pre-crash history) before any of this process's own new events
exist, and a fresh run's first call finds nothing there yet either way.
"""
from __future__ import annotations

import json
import os
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Deque

_ROLLING_WINDOW_SIZE = 10
"""How many of the most recent ticks' own durations the ETA averages over,
not the whole run's history -- tick cost is genuinely heterogeneous (an
election/coalition/chamber tick costs far more than a routine one), so a
flat whole-run average would converge slowly and misrepresent the CURRENT
phase of the run; a short rolling window adapts to it instead."""


def write_progress(
    path: Path,
    *,
    run_id: str,
    tick: int,
    total_ticks: int,
    ticks_per_year: int,
    wall_clock_elapsed_seconds: float,
    last_tick_duration_seconds: float,
    avg_recent_tick_duration_seconds: float,
    decisions_by_type: dict[str, int],
    retry_count: int,
    fallback_count: int,
    last_checkpoint_tick: int,
) -> None:
    """Atomic write (temp file + `os.replace`), same discipline as
    `checkpoint.save_checkpoint` -- a process killed mid-write must never
    leave a reader (an operator's `cat`, a future UI's polling fetch) a
    half-written, unparseable file."""
    remaining_ticks = max(total_ticks - tick, 0)
    eta_seconds = avg_recent_tick_duration_seconds * remaining_ticks
    payload: dict[str, Any] = {
        "run_id": run_id,
        "tick": tick,
        "total_ticks": total_ticks,
        "simulated_year": round(tick / ticks_per_year, 2),
        "wall_clock_elapsed_seconds": round(wall_clock_elapsed_seconds, 1),
        "last_tick_duration_seconds": round(last_tick_duration_seconds, 2),
        "avg_recent_tick_duration_seconds": round(avg_recent_tick_duration_seconds, 2),
        "eta_seconds": round(eta_seconds, 1),
        "eta_timestamp": (datetime.now(timezone.utc) + timedelta(seconds=eta_seconds)).isoformat(),
        "decisions_by_type": dict(sorted(decisions_by_type.items())),
        "decisions_total": sum(decisions_by_type.values()),
        "retry_count": retry_count,
        "fallback_count": fallback_count,
        "last_checkpoint_tick": last_checkpoint_tick,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


class ProgressTracker:
    """See module docstring for the resume-correctness argument. `decisions_
    by_type`/`retry_count`/`fallback_count` are derived from the journal
    itself (never passed in by the caller) -- `run_simulation`'s own phase
    functions already write every decision's provenance
    (`codebook_version`, `retry_sampling_varied`, `llm_fallback`) to
    `events.jsonl`; re-deriving from that single source of truth means this
    tracker can never drift out of sync with what actually happened, the
    same reasoning `run_polity_flagship.py`'s own post-hoc `_count_llm_
    decisions` already uses -- this is that same computation, incremental
    and live instead of a one-shot post-run pass."""

    def __init__(
        self, *, run_id: str, total_ticks: int, ticks_per_year: int, progress_path: Path, llm_enabled: bool = True
    ) -> None:
        self._run_id = run_id
        self._total_ticks = total_ticks
        self._ticks_per_year = ticks_per_year
        self._progress_path = progress_path
        self._llm_enabled = llm_enabled
        self._byte_offset = 0
        self.decisions_by_type: dict[str, int] = {}
        self.retry_count = 0
        self.fallback_count = 0
        self._tick_durations: Deque[float] = deque(maxlen=_ROLLING_WINDOW_SIZE)
        self._wall_clock_start: float | None = None

    def _scan_new_events(self, journal_path: Path) -> None:
        """Reads only what's new since the last call, via a running byte
        offset -- NOT event_id bookkeeping, which would need this class to
        know how many events the caller's own Journal has written; a plain
        `seek`/`tell` pair is sufficient and simpler, since journal writes
        are always flushed synchronously (`Journal.write`'s own contract)
        before this is ever called. A tick that journaled nothing (legal --
        many ticks hold no election, no scandal, nothing chamber-related)
        is a normal, cheap no-op call, not a special case.

        `llm_enabled=False` skips the counting below entirely (the byte
        offset still advances, so nothing is ever re-read) -- NOT an
        optimization, a correctness fix: `_run_reaction_to_event`
        (run_polity_simulation.py) writes `codebook_version` unconditionally,
        including on its own deterministic branch, so "codebook_version is
        truthy" is not a reliable LLM-decision signal when `llm.enabled` is
        False. `run_polity_flagship.py`'s own post-hoc `_count_llm_decisions`
        already gates on `engine == "llm"` for the exact same reason; this
        mirrors that fix rather than re-introducing the bug it exists for."""
        if not self._llm_enabled:
            if journal_path.exists():
                with journal_path.open(encoding="utf-8") as handle:
                    handle.seek(0, 2)  # os.SEEK_END -- nothing to tally, just track position
                    self._byte_offset = handle.tell()
            return
        if not journal_path.exists():
            return
        with journal_path.open(encoding="utf-8") as handle:
            handle.seek(self._byte_offset)
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                event = json.loads(line)
                if event.get("codebook_version"):
                    event_type = event["event_type"]
                    self.decisions_by_type[event_type] = self.decisions_by_type.get(event_type, 0) + 1
                    payload = event.get("payload") or {}
                    if payload.get("retry_sampling_varied"):
                        self.retry_count += 1
                    if payload.get("llm_fallback"):
                        self.fallback_count += 1
            self._byte_offset = handle.tell()

    def record_tick(
        self, *, tick: int, tick_duration: float, wall_clock_elapsed: float, journal_path: Path, checkpoint_tick: int
    ) -> None:
        """Called once per completed tick, at the same point in
        `run_simulation`'s own loop as `checkpoint.save_checkpoint` --
        after every one of that tick's phases has run and journaled, never
        mid-tick. `wall_clock_elapsed` is the caller's own responsibility
        (not tracked here): it is THIS process's own monotonic uptime, so
        on a resumed run it restarts at 0 rather than also reflecting the
        crashed attempt's own pre-resume elapsed time -- the same
        acknowledged limitation Phase 3's own checkpoint elapsed-time
        accounting already accepted (tracking true cross-restart wall clock
        would mean persisting it in the checkpoint itself, out of scope for
        both phases), not a new gap introduced here."""
        self._scan_new_events(journal_path)
        self._tick_durations.append(tick_duration)
        avg_recent = sum(self._tick_durations) / len(self._tick_durations)
        write_progress(
            self._progress_path,
            run_id=self._run_id,
            tick=tick,
            total_ticks=self._total_ticks,
            ticks_per_year=self._ticks_per_year,
            wall_clock_elapsed_seconds=wall_clock_elapsed,
            last_tick_duration_seconds=tick_duration,
            avg_recent_tick_duration_seconds=avg_recent,
            decisions_by_type=self.decisions_by_type,
            retry_count=self.retry_count,
            fallback_count=self.fallback_count,
            last_checkpoint_tick=checkpoint_tick,
        )
