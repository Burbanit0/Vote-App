"""progress.py — per-tick live status (Phase 4, plan-flagship-30y-run.md).

`ProgressTracker` re-derives every cumulative count from the journal itself
(never from a caller-maintained running total), so these tests write real
journal lines and assert on what `record_tick` reads back out of them --
the same discipline `checkpoint.py`'s own round-trip tests use.
"""
import json

from api.domain.polity.journal import Journal
from api.domain.polity.progress import HeartbeatClient, ProgressTracker, write_progress


def _write_event(journal, *, event_type, codebook_version="", payload=None, tick=0):
    journal.write(tick=tick, event_type=event_type, payload=payload or {}, codebook_version=codebook_version)


def test_write_progress_computes_simulated_year(tmp_path):
    path = tmp_path / "progress.json"
    write_progress(
        path, run_id="r1", tick=52, total_ticks=120, ticks_per_year=4,
        wall_clock_elapsed_seconds=100.0, last_tick_duration_seconds=5.0,
        avg_recent_tick_duration_seconds=5.0, decisions_by_type={}, retry_count=0,
        fallback_count=0, fallback_by_type={}, last_checkpoint_tick=52,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["simulated_year"] == 13.0


def test_write_progress_computes_eta_from_remaining_ticks_and_avg_duration(tmp_path):
    path = tmp_path / "progress.json"
    write_progress(
        path, run_id="r1", tick=10, total_ticks=20, ticks_per_year=4,
        wall_clock_elapsed_seconds=50.0, last_tick_duration_seconds=5.0,
        avg_recent_tick_duration_seconds=5.0, decisions_by_type={}, retry_count=0,
        fallback_count=0, fallback_by_type={}, last_checkpoint_tick=10,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["eta_seconds"] == 50.0  # 10 remaining ticks x 5.0s avg


def test_write_progress_eta_is_zero_at_the_final_tick(tmp_path):
    path = tmp_path / "progress.json"
    write_progress(
        path, run_id="r1", tick=20, total_ticks=20, ticks_per_year=4,
        wall_clock_elapsed_seconds=200.0, last_tick_duration_seconds=5.0,
        avg_recent_tick_duration_seconds=5.0, decisions_by_type={}, retry_count=0,
        fallback_count=0, fallback_by_type={}, last_checkpoint_tick=20,
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
        fallback_count=0, fallback_by_type={}, last_checkpoint_tick=1,
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
        fallback_count=0, fallback_by_type={}, last_checkpoint_tick=1,
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


def test_record_tick_buckets_fallback_count_by_decision_type(tmp_path):
    # Track C2 (2026-09-11, lets-build-a-solid-spicy-otter.md): the aggregate
    # fallback_count alone hid a real problem in Stage 3 -- 0.26% overall
    # concealed a single decision type failing 67% of the time. Per-type
    # tracking is what a rate alert needs to actually catch that.
    journal_path = tmp_path / "events.jsonl"
    with Journal(journal_path, run_id="r1") as journal:
        _write_event(journal, event_type="vote_cast", codebook_version="1.6", payload={"llm_fallback": 1})
        _write_event(journal, event_type="vote_cast", codebook_version="1.6", payload={"llm_fallback": 0})
        _write_event(journal, event_type="party_nomination_choice", codebook_version="1.6", payload={"llm_fallback": 1})

    tracker = ProgressTracker(run_id="r1", total_ticks=10, ticks_per_year=4, progress_path=tmp_path / "progress.json")
    tracker.record_tick(tick=0, tick_duration=1.0, wall_clock_elapsed=1.0, journal_path=journal_path, checkpoint_tick=0)

    assert tracker.fallback_count == 2
    assert tracker.fallback_by_type == {"vote_cast": 1, "party_nomination_choice": 1}


def test_write_progress_serializes_fallback_by_type_sorted(tmp_path):
    path = tmp_path / "progress.json"
    write_progress(
        path, run_id="r1", tick=1, total_ticks=10, ticks_per_year=4,
        wall_clock_elapsed_seconds=1.0, last_tick_duration_seconds=1.0,
        avg_recent_tick_duration_seconds=1.0, decisions_by_type={}, retry_count=0,
        fallback_count=2, fallback_by_type={"vote_cast": 1, "party_nomination_choice": 1}, last_checkpoint_tick=1,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["fallback_by_type"] == {"party_nomination_choice": 1, "vote_cast": 1}


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


# ── Intra-tick heartbeat (2026-09-11) ────────────────────────────────────
#
# This whole block exists because per-tick writes alone made a healthy run
# indistinguishable from a dead one, and a working Stage 3 run was killed on
# that ambiguity (~2h of GPU compute discarded). See progress.py's module
# docstring for the four misleading symptoms.


def _tracker(tmp_path, **overrides):
    kwargs = dict(run_id="r1", total_ticks=32, ticks_per_year=4,
                  progress_path=tmp_path / "progress.json", llm_enabled=True)
    kwargs.update(overrides)
    return ProgressTracker(**kwargs)


def _progress(tmp_path):
    return json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))


def test_write_progress_still_valid_without_any_heartbeat_argument(tmp_path):
    # Back-compat: the three heartbeat parameters default, so a caller that
    # predates them still produces a well-formed file.
    write_progress(
        tmp_path / "progress.json", run_id="r1", tick=1, total_ticks=4, ticks_per_year=4,
        wall_clock_elapsed_seconds=1.0, last_tick_duration_seconds=1.0,
        avg_recent_tick_duration_seconds=1.0, decisions_by_type={}, retry_count=0,
        fallback_count=0, fallback_by_type={}, last_checkpoint_tick=1,
    )
    payload = _progress(tmp_path)
    assert payload["tick_in_progress"] is None
    assert payload["llm_calls_completed"] == 0
    assert payload["last_llm_response_at"] is None
    assert payload["last_llm_response_timestamp"] is None


def test_begin_tick_publishes_the_tick_being_computed(tmp_path):
    tracker = _tracker(tmp_path)
    tracker.begin_tick(16)
    payload = _progress(tmp_path)
    assert payload["tick_in_progress"] == 16
    assert payload["tick"] == 0  # nothing has COMPLETED yet


def test_record_tick_clears_tick_in_progress(tmp_path):
    # The pair (tick, tick_in_progress) is the whole signal: "16 in progress"
    # and "16 done, nothing started" were indistinguishable before this.
    tracker = _tracker(tmp_path)
    tracker.begin_tick(16)
    tracker.record_tick(tick=16, tick_duration=1.0, wall_clock_elapsed=1.0,
                        journal_path=tmp_path / "events.jsonl", checkpoint_tick=16)
    payload = _progress(tmp_path)
    assert payload["tick"] == 16
    assert payload["tick_in_progress"] is None


def _no_throttle(monkeypatch):
    """Makes every beat write, for tests about the COUNTER rather than the
    throttle. Without this they would assert the file is never stale, which
    is not the contract -- see test_the_file_may_lag_but_only_by_the_throttle."""
    import api.domain.polity.progress as progress_module
    monkeypatch.setattr(progress_module, "_HEARTBEAT_MIN_WRITE_INTERVAL_SECONDS", 0.0)


def test_record_llm_activity_counts_every_call(tmp_path, monkeypatch):
    _no_throttle(monkeypatch)
    tracker = _tracker(tmp_path)
    tracker.begin_tick(16)
    for _ in range(50):
        tracker.record_llm_activity()
    payload = _progress(tmp_path)
    assert payload["llm_calls_completed"] == 50
    assert payload["last_llm_response_at"] is not None


def test_the_file_may_lag_but_only_by_the_throttle(tmp_path):
    # The real contract, stated as a test: the counter is exact IN MEMORY and
    # the file is a snapshot at most _HEARTBEAT_MIN_WRITE_INTERVAL_SECONDS
    # stale. That bound is what makes the file trustworthy for liveness -- a
    # few seconds of lag is irrelevant to a question asked on a minute scale.
    tracker = _tracker(tmp_path)
    for _ in range(50):
        tracker.record_llm_activity()
    assert tracker._llm_calls_completed == 50          # exact in memory
    assert _progress(tmp_path)["llm_calls_completed"] == 1  # file lags within the window


def test_record_llm_activity_throttles_the_rewrite(tmp_path, monkeypatch):
    import api.domain.polity.progress as progress_module

    writes = []
    real_write = progress_module.write_progress
    monkeypatch.setattr(
        progress_module, "write_progress",
        lambda *a, **k: (writes.append(1), real_write(*a, **k))[1],
    )
    tracker = _tracker(tmp_path)
    for _ in range(20):
        tracker.record_llm_activity()
    # 20 back-to-back beats inside the 5s window: the first writes, the rest
    # are suppressed. Rewriting a ~1KB file 20 times for the same second of
    # information is pure I/O waste.
    assert len(writes) == 1


def test_heartbeat_survives_a_tick_boundary_and_keeps_counting(tmp_path, monkeypatch):
    _no_throttle(monkeypatch)
    tracker = _tracker(tmp_path)
    tracker.begin_tick(1)
    tracker.record_llm_activity()
    tracker.record_tick(tick=1, tick_duration=1.0, wall_clock_elapsed=1.0,
                        journal_path=tmp_path / "events.jsonl", checkpoint_tick=1)
    tracker.begin_tick(2)
    tracker.record_llm_activity()
    assert _progress(tmp_path)["llm_calls_completed"] == 2


def test_the_scenario_that_caused_the_incident_is_now_legible(tmp_path, monkeypatch):
    # 2026-09-11, reconstructed: an election tick mid-flight, journal silent
    # for an hour because cast_votes decides the whole population before its
    # caller journals anything, ~0% CPU because the process is blocked on a
    # GPU server. Previously every visible artifact was frozen and the run
    # looked dead. Now the file itself says otherwise.
    _no_throttle(monkeypatch)
    tracker = _tracker(tmp_path)
    tracker.record_tick(tick=15, tick_duration=60.0, wall_clock_elapsed=900.0,
                        journal_path=tmp_path / "events.jsonl", checkpoint_tick=15)
    tracker.begin_tick(16)
    tracker.record_llm_activity()

    payload = _progress(tmp_path)
    assert payload["tick"] == 15            # last COMPLETED tick, unchanged for an hour
    assert payload["tick_in_progress"] == 16  # ...but tick 16 is being worked on
    assert payload["llm_calls_completed"] == 1
    # And the one fact that settles "alive or stuck", with no reference to CPU
    # time, socket age, or journal silence -- all three of which misled.
    assert payload["last_llm_response_at"] is not None


# ── HeartbeatClient ──────────────────────────────────────────────────────

class _RecordingClient:
    def __init__(self, raises=None):
        self.complete_calls = []
        self.count_calls = 0
        self._raises = raises

    def complete_json(self, **kwargs):
        self.complete_calls.append(kwargs)
        if self._raises is not None:
            raise self._raises
        return '{"decisions": []}'

    def count_prompt_tokens(self, **kwargs):
        self.count_calls += 1
        return 42


def test_heartbeat_client_forwards_kwargs_and_result_untouched():
    inner = _RecordingClient()
    beats = []
    client = HeartbeatClient(inner, lambda: beats.append(1))

    result = client.complete_json(system_prompt="s", user_prompt="u", json_schema={},
                                  max_tokens=10, think=False, temperature=0.3, seed=7)

    assert result == '{"decisions": []}'
    # Every kwarg survives -- retry_temperature/retry_seed_base ride on these,
    # and a wrapper that dropped them would silently disable retry sampling
    # variation for all nine decision types.
    assert inner.complete_calls[0]["temperature"] == 0.3
    assert inner.complete_calls[0]["seed"] == 7
    assert len(beats) == 1


def test_heartbeat_client_does_not_beat_on_a_token_count_probe():
    # count_prompt_tokens is a max_tokens=1 prefill probe, not a decision.
    # Counting it would let a run look busy while producing nothing.
    inner = _RecordingClient()
    beats = []
    client = HeartbeatClient(inner, lambda: beats.append(1))

    assert client.count_prompt_tokens(system_prompt="s", user_prompt="u") == 42
    assert inner.count_calls == 1
    assert beats == []


def test_heartbeat_client_does_not_beat_when_the_call_never_returns():
    # THE point of the whole mechanism. A request that fails (or, in
    # production, one that never comes back) must not refresh the heartbeat --
    # otherwise a stuck run would keep reporting itself alive, which is
    # exactly the false reassurance this was built to prevent.
    inner = _RecordingClient(raises=RuntimeError("connection died"))
    beats = []
    client = HeartbeatClient(inner, lambda: beats.append(1))

    try:
        client.complete_json(system_prompt="s", user_prompt="u", json_schema={}, max_tokens=10)
    except RuntimeError:
        pass

    assert beats == []
