"""Lot 7 — journal.py: append-only JSONL event log.

Contract (dev-plan-v0-worktree.md §3, Lot 7): a run interrupted abruptly
leaves a journal readable up to the last complete event.
"""
import json

from api.domain.polity.config import load_config
from api.domain.polity.journal import Journal


def test_events_get_sequential_ids_in_write_order(tmp_path):
    journal = Journal(tmp_path / "run.jsonl", run_id="r1")
    ids = [journal.write(tick=t, event_type="vote_cast", payload={"t": t}) for t in range(5)]
    journal.close()
    assert ids == [0, 1, 2, 3, 4]


def test_written_events_round_trip_through_json(tmp_path):
    path = tmp_path / "run.jsonl"
    with Journal(path, run_id="r1") as journal:
        journal.write(
            tick=3,
            event_type="candidacy_declared",
            payload={"party_id": 2},
            citizen_id=42,
            motif="AMBITION_THRESHOLD",
        )
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event == {
        "run_id": "r1",
        "event_id": 0,
        "tick": 3,
        "event_type": "candidacy_declared",
        "payload": {"party_id": 2},
        "citizen_id": 42,
        "motif": "AMBITION_THRESHOLD",
        "rationale": None,
        "codebook_version": "",
    }


def test_events_before_an_abrupt_interruption_remain_readable(tmp_path):
    path = tmp_path / "run.jsonl"
    journal = Journal(path, run_id="r1")
    for t in range(5):
        journal.write(tick=t, event_type="vote_cast", payload={"t": t})
    # Simulate a crash mid-write: a truncated, unterminated line appended
    # directly, as if the process died mid os-level write() of event 6 —
    # never call journal.close() either, matching an abrupt kill.
    with path.open("a", encoding="utf-8") as raw:
        raw.write('{"event_type": "vote_cast", "incomplete"')

    complete_events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            complete_events.append(json.loads(line))
        except json.JSONDecodeError:
            break  # the truncated tail -- everything before it is still good
    assert len(complete_events) == 5
    assert [e["event_id"] for e in complete_events] == [0, 1, 2, 3, 4]


def test_from_config_writes_under_output_dir_run_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = load_config().journal
    with Journal.from_config(config, run_id="baseline-42") as journal:
        journal.write(tick=0, event_type="elected", payload={})
    expected = tmp_path / config.output_dir / "baseline-42" / "events.jsonl"
    assert expected.is_file()
    assert len(expected.read_text(encoding="utf-8").splitlines()) == 1


def test_two_journals_with_the_same_writes_produce_byte_identical_files(tmp_path):
    def write_five(path):
        with Journal(path, run_id="r1") as journal:
            for t in range(5):
                journal.write(tick=t, event_type="vote_cast", payload={"b": 2, "a": 1})

    path_a, path_b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    write_five(path_a)
    write_five(path_b)
    assert path_a.read_bytes() == path_b.read_bytes()
