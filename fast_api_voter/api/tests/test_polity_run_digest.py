"""run_digest.py — the account written on EVERY run ending, not just clean
ones. Hand-built event lists for the pure-shaping functions, the same
direct-call register test_polity_viz_export.py uses; the end-to-end tests run
a real deterministic simulation and digest its real journal.

The failure-path behaviour is the whole reason this module exists, so it is
tested first-class here: a truncated tail must be counted rather than raised,
and a resumed attempt must not erase the record of the attempt that died.
"""
import dataclasses
import json

import pytest

from api.domain.polity.config import load_config
from api.domain.polity.run_digest import (
    ALL_EVENT_TYPES,
    build_digest,
    event_counts_by_year,
    institutional_timeline,
    legitimacy_trajectory,
    llm_fallback_alerts,
    llm_fallback_rates,
    population_impact_by_year,
    read_journal_tolerant,
    write_digest,
)
from api.domain.polity.run_polity_simulation import run_simulation


def _e(tick, event_type, payload, citizen_id=None, motif=None, codebook_version=""):
    return {
        "tick": tick, "event_type": event_type, "payload": payload,
        "citizen_id": citizen_id, "motif": motif, "codebook_version": codebook_version,
    }


def _write_journal(path, events):
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    return path


# ── read_journal_tolerant ────────────────────────────────────────────────

def test_read_journal_tolerant_parses_a_clean_journal(tmp_path):
    path = _write_journal(tmp_path / "events.jsonl", [_e(0, "elected", {"office": "president"})])

    events, skipped = read_journal_tolerant(path)

    assert len(events) == 1
    assert skipped == 0


def test_read_journal_tolerant_counts_a_truncated_tail_instead_of_raising(tmp_path):
    # The exact state a hard kill leaves: the final line cut mid-write.
    # indexer.read_journal raises here by design; this one must not, or a
    # crashed run could never be described -- see run_digest's own docstring.
    path = tmp_path / "events.jsonl"
    path.write_text(
        json.dumps(_e(0, "elected", {"office": "president"})) + "\n" + '{"tick": 1, "event_ty',
        encoding="utf-8",
    )

    events, skipped = read_journal_tolerant(path)

    assert len(events) == 1
    assert skipped == 1  # reported, not silently dropped


def test_read_journal_tolerant_on_a_missing_file_is_empty_not_an_error(tmp_path):
    # A run killed before its first journal write leaves no file at all.
    events, skipped = read_journal_tolerant(tmp_path / "nope.jsonl")

    assert events == []
    assert skipped == 0


# ── event_counts_by_year ─────────────────────────────────────────────────

def test_event_counts_by_year_reports_every_event_type_including_zeros():
    counts = event_counts_by_year([_e(0, "elected", {})], ticks_per_year=4)

    assert set(ALL_EVENT_TYPES) <= set(counts["0"])
    assert counts["0"]["elected"] == 1
    # "did not happen" must be distinguishable from "nobody looked".
    assert counts["0"]["recalled"] == 0


def test_event_counts_by_year_buckets_by_ticks_per_year():
    events = [_e(0, "elected", {}), _e(4, "recalled", {}), _e(7, "recalled", {})]

    counts = event_counts_by_year(events, ticks_per_year=4)

    assert counts["0"]["elected"] == 1
    assert counts["1"]["recalled"] == 2


def test_event_counts_by_year_emits_a_row_for_a_completely_silent_year():
    # Found by the end-to-end test: a 2-year deterministic run had no events at
    # all in year 1, and that year simply vanished from the map -- exactly the
    # "nothing happened" vs "nobody looked" ambiguity this digest exists to
    # remove. A silent year is a row of zeros, not an absent key.
    events = [_e(0, "elected", {}), _e(8, "recalled", {})]

    counts = event_counts_by_year(events, ticks_per_year=4)

    assert list(counts) == ["0", "1", "2"]
    assert set(counts["1"].values()) == {0}


def test_population_impact_emits_a_row_for_a_silent_year():
    config = load_config()

    series = population_impact_by_year([_e(0, "elected", {}), _e(8, "recalled", {})], config)

    assert [row["year"] for row in series] == [0, 1, 2]
    assert series[1]["pressure"]["consulted"] == 0


def test_year_rows_stop_at_the_last_tick_reached_not_the_planned_total():
    # An interrupted run must not sprout empty years it never lived through.
    counts = event_counts_by_year([_e(0, "elected", {})], ticks_per_year=4)

    assert list(counts) == ["0"]


def test_event_counts_by_year_keeps_an_unknown_event_type():
    # If the simulation gains a 31st event type and ALL_EVENT_TYPES is not
    # updated, the digest must still show it rather than silently lose it.
    counts = event_counts_by_year([_e(0, "brand_new_thing", {})], ticks_per_year=4)

    assert counts["0"]["brand_new_thing"] == 1


def test_all_event_types_matches_what_the_simulation_can_journal():
    # Pins the constant against the real writer. 29 event_type= literals plus
    # election_no_winner, which is the false branch of a ternary and therefore
    # invisible to a naive literal grep.
    import re
    from pathlib import Path

    source = Path(__file__).resolve().parents[1] / "domain" / "polity" / "run_polity_simulation.py"
    written = set(re.findall(r'event_type="([a-z_]+)"', source.read_text(encoding="utf-8")))
    written.add("election_no_winner")

    assert written == set(ALL_EVENT_TYPES)


# ── population_impact_by_year ────────────────────────────────────────────

def test_population_impact_reports_candidacy_rates():
    config = load_config()
    config = dataclasses.replace(config, run=dataclasses.replace(config.run, population_size=10))
    events = [_e(0, "candidacy_considered", {"outcome": 1}) for _ in range(4)]
    events += [_e(0, "candidacy_considered", {"outcome": 0}) for _ in range(6)]

    [year0] = population_impact_by_year(events, config)

    assert year0["candidacy"] == {
        "considered": 10, "declared": 4, "declined": 6,
        "declared_rate_of_considered": 0.4, "declared_rate_of_population": 0.4,
        "declared_events": 0,
    }


def test_population_impact_decodes_pressure_acts_by_name():
    config = load_config()
    events = [_e(0, "pressure_action", {"act": 0}), _e(0, "pressure_action", {"act": 4})]

    [year0] = population_impact_by_year(events, config)

    assert year0["pressure"]["acts_decided"] == {"NOTHING": 1, "WAIT_FOR_ELECTION": 1}
    assert year0["pressure"]["inaction_rate"] == 0.5


def test_population_impact_rate_is_none_not_zero_when_nothing_was_tracked():
    # indexer.py's own rule: 0.0 is a claim, None says this run does not track
    # that. A deterministic run journals no candidacy_considered at all.
    config = load_config()
    [year0] = population_impact_by_year([_e(0, "elected", {})], config)

    assert year0["candidacy"]["declared_rate_of_considered"] is None
    assert year0["votes"]["blank_rate"] is None
    assert year0["reactions"]["mean_salience_delta"] is None


def test_population_impact_counts_blank_ballots():
    config = load_config()
    events = [_e(0, "vote_cast", {"blank": 1}), _e(0, "vote_cast", {"blank": 0}),
              _e(0, "vote_cast", {"blank": 0}), _e(0, "vote_cast", {"blank": 0})]

    [year0] = population_impact_by_year(events, config)

    assert year0["votes"] == {"ballots": 4, "blank": 1, "blank_rate": 0.25}


# ── institutional_timeline / legitimacy_trajectory ───────────────────────

def test_institutional_timeline_filters_to_institutional_events():
    events = [_e(0, "elected", {"office": "president"}), _e(0, "pressure_action", {"act": 0})]

    timeline = institutional_timeline(events)

    assert [e["event_type"] for e in timeline] == ["elected"]


def test_institutional_timeline_passes_payloads_through_whole():
    # coalition_failed has three different payload shapes; reshaping to a
    # fixed schema here would drop keys from two of them.
    events = [_e(8, "coalition_failed", {"coalition": None, "seats": {"0": 20}, "aborted_at_round": 2})]

    [entry] = institutional_timeline(events)

    assert entry["payload"]["aborted_at_round"] == 2


def test_legitimacy_trajectory_is_ordered_and_typed():
    events = [
        _e(0, "legitimacy_updated", {"legitimacy": 0.7, "mandate_strength": 0.8, "ecart": 0.01}, citizen_id=5),
        _e(1, "legitimacy_updated", {"legitimacy": 0.6, "mandate_strength": 0.8, "ecart": 0.02}, citizen_id=5),
    ]

    trajectory = legitimacy_trajectory(events)

    assert [row["tick"] for row in trajectory] == [0, 1]
    assert trajectory[0]["legitimacy"] == 0.7
    assert trajectory[1]["citizen_id"] == 5


# ── build_digest / write_digest ──────────────────────────────────────────

def _digest_for(tmp_path, outcome, **kwargs):
    config = load_config()
    journal = _write_journal(tmp_path / "events.jsonl", [
        _e(0, "elected", {"office": "president"}, citizen_id=5),
        _e(1, "legitimacy_updated", {"legitimacy": 0.7, "mandate_strength": 0.8, "ecart": 0.0}, citizen_id=5),
    ])
    return build_digest(journal, config, run_id="r", outcome=outcome, **kwargs)


@pytest.mark.parametrize("outcome", ["completed", "crashed", "interrupted"])
def test_build_digest_records_each_outcome(tmp_path, outcome):
    digest = _digest_for(tmp_path, outcome, resume=False)

    assert digest["outcome"] == outcome
    assert digest["run_id"] == "r"


def test_build_digest_records_the_error_for_a_crash(tmp_path):
    digest = _digest_for(tmp_path, "crashed", resume=False, error=ValueError("boom"))

    assert digest["error"] == {"type": "ValueError", "message": "boom"}


def test_build_digest_reports_planned_versus_reached_ticks(tmp_path):
    # The single most important fact about an interrupted run.
    digest = _digest_for(tmp_path, "interrupted", resume=False)

    assert digest["ticks"]["last_tick_journaled"] == 1
    assert digest["ticks"]["planned_total"] > 1


def test_build_digest_closes_an_open_term_at_the_last_reached_tick(tmp_path):
    # Not at the planned total: for an interrupted run the real end is where
    # it stopped, and segment_terms would otherwise extend a term the run
    # never lived through.
    digest = _digest_for(tmp_path, "interrupted", resume=False)

    [term] = digest["terms"]
    assert term["holder_id"] == 5
    assert term["end_tick"] == 1
    assert term["ended_by"] == "run_end"


def test_build_digest_on_a_deterministic_run_reports_no_llm_decisions(tmp_path):
    # decisions_by_type == {} is correct on a deterministic run, not a signal
    # that nothing happened -- the events are all still there.
    digest = _digest_for(tmp_path, "completed", resume=False)

    assert digest["llm_decisions"] == {}
    assert digest["journal"]["total_events"] == 2
    assert digest["metadata"]["unverified_decision_types"] == []
    assert digest["llm_fallback_rates"] == {}
    assert digest["llm_fallback_alerts"] == {}


# ── llm_fallback_rates / llm_fallback_alerts (Track C2, 2026-09-11) ─────────

def test_llm_fallback_rates_computes_per_type_ratio():
    rates = llm_fallback_rates(
        decisions_by_type={"vote_cast": 100, "party_nomination_choice": 15},
        fallback_by_type={"vote_cast": 1, "party_nomination_choice": 10},
    )
    assert rates == {"vote_cast": 0.01, "party_nomination_choice": 0.6667}


def test_llm_fallback_rates_omits_types_never_decided_this_run():
    # A type absent from decisions_by_type never appeared this run at all --
    # a rate over zero decisions would not measure anything real.
    rates = llm_fallback_rates(decisions_by_type={"vote_cast": 100}, fallback_by_type={})
    assert rates == {"vote_cast": 0.0}
    assert "party_nomination_choice" not in rates


def test_llm_fallback_rates_treats_a_type_with_no_fallback_key_as_zero():
    rates = llm_fallback_rates(decisions_by_type={"vote_cast": 100}, fallback_by_type={"other_type": 5})
    assert rates == {"vote_cast": 0.0}


def test_llm_fallback_alerts_flags_only_types_above_the_threshold():
    # Stage 3's own real numbers: 0.26% overall hid party_nomination_choice's
    # 67% -- an aggregate check would have missed exactly this.
    rates = {"vote_cast": 0.0026, "party_nomination_choice": 0.6667}
    alerts = llm_fallback_alerts(rates, threshold=0.10)
    assert alerts == {"party_nomination_choice": 0.6667}


def test_llm_fallback_alerts_is_empty_when_everything_is_under_the_threshold():
    rates = {"vote_cast": 0.01, "party_nomination_choice": 0.05}
    assert llm_fallback_alerts(rates, threshold=0.10) == {}


def test_build_digest_surfaces_a_fallback_alert_from_a_real_progress_json(tmp_path):
    config = load_config()
    journal = _write_journal(tmp_path / "events.jsonl", [_e(0, "elected", {"office": "president"}, citizen_id=5)])
    (tmp_path / "progress.json").write_text(
        json.dumps({
            "decisions_by_type": {"vote_cast": 100, "party_nomination_choice": 15},
            "fallback_by_type": {"vote_cast": 1, "party_nomination_choice": 10},
        }),
        encoding="utf-8",
    )

    digest = build_digest(journal, config, run_id="r", outcome="completed", resume=False)

    assert digest["llm_fallback_rates"] == {"vote_cast": 0.01, "party_nomination_choice": 0.6667}
    assert digest["llm_fallback_alerts"] == {"party_nomination_choice": 0.6667}


def test_write_digest_appends_one_line_per_attempt_and_overwrites_the_latest(tmp_path):
    # A completed retry must not erase the record that an earlier attempt died.
    config = load_config()
    journal = _write_journal(tmp_path / "events.jsonl", [_e(0, "elected", {"office": "president"}, citizen_id=5)])

    write_digest(journal, config, run_id="r", outcome="interrupted", resume=False)
    write_digest(journal, config, run_id="r", outcome="completed", resume=True)

    attempts = [json.loads(line) for line in (tmp_path / "digest.jsonl").read_text(encoding="utf-8").splitlines()]
    latest = json.loads((tmp_path / "digest.json").read_text(encoding="utf-8"))

    assert [a["outcome"] for a in attempts] == ["interrupted", "completed"]
    assert [a["resumed_attempt"] for a in attempts] == [False, True]
    assert latest["outcome"] == "completed"


def test_write_digest_lands_beside_the_journal(tmp_path):
    # Not in the runner's outer bookkeeping directory -- the mix-up already
    # documented at run_polity_flagship.py:407-411.
    config = load_config()
    journal = _write_journal(tmp_path / "events.jsonl", [_e(0, "elected", {}, citizen_id=5)])

    path = write_digest(journal, config, run_id="r", outcome="completed", resume=False)

    assert path == tmp_path / "digest.json"


def test_digest_is_json_serializable(tmp_path):
    config = load_config()
    journal = _write_journal(tmp_path / "events.jsonl", [_e(0, "elected", {}, citizen_id=5)])

    json.dumps(build_digest(journal, config, run_id="r", outcome="completed", resume=False))  # must not raise


def test_build_digest_end_to_end_on_a_real_journal(tmp_path):
    config = load_config()
    config = dataclasses.replace(config, journal=dataclasses.replace(config.journal, output_dir=str(tmp_path)))
    config = dataclasses.replace(config, run=dataclasses.replace(config.run, population_size=40, duration_years=2))
    journal_path = run_simulation(config, run_id="real")

    digest = build_digest(journal_path, config, run_id="real", outcome="completed", resume=False, elapsed_seconds=1.0)

    assert digest["journal"]["malformed_lines_skipped"] == 0
    assert digest["ticks"]["last_tick_journaled"] == config.run.ticks_per_year * config.run.duration_years
    assert digest["shape"]["population_size"] == 40
    assert len(digest["event_counts_by_year"]) == config.run.duration_years + 1  # tick 0 opens year 0
    assert digest["population_impact_by_year"][0]["year"] == 0
