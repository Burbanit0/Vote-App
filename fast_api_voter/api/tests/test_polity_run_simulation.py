"""Lot 8 — run_polity_simulation.py: orchestration + the reproducibility test.

Contracts (dev-plan-v0-worktree.md §3-4, Lot 8):
- Integration: a full 30-year run completes without error and produces a
  non-empty journal.
- Transversal, "the test that matters more than the others": two full runs
  with the same seed produce byte-identical journals.
"""
import dataclasses
import json

import pytest

from api.domain.polity.accountability import update_street_pressure
from api.domain.polity.citizen import Citizen, Office, Role, generate_population
from api.domain.polity.config import PolityConfig, load_config
from api.domain.polity.journal import Journal
from api.domain.polity.llm_client import LlmResponseError
from api.domain.polity.metrics import mobilization_rate
from api.domain.polity.parties import Party, initialize_parties
from api.domain.polity.run_polity_simulation import (
    _hold_presidential_election,
    _run_accountability_phase,
    run_simulation,
)
from api.domain.polity.simple_rules import assign_party_affiliation, declare_candidacy

_PETITION_LIFECYCLE_EVENT_TYPES = {
    "petition_launched", "petition_signed", "petition_expired",
    "confidence_vote_triggered", "confidence_vote_result",
}


def _config_with_output_dir(output_dir) -> PolityConfig:
    config = load_config()
    return dataclasses.replace(config, journal=dataclasses.replace(config.journal, output_dir=str(output_dir)))


def _events(journal_path):
    return [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]


def test_full_run_completes_and_produces_a_non_empty_journal(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    assert journal_path.is_file()
    lines = journal_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) > 0
    for line in lines:
        json.loads(line)  # every line is valid, complete JSON


def test_election_counts_match_the_calendar(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    events = _events(journal_path)
    presidential_outcomes = [e for e in events if e["event_type"] in ("elected", "election_no_winner")]
    legislative_results = [e for e in events if e["event_type"] == "legislative_result"]
    assert len(presidential_outcomes) == 8
    assert len(legislative_results) == 8


def test_every_legislative_result_allocates_all_seats(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    config = load_config()
    for event in _events(journal_path):
        if event["event_type"] == "legislative_result":
            assert sum(event["payload"]["seats"].values()) == config.institutions.assembly_seats


def test_two_runs_with_the_same_seed_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(_config_with_output_dir(tmp_path / "a"), run_id="same-run-id")
    path_b = run_simulation(_config_with_output_dir(tmp_path / "b"), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


def test_different_seed_produces_a_different_journal(tmp_path):
    config_a = _config_with_output_dir(tmp_path / "a")
    config_b = _config_with_output_dir(tmp_path / "b")
    config_b = dataclasses.replace(config_b, run=dataclasses.replace(config_b.run, seed=999))
    path_a = run_simulation(config_a, run_id="r")
    path_b = run_simulation(config_b, run_id="r")
    assert path_a.read_bytes() != path_b.read_bytes()


# ── outgoing president's stale office/role reset ─────────────────────────

def _office_test_citizen(cid, position):
    return Citizen(
        citizen_id=cid,
        issue_positions=(position,),
        issue_priorities=(1.0,),
        blank_threshold=1.0,
        ambition_score=0.5,
    )


def test_outgoing_president_is_reset_when_the_next_presidential_election_runs(tmp_path):
    # Regression test: without the fix, a president who isn't immediately
    # re-nominated keeps role=ELECTED/office=PRESIDENT forever, so a second
    # election leaves two citizens simultaneously holding Office.PRESIDENT.
    config = load_config()
    term_ticks = config.institutions.president_term_years * config.run.ticks_per_year

    citizen_a = _office_test_citizen(0, 0.1)
    citizen_b = _office_test_citizen(1, 0.9)
    electors = [_office_test_citizen(i, 0.5) for i in range(2, 7)]
    declare_candidacy(citizen_a)

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        # Tick 0: A stands uncontested and wins.
        _hold_presidential_election([citizen_a] + electors, [], config, journal, tick=0, llm_client=None)
        assert citizen_a.role == Role.ELECTED
        assert citizen_a.office == Office.PRESIDENT
        assert citizen_a.term_end_tick == term_ticks

        # Tick term_ticks: A's term has ended. A is not re-nominated -- only
        # B declares -- so B stands uncontested and wins.
        declare_candidacy(citizen_b)
        _hold_presidential_election(
            [citizen_a, citizen_b] + electors, [], config, journal, tick=term_ticks, llm_client=None
        )

    assert citizen_b.role == Role.ELECTED
    assert citizen_b.office == Office.PRESIDENT
    assert citizen_b.term_end_tick == 2 * term_ticks

    assert citizen_a.role == Role.ELECTOR
    assert citizen_a.office == Office.NONE
    assert citizen_a.term_end_tick is None


def test_a_reelected_president_keeps_office_and_accumulates_mandates(tmp_path):
    # A's own party re-nominates them each cycle (select_party_nominee has
    # no role filter, so this works whether A is currently ELECTOR or
    # ELECTED) -- the realistic path an incumbent's re-election takes,
    # unlike manually pre-declaring candidacy between calls: the reset at
    # the top of _hold_presidential_election runs before nominees are
    # (re)declared each time it's called, so a role set before the call
    # would just be overwritten by it.
    config = load_config()
    term_ticks = config.institutions.president_term_years * config.run.ticks_per_year

    citizen_a = _office_test_citizen(0, 0.1)
    citizen_a.ambition_score = 1.0
    citizen_a.party_affiliation = 0
    party = Party(party_id=0, platform=(0.1,))
    electors = [_office_test_citizen(i, 0.5) for i in range(1, 6)]

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        _hold_presidential_election([citizen_a] + electors, [party], config, journal, tick=0, llm_client=None)
        assert citizen_a.mandates_served == 1
        assert citizen_a.office == Office.PRESIDENT

        _hold_presidential_election(
            [citizen_a] + electors, [party], config, journal, tick=term_ticks, llm_client=None
        )

    assert citizen_a.role == Role.ELECTED
    assert citizen_a.office == Office.PRESIDENT
    assert citizen_a.term_end_tick == 2 * term_ticks
    assert citizen_a.mandates_served == 2


def _config_with_rupture_enabled(output_dir) -> PolityConfig:
    config = _config_with_output_dir(output_dir)
    return dataclasses.replace(
        config,
        candidacy=dataclasses.replace(
            config.candidacy,
            rupture_path_enabled=True,
            rupture_base_probability=0.05,
            rupture_signature_ratio=0.01,
        ),
    )


def test_rupture_path_produces_a_rupture_candidacy_event(tmp_path):
    journal_path = run_simulation(_config_with_rupture_enabled(tmp_path), run_id="rupture")
    events = _events(journal_path)
    rupture_events = [
        e for e in events if e["event_type"] == "candidacy_declared" and e["payload"].get("path") == "rupture"
    ]
    assert len(rupture_events) > 0


def test_two_runs_with_rupture_enabled_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(_config_with_rupture_enabled(tmp_path / "a"), run_id="same-run-id")
    path_b = run_simulation(_config_with_rupture_enabled(tmp_path / "b"), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


# ── mandate tracking (v4 Lot 2) ──────────────────────────────────────────

def _config_with_mandate_enabled(output_dir) -> PolityConfig:
    config = _config_with_output_dir(output_dir)
    return dataclasses.replace(config, mandate=dataclasses.replace(config.mandate, enabled=True))


def _config_with_mandate_enabled_and_guaranteed_winners(output_dir) -> PolityConfig:
    # The shipped default ambition_threshold (0.7) never actually produces a
    # presidential winner at seed=42 (every election_no_winner) -- lowering
    # it to 0 guarantees nominees, and therefore `elected` events to assert
    # mandate_pledge_declared against.
    config = _config_with_mandate_enabled(output_dir)
    return dataclasses.replace(config, candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0))


def test_default_config_run_emits_no_mandate_events(tmp_path):
    # The accountability phase is wired into every tick (v4 Lot 2's
    # structural change) but must stay inert under the shipped default
    # (mandate.enabled: false) -- zero new journal bytes.
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] in ("mandate_pledge_declared", "mandate_deviation_recorded")]


def test_mandate_enabled_run_declares_a_pledge_per_election_and_records_no_deviation(tmp_path):
    # §7bis.5 control case: without representative_response (Lot 6),
    # revealed_position never diverges from pledged_platform, so deviation
    # is 0 everywhere through Lot 5 -- asserted here, not just claimed.
    journal_path = run_simulation(_config_with_mandate_enabled_and_guaranteed_winners(tmp_path), run_id="mandate-on")
    events = _events(journal_path)
    elected = [e for e in events if e["event_type"] == "elected"]
    pledges = [e for e in events if e["event_type"] == "mandate_pledge_declared"]
    deviations = [e for e in events if e["event_type"] == "mandate_deviation_recorded"]
    assert len(elected) > 0
    assert len(pledges) == len(elected)
    for pledge in pledges:
        assert len(pledge["payload"]["pledged_platform"]) == load_config().citizens.issue_count
        assert pledge["payload"]["lame_duck"] is False
    assert deviations == []


def test_two_mandate_enabled_runs_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(_config_with_mandate_enabled(tmp_path / "a"), run_id="same-run-id")
    path_b = run_simulation(_config_with_mandate_enabled(tmp_path / "b"), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


def test_accountability_phase_records_deviation_only_above_the_threshold(tmp_path):
    # The only way to exercise mandate_deviation_recorded's write path before
    # Lot 6 exists: nothing in the tick loop can produce a nonzero deviation
    # on its own, so this perturbs revealed_position directly.
    config = _config_with_mandate_enabled(tmp_path)
    citizens = [
        Citizen(
            citizen_id=0,
            issue_positions=tuple(0.5 for _ in range(config.citizens.issue_count)),
            issue_priorities=tuple(1.0 / config.citizens.issue_count for _ in range(config.citizens.issue_count)),
            blank_threshold=0.5,
            ambition_score=0.5,
            role=Role.ELECTED,
            office=Office.PRESIDENT,
        )
    ]
    top_dim = 0  # uniform priorities -- any dimension is "the" top one
    pledged = tuple(0.5 for _ in range(config.citizens.issue_count))
    below_threshold = list(pledged)
    below_threshold[top_dim] += 0.05
    above_threshold = list(pledged)
    above_threshold[top_dim] += 0.9

    below_path = tmp_path / "below.jsonl"
    with Journal(below_path, run_id="below") as journal:
        citizens[0].pledged_platform = pledged
        citizens[0].revealed_position = tuple(below_threshold)
        _run_accountability_phase(citizens, config, journal, tick=0)
    assert _events(below_path) == []

    above_path = tmp_path / "above.jsonl"
    with Journal(above_path, run_id="above") as journal:
        citizens[0].pledged_platform = pledged
        citizens[0].revealed_position = tuple(above_threshold)
        _run_accountability_phase(citizens, config, journal, tick=0)
    above_events = _events(above_path)
    assert len(above_events) == 1
    assert above_events[0]["event_type"] == "mandate_deviation_recorded"
    assert above_events[0]["citizen_id"] == 0
    assert above_events[0]["payload"]["deviation"] > config.mandate.deviation_log_threshold


# ── term limits (v4 Lot 2, §6bis.1) ──────────────────────────────────────

def test_term_limited_incumbent_is_not_re_nominated(tmp_path):
    config = dataclasses.replace(
        load_config(), institutions=dataclasses.replace(load_config().institutions, president_term_limit=1)
    )
    term_ticks = config.institutions.president_term_years * config.run.ticks_per_year

    citizen_a = _office_test_citizen(0, 0.1)
    citizen_a.ambition_score = 1.0
    citizen_a.party_affiliation = 0
    citizen_b = _office_test_citizen(1, 0.9)
    citizen_b.ambition_score = 1.0
    citizen_b.party_affiliation = 1
    party_a = Party(party_id=0, platform=(0.1,))
    party_b = Party(party_id=1, platform=(0.9,))
    # Electors sit next to A so A wins the first, contested election clearly.
    electors = [_office_test_citizen(i, 0.1) for i in range(2, 7)]

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        _hold_presidential_election(
            [citizen_a, citizen_b] + electors, [party_a, party_b], config, journal, tick=0, llm_client=None
        )
        assert citizen_a.office == Office.PRESIDENT
        assert citizen_a.mandates_served == 1

        # A has now served their one permitted mandate: excluded from the
        # eligible pool, so B is the only nominee and wins uncontested even
        # though the electorate still sits next to A's platform.
        _hold_presidential_election(
            [citizen_a, citizen_b] + electors, [party_a, party_b], config, journal, tick=term_ticks, llm_client=None
        )

    assert citizen_b.office == Office.PRESIDENT
    assert citizen_b.role == Role.ELECTED
    assert citizen_a.office == Office.NONE
    assert citizen_a.role == Role.ELECTOR
    assert citizen_a.mandates_served == 1


# ── legitimacy (v4 Lot 3) ─────────────────────────────────────────────────

def _config_with_legitimacy_enabled(output_dir, **overrides) -> PolityConfig:
    config = _config_with_output_dir(output_dir)
    legitimacy = dataclasses.replace(config.legitimacy, enabled=True, **overrides)
    return dataclasses.replace(config, legitimacy=legitimacy)


def _config_with_legitimacy_enabled_and_guaranteed_winners(output_dir, **overrides) -> PolityConfig:
    # Same rationale as mandate's own helper: ambition_threshold=0.7 never
    # produces a presidential winner at seed=42.
    config = _config_with_legitimacy_enabled(output_dir, **overrides)
    return dataclasses.replace(config, candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0))


def test_default_config_run_emits_no_legitimacy_events(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] in ("legitimacy_updated", "recalled")]


def test_legitimacy_is_flat_at_mandate_strength_for_the_entire_run(tmp_path):
    # §7bis.6's central claim, now a passing test: with no citizen pressure
    # (Lots 4-5 not built yet) and recall_floor=0.0 isolating this from the
    # recall mechanism, L(t) == m at every single tick, every term.
    config = _config_with_legitimacy_enabled_and_guaranteed_winners(tmp_path, recall_floor=0.0)
    journal_path = run_simulation(config, run_id="legitimacy-flat")
    events = _events(journal_path)
    updates = [e for e in events if e["event_type"] == "legitimacy_updated"]
    assert not [e for e in events if e["event_type"] == "recalled"]
    # Exactly one update per tick for the whole run -- elections hand off
    # the office with zero vacancy gap, so there's no term-boundary
    # double-count or undercount to account for (the last term is simply
    # truncated by the run's own end, not by anything this test predicts).
    assert len(updates) == config.run.duration_years * config.run.ticks_per_year + 1
    for update in updates:
        assert update["payload"]["mandate_strength"] == pytest.approx(0.51)
        assert update["payload"]["legitimacy"] == pytest.approx(update["payload"]["mandate_strength"])


@pytest.mark.parametrize(
    "method,expected_winner_cid,expected_m",
    [
        ("two_round", 62, 0.51),
        ("irv", 62, 0.51),
        ("borda", 48, 0.56),
        ("schulze", 48, 0.56),
    ],
)
def test_mandate_strength_is_correct_and_method_agnostic(tmp_path, method, expected_winner_cid, expected_m):
    config = _config_with_legitimacy_enabled_and_guaranteed_winners(tmp_path)
    config = dataclasses.replace(config, institutions=dataclasses.replace(config.institutions, presidential_method=method))
    citizens = generate_population(config.citizens, config.run.population_size, config.run.seed)
    parties = initialize_parties(citizens, config.parties.initial_count, config.run.seed)
    for citizen in citizens:
        citizen.party_affiliation = assign_party_affiliation(citizen, parties)

    with Journal(tmp_path / "run.jsonl", run_id="m") as journal:
        _hold_presidential_election(citizens, parties, config, journal, tick=0, llm_client=None)

    winner = next(c for c in citizens if c.office == Office.PRESIDENT)
    assert winner.citizen_id == expected_winner_cid
    assert winner.mandate_strength == pytest.approx(expected_m)
    assert winner.legitimacy_capital == pytest.approx(expected_m)


def test_two_legitimacy_enabled_runs_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(_config_with_legitimacy_enabled(tmp_path / "a"), run_id="same-run-id")
    path_b = run_simulation(_config_with_legitimacy_enabled(tmp_path / "b"), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


def test_legitimacy_enabled_without_mandate_enabled_emits_no_deviation_events(tmp_path):
    # Independent toggles: legitimacy.enabled does not imply mandate.enabled.
    config = _config_with_legitimacy_enabled_and_guaranteed_winners(tmp_path)
    journal_path = run_simulation(config, run_id="legitimacy-only")
    events = _events(journal_path)
    assert [e for e in events if e["event_type"] == "legitimacy_updated"]
    assert not [e for e in events if e["event_type"] == "mandate_deviation_recorded"]


def _legitimacy_test_citizen(cid, legitimacy_capital, mandate_strength_value):
    return Citizen(
        citizen_id=cid,
        issue_positions=(0.5,),
        issue_priorities=(1.0,),
        blank_threshold=0.5,
        ambition_score=0.5,
        role=Role.ELECTED,
        office=Office.PRESIDENT,
        legitimacy_capital=legitimacy_capital,
        mandate_strength=mandate_strength_value,
    )


def test_recall_fires_when_legitimacy_crosses_the_floor_and_vacates_the_office(tmp_path):
    # Fixed point at m=0.1, below the shipped recall_floor (0.2): stays
    # below every tick, so the floor fires on the very first call.
    config = _config_with_legitimacy_enabled(tmp_path)
    citizens = [_legitimacy_test_citizen(0, legitimacy_capital=0.1, mandate_strength_value=0.1)]

    journal_path = tmp_path / "recall.jsonl"
    with Journal(journal_path, run_id="recall") as journal:
        _run_accountability_phase(citizens, config, journal, tick=0)
    events = _events(journal_path)
    assert [e["event_type"] for e in events] == ["legitimacy_updated", "recalled"]
    assert events[0]["payload"]["legitimacy"] == pytest.approx(0.1)
    assert events[1]["payload"]["legitimacy"] == pytest.approx(0.1)
    assert events[1]["payload"]["recall_floor"] == config.legitimacy.recall_floor

    holder = citizens[0]
    assert holder.role == Role.ELECTOR
    assert holder.office == Office.NONE
    assert holder.term_end_tick is None
    # Not reset -- post-mortem legibility, same precedent as Lot 2's
    # pledged_platform/revealed_position on a term-end vacate.
    assert holder.legitimacy_capital == pytest.approx(0.1)
    assert holder.mandate_strength == pytest.approx(0.1)

    # Office is now vacant: a second call is a no-op.
    with Journal(tmp_path / "recall2.jsonl", run_id="recall2") as journal:
        _run_accountability_phase(citizens, config, journal, tick=1)
    assert _events(tmp_path / "recall2.jsonl") == []


def test_same_tick_election_recall_is_reachable(tmp_path):
    # A fixed, externally-legible floor means exactly this can happen: a
    # winner with m below the floor is recalled the tick they're elected.
    config = _config_with_legitimacy_enabled_and_guaranteed_winners(tmp_path, recall_floor=0.99)
    journal_path = run_simulation(config, run_id="same-tick-recall")
    events = _events(journal_path)
    elected_ticks = [e["tick"] for e in events if e["event_type"] == "elected"]
    recalled_ticks = [e["tick"] for e in events if e["event_type"] == "recalled"]
    assert elected_ticks
    assert elected_ticks == recalled_ticks


def test_passive_erosion_applies_without_mandate_tracking_enabled(tmp_path):
    # Guards the gating design's own silent-zero gap: passive_erosion_weight
    # must still erode L even when mandate.enabled is False, since
    # measurement is free and only the mandate_deviation_recorded *write*
    # is gated on mandate.enabled.
    config = _config_with_legitimacy_enabled(tmp_path, passive_erosion_weight=0.5)
    assert config.mandate.enabled is False
    citizen = _legitimacy_test_citizen(0, legitimacy_capital=0.5, mandate_strength_value=0.5)
    citizen.pledged_platform = (0.0,)
    citizen.revealed_position = (1.0,)  # deviation = 1.0

    journal_path = tmp_path / "passive.jsonl"
    with Journal(journal_path, run_id="passive") as journal:
        _run_accountability_phase([citizen], config, journal, tick=0)
    events = _events(journal_path)
    update = next(e for e in events if e["event_type"] == "legitimacy_updated")
    assert update["payload"]["ecart"] == pytest.approx(0.5 * 1.0)
    assert not [e for e in events if e["event_type"] == "mandate_deviation_recorded"]


# ── awakening / mobilization (v4 Lot 4) ──────────────────────────────────

def _config_with_awakening_enabled(output_dir, **overrides) -> PolityConfig:
    config = _config_with_legitimacy_enabled(output_dir)
    return dataclasses.replace(config, awakening=dataclasses.replace(config.awakening, enabled=True, **overrides))


def _config_with_awakening_enabled_and_guaranteed_winners(output_dir, **overrides) -> PolityConfig:
    config = _config_with_awakening_enabled(output_dir, **overrides)
    return dataclasses.replace(config, candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0))


def _config_with_mobilization_enabled(output_dir, base_threshold_dist=None):
    config = _config_with_awakening_enabled_and_guaranteed_winners(output_dir)
    config = dataclasses.replace(
        config,
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True),
    )
    if base_threshold_dist is not None:
        config = dataclasses.replace(config, citizens=dataclasses.replace(config.citizens, base_threshold_dist=base_threshold_dist))
    return config


def test_default_config_run_emits_no_pressure_action_events(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "pressure_action"]


def test_two_awakening_enabled_runs_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(_config_with_awakening_enabled(tmp_path / "a"), run_id="same-run-id")
    path_b = run_simulation(_config_with_awakening_enabled(tmp_path / "b"), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


def test_two_mobilization_enabled_runs_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(_config_with_mobilization_enabled(tmp_path / "a"), run_id="same-run-id")
    path_b = run_simulation(_config_with_mobilization_enabled(tmp_path / "b"), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


def test_electoral_only_control_arm_is_flat_legitimacy_and_only_nothing_or_wait(tmp_path):
    # The control arm this whole palier compares against: awakening AND
    # legitimacy both on, but electoral_only leaves no real lever to pull.
    config = _config_with_awakening_enabled_and_guaranteed_winners(tmp_path)
    journal_path = run_simulation(config, run_id="control-arm")
    events = _events(journal_path)

    pressure_events = [e for e in events if e["event_type"] == "pressure_action"]
    assert pressure_events
    acts = {e["payload"]["act"] for e in pressure_events}
    assert acts == {0, 4}  # both members of the DoD's stated set actually occur

    updates = [e for e in events if e["event_type"] == "legitimacy_updated"]
    assert updates
    for update in updates:
        assert update["payload"]["legitimacy"] == pytest.approx(update["payload"]["mandate_strength"])
    assert not [e for e in events if e["event_type"] == "recalled"]


def test_mobilization_moves_and_recovers_legitimacy(tmp_path):
    # A tuned (not shipped) base_threshold_dist so L dips without hitting
    # the recall floor, so a "recovery" is actually observable -- the
    # shipped beta(3,5) recalls on essentially the first tick of every term
    # (see scripts/awakening_calibration_results.md).
    config = _config_with_mobilization_enabled(tmp_path, base_threshold_dist="beta(7,3)")
    journal_path = run_simulation(config, run_id="mobilization")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "recalled"]

    term_ticks = config.institutions.president_term_years * config.run.ticks_per_year
    updates = [e for e in events if e["event_type"] == "legitimacy_updated"]
    first_term = [e for e in updates if e["tick"] < term_ticks]
    legitimacies = [e["payload"]["legitimacy"] for e in first_term]

    assert min(legitimacies) < legitimacies[0]  # L actually moves below m
    min_index = legitimacies.index(min(legitimacies))
    assert legitimacies[-1] > legitimacies[min_index]  # and recovers before the next election


def test_pressure_action_journals_act_zero_when_it_occurs(tmp_path):
    # §16.3: "y compris act=0 (inaction)" -- not just theoretically legal.
    config = _config_with_awakening_enabled_and_guaranteed_winners(tmp_path)
    journal_path = run_simulation(config, run_id="act-zero")
    events = _events(journal_path)
    assert any(e["event_type"] == "pressure_action" and e["payload"]["act"] == 0 for e in events)


def test_pressure_action_events_precede_legitimacy_updated_and_are_ascending_within_a_tick(tmp_path):
    config = _config_with_awakening_enabled_and_guaranteed_winners(tmp_path)
    journal_path = run_simulation(config, run_id="ordering")
    events = _events(journal_path)
    for tick in {e["tick"] for e in events}:
        tick_events = [e for e in events if e["tick"] == tick]
        types = [e["event_type"] for e in tick_events]
        pressure_indices = [i for i, t in enumerate(types) if t == "pressure_action"]
        legitimacy_indices = [i for i, t in enumerate(types) if t == "legitimacy_updated"]
        if pressure_indices and legitimacy_indices:
            assert max(pressure_indices) < min(legitimacy_indices)
        cids = [tick_events[i]["citizen_id"] for i in pressure_indices]
        assert cids == sorted(cids)


def test_no_pressure_action_events_while_the_presidency_is_vacant(tmp_path):
    # Shipped ambition_threshold never produces a winner (Lot 2/3) -- the
    # presidency stays vacant the entire run.
    config = _config_with_awakening_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="vacant")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "elected"]
    assert not [e for e in events if e["event_type"] == "pressure_action"]


def test_reelected_president_street_pressure_resets_at_the_new_term(tmp_path):
    config = load_config()
    config = dataclasses.replace(config, street_pressure=dataclasses.replace(config.street_pressure, enabled=True))
    term_ticks = config.institutions.president_term_years * config.run.ticks_per_year

    citizen_a = _office_test_citizen(0, 0.1)
    citizen_a.ambition_score = 1.0
    citizen_a.party_affiliation = 0
    party = Party(party_id=0, platform=(0.1,))
    electors = [_office_test_citizen(i, 0.5) for i in range(1, 6)]

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        _hold_presidential_election([citizen_a] + electors, [party], config, journal, tick=0, llm_client=None)
        citizen_a.street_pressure = 0.75  # simulate pressure accumulated during the term

        _hold_presidential_election(
            [citizen_a] + electors, [party], config, journal, tick=term_ticks, llm_client=None
        )

    assert citizen_a.office == Office.PRESIDENT
    assert citizen_a.street_pressure == 0.0


# ── petition + confidence vote (v4 Lot 5) ─────────────────────────────────

def _config_with_petition_enabled(output_dir, base_threshold_dist=None, **petition_overrides) -> PolityConfig:
    config = _config_with_awakening_enabled_and_guaranteed_winners(output_dir)
    config = dataclasses.replace(
        config,
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, petition_enabled=True),
        petition=dataclasses.replace(config.petition, enabled=True, **petition_overrides),
    )
    if base_threshold_dist is not None:
        config = dataclasses.replace(config, citizens=dataclasses.replace(config.citizens, base_threshold_dist=base_threshold_dist))
    return config


def _config_with_full_menu_enabled(output_dir, base_threshold_dist=None) -> PolityConfig:
    config = _config_with_petition_enabled(output_dir, base_threshold_dist=base_threshold_dist)
    return dataclasses.replace(
        config,
        pressure_menu=dataclasses.replace(config.pressure_menu, mobilization_enabled=True),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True),
    )


def test_default_config_run_emits_no_petition_events(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] in _PETITION_LIFECYCLE_EVENT_TYPES]
    # No recalled event carries a trigger key under the shipped default --
    # legitimacy is disabled entirely, so no recalled event occurs at all.
    assert not [e for e in events if e["event_type"] == "recalled"]


def test_two_petition_enabled_runs_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(_config_with_petition_enabled(tmp_path / "a"), run_id="same-run-id")
    path_b = run_simulation(_config_with_petition_enabled(tmp_path / "b"), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


def test_two_full_menu_runs_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(_config_with_full_menu_enabled(tmp_path / "a"), run_id="same-run-id")
    path_b = run_simulation(_config_with_full_menu_enabled(tmp_path / "b"), run_id="same-run-id")
    assert path_a.read_bytes() == path_b.read_bytes()


def test_petition_only_run_journals_a_complete_petition_lifecycle(tmp_path):
    # Headline DoD: the full §7bis.4a lifecycle actually occurs in a
    # petition-only run, not just as unit-tested primitives.
    config = _config_with_petition_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="petition-lifecycle")
    events = _events(journal_path)

    assert [e for e in events if e["event_type"] == "petition_launched"]
    assert [e for e in events if e["event_type"] == "petition_signed"]
    assert [e for e in events if e["event_type"] == "confidence_vote_triggered"]
    assert [e for e in events if e["event_type"] == "confidence_vote_result"]

    # Walk the journal reconstructing petition "epochs": launch resets the
    # signature count to 1, each sign increments it by exactly 1, and a
    # resolution (trigger, expiry, OR a floor recall that overtakes an
    # unresolved petition -- Lot 4's own predicted dynamic: w_pet's
    # amplification can cross the floor before a petition's own threshold
    # or lifespan resolves it, orphaning it without a closing petition
    # event of its own) clears it -- no two petitions ever overlap
    # (concurrent_allowed is TRANCHÉ false).
    current_signatures = None
    for e in events:
        t = e["event_type"]
        if t == "petition_launched":
            assert current_signatures is None
            current_signatures = e["payload"]["signatures"]
            assert current_signatures == 1
        elif t == "petition_signed":
            assert current_signatures is not None
            assert e["payload"]["signatures"] == current_signatures + 1
            current_signatures = e["payload"]["signatures"]
        elif t in ("confidence_vote_triggered", "petition_expired", "recalled"):
            current_signatures = None

    # Every confidence_vote_triggered is immediately followed by its own
    # confidence_vote_result -- never short-circuited, never deferred.
    for i, e in enumerate(events):
        if e["event_type"] == "confidence_vote_triggered":
            assert events[i + 1]["event_type"] == "confidence_vote_result"


def test_petition_expires_when_its_threshold_is_unreachable(tmp_path):
    # signature_threshold > 1.0 is structurally unreachable (signed_ratio's
    # numerator can never exceed its denominator) -- a tuned config, not a
    # reading of the shipped default (Lot 4's own precedent). base_threshold_dist
    # is ALSO tuned gentler (Lot 4's own beta(7,3), which avoids floor-crashing
    # every term) so a petition survives long enough to actually reach its own
    # lifespan instead of being orphaned by a floor recall first.
    config = _config_with_petition_enabled(tmp_path, base_threshold_dist="beta(7,3)", signature_threshold=1.5)
    journal_path = run_simulation(config, run_id="petition-expiry")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "confidence_vote_triggered"]
    launched = [e for e in events if e["event_type"] == "petition_launched"]
    expired = [e for e in events if e["event_type"] == "petition_expired"]
    assert launched
    assert expired
    for e in expired:
        matching_launch = next(le for le in launched if le["payload"]["expires_at_tick"] == e["tick"])
        assert e["payload"]["opened_at_tick"] == matching_launch["tick"]


def test_petition_events_follow_their_own_pressure_action_within_a_tick(tmp_path):
    config = _config_with_petition_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="petition-ordering")
    events = _events(journal_path)
    for tick in {e["tick"] for e in events}:
        tick_events = [e for e in events if e["tick"] == tick]
        for i, e in enumerate(tick_events):
            if e["event_type"] in ("petition_launched", "petition_signed"):
                assert i > 0
                prev = tick_events[i - 1]
                assert prev["event_type"] == "pressure_action"
                assert prev["citizen_id"] == e["citizen_id"]


def test_petition_threshold_uses_signatures_gathered_this_same_tick(tmp_path):
    # Direct call: population_size=2 so the launcher's own seed signature
    # alone already clears signature_threshold on the launch tick itself.
    config = _config_with_legitimacy_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        run=dataclasses.replace(config.run, population_size=2),
        awakening=dataclasses.replace(config.awakening, enabled=True, modulation_amplitude=0.0),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, petition_enabled=True),
        petition=dataclasses.replace(config.petition, enabled=True, signature_threshold=0.4),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.5, mandate_strength_value=0.5)
    holder.revealed_position = (0.5,)
    launcher = Citizen(
        citizen_id=1, issue_positions=(0.0,), issue_priorities=(1.0,), blank_threshold=0.0,
        ambition_score=0.5, base_threshold=0.0,
    )
    journal_path = tmp_path / "same-tick.jsonl"
    with Journal(journal_path, run_id="same-tick") as journal:
        _run_accountability_phase([holder, launcher], config, journal, tick=0)
    events = _events(journal_path)
    launched = next(e for e in events if e["event_type"] == "petition_launched")
    triggered = next(e for e in events if e["event_type"] == "confidence_vote_triggered")
    assert launched["tick"] == triggered["tick"] == 0
    assert triggered["payload"]["opened_at_tick"] == 0


def test_petition_pressure_enters_ecart_on_the_same_tick_as_its_signatures(tmp_path):
    config = _config_with_legitimacy_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        run=dataclasses.replace(config.run, population_size=2),
        awakening=dataclasses.replace(config.awakening, enabled=True, modulation_amplitude=0.0),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, petition_enabled=True),
        petition=dataclasses.replace(config.petition, enabled=True, signature_threshold=0.99),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.5, mandate_strength_value=0.5)
    holder.revealed_position = (0.5,)
    launcher = Citizen(
        citizen_id=1, issue_positions=(0.0,), issue_priorities=(1.0,), blank_threshold=0.0,
        ambition_score=0.5, base_threshold=0.0,
    )
    journal_path = tmp_path / "ecart.jsonl"
    with Journal(journal_path, run_id="ecart") as journal:
        _run_accountability_phase([holder, launcher], config, journal, tick=0)
    events = _events(journal_path)
    update = next(e for e in events if e["event_type"] == "legitimacy_updated")
    expected = config.petition.weight_in_ecart * 0.5 + config.street_pressure.weight_in_ecart * 0.0
    assert update["payload"]["ecart"] == pytest.approx(expected)


def test_the_hard_floor_beats_the_petition_on_a_same_tick_collision(tmp_path):
    config = _config_with_legitimacy_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        run=dataclasses.replace(config.run, population_size=4),
        petition=dataclasses.replace(config.petition, enabled=True),
    )
    # Fixed point at m=0.1, below the shipped recall_floor -- the floor
    # fires regardless of the petition's own ecart contribution.
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.1, mandate_strength_value=0.1)
    holder.revealed_position = (0.5,)
    holder.petition_open_since_tick = 0
    holder.petition_signers = frozenset({1, 2, 3})  # 3/4 = 0.75 >= signature_threshold (0.25)
    voters = [
        Citizen(citizen_id=i, issue_positions=(0.0,), issue_priorities=(1.0,), blank_threshold=0.0, ambition_score=0.5)
        for i in (1, 2, 3)
    ]  # each sits 0.5 away from holder.revealed_position, beyond their own 0.0 tolerance -> votes remove

    journal_path = tmp_path / "collision.jsonl"
    with Journal(journal_path, run_id="collision") as journal:
        _run_accountability_phase([holder] + voters, config, journal, tick=5)

    events = _events(journal_path)
    assert [e["event_type"] for e in events] == [
        "legitimacy_updated", "confidence_vote_triggered", "confidence_vote_result", "recalled",
    ]
    # Anti-short-circuit: the confidence vote still ran and journaled in
    # full even though the floor is what ultimately wins the attribution.
    assert events[2]["payload"]["retained"] is False
    assert events[3]["payload"]["trigger"] == "legitimacy_floor"

    assert holder.role == Role.ELECTOR
    assert holder.office == Office.NONE
    assert holder.petition_open_since_tick is None
    assert holder.petition_cooldown_until_tick == 5 + config.petition.cooldown_ticks


def test_a_lost_confidence_vote_recalls_and_vacates_the_office(tmp_path):
    config = _config_with_legitimacy_enabled(tmp_path, recall_floor=0.0)
    config = dataclasses.replace(
        config,
        run=dataclasses.replace(config.run, population_size=4),
        petition=dataclasses.replace(config.petition, enabled=True),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.revealed_position = (0.5,)
    holder.petition_open_since_tick = 0
    holder.petition_signers = frozenset({1, 2, 3})
    voters = [
        Citizen(citizen_id=i, issue_positions=(0.0,), issue_priorities=(1.0,), blank_threshold=0.0, ambition_score=0.5)
        for i in (1, 2, 3)
    ]

    journal_path = tmp_path / "lost-confidence.jsonl"
    with Journal(journal_path, run_id="lost-confidence") as journal:
        _run_accountability_phase([holder] + voters, config, journal, tick=3)

    events = _events(journal_path)
    recalled = next(e for e in events if e["event_type"] == "recalled")
    assert recalled["payload"]["trigger"] == "confidence_vote"

    assert holder.role == Role.ELECTOR
    assert holder.office == Office.NONE
    assert holder.term_end_tick is None
    update_event = next(e for e in events if e["event_type"] == "legitimacy_updated")
    # Not reset by the recall -- same precedent as the floor-recall path.
    assert holder.legitimacy_capital == pytest.approx(update_event["payload"]["legitimacy"])

    # Office is now vacant: a second call is a no-op.
    with Journal(tmp_path / "lost-confidence-2.jsonl", run_id="lost-confidence-2") as journal:
        _run_accountability_phase([holder] + voters, config, journal, tick=4)
    assert _events(tmp_path / "lost-confidence-2.jsonl") == []


def test_a_survived_confidence_vote_leaves_legitimacy_untouched_and_opens_the_cooldown(tmp_path):
    config = _config_with_legitimacy_enabled(tmp_path, recall_floor=0.0)
    config = dataclasses.replace(
        config,
        run=dataclasses.replace(config.run, population_size=4),
        petition=dataclasses.replace(config.petition, enabled=True),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.revealed_position = (0.5,)
    holder.petition_open_since_tick = 0
    holder.petition_signers = frozenset({1, 2, 3})
    voters = [
        Citizen(citizen_id=i, issue_positions=(0.5,), issue_priorities=(1.0,), blank_threshold=0.5, ambition_score=0.5)
        for i in (1, 2, 3)
    ]  # each sits exactly on holder.revealed_position -> votes keep

    journal_path = tmp_path / "survived.jsonl"
    with Journal(journal_path, run_id="survived") as journal:
        _run_accountability_phase([holder] + voters, config, journal, tick=7)

    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "recalled"]
    result = next(e for e in events if e["event_type"] == "confidence_vote_result")
    assert result["payload"]["retained"] is True

    update_event = next(e for e in events if e["event_type"] == "legitimacy_updated")
    # No L change attributable to surviving -- legitimacy_updated (step 4)
    # already ran before the vote resolved (step 5).
    assert holder.legitimacy_capital == pytest.approx(update_event["payload"]["legitimacy"])
    assert holder.petition_open_since_tick is None
    assert holder.petition_cooldown_until_tick == 7 + config.petition.cooldown_ticks


def test_a_second_petition_cannot_launch_during_the_cooldown(tmp_path):
    config = _config_with_legitimacy_enabled(tmp_path, recall_floor=0.0)
    config = dataclasses.replace(
        config,
        run=dataclasses.replace(config.run, population_size=2),
        awakening=dataclasses.replace(config.awakening, enabled=True, modulation_amplitude=0.0),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, petition_enabled=True),
        petition=dataclasses.replace(config.petition, enabled=True),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.revealed_position = (0.5,)
    holder.petition_cooldown_until_tick = 5
    launcher = Citizen(
        citizen_id=1, issue_positions=(0.0,), issue_priorities=(1.0,), blank_threshold=0.0,
        ambition_score=0.5, base_threshold=0.0,
    )

    launched_ticks = []
    for tick in range(1, 6):
        journal_path = tmp_path / f"tick-{tick}.jsonl"
        with Journal(journal_path, run_id=f"t{tick}") as journal:
            _run_accountability_phase([holder, launcher], config, journal, tick=tick)
        launched_ticks += [e["tick"] for e in _events(journal_path) if e["event_type"] == "petition_launched"]

    assert launched_ticks == [5]


def test_reelected_president_petition_state_resets_at_the_new_term(tmp_path):
    config = load_config()
    config = dataclasses.replace(config, petition=dataclasses.replace(config.petition, enabled=True))
    term_ticks = config.institutions.president_term_years * config.run.ticks_per_year

    citizen_a = _office_test_citizen(0, 0.1)
    citizen_a.ambition_score = 1.0
    citizen_a.party_affiliation = 0
    party = Party(party_id=0, platform=(0.1,))
    electors = [_office_test_citizen(i, 0.5) for i in range(1, 6)]

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        _hold_presidential_election([citizen_a] + electors, [party], config, journal, tick=0, llm_client=None)
        citizen_a.petition_open_since_tick = 3
        citizen_a.petition_signers = frozenset({1, 2})
        citizen_a.petition_cooldown_until_tick = 10

        _hold_presidential_election(
            [citizen_a] + electors, [party], config, journal, tick=term_ticks, llm_client=None
        )

    assert citizen_a.office == Office.PRESIDENT
    assert citizen_a.petition_open_since_tick is None
    assert citizen_a.petition_signers == frozenset()
    assert citizen_a.petition_cooldown_until_tick is None


def test_a_defeated_incumbents_petition_state_is_deliberately_not_cleared(tmp_path):
    config = dataclasses.replace(
        load_config(), institutions=dataclasses.replace(load_config().institutions, president_term_limit=1)
    )
    config = dataclasses.replace(config, petition=dataclasses.replace(config.petition, enabled=True))
    term_ticks = config.institutions.president_term_years * config.run.ticks_per_year

    citizen_a = _office_test_citizen(0, 0.1)
    citizen_a.ambition_score = 1.0
    citizen_a.party_affiliation = 0
    citizen_b = _office_test_citizen(1, 0.9)
    citizen_b.ambition_score = 1.0
    citizen_b.party_affiliation = 1
    party_a = Party(party_id=0, platform=(0.1,))
    party_b = Party(party_id=1, platform=(0.9,))
    electors = [_office_test_citizen(i, 0.1) for i in range(2, 7)]

    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        _hold_presidential_election(
            [citizen_a, citizen_b] + electors, [party_a, party_b], config, journal, tick=0, llm_client=None
        )
        citizen_a.petition_open_since_tick = 3
        citizen_a.petition_signers = frozenset({2})

        _hold_presidential_election(
            [citizen_a, citizen_b] + electors, [party_a, party_b], config, journal, tick=term_ticks, llm_client=None
        )

    assert citizen_a.office == Office.NONE
    assert citizen_a.petition_open_since_tick == 3
    assert citizen_a.petition_signers == frozenset({2})


def test_no_petition_events_while_the_presidency_is_vacant(tmp_path):
    config = _config_with_awakening_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, petition_enabled=True),
        petition=dataclasses.replace(config.petition, enabled=True),
    )
    journal_path = run_simulation(config, run_id="vacant-petition")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "elected"]
    assert not [e for e in events if e["event_type"] in _PETITION_LIFECYCLE_EVENT_TYPES]


def test_full_menu_run_reaches_sign_launch_and_mobilize_acts(tmp_path):
    config = _config_with_full_menu_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="full-menu")
    events = _events(journal_path)
    acts = {e["payload"]["act"] for e in events if e["event_type"] == "pressure_action"}
    assert {0, 1, 2, 3}.issubset(acts)


def test_confidence_vote_keep_ratio_equals_mandate_strength_on_the_deterministic_path(tmp_path):
    # Lot 6 is what breaks this identity, on purpose (build_confidence_ballot's
    # own docstring): once revealed_position can drift, the two decouple.
    config = _config_with_petition_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="keep-ratio-identity")
    events = _events(journal_path)
    results = [e for e in events if e["event_type"] == "confidence_vote_result"]
    assert results
    for result in results:
        same_tick_updates = [
            e for e in events
            if e["event_type"] == "legitimacy_updated"
            and e["tick"] == result["tick"]
            and e["citizen_id"] == result["citizen_id"]
        ]
        assert same_tick_updates
        assert result["payload"]["keep_ratio"] == pytest.approx(same_tick_updates[-1]["payload"]["mandate_strength"])


# ── LLM-enabled path (v2 increments 1-2) ─────────────────────────────────

class _FakeLlmClient:
    """Deterministic fake dispatching on user_prompt shape, since one client
    instance now serves decide_candidacies ("citizens" key),
    decide_party_nominations ("parties" key), decide_campaign_positioning
    ("nominees" key), decide_coalition ("responders" key),
    decide_representative_response ("holders" key),
    decide_pressure_actions ("consulted" key), and cast_votes
    ("voters"/"candidates" keys) within the same run.
    Candidacy: declares (outcome=1) whenever ambition_score >= 0.1 --
    config.candidacy.ambition_threshold is NOT consulted by the LLM path at
    all (decide_candidacies never reads it; only the deterministic
    decide_candidacy does), so this fake owns its own threshold rather than
    reading one from config. Party nomination: picks the highest-ambition
    candidate per contested party (motif 206). Campaign positioning: every
    nominee shifts dimension 0 by +0.1 (motif 602) -- always non-empty, so
    tests can assert a real pledged_platform change, well within the
    default config.campaign bounds (max_positioning_delta=0.3,
    max_positioning_shifts=3). Coalition: every responder joins (motif 501)
    -- the assemble_coalition parity invariant (unanimous join ==
    form_coalition's own output) means this fake's coalitions match the
    deterministic baseline exactly, useful for the byte-identical
    reproducibility test. Representative response: every holder concedes,
    shifting dimension 0 by +0.1 (stance=1, motif=301) -- within the
    shipped mandate.max_response_delta=0.3/max_response_shifts=3 bounds and
    coherent under ResponseDecision's own stance/motif validator; the
    +0.1/tick drift saturates at apply_shifts's [0,1] clamp after ~10 ticks,
    itself worth having show up in an integration run. Pressure action:
    every consulted citizen mobilizes (act=3, motif=301) -- always
    menu-legal whenever mobilization_enabled, and exercises
    street_pressure/participants exactly like the deterministic baseline's
    own MOBILIZE branch. Voting: every citizen votes blank -- enough to
    exercise the integration plumbing (journal writes, reproducibility,
    error propagation) without needing real vote-quality logic."""

    def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
        payload = json.loads(user_prompt)
        if "citizens" in payload:
            decisions = [
                {"cid": c["cid"], "outcome": 1, "motif": 203}
                if c["ambition_score"] >= 0.1
                else {"cid": c["cid"], "outcome": 0, "motif": 201}
                for c in payload["citizens"]
            ]
            return json.dumps({"decisions": decisions})
        if "parties" in payload:
            decisions = [
                {
                    "party_id": p["party_id"],
                    "winner_position": max(p["candidates"], key=lambda c: c["ambition_score"])["position"],
                    "motif": 206,
                }
                for p in payload["parties"]
            ]
            return json.dumps({"decisions": decisions})
        if "nominees" in payload:
            decisions = [
                {"cid": n["cid"], "shifts": [{"dimension": 0, "delta": 0.1}], "motif": 602}
                for n in payload["nominees"]
            ]
            return json.dumps({"decisions": decisions})
        if "responders" in payload:
            decisions = [{"party_id": r["party_id"], "action": 1, "motif": 501} for r in payload["responders"]]
            return json.dumps({"decisions": decisions})
        if "holders" in payload:
            decisions = [
                {"cid": h["cid"], "shifts": [{"dimension": 0, "delta": 0.1}], "stance": 1, "motif": 301}
                for h in payload["holders"]
            ]
            return json.dumps({"decisions": decisions})
        if "consulted" in payload:
            return json.dumps({"decisions": self._pressure_decisions(payload["consulted"])})
        return json.dumps({"decisions": self._vote_decisions(payload["voters"])})

    def _vote_decisions(self, voters):
        return [{"cid": v["cid"], "blank": 1, "ranking": [], "motif": 101} for v in voters]

    def _pressure_decisions(self, consulted):
        # Same priority order as deterministic_pressure_action's own chain
        # (sign > launch > mobilize > wait), restricted to each citizen's
        # own frozen `available` list -- reading `available` from the
        # payload itself, rather than hardcoding one act, is what keeps
        # this fake menu-aware across every pressure_menu modality the
        # test suite exercises without needing the config directly. A
        # naive "prefer the largest available code" fallback was tried
        # first and rejected: 4 (WAIT_FOR_ELECTION) is always legal, so it
        # always wins under max(), starving the petition lever entirely
        # and silently breaking every test that expects a petition to
        # ever launch.
        priority = (1, 2, 3, 4)
        decisions = []
        for c in consulted:
            available = c["available"]
            act = next((a for a in priority if a in available), 0)
            decisions.append({"cid": c["cid"], "target": c["target"], "act": act, "motif": 301})
        return decisions


class _ElectingFakeLlmClient(_FakeLlmClient):
    """Same as _FakeLlmClient in every other respect, but every voter ranks
    the first candidate (by position) instead of voting blank -- unanimous
    support, so a winner is elected every term under any ranked method.
    _FakeLlmClient's own "everyone votes blank" behavior means NO
    presidential election ever produces a winner (confirmed: every existing
    LLM-path test either doesn't check `elected` at all, or explicitly
    asserts its absence) -- harmless for candidacy/positioning/coalition
    tests, but v4 Lot 6's representative_response needs a real, sitting
    officeholder to exercise at all."""

    def _vote_decisions(self, voters):
        return [{"cid": v["cid"], "blank": 0, "ranking": [1], "motif": 104} for v in voters]


class _LaunchingFakeLlmClient(_ElectingFakeLlmClient):
    """v4 Lot 7: every consulted citizen tries to LAUNCH a petition (act=2,
    motif=301) -- the pathological input the central judgment call (a
    frozen batch call vs. live, sequential petition state) exists to
    resolve. Under concurrent_allowed=false, only the first (lowest
    citizen_id) citizen's launch can actually succeed; every later
    citizen's decided act=2 must be downgraded by
    accountability.applicable_pressure_act to a signature (or, if petitions
    are off/unavailable, to NOTHING) -- see
    test_a_second_launch_in_the_same_tick_is_journaled_as_act_2_then_petition_signed."""

    def _pressure_decisions(self, consulted):
        return [{"cid": c["cid"], "target": c["target"], "act": 2, "motif": 301} for c in consulted]


def _config_with_llm_enabled(output_dir) -> PolityConfig:
    config = _config_with_output_dir(output_dir)
    return dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))


def test_llm_path_completes_and_journals_vote_cast_events(tmp_path):
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    vote_events = [e for e in events if e["event_type"] == "vote_cast"]
    assert len(vote_events) == config.run.population_size * 8
    assert all(e["motif"] == "101" for e in vote_events)
    assert all(e["codebook_version"] == config.llm.codebook_version for e in vote_events)


def test_two_llm_runs_with_the_same_seed_produce_byte_identical_journals(tmp_path):
    config_a = _config_with_llm_enabled(tmp_path / "a")
    config_b = _config_with_llm_enabled(tmp_path / "b")
    path_a = run_simulation(config_a, run_id="same-run-id", llm_client=_FakeLlmClient())
    path_b = run_simulation(config_b, run_id="same-run-id", llm_client=_FakeLlmClient())
    assert path_a.read_bytes() == path_b.read_bytes()


# ── representative_response (v4 Lot 6, dt=6) ─────────────────────────────

def _config_with_mandate_llm_enabled(output_dir, **overrides) -> PolityConfig:
    config = _config_with_llm_enabled(output_dir)
    config = dataclasses.replace(config, legitimacy=dataclasses.replace(config.legitimacy, enabled=True))
    return dataclasses.replace(config, mandate=dataclasses.replace(config.mandate, enabled=True, **overrides))


def test_default_config_run_emits_no_representative_response_events(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "representative_response"]


def test_llm_enabled_without_mandate_tracking_emits_no_representative_response_events(tmp_path):
    # mandate.enabled stays at its shipped False -- this is also why the two
    # existing byte-identical LLM reproducibility tests need no edit.
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-no-mandate", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "representative_response"]


def test_mandate_tracking_without_the_llm_never_moves_revealed_position(tmp_path):
    # §7bis.5 control case, re-asserted now that the gate exists: with
    # llm.enabled False, nothing can diverge revealed_position from
    # pledged_platform -- "no delta, stance=silence" by construction.
    config = _config_with_mandate_enabled_and_guaranteed_winners(tmp_path)
    journal_path = run_simulation(config, run_id="mandate-no-llm")
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "representative_response"]
    assert not [e for e in events if e["event_type"] == "mandate_deviation_recorded"]


def test_representative_response_is_journalled_once_per_presided_tick(tmp_path):
    config = _config_with_mandate_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="dt6", llm_client=_ElectingFakeLlmClient())
    events = _events(journal_path)
    response_events = [e for e in events if e["event_type"] == "representative_response"]
    legitimacy_events = [e for e in events if e["event_type"] == "legitimacy_updated"]
    assert response_events
    # legitimacy_updated is already a proven once-per-presided-tick invariant
    # (Lot 3) -- cross-checking against it avoids hardcoding a tick count.
    assert {e["tick"] for e in response_events} == {e["tick"] for e in legitimacy_events}

    for e in response_events:
        assert e["payload"]["office"] == Office.PRESIDENT.value
        assert set(e["payload"].keys()) == {"office", "stance", "shifts", "ctx"}
        assert set(e["payload"]["ctx"].keys()) == {"L", "mandate_dev", "street", "lame_duck", "ticks_left"}
        assert e["payload"]["ctx"]["lame_duck"] in (0, 1)
        assert e["motif"] == "301"
        assert e["codebook_version"] == config.llm.codebook_version


def test_representative_response_sees_the_previous_ticks_street_pressure(tmp_path):
    # DoD: the one-tick lag is an emergent property of step ordering, pinned
    # here so a later refactor that silently breaks it fails loudly.
    config = _config_with_llm_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        mandate=dataclasses.replace(config.mandate, enabled=True),
        legitimacy=dataclasses.replace(config.legitimacy, enabled=True),
        awakening=dataclasses.replace(config.awakening, enabled=True, modulation_amplitude=0.0),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True),
        run=dataclasses.replace(config.run, population_size=2),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.pledged_platform = (0.5,)
    holder.revealed_position = (0.5,)
    mobilizer = Citizen(
        citizen_id=1, issue_positions=(0.0,), issue_priorities=(1.0,), blank_threshold=0.0,
        ambition_score=0.5, base_threshold=0.0,
    )

    seen_street = []

    class RecordingClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            if "consulted" in payload:
                # dt=10 now also fires (llm.enabled + awakening.enabled): every
                # consulted citizen mobilizes, preserving this test's own intent
                # (the mobilizer raises street_pressure) now that the act comes
                # from the LLM path instead of deterministic_pressure_action.
                decisions = [
                    {"cid": c["cid"], "target": c["target"], "act": 3, "motif": 301} for c in payload["consulted"]
                ]
                return json.dumps({"decisions": decisions})
            seen_street.append(payload["holders"][0]["ctx"]["street"])
            decisions = [{"cid": h["cid"], "shifts": [], "stance": 3, "motif": 308} for h in payload["holders"]]
            return json.dumps({"decisions": decisions})

    client = RecordingClient()
    with Journal(tmp_path / "tick0.jsonl", run_id="tick0") as journal:
        _run_accountability_phase([holder, mobilizer], config, journal, tick=0, llm_client=client)
    street_after_tick0 = holder.street_pressure

    with Journal(tmp_path / "tick1.jsonl", run_id="tick1") as journal:
        _run_accountability_phase([holder, mobilizer], config, journal, tick=1, llm_client=client)

    assert seen_street[0] == 0.0  # tick 0: nothing has mobilized yet
    assert street_after_tick0 > 0.0  # tick 0's OWN mobilization raised it
    assert seen_street[1] == pytest.approx(street_after_tick0)  # tick 1 sees tick 0's write, not tick 1's


def test_mandate_deviation_is_recorded_once_revealed_position_drifts(tmp_path):
    # The first nonzero mandate_deviation_recorded in the project's history.
    # pledge_scope=full_platform so dimension 0 (the only one
    # _ElectingFakeLlmClient/_FakeLlmClient's holders branch ever shifts)
    # always carries nonzero weight, regardless of whether it happens to
    # land in the officeholder's own top-5 priority dimensions.
    config = _config_with_mandate_llm_enabled(tmp_path, pledge_scope="full_platform")
    journal_path = run_simulation(config, run_id="drift", llm_client=_ElectingFakeLlmClient())
    events = _events(journal_path)
    deviations = [e for e in events if e["event_type"] == "mandate_deviation_recorded"]
    assert deviations
    assert all(e["payload"]["deviation"] > config.mandate.deviation_log_threshold for e in deviations)
    pledges = [e for e in events if e["event_type"] == "mandate_pledge_declared"]
    assert pledges
    # pledged_platform is never touched by representative_response -- every
    # pledge event's platform is a fresh 20-dim vector from election time,
    # never itself drifting across a term.
    assert all(len(p["payload"]["pledged_platform"]) == config.citizens.issue_count for p in pledges)


def test_representative_response_precedes_the_rest_of_the_tick(tmp_path):
    config = _config_with_mandate_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="ordering", llm_client=_ElectingFakeLlmClient())
    events = _events(journal_path)
    for tick in {e["tick"] for e in events}:
        tick_events = [e for e in events if e["tick"] == tick]
        types = [e["event_type"] for e in tick_events]
        if "representative_response" in types and "legitimacy_updated" in types:
            assert types.index("representative_response") < types.index("legitimacy_updated")


def test_ctx_mandate_dev_is_the_pre_decision_deviation(tmp_path):
    config = _config_with_legitimacy_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        llm=dataclasses.replace(config.llm, enabled=True),
        mandate=dataclasses.replace(config.mandate, enabled=True),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.pledged_platform = (0.5,)
    holder.revealed_position = (0.5,)

    seen_mandate_devs = []

    class RecordingClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            seen_mandate_devs.append(payload["holders"][0]["ctx"]["mandate_dev"])
            decisions = [
                {"cid": h["cid"], "shifts": [{"dimension": 0, "delta": 0.2}], "stance": 1, "motif": 301}
                for h in payload["holders"]
            ]
            return json.dumps({"decisions": decisions})

    client = RecordingClient()
    with Journal(tmp_path / "t0.jsonl", run_id="t0") as journal:
        _run_accountability_phase([holder], config, journal, tick=0, llm_client=client)
    events_t0 = _events(tmp_path / "t0.jsonl")
    deviation_t0 = next(e["payload"]["deviation"] for e in events_t0 if e["event_type"] == "mandate_deviation_recorded")

    with Journal(tmp_path / "t1.jsonl", run_id="t1") as journal:
        _run_accountability_phase([holder], config, journal, tick=1, llm_client=client)

    assert seen_mandate_devs[0] == 0.0  # tick 0: no drift yet -- pre-decision
    assert seen_mandate_devs[1] == pytest.approx(deviation_t0)  # tick 1 sees tick 0's post-decision deviation


def test_no_representative_response_while_the_presidency_is_vacant(tmp_path):
    config = _config_with_llm_enabled(tmp_path)
    config = dataclasses.replace(config, mandate=dataclasses.replace(config.mandate, enabled=True))

    class VacantClient:
        """Declines every candidacy -- the presidency stays vacant the
        entire run, and no vote_cast/holders call ever happens. Legislative
        elections/coalitions are unaffected (choose_party is deterministic,
        never LLM-gated) -- still need to answer "responders" so a
        contested coalition round doesn't fail schema validation on an
        empty decisions list."""

        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            if "citizens" in payload:
                decisions = [{"cid": c["cid"], "outcome": 0, "motif": 201} for c in payload["citizens"]]
                return json.dumps({"decisions": decisions})
            if "responders" in payload:
                decisions = [{"party_id": r["party_id"], "action": 2, "motif": 504} for r in payload["responders"]]
                return json.dumps({"decisions": decisions})
            decisions = [{"cid": v["cid"], "blank": 1, "ranking": [], "motif": 101} for v in payload.get("voters", [])]
            return json.dumps({"decisions": decisions})

    journal_path = run_simulation(config, run_id="vacant-llm", llm_client=VacantClient())
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "elected"]
    assert not [e for e in events if e["event_type"] == "representative_response"]


def test_two_mandate_llm_runs_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(
        _config_with_mandate_llm_enabled(tmp_path / "a"), run_id="same-run-id", llm_client=_ElectingFakeLlmClient()
    )
    path_b = run_simulation(
        _config_with_mandate_llm_enabled(tmp_path / "b"), run_id="same-run-id", llm_client=_ElectingFakeLlmClient()
    )
    assert path_a.read_bytes() == path_b.read_bytes()


def test_ctx_omits_street_pressure_when_it_is_not_visible_to_the_representative(tmp_path):
    config = _config_with_mandate_llm_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        awakening=dataclasses.replace(config.awakening, enabled=True),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True, visible_to_representative=False),
    )
    journal_path = run_simulation(config, run_id="street-invisible", llm_client=_ElectingFakeLlmClient())
    events = _events(journal_path)
    response_events = [e for e in events if e["event_type"] == "representative_response"]
    assert response_events
    assert all(e["payload"]["ctx"]["street"] is None for e in response_events)


def test_confidence_vote_keep_ratio_decouples_from_mandate_strength_once_the_position_drifts(tmp_path):
    # Lot 5's own test_confidence_vote_keep_ratio_equals_mandate_strength_on_the_deterministic_path
    # stays green UNMODIFIED (it runs with llm.enabled=False) -- this is the
    # LLM-path counterpart, deliberately breaking the identity dt=6 was
    # named for breaking (build_confidence_ballot's own docstring).
    config = _config_with_mandate_llm_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        awakening=dataclasses.replace(config.awakening, enabled=True),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, petition_enabled=True),
        petition=dataclasses.replace(config.petition, enabled=True, signature_threshold=0.05),
    )
    journal_path = run_simulation(config, run_id="decouple", llm_client=_ElectingFakeLlmClient())
    events = _events(journal_path)
    results = [e for e in events if e["event_type"] == "confidence_vote_result"]
    assert results

    mismatches = 0
    for result in results:
        same_tick_updates = [
            e for e in events
            if e["event_type"] == "legitimacy_updated"
            and e["tick"] == result["tick"]
            and e["citizen_id"] == result["citizen_id"]
        ]
        assert same_tick_updates
        if result["payload"]["keep_ratio"] != pytest.approx(same_tick_updates[-1]["payload"]["mandate_strength"]):
            mismatches += 1
    assert mismatches > 0  # the identity deliberately breaks once the position has drifted


def test_llm_batch_misalignment_aborts_the_run_with_no_partial_journal(tmp_path):
    class _ShortClient:
        """Answers candidacy calls in full (so nominees exist to vote on),
        but drops every decision but the first on a vote call -- isolates
        the misalignment failure to cast_votes specifically."""

        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            if "citizens" in payload:
                decisions = [
                    {"cid": c["cid"], "outcome": 1, "motif": 203}
                    if c["ambition_score"] >= 0.1
                    else {"cid": c["cid"], "outcome": 0, "motif": 201}
                    for c in payload["citizens"]
                ]
                return json.dumps({"decisions": decisions})
            if "parties" in payload:
                decisions = [
                    {
                        "party_id": p["party_id"],
                        "winner_position": max(p["candidates"], key=lambda c: c["ambition_score"])["position"],
                        "motif": 206,
                    }
                    for p in payload["parties"]
                ]
                return json.dumps({"decisions": decisions})
            if "nominees" in payload:
                decisions = [{"cid": n["cid"], "shifts": [], "motif": 601} for n in payload["nominees"]]
                return json.dumps({"decisions": decisions})
            first = payload["voters"][0]
            return json.dumps({"decisions": [{"cid": first["cid"], "blank": 1, "ranking": [], "motif": 101}]})

    config = _config_with_llm_enabled(tmp_path)
    with pytest.raises(LlmResponseError, match="misaligned"):
        run_simulation(config, run_id="r", llm_client=_ShortClient())


# ── pressure_action (v4 Lot 7, dt=10) ────────────────────────────────────

def _config_with_awakening_llm_enabled(output_dir, **overrides) -> PolityConfig:
    config = _config_with_llm_enabled(output_dir)
    config = dataclasses.replace(config, legitimacy=dataclasses.replace(config.legitimacy, enabled=True))
    config = dataclasses.replace(config, candidacy=dataclasses.replace(config.candidacy, ambition_threshold=0.0))
    return dataclasses.replace(config, awakening=dataclasses.replace(config.awakening, enabled=True, **overrides))


def _config_with_full_menu_llm_enabled(output_dir) -> PolityConfig:
    config = _config_with_awakening_llm_enabled(output_dir)
    return dataclasses.replace(
        config,
        pressure_menu=dataclasses.replace(
            config.pressure_menu, electoral_only=False, petition_enabled=True, mobilization_enabled=True
        ),
        petition=dataclasses.replace(config.petition, enabled=True),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True),
    )


def _pressure_test_citizen(cid, base_threshold=0.0):
    return Citizen(
        citizen_id=cid, issue_positions=(0.0,), issue_priorities=(1.0,), blank_threshold=0.0,
        ambition_score=0.5, base_threshold=base_threshold,
    )


def test_llm_enabled_without_awakening_emits_no_pressure_action_events(tmp_path):
    # awakening.enabled stays at its shipped False -- this is also why the
    # existing LLM byte-identical tests need no edit.
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-no-awakening", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "pressure_action"]


def test_awakening_without_the_llm_still_uses_the_deterministic_baseline(tmp_path):
    config = _config_with_awakening_enabled_and_guaranteed_winners(tmp_path)
    journal_path = run_simulation(config, run_id="awakening-no-llm")
    events = _events(journal_path)
    pressure_events = [e for e in events if e["event_type"] == "pressure_action"]
    assert pressure_events
    for e in pressure_events:
        assert set(e["payload"].keys()) == {"target", "act"}  # byte-identical to Lot 4's shape, no ctx
        assert e["motif"] is None
        assert e["codebook_version"] == ""


def test_pressure_action_is_journalled_once_per_consulted_citizen_with_its_ctx(tmp_path):
    config = _config_with_awakening_llm_enabled(tmp_path)
    config = dataclasses.replace(
        config, pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True)
    )
    journal_path = run_simulation(config, run_id="dt10", llm_client=_ElectingFakeLlmClient())
    events = _events(journal_path)
    pressure_events = [e for e in events if e["event_type"] == "pressure_action"]
    assert pressure_events
    for e in pressure_events:
        assert set(e["payload"].keys()) == {"target", "act", "ctx"}
        assert set(e["payload"]["ctx"].keys()) == {"self_gap", "mandate_dev", "neighbors_acting", "ticks_to_election"}
        assert e["payload"]["ctx"]["neighbors_acting"] is None
        assert e["motif"] == "301"
        assert e["codebook_version"] == config.llm.codebook_version
    for tick in {e["tick"] for e in pressure_events}:
        cids = [e["citizen_id"] for e in pressure_events if e["tick"] == tick]
        assert cids == sorted(cids)


def test_a_second_launch_in_the_same_tick_is_journaled_as_act_2_then_petition_signed(tmp_path):
    # DoD, the central judgment call: a frozen batch call vs LIVE petition
    # state. Every consulted citizen decides LAUNCH (act=2); under
    # concurrent_allowed=false, only the lowest-cid citizen's launch can
    # actually succeed -- every later citizen's decided act=2 must be
    # downgraded by applicable_pressure_act to a signature.
    config = _config_with_petition_enabled(tmp_path)
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.revealed_position = (0.5,)
    citizens = [holder] + [_pressure_test_citizen(i) for i in range(1, 4)]

    class AllLaunchClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            decisions = [
                {"cid": c["cid"], "target": c["target"], "act": 2, "motif": 301} for c in payload["consulted"]
            ]
            return json.dumps({"decisions": decisions})

    journal_path = tmp_path / "collision.jsonl"
    with Journal(journal_path, run_id="collision") as journal:
        _run_accountability_phase(citizens, config, journal, tick=0, llm_client=AllLaunchClient())
    events = _events(journal_path)

    launches = [e for e in events if e["event_type"] == "petition_launched"]
    signs = [e for e in events if e["event_type"] == "petition_signed"]
    assert len(launches) == 1
    assert launches[0]["citizen_id"] == 1  # lowest consulted citizen_id
    assert len(signs) == 2  # citizens 2 and 3, downgraded

    pressure_events = [e for e in events if e["event_type"] == "pressure_action"]
    assert all(e["payload"]["act"] == 2 for e in pressure_events)  # decided act, never rewritten
    for i, e in enumerate(events):
        if e["event_type"] == "pressure_action" and e["citizen_id"] != 1:
            assert events[i + 1]["event_type"] == "petition_signed"
            assert events[i + 1]["citizen_id"] == e["citizen_id"]

    assert holder.petition_signers == {1, 2, 3}


def test_an_out_of_menu_act_aborts_the_run_with_no_partial_journal(tmp_path):
    config = _config_with_awakening_llm_enabled(tmp_path)  # shipped electoral_only menu, legal={0,4}

    class OutOfMenuClient(_ElectingFakeLlmClient):
        def _pressure_decisions(self, consulted):
            return [{"cid": c["cid"], "target": c["target"], "act": 3, "motif": 301} for c in consulted]

    with pytest.raises(LlmResponseError, match="outside the active"):
        run_simulation(config, run_id="out-of-menu", llm_client=OutOfMenuClient())


def test_a_stale_sign_does_not_abort_the_run(tmp_path):
    # The two-tier split proven end to end: act=1 is menu-legal but
    # unsatisfiable live (no petition open, target still in cooldown) --
    # validate_pressure_decision does not reject it; applicable_pressure_act
    # downgrades it to NOTHING instead of aborting the whole batch.
    config = _config_with_petition_enabled(tmp_path)
    config = dataclasses.replace(config, llm=dataclasses.replace(config.llm, enabled=True))
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.revealed_position = (0.5,)
    holder.petition_cooldown_until_tick = 100  # still cooling down: can_launch is False
    citizen = _pressure_test_citizen(1)

    class AlwaysSignClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            decisions = [
                {"cid": c["cid"], "target": c["target"], "act": 1, "motif": 301} for c in payload["consulted"]
            ]
            return json.dumps({"decisions": decisions})

    journal_path = tmp_path / "stale.jsonl"
    with Journal(journal_path, run_id="stale") as journal:
        _run_accountability_phase([holder, citizen], config, journal, tick=0, llm_client=AlwaysSignClient())
    events = _events(journal_path)
    pressure_events = [e for e in events if e["event_type"] == "pressure_action"]
    assert pressure_events
    assert pressure_events[0]["payload"]["act"] == 1  # decided act, unchanged in the journal
    assert not [e for e in events if e["event_type"] in ("petition_launched", "petition_signed")]
    assert holder.petition_open_since_tick is None


def test_pressure_action_ctx_reflects_this_ticks_revealed_position(tmp_path):
    # The no-lag pin, the symmetric twin of
    # test_representative_response_sees_the_previous_ticks_street_pressure:
    # dt=10 sees THIS tick's revealed_position, including a shift dt=6 just
    # made earlier in the SAME tick.
    config = _config_with_mandate_llm_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        awakening=dataclasses.replace(config.awakening, enabled=True, modulation_amplitude=0.0),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.pledged_platform = (0.5,)
    holder.revealed_position = (0.5,)
    citizen = _pressure_test_citizen(1)

    seen_self_gap = []

    class RecordingClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            if "holders" in payload:
                decisions = [
                    {"cid": h["cid"], "shifts": [{"dimension": 0, "delta": 0.3}], "stance": 1, "motif": 301}
                    for h in payload["holders"]
                ]
                return json.dumps({"decisions": decisions})
            seen_self_gap.append(payload["consulted"][0]["ctx"]["self_gap"])
            decisions = [
                {"cid": c["cid"], "target": c["target"], "act": 3, "motif": 301} for c in payload["consulted"]
            ]
            return json.dumps({"decisions": decisions})

    with Journal(tmp_path / "tick0.jsonl", run_id="t0") as journal:
        _run_accountability_phase([holder, citizen], config, journal, tick=0, llm_client=RecordingClient())

    # dt=6 shifted holder.revealed_position by +0.3 (0.5 -> 0.8) THIS tick,
    # before dt=10 ran -- ctx.self_gap must reflect 0.8, not the stale 0.5.
    assert holder.revealed_position[0] == pytest.approx(0.8)
    expected_gap = abs(citizen.issue_positions[0] - holder.revealed_position[0])
    assert seen_self_gap[0] == pytest.approx(expected_gap)


def test_pressure_action_ctx_never_carries_street_pressure(tmp_path):
    # The asymmetry with dt=6 asserted, not just implemented: the same run's
    # representative_response.ctx.street is populated while
    # pressure_action's ctx never contains a street-pressure key at all.
    config = _config_with_mandate_llm_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        awakening=dataclasses.replace(config.awakening, enabled=True),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True, visible_to_representative=True),
    )
    journal_path = run_simulation(config, run_id="no-street-leak", llm_client=_ElectingFakeLlmClient())
    events = _events(journal_path)
    pressure_events = [e for e in events if e["event_type"] == "pressure_action"]
    response_events = [e for e in events if e["event_type"] == "representative_response"]
    assert pressure_events
    assert response_events
    assert any(e["payload"]["ctx"]["street"] is not None for e in response_events)
    for e in pressure_events:
        assert set(e["payload"]["ctx"].keys()) == {"self_gap", "mandate_dev", "neighbors_acting", "ticks_to_election"}


def test_two_awakening_llm_runs_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(
        _config_with_awakening_llm_enabled(tmp_path / "a"), run_id="same-run-id", llm_client=_ElectingFakeLlmClient()
    )
    path_b = run_simulation(
        _config_with_awakening_llm_enabled(tmp_path / "b"), run_id="same-run-id", llm_client=_ElectingFakeLlmClient()
    )
    assert path_a.read_bytes() == path_b.read_bytes()


def test_two_full_menu_llm_runs_produce_byte_identical_journals(tmp_path):
    path_a = run_simulation(
        _config_with_full_menu_llm_enabled(tmp_path / "a"), run_id="same-run-id", llm_client=_ElectingFakeLlmClient()
    )
    path_b = run_simulation(
        _config_with_full_menu_llm_enabled(tmp_path / "b"), run_id="same-run-id", llm_client=_ElectingFakeLlmClient()
    )
    assert path_a.read_bytes() == path_b.read_bytes()


def test_llm_pressure_actions_reach_every_menu_modality(tmp_path):
    # Unlike the shared _FakeLlmClient's fixed sign>launch>mobilize>wait
    # priority order -- which under a full menu never lets act 0 or 4 win,
    # since MOBILIZE is always reachable first -- this fake varies its
    # preference by cid so a full-menu run exercises every PressureAct.
    class AllActsClient(_ElectingFakeLlmClient):
        def _pressure_decisions(self, consulted):
            decisions = []
            for c in consulted:
                available = c["available"]
                preferred = c["cid"] % 5
                act = preferred if preferred in available else next(iter(available))
                decisions.append({"cid": c["cid"], "target": c["target"], "act": act, "motif": 301})
            return decisions

    config = _config_with_full_menu_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="full-menu-llm", llm_client=AllActsClient())
    events = _events(journal_path)
    pressure_events = [e for e in events if e["event_type"] == "pressure_action"]
    assert pressure_events
    acts = {e["payload"]["act"] for e in pressure_events}
    assert acts == {0, 1, 2, 3, 4}


def test_street_pressure_counts_llm_mobilize_decisions(tmp_path):
    config = _config_with_legitimacy_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        llm=dataclasses.replace(config.llm, enabled=True),
        awakening=dataclasses.replace(config.awakening, enabled=True, modulation_amplitude=0.0),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True),
        street_pressure=dataclasses.replace(config.street_pressure, enabled=True),
        run=dataclasses.replace(config.run, population_size=4),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.revealed_position = (0.5,)
    citizens = [holder] + [_pressure_test_citizen(i) for i in range(1, 4)]

    class MobilizeClient:
        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            decisions = [
                {"cid": c["cid"], "target": c["target"], "act": 3, "motif": 301} for c in payload["consulted"]
            ]
            return json.dumps({"decisions": decisions})

    journal_path = tmp_path / "mobilize.jsonl"
    with Journal(journal_path, run_id="mobilize") as journal:
        _run_accountability_phase(citizens, config, journal, tick=0, llm_client=MobilizeClient())

    expected = update_street_pressure(0.0, mobilization_rate(3, 4), config.street_pressure)
    assert holder.street_pressure == pytest.approx(expected)


def test_no_pressure_action_llm_call_while_the_presidency_is_vacant(tmp_path):
    # Shipped ambition_threshold never produces a winner -- the presidency
    # stays vacant, so decide_pressure_actions must never even be called.
    config = _config_with_llm_enabled(tmp_path)
    config = dataclasses.replace(config, awakening=dataclasses.replace(config.awakening, enabled=True))

    class RecordingVacantClient(_FakeLlmClient):
        def __init__(self):
            self.pressure_calls = 0

        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            if "consulted" in payload:
                self.pressure_calls += 1
            return super().complete_json(
                system_prompt=system_prompt, user_prompt=user_prompt, json_schema=json_schema,
                max_tokens=max_tokens, think=think,
            )

    client = RecordingVacantClient()
    journal_path = run_simulation(config, run_id="vacant-dt10", llm_client=client)
    events = _events(journal_path)
    assert not [e for e in events if e["event_type"] == "elected"]
    assert not [e for e in events if e["event_type"] == "pressure_action"]
    assert client.pressure_calls == 0


def test_a_cohort_of_one_still_produces_a_single_call(tmp_path):
    # The small-cohort path MIN_SAFE_BATCH_SIZE's default floor would have
    # aborted -- exercised through the real wiring, not just chunk_voters
    # directly.
    config = _config_with_legitimacy_enabled(tmp_path)
    config = dataclasses.replace(
        config,
        llm=dataclasses.replace(config.llm, enabled=True),
        awakening=dataclasses.replace(config.awakening, enabled=True, modulation_amplitude=0.0),
        pressure_menu=dataclasses.replace(config.pressure_menu, electoral_only=False, mobilization_enabled=True),
    )
    holder = _legitimacy_test_citizen(0, legitimacy_capital=0.9, mandate_strength_value=0.9)
    holder.revealed_position = (0.5,)
    citizen = _pressure_test_citizen(1)

    class RecordingClient:
        def __init__(self):
            self.calls = 0

        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            self.calls += 1
            payload = json.loads(user_prompt)
            decisions = [
                {"cid": c["cid"], "target": c["target"], "act": 3, "motif": 301} for c in payload["consulted"]
            ]
            return json.dumps({"decisions": decisions})

    client = RecordingClient()
    journal_path = tmp_path / "cohort_one.jsonl"
    with Journal(journal_path, run_id="cohort-one") as journal:
        _run_accountability_phase([holder, citizen], config, journal, tick=0, llm_client=client)
    assert client.calls == 1
    events = _events(journal_path)
    assert [e for e in events if e["event_type"] == "pressure_action"]


# ── LLM candidacy path (v2 increment 2) ──────────────────────────────────

def test_llm_path_journals_candidacy_considered_for_every_evaluated_citizen(tmp_path):
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-candidacy", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    considered_events = [e for e in events if e["event_type"] == "candidacy_considered"]
    # One candidacy_considered event per citizen per presidential election
    # (8 in the default calendar) -- including the citizens who declined,
    # which the deterministic baseline never journals at all.
    assert len(considered_events) == config.run.population_size * 8
    assert all(e["payload"]["path"] == "dominant" for e in considered_events)
    assert all(e["codebook_version"] == config.llm.codebook_version for e in considered_events)
    assert {e["payload"]["outcome"] for e in considered_events} == {0, 1}


def test_llm_path_journals_candidacy_declared_only_for_outcome_one(tmp_path):
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-candidacy-declared", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    declared_cids = {
        e["citizen_id"] for e in events if e["event_type"] == "candidacy_declared" and e["payload"].get("path") == "dominant"
    }
    considered_declared_cids = {
        e["citizen_id"] for e in events if e["event_type"] == "candidacy_considered" and e["payload"]["outcome"] == 1
    }
    assert declared_cids.issubset(considered_declared_cids)


def test_llm_path_journals_nomination_lost_for_declared_but_unpicked_citizens(tmp_path):
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-nomination-lost", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    lost_events = [e for e in events if e["event_type"] == "nomination_lost"]
    assert len(lost_events) > 0  # default config has multiple ambitious members per party most ticks
    considered_declared_cids = {
        e["citizen_id"] for e in events if e["event_type"] == "candidacy_considered" and e["payload"]["outcome"] == 1
    }
    # Every lost citizen was genuinely LLM-approved (outcome=1) at some
    # point, and never also the party's chosen nominee in that same tick.
    assert set(e["citizen_id"] for e in lost_events).issubset(considered_declared_cids)
    for event in lost_events:
        assert event["citizen_id"] not in {
            e["citizen_id"]
            for e in events
            if e["event_type"] == "candidacy_declared" and e["tick"] == event["tick"]
        }


# ── LLM party-nomination path (v2 increment 3) ───────────────────────────

def test_llm_path_journals_party_nomination_choice_only_for_contested_parties(tmp_path):
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-party-nomination", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    nomination_events = [e for e in events if e["event_type"] == "party_nomination_choice"]
    # Default config + _FakeLlmClient's 0.1 ambition cutoff already produces
    # nomination_lost events (see the test above) -- proof some party is
    # contested most ticks, so this event must appear too.
    assert len(nomination_events) > 0
    for event in nomination_events:
        assert event["codebook_version"] == config.llm.codebook_version
        assert event["motif"] == "206"
        assert len(event["payload"]["contenders"]) >= 2
        assert event["citizen_id"] in event["payload"]["contenders"]

    declared = {
        (e["tick"], e["citizen_id"])
        for e in events
        if e["event_type"] == "candidacy_declared" and e["payload"].get("path") == "dominant"
    }
    for event in nomination_events:
        # Every contested party's LLM-chosen winner is also the tick's
        # candidacy_declared nominee -- decide_party_nominations' output
        # actually drives who runs, not just an unused side record.
        assert (event["tick"], event["citizen_id"]) in declared


# ── LLM campaign-positioning path (v2 increment 4) ───────────────────────

def test_llm_path_journals_campaign_positioning_once_per_dominant_nominee(tmp_path):
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-campaign-positioning", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    positioning_events = [e for e in events if e["event_type"] == "campaign_positioning"]
    declared_dominant = [
        e for e in events if e["event_type"] == "candidacy_declared" and e["payload"].get("path") == "dominant"
    ]
    assert len(positioning_events) > 0
    assert len(positioning_events) == len(declared_dominant)
    for event in positioning_events:
        assert event["codebook_version"] == config.llm.codebook_version
        assert event["motif"] == "602"
        # Non-empty shifts (the fake always shifts dimension 0 by +0.1) is
        # the observable proxy for a real pledged_platform change -- the
        # actual position math (apply_shifts) is unit-tested separately.
        assert event["payload"]["shifts"] == [{"dimension": 0, "delta": 0.1}]

    # Positioning fires for exactly the same (tick, nominee) pairs that get
    # declared dominant -- confirms rupture candidates are excluded (they're
    # never part of `nominees` when this runs) and every dominant nominee is
    # covered, not just a subset.
    declared_ticks_and_cids = {(e["tick"], e["citizen_id"]) for e in declared_dominant}
    positioning_ticks_and_cids = {(e["tick"], e["citizen_id"]) for e in positioning_events}
    assert positioning_ticks_and_cids == declared_ticks_and_cids


# ── LLM coalition path (v2 increment 5) ──────────────────────────────────

def test_llm_path_journals_coalition_decision_per_seated_non_initiator_party(tmp_path):
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-coalition", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    decision_events = [e for e in events if e["event_type"] == "coalition_decision"]
    aggregate_events = [e for e in events if e["event_type"] in ("coalition_formed", "coalition_failed")]

    assert len(aggregate_events) == 8  # one per legislative election, same as the deterministic baseline
    assert len(decision_events) > 0  # default 5-party config produces contested legislative ticks

    for event in decision_events:
        assert event["codebook_version"] == config.llm.codebook_version
        assert event["motif"] == "501"
        assert event["payload"]["action"] == 1
        assert "initiator" in event["payload"]
        assert "party_id" in event["payload"]


def test_llm_path_aggregate_coalition_payload_shape_is_unchanged(tmp_path):
    # metrics.py's is_cohabitation/coalition_lifespans read payload["coalition"]
    # as a plain list[int] | None -- this must never change shape, on either
    # path, or those consumers break silently.
    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-coalition-shape", llm_client=_FakeLlmClient())
    events = _events(journal_path)
    aggregate_events = [e for e in events if e["event_type"] in ("coalition_formed", "coalition_failed")]
    assert aggregate_events
    for event in aggregate_events:
        assert set(event["payload"].keys()) == {"coalition", "seats"}
        assert event["payload"]["coalition"] is None or isinstance(event["payload"]["coalition"], list)


def test_deterministic_path_emits_no_coalition_decision_events(tmp_path):
    journal_path = run_simulation(_config_with_output_dir(tmp_path), run_id="baseline-coalition")
    events = _events(journal_path)
    assert [e for e in events if e["event_type"] == "coalition_decision"] == []
    aggregate_events = [e for e in events if e["event_type"] in ("coalition_formed", "coalition_failed")]
    assert len(aggregate_events) == 8
    for event in aggregate_events:
        assert set(event["payload"].keys()) == {"coalition", "seats"}


def test_llm_path_all_decline_produces_coalition_failed(tmp_path):
    class _AllDeclineClient:
        """Same dispatch as _FakeLlmClient for every decision type except
        coalition, where every responder refuses -- isolates
        assemble_coalition's all-decline None contract inside a full run."""

        def complete_json(self, *, system_prompt, user_prompt, json_schema, max_tokens, think=True):
            payload = json.loads(user_prompt)
            if "citizens" in payload:
                decisions = [
                    {"cid": c["cid"], "outcome": 1, "motif": 203}
                    if c["ambition_score"] >= 0.1
                    else {"cid": c["cid"], "outcome": 0, "motif": 201}
                    for c in payload["citizens"]
                ]
                return json.dumps({"decisions": decisions})
            if "parties" in payload:
                decisions = [
                    {
                        "party_id": p["party_id"],
                        "winner_position": max(p["candidates"], key=lambda c: c["ambition_score"])["position"],
                        "motif": 206,
                    }
                    for p in payload["parties"]
                ]
                return json.dumps({"decisions": decisions})
            if "nominees" in payload:
                decisions = [{"cid": n["cid"], "shifts": [], "motif": 601} for n in payload["nominees"]]
                return json.dumps({"decisions": decisions})
            if "responders" in payload:
                decisions = [{"party_id": r["party_id"], "action": 2, "motif": 504} for r in payload["responders"]]
                return json.dumps({"decisions": decisions})
            decisions = [{"cid": v["cid"], "blank": 1, "ranking": [], "motif": 101} for v in payload["voters"]]
            return json.dumps({"decisions": decisions})

    config = _config_with_llm_enabled(tmp_path)
    journal_path = run_simulation(config, run_id="llm-coalition-all-decline", llm_client=_AllDeclineClient())
    events = _events(journal_path)
    decision_events = [e for e in events if e["event_type"] == "coalition_decision"]
    assert decision_events  # confirms responders were actually asked at least once
    assert all(e["payload"]["action"] == 2 for e in decision_events)
    failed_events = [e for e in events if e["event_type"] == "coalition_failed"]
    assert len(failed_events) > 0
    for event in failed_events:
        assert event["payload"]["coalition"] is None


def test_two_llm_coalition_runs_with_the_same_seed_produce_byte_identical_journals(tmp_path):
    config_a = _config_with_llm_enabled(tmp_path / "a")
    config_b = _config_with_llm_enabled(tmp_path / "b")
    path_a = run_simulation(config_a, run_id="same-run-id", llm_client=_FakeLlmClient())
    path_b = run_simulation(config_b, run_id="same-run-id", llm_client=_FakeLlmClient())
    assert path_a.read_bytes() == path_b.read_bytes()


def test_unsupported_presidential_method_raises_before_any_work(tmp_path):
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(
        config, institutions=dataclasses.replace(config.institutions, presidential_method="star")
    )
    with pytest.raises(NotImplementedError, match="star"):
        run_simulation(config, run_id="r")
    assert not (tmp_path / "r").exists()
