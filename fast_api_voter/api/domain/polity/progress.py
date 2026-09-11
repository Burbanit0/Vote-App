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

THE INTRA-TICK HEARTBEAT (2026-09-11) exists because per-tick writes alone
made a healthy run indistinguishable from a dead one, and that cost a real
run. A pop-500 election tick legitimately spends **about an hour** inside a
single tick: `cast_votes` decides the entire population (~167 sequential LLM
calls at chunk size 3) before its caller journals anything at all. During
that hour, with only `record_tick` writing, every artifact an operator can
see is frozen -- no new journal line, no `progress.json` update, and a
near-zero CPU reading because the process is blocked on a GPU server the
whole time. On 2026-09-11 that combination was (incorrectly) read as a hang
and a working run was killed, discarding ~2h of compute.

So `record_llm_activity` updates `progress.json` from the LLM client itself,
independently of ticks: an operator can now answer "is this alive?" from
`last_llm_response_at` without reading the inference server's logs, and
without inferring anything from CPU time or socket state (both of which are
actively misleading for this workload -- see `check_run_liveness.py`).
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Deque

_HEARTBEAT_MIN_WRITE_INTERVAL_SECONDS = 5.0
"""Floor on how often `record_llm_activity` may rewrite `progress.json`.

Not a performance guess: the fastest decision type observed in production
completes a few calls per second at small chunk sizes, and rewriting a ~1 KB
file (temp + `os.replace`) that often is pure waste. Five seconds is far
below the minute-scale staleness anyone actually reasons about when asking
"is this run alive", so the throttle costs nothing diagnostically. A write is
never skipped for the LAST call of a batch in any harmful way -- `record_tick`
always writes unconditionally at the tick boundary."""

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
    tick_in_progress: int | None = None,
    llm_calls_completed: int = 0,
    last_llm_response_at: float | None = None,
) -> None:
    """Atomic write (temp file + `os.replace`), same discipline as
    `checkpoint.save_checkpoint` -- a process killed mid-write must never
    leave a reader (an operator's `cat`, a future UI's polling fetch) a
    half-written, unparseable file.

    The three heartbeat parameters default to the pre-2026-09-11 shape, so a
    caller that only knows about per-tick progress still produces a valid
    file. `last_llm_response_at` is a `time.time()` wall-clock epoch, NOT
    monotonic: it is written for a reader in another process, which shares no
    monotonic origin with this one.

    Only the ABSOLUTE timestamp is stored, never a "seconds since" figure --
    that would be stale the instant it is written, and staleness is the exact
    quantity a reader needs to be right about. Readers compute the delta
    themselves against their own clock (`check_run_liveness.py` does)."""
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
        # `tick` above is the last tick that COMPLETED; this is the one being
        # computed right now. During a pop-500 election tick the two differ
        # for about an hour, and that gap is exactly the state that used to be
        # invisible.
        "tick_in_progress": tick_in_progress,
        "llm_calls_completed": llm_calls_completed,
        "last_llm_response_at": last_llm_response_at,
        "last_llm_response_timestamp": (
            datetime.fromtimestamp(last_llm_response_at, timezone.utc).isoformat()
            if last_llm_response_at is not None
            else None
        ),
        "progress_written_at": datetime.now(timezone.utc).isoformat(),
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
        # --- intra-tick heartbeat state (2026-09-11) ---
        # A lock, even though the shipped config is parallel.intra_run_workers=1:
        # run_chunks CAN fan out, and then record_llm_activity is called from
        # several worker threads at once. The counter and the throttle decision
        # must not interleave, and two threads must never write the temp file
        # concurrently (os.replace is atomic, but two writers sharing one temp
        # PATH are not).
        self._lock = threading.Lock()
        self._tick_in_progress: int | None = None
        self._llm_calls_completed = 0
        self._last_llm_response_at: float | None = None
        self._last_heartbeat_write_monotonic: float | None = None
        # Last values seen at a tick boundary, replayed verbatim into a
        # heartbeat write so it never invents tick-level numbers it cannot
        # know -- a heartbeat updates the liveness fields and nothing else.
        self._last_tick = 0
        self._last_tick_duration = 0.0
        self._last_checkpoint_tick = 0
        self._last_wall_clock_elapsed = 0.0
        self._last_wall_clock_at_monotonic: float | None = None
        self._avg_recent = 0.0

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
        with self._lock:
            self._last_tick = tick
            self._last_tick_duration = tick_duration
            self._last_checkpoint_tick = checkpoint_tick
            self._last_wall_clock_elapsed = wall_clock_elapsed
            self._last_wall_clock_at_monotonic = time.monotonic()
            self._avg_recent = avg_recent
            # This tick is done; nothing is in progress until begin_tick says so.
            self._tick_in_progress = None
            self._write_locked(avg_recent_tick_duration_seconds=avg_recent, wall_clock_elapsed=wall_clock_elapsed)

    def begin_tick(self, tick: int) -> None:
        """Called at the TOP of the run loop's tick body, before any phase
        runs. Publishes which tick is being computed, so a reader can tell
        "tick 16 has been in progress for 40 minutes" from "tick 16 finished
        and nothing has started" -- indistinguishable before this existed."""
        with self._lock:
            self._tick_in_progress = tick
            self._write_locked(
                avg_recent_tick_duration_seconds=self._avg_recent,
                wall_clock_elapsed=self._current_wall_clock_locked(),
            )

    def record_llm_activity(self) -> None:
        """Called once per completed LLM response, by the client wrapper
        (`HeartbeatClient`) rather than by any decision type -- one choke
        point, so no caller in `llm_behavior_engine` needs to know this
        exists, and no decision type can be added later that forgets to
        report.

        Deliberately records only "a response arrived, and when", not which
        decision type produced it: `complete_json` genuinely does not know the
        decision type (it is a parameter of the engine's own
        `_complete_and_decode_with_replay`, one layer up), and threading it
        through the client protocol to decorate a diagnostic would be a real
        cost for a nice-to-have. Liveness is fully answered without it; for
        "what is it doing", `tick_in_progress` plus the journal's last event
        already say enough.

        Writes are throttled (see _HEARTBEAT_MIN_WRITE_INTERVAL_SECONDS) but
        the counter is never throttled -- `llm_calls_completed` is exact."""
        with self._lock:
            self._llm_calls_completed += 1
            self._last_llm_response_at = time.time()
            now = time.monotonic()
            last_write = self._last_heartbeat_write_monotonic
            if last_write is not None and now - last_write < _HEARTBEAT_MIN_WRITE_INTERVAL_SECONDS:
                return
            self._last_heartbeat_write_monotonic = now
            self._write_locked(
                avg_recent_tick_duration_seconds=self._avg_recent,
                wall_clock_elapsed=self._current_wall_clock_locked(),
            )

    def _current_wall_clock_locked(self) -> float:
        """The caller owns run-start time (see record_tick's docstring), so a
        between-ticks write extrapolates from the last value it was handed
        rather than inventing its own origin -- which would disagree with
        every per-tick write in the same file."""
        if self._last_wall_clock_at_monotonic is None:
            return self._last_wall_clock_elapsed
        return self._last_wall_clock_elapsed + (time.monotonic() - self._last_wall_clock_at_monotonic)

    def _write_locked(self, *, avg_recent_tick_duration_seconds: float, wall_clock_elapsed: float) -> None:
        """Must be called with self._lock held."""
        write_progress(
            self._progress_path,
            run_id=self._run_id,
            tick=self._last_tick,
            total_ticks=self._total_ticks,
            ticks_per_year=self._ticks_per_year,
            wall_clock_elapsed_seconds=wall_clock_elapsed,
            last_tick_duration_seconds=self._last_tick_duration,
            avg_recent_tick_duration_seconds=avg_recent_tick_duration_seconds,
            decisions_by_type=self.decisions_by_type,
            retry_count=self.retry_count,
            fallback_count=self.fallback_count,
            last_checkpoint_tick=self._last_checkpoint_tick,
            tick_in_progress=self._tick_in_progress,
            llm_calls_completed=self._llm_calls_completed,
            last_llm_response_at=self._last_llm_response_at,
        )


class HeartbeatClient:
    """Wraps a real `LlmClientProtocol` and reports every completed response
    to a `ProgressTracker`. Structural typing only -- it imports nothing from
    `llm_client`, it just forwards the protocol's two methods.

    Applied in `run_polity_simulation._llm_client_scope`, and ONLY to a client
    this process owns: an injected client (every test) is passed through
    untouched, exactly as that function's existing short-circuit already does
    for real HTTP calls.

    `count_prompt_tokens` deliberately does NOT beat: it is a `max_tokens=1`
    prefill probe, not a decision, and counting it would let a run look busy
    while making no actual progress. Only `complete_json` -- the call that
    produces a decision -- counts.

    The beat fires AFTER the inner call returns, so it means "a response
    arrived", never "a request was sent". A request that never comes back must
    not refresh the heartbeat; that is the entire point."""

    def __init__(self, inner: Any, on_response: Callable[[], None]) -> None:
        self._inner = inner
        self._on_response = on_response

    def complete_json(self, **kwargs: Any) -> str:
        result = self._inner.complete_json(**kwargs)
        self._on_response()
        return str(result)

    def count_prompt_tokens(self, **kwargs: Any) -> int:
        return int(self._inner.count_prompt_tokens(**kwargs))
