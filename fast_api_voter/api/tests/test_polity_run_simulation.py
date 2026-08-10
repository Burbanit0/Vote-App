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

from api.domain.polity.citizen import Citizen, Office, Role, generate_population
from api.domain.polity.config import PolityConfig, load_config
from api.domain.polity.journal import Journal
from api.domain.polity.llm_client import LlmResponseError
from api.domain.polity.parties import Party, initialize_parties
from api.domain.polity.run_polity_simulation import (
    _hold_presidential_election,
    _run_accountability_phase,
    run_simulation,
)
from api.domain.polity.simple_rules import assign_party_affiliation, declare_candidacy


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


# ── LLM-enabled path (v2 increments 1-2) ─────────────────────────────────

class _FakeLlmClient:
    """Deterministic fake dispatching on user_prompt shape, since one client
    instance now serves decide_candidacies ("citizens" key),
    decide_party_nominations ("parties" key), decide_campaign_positioning
    ("nominees" key), decide_coalition ("responders" key), and cast_votes
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
    reproducibility test. Voting: every citizen votes blank -- enough to
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
        decisions = [{"cid": v["cid"], "blank": 1, "ranking": [], "motif": 101} for v in payload["voters"]]
        return json.dumps({"decisions": decisions})


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
