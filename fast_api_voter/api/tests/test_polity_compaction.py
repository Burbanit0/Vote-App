"""compaction.py — v4 storage lot (§16.6): the post-run DuckDB analytical
store. Hand-built event lists against a real duckdb.connect(':memory:'),
no tmp_path, no Journal, no run -- the same direct-call register
test_polity_indexer.py uses, and for the same reason (no live/opt-in
gating needed here -- DuckDB is embedded, this lot is fully offline-
testable). The one exception is the headline end-to-end test.
"""
import dataclasses
import json

import duckdb
import pytest

from api.domain.polity.codebook import CODEBOOK_VERSION
from api.domain.polity.compaction import PolityCompactionError, compact_events, compact_run
from api.domain.polity.config import load_config
from api.domain.polity.run_polity_simulation import run_simulation


def _e(run_id, event_id, tick, event_type, payload, citizen_id=None, motif=None, rationale=None, codebook_version=""):
    return {
        "run_id": run_id, "event_id": event_id, "tick": tick, "event_type": event_type,
        "payload": payload, "citizen_id": citizen_id, "motif": motif, "rationale": rationale,
        "codebook_version": codebook_version,
    }


def _con():
    return duckdb.connect(":memory:")


# ── schema and raw fidelity ────────────────────────────────────────────────

def test_the_citizen_events_table_has_section_16_3_columns_in_order():
    con = _con()
    compact_events([], con)
    columns = con.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'citizen_events' ORDER BY ordinal_position"
    ).fetchall()
    assert [c[0] for c in columns] == [
        "run_id", "event_id", "codebook_version", "tick", "citizen_id",
        "event_type", "payload", "motif", "rationale",
    ]


def test_every_journal_line_becomes_exactly_one_row_in_journal_order():
    events = [
        _e("r", 0, 0, "vote_cast", {}, motif="101"),
        _e("r", 1, 0, "vote_cast", {}, motif="102"),
        _e("r", 2, 4, "legislative_result", {}),
    ]
    con = _con()
    n = compact_events(events, con)
    assert n == 3
    rows = con.execute("SELECT event_id FROM citizen_events ORDER BY event_id").fetchall()
    assert [r[0] for r in rows] == [0, 1, 2]


def test_payload_json_is_byte_identical_to_the_journal_line():
    payload = {"b": 2, "a": 1, "nested": {"z": 9, "y": 8}}
    con = _con()
    compact_events([_e("r", 0, 0, "vote_cast", payload)], con)
    stored = con.execute("SELECT payload::VARCHAR FROM citizen_events").fetchone()[0]
    assert stored == json.dumps(payload, sort_keys=True)


def test_null_citizen_id_motif_and_rationale_survive_as_sql_nulls():
    con = _con()
    compact_events([_e("r", 0, 0, "legislative_result", {})], con)
    row = con.execute("SELECT citizen_id, motif, rationale FROM citizen_events").fetchone()
    assert row == (None, None, None)


def test_an_empty_codebook_version_stays_an_empty_string_not_null():
    con = _con()
    compact_events([_e("r", 0, 0, "vote_cast", {}, codebook_version="")], con)
    version = con.execute("SELECT codebook_version FROM citizen_events").fetchone()[0]
    assert version == ""


def test_the_three_section_16_1_indexes_exist():
    con = _con()
    compact_events([], con)
    names = {row[0] for row in con.execute("SELECT index_name FROM duckdb_indexes()").fetchall()}
    assert {
        "idx_citizen_events_citizen_id", "idx_citizen_events_tick", "idx_citizen_events_event_type",
    } <= names


def test_a_payload_with_dynamic_keys_is_stored_whole_not_flattened():
    # The read_json_auto landmine, guarded directly: legislative_result's
    # {"seats": {"0": 12, "1": 30}} has party-id keys that vary per run --
    # this must never become columns.
    payload = {"seats": {"0": 12, "1": 30}}
    con = _con()
    compact_events([_e("r", 0, 4, "legislative_result", payload)], con)
    columns = {r[0] for r in con.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'citizen_events'"
    ).fetchall()}
    assert "seats" not in columns and "0" not in columns
    value = con.execute("SELECT payload ->> '$.seats.0' FROM citizen_events").fetchone()[0]
    assert value == "12"


def test_compacting_the_same_journal_twice_produces_the_same_store(tmp_path):
    journal_path = tmp_path / "events.jsonl"
    journal_path.write_text(
        "\n".join(json.dumps(e) for e in [
            _e("r", 0, 0, "vote_cast", {}, motif="101"),
            _e("r", 1, 4, "legislative_result", {}),
        ]) + "\n",
        encoding="utf-8",
    )
    config = dataclasses.replace(load_config(), journal=dataclasses.replace(load_config().journal, output_dir=str(tmp_path)))

    db_path_a = compact_run(journal_path, config)
    result_a = duckdb.connect(str(db_path_a)).execute("SELECT event_id, tick, motif FROM citizen_events ORDER BY event_id").fetchall()
    db_path_b = compact_run(journal_path, config)
    result_b = duckdb.connect(str(db_path_b)).execute("SELECT event_id, tick, motif FROM citizen_events ORDER BY event_id").fetchall()

    assert db_path_a == db_path_b
    assert result_a == result_b
    assert len(result_a) == 2  # not doubled


def test_a_truncated_journal_line_raises_naming_its_line_number(tmp_path):
    journal_path = tmp_path / "events.jsonl"
    journal_path.write_text(json.dumps(_e("r", 0, 0, "vote_cast", {})) + "\n" + "{not valid json", encoding="utf-8")
    config = dataclasses.replace(load_config(), journal=dataclasses.replace(load_config().journal, output_dir=str(tmp_path)))

    with pytest.raises(ValueError, match=r"events\.jsonl:2"):
        compact_run(journal_path, config)


def test_an_empty_journal_produces_an_empty_but_well_formed_table():
    con = _con()
    n = compact_events([], con)
    assert n == 0
    assert con.execute("SELECT count(*) FROM citizen_events").fetchone()[0] == 0
    names = {row[0] for row in con.execute("SELECT index_name FROM duckdb_indexes()").fetchall()}
    assert "idx_citizen_events_citizen_id" in names
    assert con.execute("SELECT count(*) FROM citizen_events_decoded").fetchone()[0] == 0


def test_compact_run_rejects_a_non_jsonl_journal_format(tmp_path):
    journal_path = tmp_path / "events.jsonl"
    journal_path.write_text("", encoding="utf-8")
    config = load_config()
    config = dataclasses.replace(config, journal=dataclasses.replace(config.journal, format="parquet"))

    with pytest.raises(PolityCompactionError, match="format"):
        compact_run(journal_path, config)


# ── codebook decoding (§3.7.4) ─────────────────────────────────────────────

def test_codebook_motifs_has_one_row_per_distinct_motif_code_stamped_with_the_version():
    con = _con()
    compact_events([], con)
    rows = con.execute("SELECT count(*), count(DISTINCT codebook_version) FROM codebook_motifs").fetchone()
    assert rows == (35, 1)  # v6b Lot 1 added ChamberMotif's 2 codes to the 33 prior (v6 Lot 1: +1 PressureMotif 306)
    version = con.execute("SELECT DISTINCT codebook_version FROM codebook_motifs").fetchone()[0]
    assert version == CODEBOOK_VERSION


def test_the_decoded_view_labels_a_motif_by_join():
    con = _con()
    compact_events([_e("r", 0, 0, "vote_cast", {}, motif="101")], con)
    label = con.execute("SELECT motif_label FROM citizen_events_decoded").fetchone()[0]
    assert label == "NO_MATCHING_PRIORITY"


def test_an_unknown_motif_code_keeps_its_row_with_a_null_label():
    con = _con()
    compact_events([_e("r", 0, 0, "vote_cast", {}, motif="999")], con)
    row = con.execute("SELECT motif, motif_label FROM citizen_events_decoded").fetchone()
    assert row == ("999", None)


def test_a_non_numeric_motif_keeps_its_row_with_a_null_label():
    # The exact string test_polity_journal.py already writes for a
    # non-motif event (candidacy_considered's "AMBITION_THRESHOLD" motif
    # arg in an early fixture) -- pins TRY_CAST over a plain CAST.
    con = _con()
    compact_events([_e("r", 0, 0, "candidacy_considered", {}, motif="AMBITION_THRESHOLD")], con)
    row = con.execute("SELECT motif, motif_label FROM citizen_events_decoded").fetchone()
    assert row == ("AMBITION_THRESHOLD", None)


def test_the_shared_301_code_does_not_duplicate_a_row_in_the_decoded_view():
    # The D-6 fan-out regression test: 301 is MANDATE_DEVIATION_HIGH in
    # both ResponseMotif and PressureMotif. codebook_motifs is keyed on
    # `code` alone (one row), so the LEFT JOIN must not fan out.
    events = [
        _e("r", 0, 0, "representative_response", {}, citizen_id=1, motif="301"),
        _e("r", 1, 0, "pressure_action", {}, citizen_id=2, motif="301"),
    ]
    con = _con()
    compact_events(events, con)
    rows = con.execute("SELECT event_id, motif_label FROM citizen_events_decoded ORDER BY event_id").fetchall()
    assert rows == [(0, "MANDATE_DEVIATION_HIGH"), (1, "MANDATE_DEVIATION_HIGH")]


def test_the_raw_table_carries_no_decoded_column():
    con = _con()
    compact_events([_e("r", 0, 0, "vote_cast", {}, motif="101")], con)
    columns = {r[0] for r in con.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'citizen_events'"
    ).fetchall()}
    assert "motif_label" not in columns
    decoded_columns = {r[0] for r in con.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'citizen_events_decoded'"
    ).fetchall()}
    assert "motif_label" in decoded_columns


def test_decode_disabled_creates_no_codebook_table_and_no_decoded_view():
    con = _con()
    compact_events([_e("r", 0, 0, "vote_cast", {}, motif="101")], con, decode_codebook=False)
    table_names = {r[0] for r in con.execute("SELECT table_name FROM information_schema.tables").fetchall()}
    assert "codebook_motifs" not in table_names
    assert "citizen_events_decoded" not in table_names
    assert "citizen_events" in table_names
    names = {row[0] for row in con.execute("SELECT index_name FROM duckdb_indexes()").fetchall()}
    assert "idx_citizen_events_citizen_id" in names  # indexes still built


# ── headline, end-to-end ────────────────────────────────────────────────────

def test_compacting_a_full_menu_llm_run_answers_the_16_6_example_queries(tmp_path):
    # Reuses test_polity_run_simulation.py's own Lot 6/7 fixtures verbatim
    # (no new fixtures), same precedent as test_polity_indexer.py's own
    # headline test.
    from api.tests.test_polity_run_simulation import _config_with_full_menu_llm_enabled, _LaunchingFakeLlmClient

    config = _config_with_full_menu_llm_enabled(tmp_path)
    config = dataclasses.replace(config, mandate=dataclasses.replace(config.mandate, enabled=True))
    config = dataclasses.replace(config, run=dataclasses.replace(config.run, duration_years=8))
    # _config_with_output_dir (which this fixture chains through) sets
    # index_after_run=False for the run_simulation suite's wall-clock --
    # this test's whole point is compaction, so it turns it back on.
    config = dataclasses.replace(config, journal=dataclasses.replace(config.journal, index_after_run=True))

    journal_path = run_simulation(config, run_id="compaction-headline", llm_client=_LaunchingFakeLlmClient())
    db_path = journal_path.with_name("events.duckdb")
    assert db_path.is_file()  # run_simulation's own wiring already compacted it

    con = duckdb.connect(str(db_path))

    some_citizen_id = con.execute("SELECT citizen_id FROM citizen_events WHERE citizen_id IS NOT NULL LIMIT 1").fetchone()[0]
    biography = con.execute(
        "SELECT tick, event_type, motif_label, payload FROM citizen_events_decoded "
        "WHERE citizen_id = ? ORDER BY event_id", [some_citizen_id],
    ).fetchall()
    assert biography

    distribution = con.execute(
        "SELECT tick / 4 AS year, motif_label, count(*) FROM citizen_events_decoded "
        "WHERE event_type = 'vote_cast' AND (payload ->> '$.blank') = '1' "
        "GROUP BY 1, 2 ORDER BY 1, 2"
    ).fetchall()
    # A blank-vote motif always decodes -- every VoteMotif member is a
    # valid code, so no row here should ever carry a NULL label.
    assert all(row[1] is not None for row in distribution)

    motif_events = con.execute("SELECT count(*) FROM citizen_events WHERE motif IS NOT NULL").fetchone()[0]
    decoded = con.execute("SELECT count(*) FROM citizen_events_decoded WHERE motif IS NOT NULL AND motif_label IS NOT NULL").fetchone()[0]
    assert motif_events == decoded  # every motif this run actually produced decodes
