"""indexer.py — v4 Lot 8: the journal-replay module. Hand-built event lists,
no tmp_path, no Journal, no run -- the direct-call register this project's
hand-built-citizen tests have used since Lot 2. The one exception is the
headline end-to-end test, which runs a real (fake-client) simulation and
indexes its real journal.
"""
import dataclasses

import pytest

from api.domain.polity.config import load_config
from api.domain.polity.indexer import Term, index_events, index_run, read_journal, segment_terms
from api.domain.polity.run_polity_simulation import run_simulation


def _e(tick, event_type, payload, citizen_id=None, motif=None, codebook_version=""):
    return {
        "tick": tick, "event_type": event_type, "payload": payload,
        "citizen_id": citizen_id, "motif": motif, "codebook_version": codebook_version,
    }


def _ctx(mandate_dev=0.0):
    return {"self_gap": 0.0, "mandate_dev": mandate_dev, "neighbors_acting": None, "ticks_to_election": 4}


def _config(*, legitimacy_enabled=False, **metrics_overrides):
    config = load_config()
    config = dataclasses.replace(config, legitimacy=dataclasses.replace(config.legitimacy, enabled=legitimacy_enabled))
    if metrics_overrides:
        config = dataclasses.replace(config, metrics=dataclasses.replace(config.metrics, **metrics_overrides))
    return config


# ── segment_terms ──────────────────────────────────────────────────────────

def test_segment_terms_a_clean_term_runs_from_election_to_election():
    events = [
        _e(0, "elected", {"office": 1}, citizen_id=1),
        _e(16, "elected", {"office": 1}, citizen_id=2),
    ]
    terms = segment_terms(events, total_ticks=32)
    assert terms[0] == Term(holder_id=1, start_tick=0, end_tick=16, lame_duck=False, mandate_strength=None, ended_by="election")
    assert terms[1] == Term(holder_id=2, start_tick=16, end_tick=32, lame_duck=False, mandate_strength=None, ended_by="run_end")


def test_segment_terms_closed_by_recall_legitimacy_floor():
    events = [
        _e(0, "elected", {"office": 1}, citizen_id=1),
        _e(5, "recalled", {"office": 1, "legitimacy": 0.1, "recall_floor": 0.2, "trigger": "legitimacy_floor"}, citizen_id=1),
    ]
    terms = segment_terms(events, total_ticks=32)
    assert terms == (Term(holder_id=1, start_tick=0, end_tick=5, lame_duck=False, mandate_strength=None, ended_by="legitimacy_floor"),)


def test_segment_terms_closed_by_recall_confidence_vote():
    events = [
        _e(0, "elected", {"office": 1}, citizen_id=1),
        _e(5, "recalled", {"office": 1, "legitimacy": 0.3, "recall_floor": 0.2, "trigger": "confidence_vote"}, citizen_id=1),
    ]
    terms = segment_terms(events, total_ticks=32)
    assert terms[0].ended_by == "confidence_vote"
    assert terms[0].end_tick == 5


def test_segment_terms_a_term_still_open_at_run_end():
    events = [_e(0, "elected", {"office": 1}, citizen_id=1)]
    terms = segment_terms(events, total_ticks=16)
    assert terms == (Term(holder_id=1, start_tick=0, end_tick=16, lame_duck=False, mandate_strength=None, ended_by="run_end"),)


def test_segment_terms_a_vacancy_gap_produces_no_term():
    events = [
        _e(0, "election_no_winner", {"office": 1}, citizen_id=None),
        _e(16, "elected", {"office": 1}, citizen_id=1),
    ]
    terms = segment_terms(events, total_ticks=32)
    assert len(terms) == 1
    assert terms[0].holder_id == 1
    assert terms[0].start_tick == 16


def test_segment_terms_election_invalidated_closes_an_open_term_without_reopening():
    events = [
        _e(0, "elected", {"office": 1}, citizen_id=1),
        _e(16, "election_invalidated", {"office": 1, "blank_share": 0.6, "threshold": 0.5,
                                        "attempt": 1, "candidate_ids": [1, 2],
                                        "barred_candidate_ids": [1, 2], "next_attempt_tick": 17}),
        _e(17, "elected", {"office": 1}, citizen_id=3),
    ]
    terms = segment_terms(events, total_ticks=32)
    assert terms[0] == Term(holder_id=1, start_tick=0, end_tick=16, lame_duck=False, mandate_strength=None, ended_by="election")
    assert terms[1].holder_id == 3
    assert terms[1].start_tick == 17


def test_segment_terms_election_invalidated_with_no_open_term_is_a_no_op():
    events = [
        _e(0, "election_invalidated", {"office": 1, "blank_share": 0.6, "threshold": 0.5,
                                       "attempt": 1, "candidate_ids": [1, 2],
                                       "barred_candidate_ids": [1, 2], "next_attempt_tick": 1}),
        _e(1, "elected", {"office": 1}, citizen_id=3),
    ]
    terms = segment_terms(events, total_ticks=16)
    assert len(terms) == 1
    assert terms[0].holder_id == 3
    assert terms[0].start_tick == 1


def test_segment_terms_same_tick_election_recall_is_a_zero_length_term():
    events = [
        _e(0, "elected", {"office": 1}, citizen_id=1),
        _e(0, "recalled", {"office": 1, "legitimacy": 0.05, "recall_floor": 0.99, "trigger": "legitimacy_floor"}, citizen_id=1),
    ]
    terms = segment_terms(events, total_ticks=32)
    assert terms == (Term(holder_id=1, start_tick=0, end_tick=0, lame_duck=False, mandate_strength=None, ended_by="legitimacy_floor"),)


def test_segment_terms_carries_lame_duck_from_mandate_pledge_declared():
    events = [
        _e(0, "elected", {"office": 1}, citizen_id=1),
        _e(0, "mandate_pledge_declared", {"office": 1, "pledged_platform": [0.5], "mandates_served": 2, "lame_duck": True}, citizen_id=1),
    ]
    terms = segment_terms(events, total_ticks=16)
    assert terms[0].lame_duck is True


def test_segment_terms_carries_mandate_strength_from_legitimacy_updated():
    events = [
        _e(0, "elected", {"office": 1}, citizen_id=1),
        _e(0, "legitimacy_updated", {"office": 1, "legitimacy": 0.5, "mandate_strength": 0.51, "ecart": 0.0}, citizen_id=1),
    ]
    terms = segment_terms(events, total_ticks=16)
    assert terms[0].mandate_strength == 0.51


# ── mean_legitimacy / recalls (implied by legitimacy.enabled) ────────────

def test_mean_legitimacy_skips_vacant_ticks_entirely():
    events = [
        _e(0, "elected", {"office": 1}, citizen_id=1),
        _e(0, "legitimacy_updated", {"office": 1, "legitimacy": 0.5, "mandate_strength": 0.5, "ecart": 0.0}, citizen_id=1),
        _e(2, "legitimacy_updated", {"office": 1, "legitimacy": 0.6, "mandate_strength": 0.5, "ecart": -0.1}, citizen_id=1),
    ]
    config = _config(legitimacy_enabled=True)
    metrics = index_events(events, config)
    series = dict(metrics.mean_legitimacy)
    assert series == {0: 0.5, 2: 0.6}
    assert 1 not in series  # tick 1: no legitimacy_updated -- absent, never a 0.0


def test_legitimacy_disabled_means_no_legitimacy_rows():
    events = [_e(0, "elected", {"office": 1}, citizen_id=1)]
    config = _config(legitimacy_enabled=False)
    metrics = index_events(events, config)
    assert metrics.mean_legitimacy is None
    assert metrics.recalls_by_trigger is None
    assert metrics.recalls_per_term is None


def test_recalls_by_trigger_and_per_term():
    events = [
        _e(0, "elected", {"office": 1}, citizen_id=1),
        _e(5, "recalled", {"office": 1, "legitimacy": 0.1, "recall_floor": 0.2, "trigger": "legitimacy_floor"}, citizen_id=1),
        _e(5, "elected", {"office": 1}, citizen_id=2),
        _e(10, "recalled", {"office": 1, "legitimacy": 0.3, "recall_floor": 0.2, "trigger": "confidence_vote"}, citizen_id=2),
    ]
    config = _config(legitimacy_enabled=True)
    metrics = index_events(events, config)
    assert metrics.recalls_by_trigger == {"legitimacy_floor": 1, "confidence_vote": 1}
    assert metrics.recalls_per_term == pytest.approx(1.0)  # 2 recalls / 2 terms


# ── inaction_rate ──────────────────────────────────────────────────────────

def test_inaction_rate_over_a_hand_built_tick():
    events = [
        _e(5, "pressure_action", {"target": 1, "act": 0}, citizen_id=10),
        _e(5, "pressure_action", {"target": 1, "act": 0}, citizen_id=11),
        _e(5, "pressure_action", {"target": 1, "act": 3}, citizen_id=12),
        _e(5, "pressure_action", {"target": 1, "act": 4}, citizen_id=13),
        _e(5, "pressure_action", {"target": 1, "act": 1}, citizen_id=14),
    ]
    config = _config(inaction_rate=True)
    metrics = index_events(events, config)
    assert dict(metrics.inaction_rate) == {5: pytest.approx(0.4)}


# ── pressure_lever_mix / petition_downgrades ─────────────────────────────

def test_pressure_lever_mix_has_all_five_keys_including_unused_acts():
    events = [
        _e(0, "pressure_action", {"target": 1, "act": 0}, citizen_id=1),
        _e(0, "pressure_action", {"target": 1, "act": 4}, citizen_id=2),
    ]
    config = _config(pressure_lever_mix=True)
    metrics = index_events(events, config)
    assert metrics.pressure_lever_mix == {0: 0.5, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.5}
    assert metrics.pressure_lever_counts == {0: 1, 1: 0, 2: 0, 3: 0, 4: 1}


def test_petition_downgrades_counts_a_launch_decided_act_applied_as_a_signature():
    events = [
        _e(0, "pressure_action", {"target": 1, "act": 2, "ctx": {}}, citizen_id=2, motif="301"),
        _e(0, "petition_launched", {"target": 1, "signatures": 1, "signed_ratio": 0.01, "expires_at_tick": 4}, citizen_id=2),
        _e(0, "pressure_action", {"target": 1, "act": 2, "ctx": {}}, citizen_id=3, motif="301"),
        _e(0, "petition_signed", {"target": 1, "signatures": 2, "signed_ratio": 0.02}, citizen_id=3),
    ]
    config = _config(pressure_lever_mix=True)
    metrics = index_events(events, config)
    assert metrics.petition_downgrades == 1  # citizen 3's decided LAUNCH applied as a SIGN


def test_petition_downgrades_does_not_count_a_launch_that_actually_launched():
    events = [
        _e(0, "pressure_action", {"target": 1, "act": 2, "ctx": {}}, citizen_id=2, motif="301"),
        _e(0, "petition_launched", {"target": 1, "signatures": 1, "signed_ratio": 0.01, "expires_at_tick": 4}, citizen_id=2),
    ]
    config = _config(pressure_lever_mix=True)
    metrics = index_events(events, config)
    assert metrics.petition_downgrades == 0


# ── stance_distribution ───────────────────────────────────────────────────

def test_stance_distribution_has_all_four_keys():
    events = [_e(0, "representative_response", {"office": 1, "stance": 1, "shifts": [], "ctx": _ctx()}, citizen_id=1, motif="301")]
    config = _config(stance_distribution=True)
    metrics = index_events(events, config)
    assert metrics.stance_distribution == {1: 1.0, 2: 0.0, 3: 0.0, 4: 0.0}


# ── petition_success_rate / petition_removal_rate ────────────────────────

def test_petition_success_rate_and_removal_rate_are_distinguished():
    events = [
        _e(0, "petition_launched", {"target": 1, "signatures": 1, "signed_ratio": 0.01, "expires_at_tick": 4}, citizen_id=2),
        _e(1, "confidence_vote_triggered", {"office": 1, "opened_at_tick": 0, "signatures": 25, "signed_ratio": 0.25}, citizen_id=1),
        _e(1, "confidence_vote_result", {"office": 1, "bf": 4, "ballots": 100, "keep": 40, "keep_ratio": 0.4, "retained": False}, citizen_id=1),
        _e(1, "recalled", {"office": 1, "legitimacy": 0.2, "recall_floor": 0.2, "trigger": "confidence_vote"}, citizen_id=1),
    ]
    config = _config(petition_success_rate=True)
    metrics = index_events(events, config)
    assert metrics.petition_success_rate == pytest.approx(1.0)  # 1 triggered / 1 launched
    assert metrics.petition_removal_rate == pytest.approx(1.0)  # 1 confidence-vote recall / 1 triggered


def test_petition_success_rate_without_a_removal_is_zero_removal_rate():
    events = [
        _e(0, "petition_launched", {"target": 1, "signatures": 1, "signed_ratio": 0.01, "expires_at_tick": 4}, citizen_id=2),
        _e(1, "confidence_vote_triggered", {"office": 1, "opened_at_tick": 0, "signatures": 25, "signed_ratio": 0.25}, citizen_id=1),
        _e(1, "confidence_vote_result", {"office": 1, "bf": 4, "ballots": 100, "keep": 60, "keep_ratio": 0.6, "retained": True}, citizen_id=1),
    ]
    config = _config(petition_success_rate=True)
    metrics = index_events(events, config)
    assert metrics.petition_success_rate == pytest.approx(1.0)
    assert metrics.petition_removal_rate == pytest.approx(0.0)


def test_petition_success_rate_is_none_with_no_petitions_launched():
    config = _config(petition_success_rate=True)
    metrics = index_events([], config)
    assert metrics.petition_success_rate is None
    assert metrics.petition_removal_rate is None


# ── mandate_deviation: ctx preferred over the censored recorded series ───

def test_mandate_deviation_prefers_the_ctx_series_when_present():
    events = [
        _e(0, "elected", {"office": 1}, citizen_id=1),
        _e(0, "representative_response", {"office": 1, "stance": 3, "shifts": [], "ctx": _ctx(0.05)}, citizen_id=1, motif="308"),
        _e(1, "representative_response", {"office": 1, "stance": 3, "shifts": [], "ctx": _ctx(0.2)}, citizen_id=1, motif="308"),
        _e(1, "mandate_deviation_recorded", {"office": 1, "deviation": 0.2}, citizen_id=1),
    ]
    config = _config(mandate_deviation=True)
    metrics = index_events(events, config)
    assert metrics.mandate_deviation_source == "ctx"
    assert dict(metrics.mandate_deviation) == {0: 0.05, 1: 0.2}
    assert metrics.mandate_deviation_coverage == pytest.approx(0.5)  # 1 recorded / 2 ctx ticks


def test_mandate_deviation_falls_back_to_the_recorded_series_without_dt6():
    events = [
        _e(0, "elected", {"office": 1}, citizen_id=1),
        _e(1, "mandate_deviation_recorded", {"office": 1, "deviation": 0.2}, citizen_id=1),
    ]
    config = _config(mandate_deviation=True)
    metrics = index_events(events, config)
    assert metrics.mandate_deviation_source == "recorded"
    assert dict(metrics.mandate_deviation) == {1: 0.2}


def test_mandate_deviation_is_none_when_its_flag_is_off():
    events = [_e(1, "mandate_deviation_recorded", {"office": 1, "deviation": 0.2}, citizen_id=1)]
    config = _config(mandate_deviation=False)
    metrics = index_events(events, config)
    assert metrics.mandate_deviation is None
    assert metrics.mandate_deviation_source is None
    assert metrics.mandate_deviation_coverage is None


# ── lame_duck_deviation_delta ──────────────────────────────────────────────

def test_lame_duck_deviation_delta_is_none_with_no_lame_duck_term():
    events = [
        _e(0, "elected", {"office": 1}, citizen_id=1),
        _e(0, "representative_response", {"office": 1, "stance": 3, "shifts": [], "ctx": _ctx(0.1)}, citizen_id=1, motif="308"),
    ]
    config = _config(mandate_deviation=True, lame_duck_deviation_delta=True)
    metrics = index_events(events, config)
    assert metrics.lame_duck_deviation_delta is None


def test_lame_duck_deviation_delta_hand_computed_with_both_kinds_of_term():
    events = [
        _e(0, "elected", {"office": 1}, citizen_id=1),
        _e(0, "mandate_pledge_declared", {"office": 1, "pledged_platform": [0.5], "mandates_served": 2, "lame_duck": True}, citizen_id=1),
        _e(0, "representative_response", {"office": 1, "stance": 3, "shifts": [], "ctx": _ctx(0.6)}, citizen_id=1, motif="308"),
        _e(4, "elected", {"office": 1}, citizen_id=2),
        _e(4, "representative_response", {"office": 1, "stance": 3, "shifts": [], "ctx": _ctx(0.2)}, citizen_id=2, motif="308"),
    ]
    config = _config(mandate_deviation=True, lame_duck_deviation_delta=True)
    metrics = index_events(events, config)
    assert metrics.lame_duck_deviation_delta == pytest.approx(0.4)  # 0.6 - 0.2


# ── cohabitation ───────────────────────────────────────────────────────────

def test_cohabitation_resolves_the_presidents_party_through_candidacy_declared():
    events = [
        _e(0, "candidacy_declared", {"party_id": 0, "path": "dominant"}, citizen_id=1),
        _e(0, "elected", {"office": 1}, citizen_id=1),
        _e(0, "coalition_formed", {"coalition": [1, 2], "seats": {"0": 10, "1": 40, "2": 50}}),
    ]
    config = _config(cohabitation_rate=True)
    metrics = index_events(events, config)
    assert metrics.cohabitation_rate == pytest.approx(1.0)  # party 0 not in [1, 2]


def test_cohabitation_is_false_for_a_rupture_president_with_no_party():
    events = [
        _e(0, "candidacy_declared", {"path": "rupture"}, citizen_id=1),
        _e(0, "elected", {"office": 1}, citizen_id=1),
        _e(0, "coalition_formed", {"coalition": [2], "seats": {"2": 100}}),
    ]
    config = _config(cohabitation_rate=True)
    metrics = index_events(events, config)
    assert metrics.cohabitation_rate == pytest.approx(0.0)


# ── gating: every v4 metric is None when its own flag is off ─────────────

def test_every_v4_metric_is_none_when_its_flag_is_off():
    events = [
        _e(0, "elected", {"office": 1}, citizen_id=1),
        _e(0, "representative_response", {"office": 1, "stance": 1, "shifts": [], "ctx": _ctx(0.1)}, citizen_id=1, motif="301"),
        _e(0, "pressure_action", {"target": 1, "act": 0, "ctx": {}}, citizen_id=2, motif="304"),
        _e(0, "petition_launched", {"target": 1, "signatures": 1, "signed_ratio": 0.01, "expires_at_tick": 4}, citizen_id=2),
    ]
    config = _config(
        mandate_deviation=False, lame_duck_deviation_delta=False, inaction_rate=False,
        pressure_lever_mix=False, petition_success_rate=False, stance_distribution=False,
    )
    metrics = index_events(events, config)
    assert metrics.mandate_deviation is None
    assert metrics.mandate_deviation_source is None
    assert metrics.mandate_deviation_coverage is None
    assert metrics.lame_duck_deviation_delta is None
    assert metrics.inaction_rate is None
    assert metrics.pressure_lever_mix is None
    assert metrics.pressure_lever_counts is None
    assert metrics.petition_downgrades is None
    assert metrics.petition_success_rate is None
    assert metrics.petition_removal_rate is None
    assert metrics.stance_distribution is None


# ── robustness ─────────────────────────────────────────────────────────────

def test_unknown_event_type_is_ignored():
    events = [
        _e(0, "elected", {"office": 1}, citizen_id=1),
        _e(0, "some_future_event_type", {"whatever": True}, citizen_id=1),
    ]
    metrics = index_events(events, _config())  # must not raise
    assert metrics.terms[0].holder_id == 1


def test_read_journal_raises_on_a_malformed_line(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"tick": 0, "event_type": "elected", "payload": {}, "citizen_id": 1}\nnot json at all\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"bad\.jsonl:2"):
        list(read_journal(path))


def test_index_run_streams_a_real_journal_file(tmp_path):
    path = tmp_path / "run.jsonl"
    path.write_text(
        '{"run_id": "r", "event_id": 0, "tick": 0, "event_type": "elected", "payload": {"office": 1}, '
        '"citizen_id": 1, "motif": null, "rationale": null, "codebook_version": ""}\n',
        encoding="utf-8",
    )
    metrics = index_run(path, _config())
    assert metrics.run_id == "r"
    assert metrics.terms[0].holder_id == 1


# ── headline, end-to-end ──────────────────────────────────────────────────

def test_indexing_a_full_menu_llm_run_populates_every_v4_metric(tmp_path):
    # Reuses test_polity_run_simulation.py's own Lot 6/7 fixtures verbatim
    # (no new fixtures) -- the exact "full menu + mandate + llm" combination
    # every v4 metric needs at least one real event to compute against.
    from api.tests.test_polity_run_simulation import _config_with_full_menu_llm_enabled, _LaunchingFakeLlmClient

    config = _config_with_full_menu_llm_enabled(tmp_path)
    config = dataclasses.replace(config, mandate=dataclasses.replace(config.mandate, enabled=True))
    config = dataclasses.replace(config, run=dataclasses.replace(config.run, duration_years=8))

    journal_path = run_simulation(config, run_id="indexer-headline", llm_client=_LaunchingFakeLlmClient())
    metrics = index_run(journal_path, config)

    assert metrics.terms
    assert metrics.effective_parties is not None
    assert metrics.cohabitation_rate is not None
    assert metrics.coalition_lifespans is not None
    assert metrics.blank_vote_rate is not None
    assert metrics.mean_legitimacy is not None
    assert metrics.recalls_by_trigger is not None

    assert metrics.mandate_deviation is not None
    assert metrics.mandate_deviation_source == "ctx"
    assert metrics.lame_duck_deviation_delta is None  # president_term_limit: null, shipped

    assert metrics.inaction_rate is not None
    for _tick, rate in metrics.inaction_rate:
        assert 0.0 <= rate <= 1.0

    assert metrics.pressure_lever_mix is not None
    assert set(metrics.pressure_lever_mix) == {0, 1, 2, 3, 4}
    assert sum(metrics.pressure_lever_mix.values()) == pytest.approx(1.0)
    assert metrics.pressure_lever_counts is not None

    assert metrics.stance_distribution is not None
    assert set(metrics.stance_distribution) == {1, 2, 3, 4}
    assert sum(metrics.stance_distribution.values()) == pytest.approx(1.0)

    assert metrics.petition_success_rate is not None  # _LaunchingFakeLlmClient always tries to launch
