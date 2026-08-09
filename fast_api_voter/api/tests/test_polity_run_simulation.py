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

from api.domain.polity.citizen import Citizen, Office, Role
from api.domain.polity.config import PolityConfig, load_config
from api.domain.polity.journal import Journal
from api.domain.polity.llm_client import LlmResponseError
from api.domain.polity.parties import Party
from api.domain.polity.run_polity_simulation import _hold_presidential_election, run_simulation
from api.domain.polity.simple_rules import declare_candidacy


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
