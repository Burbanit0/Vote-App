"""progress.py — per-tick live status (Phase 4, plan-flagship-30y-run.md).

`ProgressTracker` re-derives every cumulative count from the journal itself
(never from a caller-maintained running total), so these tests write real
journal lines and assert on what `record_tick` reads back out of them --
the same discipline `checkpoint.py`'s own round-trip tests use.
"""
import json

from api.domain.polity.journal import Journal
from api.domain.polity.progress import ProgressTracker, write_progress


def _write_event(journal, *, event_type, codebook_version="", payload=None, tick=0):
    journal.write(tick=tick, event_type=event_type, payload=payload or {}, codebook_version=codebook_version)


def test_write_progress_computes_simulated_year(tmp_path):
    path = tmp_path / "progress.json"
    write_progress(
        path, run_id="r1", tick=52, total_ticks=120, ticks_per_year=4,
        wall_clock_elapsed_seconds=100.0, last_tick_duration_seconds=5.0,
        avg_recent_tick_duration_seconds=5.0, decisions_by_type={}, retry_count=0,
        fallback_count=0, last_checkpoint_tick=52,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["simulated_year"] == 13.0


def test_write_progress_computes_eta_from_remaining_ticks_and_avg_duration(tmp_path):
    path = tmp_path / "progress.json"
    write_progress(
        path, run_id="r1", tick=10, total_ticks=20, ticks_per_year=4,
        wall_clock_elapsed_seconds=50.0, last_tick_duration_seconds=5.0,
        avg_recent_tick_duration_seconds=5.0, decisions_by_type={}, retry_count=0,
        fallback_count=0, last_checkpoint_tick=10,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["eta_seconds"] == 50.0  # 10 remaining ticks x 5.0s avg


def test_write_progress_eta_is_zero_at_the_final_tick(tmp_path):
    path = tmp_path / "progress.json"
    write_progress(
        path, run_id="r1", tick=20, total_ticks=20, ticks_per_year=4,
        wall_clock_elapsed_seconds=200.0, last_tick_duration_seconds=5.0,
        avg_recent_tick_duration_seconds=5.0, decisions_by_type={}, retry_count=0,
        fallback_count=0, last_checkpoint_tick=20,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["eta_seconds"] == 0.0


def test_write_progress_decisions_total_sums_the_type_breakdown(tmp_path):
    path = tmp_path / "progress.json"
    write_progress(
        path, run_id="r1", tick=1, total_ticks=10, ticks_per_year=4,
        wall_clock_elapsed_seconds=1.0, last_tick_duration_seconds=1.0,
        avg_recent_tick_duration_seconds=1.0,
        decisions_by_type={"vote_cast": 100, "chamber_deliberation": 270}, retry_count=0,
        fallback_count=0, last_checkpoint_tick=1,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["decisions_total"] == 370
    assert payload["decisions_by_type"] == {"chamber_deliberation": 270, "vote_cast": 100}


def test_write_progress_is_atomic_no_tmp_file_left_behind(tmp_path):
    path = tmp_path / "progress.json"
    write_progress(
        path, run_id="r1", tick=1, total_ticks=10, ticks_per_year=4,
        wall_clock_elapsed_seconds=1.0, last_tick_duration_seconds=1.0,
        avg_recent_tick_duration_seconds=1.0, decisions_by_type={}, retry_count=0,
        fallback_count=0, last_checkpoint_tick=1,
    )
    assert path.exists()
    assert not path.with_suffix(path.suffix + ".tmp").exists()


# ── ProgressTracker ──────────────────────────────────────────────────────

def test_record_tick_counts_only_llm_sourced_events(tmp_path):
    journal_path = tmp_path / "events.jsonl"
    with Journal(journal_path, run_id="r1") as journal:
        _write_event(journal, event_type="vote_cast", codebook_version="1.6")
        _write_event(journal, event_type="legitimacy_updated")  # deterministic, no codebook_version

    tracker = ProgressTracker(run_id="r1", total_ticks=10, ticks_per_year=4, progress_path=tmp_path / "progress.json")
    tracker.record_tick(tick=0, tick_duration=1.0, wall_clock_elapsed=1.0, journal_path=journal_path, checkpoint_tick=0)

    assert tracker.decisions_by_type == {"vote_cast": 1}


def test_record_tick_counts_retry_and_fallback_from_payload_flags(tmp_path):
    journal_path = tmp_path / "events.jsonl"
    with Journal(journal_path, run_id="r1") as journal:
        _write_event(
            journal, event_type="vote_cast", codebook_version="1.6",
            payload={"retry_sampling_varied": 1, "llm_fallback": 0},
        )
        _write_event(
            journal, event_type="vote_cast", codebook_version="1.6",
            payload={"retry_sampling_varied": 0, "llm_fallback": 1},
        )
        _write_event(
            journal, event_type="vote_cast", codebook_version="1.6",
            payload={"retry_sampling_varied": 0, "llm_fallback": 0},
        )

    tracker = ProgressTracker(run_id="r1", total_ticks=10, ticks_per_year=4, progress_path=tmp_path / "progress.json")
    tracker.record_tick(tick=0, tick_duration=1.0, wall_clock_elapsed=1.0, journal_path=journal_path, checkpoint_tick=0)

    assert tracker.retry_count == 1
    assert tracker.fallback_count == 1


def test_record_tick_is_incremental_not_a_full_rescan(tmp_path):
    journal_path = tmp_path / "events.jsonl"
    tracker = ProgressTracker(run_id="r1", total_ticks=10, ticks_per_year=4, progress_path=tmp_path / "progress.json")

    with Journal(journal_path, run_id="r1") as journal:
        _write_event(journal, event_type="vote_cast", codebook_version="1.6", tick=0)
    tracker.record_tick(tick=0, tick_duration=1.0, wall_clock_elapsed=1.0, journal_path=journal_path, checkpoint_tick=0)
    assert tracker.decisions_by_type == {"vote_cast": 1}

    with Journal(journal_path, run_id="r1", start_event_id=1) as journal:
        _write_event(journal, event_type="candidacy_considered", codebook_version="1.6", tick=1)
    tracker.record_tick(tick=1, tick_duration=1.0, wall_clock_elapsed=2.0, journal_path=journal_path, checkpoint_tick=1)

    # Cumulative -- the tick-0 count is still there, not replaced by tick 1's.
    assert tracker.decisions_by_type == {"vote_cast": 1, "candidacy_considered": 1}


def test_a_fresh_tracker_pointed_at_an_existing_journal_backfills_correctly(tmp_path):
    # This IS what a resume looks like from ProgressTracker's own point of
    # view: a brand-new instance (byte_offset=0), constructed in a fresh
    # process, pointed at a journal that already holds a crashed run's own
    # pre-resume history. No special "resume mode" -- the first record_tick
    # call just finds everything that's already there.
    journal_path = tmp_path / "events.jsonl"
    with Journal(journal_path, run_id="r1") as journal:
        for _ in range(3):
            _write_event(journal, event_type="vote_cast", codebook_version="1.6")

    tracker = ProgressTracker(run_id="r1", total_ticks=10, ticks_per_year=4, progress_path=tmp_path / "progress.json")
    tracker.record_tick(tick=5, tick_duration=1.0, wall_clock_elapsed=1.0, journal_path=journal_path, checkpoint_tick=5)

    assert tracker.decisions_by_type == {"vote_cast": 3}


def test_llm_disabled_never_counts_reaction_to_events_own_unconditional_codebook_version(tmp_path):
    # run_polity_simulation._run_reaction_to_event writes codebook_version
    # unconditionally, even on its own deterministic branch (llm.enabled=
    # False) -- "codebook_version is truthy" is therefore NOT a reliable
    # LLM-decision signal on that branch. llm_enabled=False must not count
    # this event type as an LLM decision just because the field is set.
    journal_path = tmp_path / "events.jsonl"
    with Journal(journal_path, run_id="r1") as journal:
        _write_event(journal, event_type="reaction_to_event", codebook_version="1.6")

    tracker = ProgressTracker(
        run_id="r1", total_ticks=10, ticks_per_year=4, progress_path=tmp_path / "progress.json", llm_enabled=False,
    )
    tracker.record_tick(tick=0, tick_duration=1.0, wall_clock_elapsed=1.0, journal_path=journal_path, checkpoint_tick=0)

    assert tracker.decisions_by_type == {}


def test_llm_enabled_true_still_counts_normally(tmp_path):
    # The default (llm_enabled=True) must stay exactly as it was before this
    # gate was added -- every earlier test in this file already exercises
    # this, but this one pins the default explicitly.
    journal_path = tmp_path / "events.jsonl"
    with Journal(journal_path, run_id="r1") as journal:
        _write_event(journal, event_type="vote_cast", codebook_version="1.6")

    tracker = ProgressTracker(run_id="r1", total_ticks=10, ticks_per_year=4, progress_path=tmp_path / "progress.json")
    tracker.record_tick(tick=0, tick_duration=1.0, wall_clock_elapsed=1.0, journal_path=journal_path, checkpoint_tick=0)

    assert tracker.decisions_by_type == {"vote_cast": 1}


def test_record_tick_on_a_tick_with_no_new_events_is_a_safe_no_op(tmp_path):
    journal_path = tmp_path / "events.jsonl"
    with Journal(journal_path, run_id="r1"):
        pass  # a tick that journals nothing is legal (no election, no scandal, ...)

    tracker = ProgressTracker(run_id="r1", total_ticks=10, ticks_per_year=4, progress_path=tmp_path / "progress.json")
    tracker.record_tick(tick=0, tick_duration=1.0, wall_clock_elapsed=1.0, journal_path=journal_path, checkpoint_tick=0)

    assert tracker.decisions_by_type == {}
    assert tracker.retry_count == 0
    assert tracker.fallback_count == 0


def test_record_tick_writes_progress_json(tmp_path):
    journal_path = tmp_path / "events.jsonl"
    with Journal(journal_path, run_id="r1"):
        pass
    progress_path = tmp_path / "progress.json"
    tracker = ProgressTracker(run_id="r1", total_ticks=10, ticks_per_year=4, progress_path=progress_path)

    tracker.record_tick(tick=3, tick_duration=2.5, wall_clock_elapsed=10.0, journal_path=journal_path, checkpoint_tick=3)

    payload = json.loads(progress_path.read_text(encoding="utf-8"))
    assert payload["tick"] == 3
    assert payload["last_checkpoint_tick"] == 3
    assert payload["last_tick_duration_seconds"] == 2.5


def test_rolling_window_averages_only_the_most_recent_ticks(tmp_path):
    journal_path = tmp_path / "events.jsonl"
    with Journal(journal_path, run_id="r1"):
        pass
    progress_path = tmp_path / "progress.json"
    tracker = ProgressTracker(run_id="r1", total_ticks=100, ticks_per_year=4, progress_path=progress_path)

    # 10 ticks at duration 100.0, then 10 more at duration 1.0 -- the window
    # (size 10) should have fully rolled past the expensive early ticks.
    for tick in range(10):
        tracker.record_tick(
            tick=tick, tick_duration=100.0, wall_clock_elapsed=float(tick), journal_path=journal_path, checkpoint_tick=tick
        )
    for tick in range(10, 20):
        tracker.record_tick(
            tick=tick, tick_duration=1.0, wall_clock_elapsed=float(tick), journal_path=journal_path, checkpoint_tick=tick
        )

    payload = json.loads(progress_path.read_text(encoding="utf-8"))
    assert payload["avg_recent_tick_duration_seconds"] == 1.0
