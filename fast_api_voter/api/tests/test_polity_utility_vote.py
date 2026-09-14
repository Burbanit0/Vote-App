"""S4.1: the utility ballot (docs/adr/ADR-011-utility-vote-with-turnout.md). First accepted
when every new term at zero reproduces build_ranking exactly -- the property below."""
from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import api.domain.polity.run_polity_simulation as engine
from api.domain.polity.checkpoint import load_checkpoint
from api.domain.polity.citizen import Citizen
from api.domain.polity.config import PolityConfig, VoteConfig, load_config
from api.domain.polity.journal import Journal
from api.domain.polity.parties import Party
from api.domain.polity.run_polity_simulation import audit_sample, run_simulation
from api.domain.polity.simple_rules import (
    BLANK_LABEL,
    IncumbentRecord,
    abstains,
    build_ranking,
    candidate_label,
    incumbent_record,
    utility_ballot,
)
from api.domain.polity.tick_state import PendingRerun
from api.tests.polity_golden import golden_config
from api.tests.test_polity_run_simulation import (
    _config_with_legitimacy_enabled_and_guaranteed_winners,
    _ElectingFakeLlmClient,
    _events,
    _SimulatedCrash,
)

ZERO = VoteConfig(mode="utility", audit_fraction=0.0, partisanship=0.0, approval=0.0, approval_party_carryover=0.0,
                  valence=0.0, turnout_cost=0.0)


def _citizen(cid: int, positions: tuple[float, ...], priorities: tuple[float, ...], threshold: float = 0.5,
             party: int | None = None, candidate: bool = False) -> Citizen:
    citizen = Citizen(citizen_id=cid, issue_positions=positions, issue_priorities=priorities, blank_threshold=threshold,
                      ambition_score=0.5, party_affiliation=party)
    if candidate:
        citizen.pledged_platform = positions
        citizen.revealed_position = positions
    return citizen


@st.composite
def _electorates(draw: st.DrawFn) -> tuple[Citizen, list[Citizen], IncumbentRecord | None, dict[int, float]]:
    issues = draw(st.integers(1, 5))
    unit = st.floats(0.0, 1.0, allow_nan=False)
    raw_priorities = draw(st.lists(st.floats(0.01, 1.0), min_size=issues, max_size=issues))
    priorities = tuple(p / sum(raw_priorities) for p in raw_priorities)
    party = st.one_of(st.none(), st.integers(0, 3))
    voter = _citizen(0, tuple(draw(st.lists(unit, min_size=issues, max_size=issues))), priorities,
                     threshold=draw(unit), party=draw(party))
    ids = draw(st.lists(st.integers(1, 60), min_size=1, max_size=8, unique=True))
    # Duplicate platforms on purpose: distance ties are where an ordering rule can differ.
    platforms = draw(st.lists(st.lists(unit, min_size=issues, max_size=issues), min_size=1, max_size=3))
    candidates = [_citizen(cid, tuple(platforms[i % len(platforms)]), priorities, party=draw(party), candidate=True)
                  for i, cid in enumerate(ids)]
    incumbent = draw(st.one_of(st.none(), st.builds(IncumbentRecord, st.sampled_from(ids), party, st.floats(-1.0, 1.0))))
    valence = {cid: draw(st.floats(-1.0, 1.0)) for cid in ids}
    return voter, candidates, incumbent, valence


@settings(max_examples=400, deadline=None)
@given(_electorates())
def test_with_every_term_at_zero_the_utility_ballot_is_build_rankings_ballot(electorate: tuple) -> None:
    voter, candidates, incumbent, valence = electorate
    assert utility_ballot(voter, candidates, ZERO, incumbent=incumbent, valence=valence) == build_ranking(voter, candidates)


def _field() -> tuple[Citizen, Citizen, Citizen]:
    voter = _citizen(0, (0.5,), (1.0,), threshold=0.3, party=1)
    near = _citizen(1, (0.45,), (1.0,), party=2, candidate=True)     # distance 0.05
    further = _citizen(2, (0.65,), (1.0,), party=1, candidate=True)  # distance 0.15
    return voter, near, further


def test_partisanship_can_carry_a_voters_own_party_past_a_nearer_rival() -> None:
    voter, near, further = _field()
    assert utility_ballot(voter, [near, further], ZERO)[0] == candidate_label(near)
    assert utility_ballot(voter, [near, further], dataclasses.replace(ZERO, partisanship=0.2))[0] == candidate_label(further)


def test_a_poor_record_costs_the_incumbent_and_some_of_it_their_party() -> None:
    voter, near, further = _field()
    recalled = IncumbentRecord(citizen_id=near.citizen_id, party=near.party_affiliation, record=-1.0)
    vote = dataclasses.replace(ZERO, approval=0.4)
    # near: -0.05 - 0.4 = -0.45, below the voter's -0.3 blank line
    assert utility_ballot(voter, [near, further], vote, incumbent=recalled) == [candidate_label(further), BLANK_LABEL, candidate_label(near)]
    party_mate = _citizen(3, (0.46,), (1.0,), party=2, candidate=True)
    carried = dataclasses.replace(vote, approval_party_carryover=0.5)
    assert utility_ballot(voter, [party_mate, further], carried, incumbent=recalled)[0] == candidate_label(further)  # -0.04 - 0.2 < -0.15
    assert utility_ballot(voter, [party_mate, further], vote, incumbent=recalled)[0] == candidate_label(party_mate)  # no carryover
    kept = IncumbentRecord(citizen_id=further.citizen_id, party=None, record=1.0)
    assert utility_ballot(voter, [near, further], vote, incumbent=kept)[0] == candidate_label(further)


def test_valence_moves_a_candidate() -> None:
    voter, near, further = _field()
    assert utility_ballot(voter, [near, further], dataclasses.replace(ZERO, valence=1.0), valence={further.citizen_id: 0.2})[0] == candidate_label(further)


def test_an_indifferent_voter_abstains_once_turning_out_has_a_cost() -> None:
    voter, near, further = _field()
    tight = _citizen(4, (0.56,), (1.0,), party=3, candidate=True)  # distance 0.06: 0.01 behind `near`
    assert utility_ballot(voter, [near, tight], dataclasses.replace(ZERO, turnout_cost=0.02)) is None
    assert utility_ballot(voter, [near, further], dataclasses.replace(ZERO, turnout_cost=0.02)) is not None  # 0.1 ahead
    assert abstains(voter, [], 0.0) is False
    assert abstains(voter, [-0.3], 0.01) is True  # the only candidate is worth exactly the blank ballot


def test_a_presidents_record_follows_their_legitimacy() -> None:
    president = _citizen(7, (0.5,), (1.0,), party=2)
    president.legitimacy_capital = 0.25
    assert incumbent_record(president) == IncumbentRecord(citizen_id=7, party=2, record=-0.5)
    president.legitimacy_capital = 1.5
    assert incumbent_record(president).record == 1.0


def test_the_shipped_vote_is_the_utility_vote_with_every_weight_at_zero() -> None:
    vote = load_config().vote
    assert (vote.mode, vote.audit_fraction) == ("utility", 0.1)
    assert dataclasses.replace(vote, mode="utility", audit_fraction=0.0) == ZERO


# ── in the engine ─────────────────────────────────────────────────────────

def test_a_run_with_a_model_votes_by_utility_and_audits_a_sample(tmp_path: Path) -> None:
    config = golden_config(tmp_path, llm=True)  # the shipped vote: utility, audit fraction 0.1
    events = _events(run_simulation(config, run_id="audited", llm_client=_ElectingFakeLlmClient()))
    votes = [e for e in events if e["event_type"] == "vote_cast"]
    elections = sorted({e["tick"] for e in events if e["event_type"] in ("elected", "election_no_winner")})
    assert votes and all(v["payload"]["audit"] == 1 for v in votes)
    assert elections and {v["tick"] for v in votes} <= set(elections)
    assert len(votes) < config.run.population_size * len(elections) / 2  # a sample, not the electorate


def test_the_audit_sample_is_a_fixed_share_chosen_without_the_runs_random_streams() -> None:
    config = load_config()
    people = [_citizen(cid, (0.5,), (1.0,)) for cid in range(2000)]
    sample = audit_sample(people, config, tick=16)
    assert 150 < len(sample) < 250 and audit_sample(people, config, tick=16) == sample
    assert audit_sample(people, config, tick=32) != sample
    none = dataclasses.replace(config, vote=dataclasses.replace(config.vote, audit_fraction=0.0))
    every = dataclasses.replace(config, vote=dataclasses.replace(config.vote, audit_fraction=1.0))
    assert audit_sample(people, none, 16) == [] and audit_sample(people, every, 16) == people


def test_the_model_casts_every_ballot_in_llm_mode(tmp_path: Path) -> None:
    config = golden_config(tmp_path, llm=True)
    config = dataclasses.replace(config, vote=dataclasses.replace(config.vote, mode="llm"))
    events = _events(run_simulation(config, run_id="llm-votes", llm_client=_ElectingFakeLlmClient()))
    votes = [e for e in events if e["event_type"] == "vote_cast"]
    assert votes and not any("audit" in v["payload"] for v in votes)


def test_abstentions_are_recorded_on_the_elections_outcome(tmp_path: Path) -> None:
    config = golden_config(tmp_path, llm=False)
    config = dataclasses.replace(config, vote=dataclasses.replace(config.vote, turnout_cost=0.05))
    outcomes = [e for e in _events(run_simulation(config, run_id="turnout")) if e["event_type"] in ("elected", "election_no_winner")]
    assert outcomes and all(o["payload"]["abstained"] > 0 for o in outcomes)


def _config_judging(**vote: float) -> PolityConfig:
    config = load_config()
    return dataclasses.replace(
        config, vote=dataclasses.replace(config.vote, **vote), legitimacy=dataclasses.replace(config.legitimacy, enabled=True),
    )


def test_a_rerun_judges_the_president_its_pending_rerun_carries(tmp_path: Path) -> None:
    # Two identical-platform candidates; the lower citizen id wins a tie -- unless the
    # rerun's incumbent is that candidate and their record costs them.
    config = _config_judging(approval=0.1)
    parties = [Party(party_id=0, platform=(0.5,)), Party(party_id=1, platform=(0.5,))]

    def winner(incumbent_id: int | None) -> int:
        fallen = _citizen(1, (0.5,), (1.0,), party=0)  # fresh each time: an election resets its winner's legitimacy
        fallen.legitimacy_capital = 0.05
        rival = _citizen(2, (0.5,), (1.0,), party=1)
        for candidate in (fallen, rival):
            candidate.ambition_score = 1.0
        electors = [_citizen(cid, (0.5,), (1.0,), threshold=0.9) for cid in range(3, 12)]
        journal_path = tmp_path / f"run-{incumbent_id}.jsonl"
        with Journal(journal_path, run_id="r") as journal:
            engine._hold_presidential_election(
                [fallen, rival, *electors], parties, config, journal, tick=5, llm_client=None,
                pending_rerun=PendingRerun(attempt=1, next_tick=5, barred_candidate_ids=frozenset(), incumbent_id=incumbent_id),
            )
        return next(e["citizen_id"] for e in _events(journal_path) if e["event_type"] == "elected")

    assert winner(None) == 1
    assert winner(1) == 2
    untracked = dataclasses.replace(config, legitimacy=dataclasses.replace(config.legitimacy, enabled=False))
    assert engine._judged_incumbent([_citizen(1, (0.5,), (1.0,))], 1, untracked) is None


def test_an_invalidated_election_carries_the_outgoing_president_into_its_rerun(tmp_path: Path) -> None:
    config = dataclasses.replace(load_config(), institutions=dataclasses.replace(load_config().institutions, blank_vote_competitive=True))
    president = _citizen(9, (0.9,), (1.0,), threshold=0.0)
    president.office = engine.Office.PRESIDENT
    candidate = _citizen(1, (0.5,), (1.0,), threshold=0.0, party=0)
    candidate.ambition_score = 1.0
    electors = [_citizen(cid, (0.0,), (1.0,), threshold=0.0) for cid in range(2, 8)]
    with Journal(tmp_path / "run.jsonl", run_id="r") as journal:
        rerun = engine._hold_presidential_election(
            [president, candidate, *electors], [Party(party_id=0, platform=(0.5,))], config, journal, tick=16, llm_client=None,
        )
    assert rerun is not None and rerun.incumbent_id == 9


def test_a_snap_election_records_the_recalled_president_as_the_one_it_judges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _config_with_legitimacy_enabled_and_guaranteed_winners(tmp_path, recall_floor=0.99)
    config = dataclasses.replace(
        config, run=dataclasses.replace(config.run, duration_years=2, population_size=20),
        institutions=dataclasses.replace(config.institutions, snap_election_on_recall=True, president_term_limit=None),
    )
    real_rupture_phase = engine._attempt_rupture_candidacies

    def crash_at_tick_one(citizens, parties, config, journal, tick, rng, **kwargs):
        if tick == 1:
            raise _SimulatedCrash("stop after the first recall")
        return real_rupture_phase(citizens, parties, config, journal, tick, rng, **kwargs)

    monkeypatch.setattr(engine, "_attempt_rupture_candidacies", crash_at_tick_one)
    with pytest.raises(_SimulatedCrash):
        run_simulation(config, run_id="snap")
    rerun = load_checkpoint(tmp_path / "snap" / "checkpoint.json").state.pending_rerun
    recalled = next(e for e in _events(tmp_path / "snap" / "events.jsonl") if e["event_type"] == "recalled")
    assert rerun is not None and rerun.incumbent_id == recalled["citizen_id"]
