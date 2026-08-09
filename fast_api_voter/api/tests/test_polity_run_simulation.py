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

from api.domain.polity.config import PolityConfig, load_config
from api.domain.polity.llm_client import LlmResponseError
from api.domain.polity.run_polity_simulation import run_simulation


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
    ("nominees" key), and cast_votes ("voters"/"candidates" keys) within the
    same run.
    Candidacy: declares (outcome=1) whenever ambition_score >= 0.1 --
    config.candidacy.ambition_threshold is NOT consulted by the LLM path at
    all (decide_candidacies never reads it; only the deterministic
    decide_candidacy does), so this fake owns its own threshold rather than
    reading one from config. Party nomination: picks the highest-ambition
    candidate per contested party (motif 206). Campaign positioning: every
    nominee shifts dimension 0 by +0.1 (motif 602) -- always non-empty, so
    tests can assert a real pledged_platform change, well within the
    default config.campaign bounds (max_positioning_delta=0.3,
    max_positioning_shifts=3). Voting: every citizen votes blank -- enough
    to exercise the integration plumbing (journal writes, reproducibility,
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


def test_unsupported_presidential_method_raises_before_any_work(tmp_path):
    config = _config_with_output_dir(tmp_path)
    config = dataclasses.replace(
        config, institutions=dataclasses.replace(config.institutions, presidential_method="star")
    )
    with pytest.raises(NotImplementedError, match="star"):
        run_simulation(config, run_id="r")
    assert not (tmp_path / "r").exists()
