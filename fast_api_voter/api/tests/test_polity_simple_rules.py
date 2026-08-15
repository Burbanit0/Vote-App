"""Lot 6 — simple_rules.py: the v0 deterministic vote/candidacy/coalition rules.
Rupture-candidacy tests (v1) added when §2.4's rare path was implemented.

Contract (dev-plan-v0-worktree.md §3, Lot 6): each rule tested in isolation
on hand-constructed cases.
"""
import numpy as np
import pytest

from api.domain.polity.citizen import Citizen, Office, Role
from api.domain.polity.codebook import PressureAct
from api.domain.polity.config import CandidacyConfig, PressureMenuConfig
from api.domain.polity.parties import Party
from api.domain.polity.simple_rules import (
    BLANK_LABEL,
    assign_party_affiliation,
    attempt_rupture_candidacy,
    ballot_ranks_above_blank,
    blank_share,
    build_confidence_ballot,
    build_ranking,
    candidate_label,
    choose_party,
    citizen_id_from_label,
    decide_candidacy,
    declare_candidacy,
    deterministic_pressure_action,
    form_coalition,
    select_party_nominee,
    select_party_nominee_from_declared,
    vacate_office,
)


def _citizen(citizen_id, positions, priorities=None, blank_threshold=0.5, ambition=0.5, **kwargs):
    k = len(positions)
    priorities = priorities or tuple(1.0 / k for _ in range(k))
    return Citizen(
        citizen_id=citizen_id,
        issue_positions=tuple(positions),
        issue_priorities=tuple(priorities),
        blank_threshold=blank_threshold,
        ambition_score=ambition,
        **kwargs,
    )


_CANDIDACY_CONFIG = CandidacyConfig(
    ambition_threshold=0.7,
    independent_signature_ratio=0.01,
    rupture_path_enabled=False,
    rupture_base_probability=0.001,
    rupture_signature_ratio=0.005,
    max_candidates_hard_cap=20,
)


# ── candidate_label / citizen_id_from_label round-trip ──────────────────────

def test_candidate_label_round_trips():
    c = _citizen(42, (0.5, 0.5))
    assert citizen_id_from_label(candidate_label(c)) == 42


# ── assign_party_affiliation ─────────────────────────────────────────────

def test_assigns_nearest_party():
    parties = [Party(0, (0.0, 0.0)), Party(1, (1.0, 1.0))]
    near_zero = _citizen(1, (0.1, 0.1))
    near_one = _citizen(2, (0.9, 0.9))
    assert assign_party_affiliation(near_zero, parties) == 0
    assert assign_party_affiliation(near_one, parties) == 1


def test_assign_party_affiliation_ties_break_on_lowest_party_id():
    parties = [Party(5, (1.0, 0.0)), Party(2, (0.0, 1.0))]
    equidistant = _citizen(1, (0.5, 0.5))
    assert assign_party_affiliation(equidistant, parties) == 2


# ── choose_party ──────────────────────────────────────────────────────────

def test_choose_party_picks_the_nearest_platform():
    parties = [Party(0, (0.0,)), Party(1, (1.0,))]
    voter = _citizen(1, (0.1,), priorities=(1.0,), blank_threshold=1.0)
    assert choose_party(voter, parties) == 0


def test_choose_party_returns_none_when_nearest_exceeds_tolerance():
    parties = [Party(0, (0.0,)), Party(1, (1.0,))]
    voter = _citizen(1, (0.5,), priorities=(1.0,), blank_threshold=0.1)
    assert choose_party(voter, parties) is None


def test_choose_party_ties_break_on_lowest_party_id():
    parties = [Party(5, (1.0,)), Party(2, (0.0,))]
    voter = _citizen(1, (0.5,), priorities=(1.0,), blank_threshold=1.0)
    assert choose_party(voter, parties) == 2


# ── decide_candidacy ──────────────────────────────────────────────────────

def test_decide_candidacy_threshold():
    above = _citizen(1, (0.5,), ambition=0.8)
    exactly_at = _citizen(2, (0.5,), ambition=0.7)
    below = _citizen(3, (0.5,), ambition=0.6)
    assert decide_candidacy(above, _CANDIDACY_CONFIG) is True
    assert decide_candidacy(exactly_at, _CANDIDACY_CONFIG) is True
    assert decide_candidacy(below, _CANDIDACY_CONFIG) is False


def test_decide_candidacy_ignores_the_rupture_path_flag():
    # decide_candidacy is the dominant path only; rupture_path_enabled is
    # attempt_rupture_candidacy's concern, not this function's.
    config = CandidacyConfig(**{**_CANDIDACY_CONFIG.__dict__, "rupture_path_enabled": True})
    assert decide_candidacy(_citizen(1, (0.5,), ambition=0.9), config) is True
    assert decide_candidacy(_citizen(2, (0.5,), ambition=0.1), config) is False


# ── attempt_rupture_candidacy ─────────────────────────────────────────────

def test_attempt_rupture_candidacy_disabled_never_triggers_and_never_draws():
    config = CandidacyConfig(**{**_CANDIDACY_CONFIG.__dict__, "rupture_path_enabled": False})
    citizen = _citizen(1, (0.5,), priorities=(1.0,), blank_threshold=1.0)
    population = [citizen]
    rng = np.random.default_rng(0)
    for _ in range(5):
        assert attempt_rupture_candidacy(citizen, population, config, rng) is False
    # No draw consumed: an untouched rng of the same seed gives the same
    # first value as this one, which was never advanced.
    assert rng.random() == np.random.default_rng(0).random()


def test_attempt_rupture_candidacy_never_triggers_when_probability_is_zero():
    config = CandidacyConfig(
        **{**_CANDIDACY_CONFIG.__dict__, "rupture_path_enabled": True, "rupture_base_probability": 0.0}
    )
    citizen = _citizen(1, (0.5,), priorities=(1.0,), blank_threshold=1.0)
    population = [citizen]
    rng = np.random.default_rng(0)
    assert attempt_rupture_candidacy(citizen, population, config, rng) is False


def test_attempt_rupture_candidacy_requires_the_signature_bar():
    config = CandidacyConfig(
        **{
            **_CANDIDACY_CONFIG.__dict__,
            "rupture_path_enabled": True,
            "rupture_base_probability": 1.0,  # always wins the coin flip
            "rupture_signature_ratio": 0.5,
        }
    )
    citizen = _citizen(1, (0.0,), priorities=(1.0,), blank_threshold=0.01)
    # Only the citizen themself is a sympathizer (distance 0); everyone
    # else is far outside their own tolerance of citizen's position.
    population = [citizen] + [_citizen(i, (1.0,), priorities=(1.0,), blank_threshold=0.01) for i in range(2, 6)]
    rng = np.random.default_rng(0)
    assert attempt_rupture_candidacy(citizen, population, config, rng) is False


def test_attempt_rupture_candidacy_succeeds_when_probability_and_signature_bar_clear():
    config = CandidacyConfig(
        **{
            **_CANDIDACY_CONFIG.__dict__,
            "rupture_path_enabled": True,
            "rupture_base_probability": 1.0,
            "rupture_signature_ratio": 0.5,
        }
    )
    citizen = _citizen(1, (0.5,), priorities=(1.0,), blank_threshold=1.0)
    # Everyone tolerates everyone (blank_threshold=1.0 spans the whole space).
    population = [citizen] + [_citizen(i, (0.0,), priorities=(1.0,), blank_threshold=1.0) for i in range(2, 6)]
    rng = np.random.default_rng(0)
    assert attempt_rupture_candidacy(citizen, population, config, rng) is True


# ── select_party_nominee ──────────────────────────────────────────────────

def test_select_party_nominee_picks_highest_ambition():
    citizens = [
        _citizen(1, (0.5,), ambition=0.9, party_affiliation=0),
        _citizen(2, (0.5,), ambition=0.75, party_affiliation=0),
        _citizen(3, (0.5,), ambition=0.6, party_affiliation=0),  # below threshold
        _citizen(4, (0.5,), ambition=0.95, party_affiliation=1),  # different party
    ]
    nominee = select_party_nominee(0, citizens, _CANDIDACY_CONFIG)
    assert nominee is not None
    assert nominee.citizen_id == 1


def test_select_party_nominee_ties_break_on_lowest_citizen_id():
    citizens = [
        _citizen(7, (0.5,), ambition=0.9, party_affiliation=0),
        _citizen(3, (0.5,), ambition=0.9, party_affiliation=0),
    ]
    nominee = select_party_nominee(0, citizens, _CANDIDACY_CONFIG)
    assert nominee is not None
    assert nominee.citizen_id == 3


def test_select_party_nominee_returns_none_if_nobody_qualifies():
    citizens = [_citizen(1, (0.5,), ambition=0.1, party_affiliation=0)]
    assert select_party_nominee(0, citizens, _CANDIDACY_CONFIG) is None


# ── select_party_nominee_from_declared ────────────────────────────────────

def test_select_party_nominee_from_declared_picks_highest_ambition():
    citizens = [
        _citizen(1, (0.5,), ambition=0.9, party_affiliation=0),
        _citizen(2, (0.5,), ambition=0.75, party_affiliation=0),
        _citizen(3, (0.5,), ambition=0.6, party_affiliation=0),  # not in declared_cids
        _citizen(4, (0.5,), ambition=0.95, party_affiliation=1),  # different party
    ]
    nominee = select_party_nominee_from_declared(0, citizens, declared_cids={1, 2})
    assert nominee is not None
    assert nominee.citizen_id == 1


def test_select_party_nominee_from_declared_ties_break_on_lowest_citizen_id():
    citizens = [
        _citizen(7, (0.5,), ambition=0.9, party_affiliation=0),
        _citizen(3, (0.5,), ambition=0.9, party_affiliation=0),
    ]
    nominee = select_party_nominee_from_declared(0, citizens, declared_cids={7, 3})
    assert nominee is not None
    assert nominee.citizen_id == 3


def test_select_party_nominee_from_declared_returns_none_if_nobody_declared():
    citizens = [_citizen(1, (0.5,), ambition=0.9, party_affiliation=0)]
    assert select_party_nominee_from_declared(0, citizens, declared_cids=set()) is None


def test_select_party_nominee_from_declared_ignores_declared_cids_from_other_parties():
    citizens = [_citizen(1, (0.5,), ambition=0.9, party_affiliation=1)]
    assert select_party_nominee_from_declared(0, citizens, declared_cids={1}) is None


# ── declare_candidacy ─────────────────────────────────────────────────────

def test_declare_candidacy_pins_revealed_position_to_pledged_platform():
    citizen = _citizen(1, (0.2, 0.8))
    declare_candidacy(citizen)
    assert citizen.role == Role.CANDIDATE
    assert citizen.pledged_platform == (0.2, 0.8)
    assert citizen.revealed_position == citizen.pledged_platform


# ── vacate_office ─────────────────────────────────────────────────────────

def test_vacate_office_resets_role_office_and_term_end_tick():
    citizen = _citizen(
        1, (0.5,), role=Role.ELECTED, office=Office.PRESIDENT, term_end_tick=120, mandates_served=2,
        pledged_platform=(0.4,), revealed_position=(0.3,),
    )
    vacate_office(citizen)
    assert citizen.role == Role.ELECTOR
    assert citizen.office == Office.NONE
    assert citizen.term_end_tick is None


def test_vacate_office_leaves_pledged_platform_and_mandates_served_untouched():
    citizen = _citizen(
        1, (0.5,), role=Role.ELECTED, office=Office.PRESIDENT, term_end_tick=120, mandates_served=2,
        pledged_platform=(0.4,), revealed_position=(0.3,),
    )
    vacate_office(citizen)
    assert citizen.mandates_served == 2
    assert citizen.pledged_platform == (0.4,)
    assert citizen.revealed_position == (0.3,)


# ── build_ranking ─────────────────────────────────────────────────────────

def _candidate(citizen_id, platform):
    c = _citizen(citizen_id, platform)
    declare_candidacy(c)
    return c


def test_build_ranking_orders_by_weighted_distance():
    voter = _citizen(1, (0.0, 0.0), priorities=(1.0, 0.0), blank_threshold=1.0)
    near = _candidate(10, (0.1, 0.9))   # weighted distance uses only dim 0: 0.1
    far = _candidate(11, (0.9, 0.0))    # weighted distance: 0.9
    ranking = build_ranking(voter, [far, near])
    # Both candidates are within tolerance, so blank (mirroring
    # simulation_metrics._insert_blank) is present but ranked last.
    assert ranking == [candidate_label(near), candidate_label(far), BLANK_LABEL]


def test_build_ranking_inserts_blank_when_nearest_exceeds_tolerance():
    voter = _citizen(1, (0.0,), priorities=(1.0,), blank_threshold=0.05)
    candidate = _candidate(10, (0.5,))  # distance 0.5 > 0.05 tolerance
    assert build_ranking(voter, [candidate]) == [BLANK_LABEL, candidate_label(candidate)]


def test_build_ranking_ranks_blank_last_when_candidate_is_within_tolerance():
    voter = _citizen(1, (0.0,), priorities=(1.0,), blank_threshold=0.9)
    candidate = _candidate(10, (0.5,))
    assert build_ranking(voter, [candidate]) == [candidate_label(candidate), BLANK_LABEL]


def test_build_ranking_ties_break_on_lowest_citizen_id():
    voter = _citizen(1, (0.0,), priorities=(1.0,), blank_threshold=1.0)
    a = _candidate(9, (0.5,))
    b = _candidate(2, (0.5,))  # same distance as a, lower citizen_id
    assert build_ranking(voter, [a, b]) == [candidate_label(b), candidate_label(a), BLANK_LABEL]


def test_build_ranking_raises_without_a_declared_candidacy():
    voter = _citizen(1, (0.0,), priorities=(1.0,))
    not_a_candidate = _citizen(2, (0.5,))
    with pytest.raises(ValueError, match="not declared a candidacy"):
        build_ranking(voter, [not_a_candidate])


# ── ballot_ranks_above_blank ─────────────────────────────────────────────

def test_ballot_ranks_above_blank_is_true_for_a_within_tolerance_build_ranking_output():
    voter = _citizen(1, (0.0,), priorities=(1.0,), blank_threshold=0.9)
    candidate = _candidate(10, (0.5,))
    ballot = build_ranking(voter, [candidate])
    assert ballot_ranks_above_blank(ballot, candidate_label(candidate)) is True


def test_ballot_ranks_above_blank_is_false_for_a_beyond_tolerance_build_ranking_output():
    voter = _citizen(1, (0.0,), priorities=(1.0,), blank_threshold=0.05)
    candidate = _candidate(10, (0.5,))
    ballot = build_ranking(voter, [candidate])
    assert ballot_ranks_above_blank(ballot, candidate_label(candidate)) is False


def test_ballot_ranks_above_blank_is_false_on_an_all_blank_ballot():
    assert ballot_ranks_above_blank([BLANK_LABEL], "citizen_10") is False


def test_ballot_ranks_above_blank_is_false_when_the_label_is_absent_from_a_truncated_ranking():
    ballot = ["citizen_2", "citizen_3", BLANK_LABEL]
    assert ballot_ranks_above_blank(ballot, "citizen_10") is False


def test_ballot_ranks_above_blank_raises_when_blank_label_is_missing():
    with pytest.raises(ValueError, match="does not contain blank_label"):
        ballot_ranks_above_blank(["citizen_1", "citizen_2"], "citizen_1")


# ── blank_share (v4 Lot 9, §6bis.2) ──────────────────────────────────────

def test_blank_share_all_top_preference_blank_is_one():
    ballots = [[BLANK_LABEL, "citizen_10"], [BLANK_LABEL, "citizen_11"]]
    assert blank_share(ballots) == 1.0


def test_blank_share_no_blank_top_preference_is_zero():
    ballots = [["citizen_10", BLANK_LABEL], ["citizen_11", BLANK_LABEL]]
    assert blank_share(ballots) == 0.0


def test_blank_share_mixed_ballots_computes_the_correct_fraction():
    ballots = [
        [BLANK_LABEL, "citizen_10"],
        ["citizen_10", BLANK_LABEL],
        ["citizen_11", BLANK_LABEL],
        [BLANK_LABEL, "citizen_11"],
    ]
    assert blank_share(ballots) == 0.5


def test_blank_share_raises_on_empty_ballots():
    with pytest.raises(ValueError, match="no ballots cast"):
        blank_share([])


def test_blank_share_raises_when_a_ballot_is_missing_blank_label():
    with pytest.raises(ValueError, match="does not contain blank_label"):
        blank_share([["citizen_1", "citizen_2"]])


def test_blank_share_matches_build_ranking_when_no_candidate_clears_tolerance():
    voter = _citizen(1, (0.0,), priorities=(1.0,), blank_threshold=0.05)
    candidate = _candidate(10, (0.5,))  # distance 0.5 > 0.05 tolerance
    ranking = build_ranking(voter, [candidate])
    assert blank_share([ranking]) == 1.0


# ── form_coalition ────────────────────────────────────────────────────────

_TIEBREAK = ("seats", "votes", "party_id")


def test_form_coalition_adds_nearest_neighbours_until_majority():
    platforms = {0: (0.0, 0.0), 1: (0.1, 0.0), 2: (0.5, 0.5), 3: (1.0, 1.0)}
    seats = {0: 30, 1: 25, 2: 20, 3: 25}
    votes = {0: 30.0, 1: 25.0, 2: 25.0, 3: 20.0}
    coalition = form_coalition(platforms, seats, votes, _TIEBREAK, majority_ratio=0.5)
    assert coalition == [0, 1]  # 30 + 25 = 55 > 50


def test_form_coalition_distance_tie_breaks_on_seats_descending():
    platforms = {0: (0.0,), 1: (0.3,), 2: (0.3,), 3: (0.5,)}
    seats = {0: 40, 1: 20, 2: 15, 3: 25}
    votes = {0: 40.0, 1: 20.0, 2: 15.0, 3: 25.0}
    coalition = form_coalition(platforms, seats, votes, _TIEBREAK, majority_ratio=0.5)
    # Party 1 and 2 are equidistant from the initiator (party 0); party 1
    # has more seats, so it is added first and alone suffices for a majority.
    assert coalition == [0, 1]


def test_form_coalition_initiator_seat_tie_breaks_on_votes():
    platforms = {5: (0.0,), 2: (0.1,), 1: (0.9,)}
    seats = {5: 40, 2: 40, 1: 20}
    votes = {5: 1000.0, 2: 1200.0, 1: 500.0}
    coalition = form_coalition(platforms, seats, votes, _TIEBREAK, majority_ratio=0.5)
    assert coalition[0] == 2  # tied on seats with party 5, but more votes


def test_form_coalition_initiator_full_tie_breaks_on_party_id():
    platforms = {5: (0.0,), 2: (0.1,)}
    seats = {5: 40, 2: 40}
    votes = {5: 1000.0, 2: 1000.0}
    coalition = form_coalition(platforms, seats, votes, _TIEBREAK, majority_ratio=0.5)
    assert coalition[0] == 2  # tied on seats and votes, lowest party_id wins


def test_form_coalition_returns_none_when_majority_is_unreachable():
    platforms = {0: (0.0,), 1: (0.5,)}
    seats = {0: 60, 1: 40}
    votes = {0: 60.0, 1: 40.0}
    # majority_ratio=1.0 demands strictly more than 100% of all seats.
    assert form_coalition(platforms, seats, votes, _TIEBREAK, majority_ratio=1.0) is None


def test_form_coalition_returns_none_when_no_party_has_seats():
    assert form_coalition({0: (0.0,)}, {0: 0}, {0: 0.0}, _TIEBREAK, majority_ratio=0.5) is None


# ── deterministic_pressure_action (v4 Lot 4) ─────────────────────────────

_ELECTORAL_ONLY_MENU = PressureMenuConfig(petition_enabled=False, mobilization_enabled=False, electoral_only=True)
_MOBILIZATION_MENU = PressureMenuConfig(petition_enabled=False, mobilization_enabled=True, electoral_only=False)


def test_electoral_only_below_blank_threshold_is_nothing():
    citizen = _citizen(1, (0.5,), blank_threshold=0.3)
    assert deterministic_pressure_action(citizen, gap=0.1, menu=_ELECTORAL_ONLY_MENU) == PressureAct.NOTHING


def test_electoral_only_at_or_above_blank_threshold_is_wait_for_election():
    citizen = _citizen(1, (0.5,), blank_threshold=0.3)
    assert deterministic_pressure_action(citizen, gap=0.3, menu=_ELECTORAL_ONLY_MENU) == PressureAct.WAIT_FOR_ELECTION
    assert deterministic_pressure_action(citizen, gap=0.9, menu=_ELECTORAL_ONLY_MENU) == PressureAct.WAIT_FOR_ELECTION


def test_electoral_only_never_returns_a_petition_or_mobilize_act():
    for gap in (0.0, 0.1, 0.3, 0.5, 0.9, 1.0):
        citizen = _citizen(1, (0.5,), blank_threshold=0.3)
        act = deterministic_pressure_action(citizen, gap=gap, menu=_ELECTORAL_ONLY_MENU)
        assert act in (PressureAct.NOTHING, PressureAct.WAIT_FOR_ELECTION)


def test_mobilization_below_blank_threshold_is_nothing():
    citizen = _citizen(1, (0.5,), blank_threshold=0.3)
    assert deterministic_pressure_action(citizen, gap=0.1, menu=_MOBILIZATION_MENU) == PressureAct.NOTHING


def test_mobilization_at_or_above_blank_threshold_mobilizes():
    citizen = _citizen(1, (0.5,), blank_threshold=0.3)
    assert deterministic_pressure_action(citizen, gap=0.3, menu=_MOBILIZATION_MENU) == PressureAct.MOBILIZE
    assert deterministic_pressure_action(citizen, gap=0.9, menu=_MOBILIZATION_MENU) == PressureAct.MOBILIZE


_PETITION_ONLY_MENU = PressureMenuConfig(petition_enabled=True, mobilization_enabled=False, electoral_only=False)
_BOTH_MENU = PressureMenuConfig(petition_enabled=True, mobilization_enabled=True, electoral_only=False)


def test_petition_signs_an_open_petition_when_one_is_signable():
    citizen = _citizen(1, (0.5,), blank_threshold=0.3)
    act = deterministic_pressure_action(citizen, gap=0.9, menu=_PETITION_ONLY_MENU, can_sign=True, can_launch=False)
    assert act == PressureAct.SIGN_PETITION


def test_petition_launches_when_none_is_open():
    citizen = _citizen(1, (0.5,), blank_threshold=0.3)
    act = deterministic_pressure_action(citizen, gap=0.9, menu=_PETITION_ONLY_MENU, can_sign=False, can_launch=True)
    assert act == PressureAct.LAUNCH_PETITION


def test_petition_below_blank_threshold_is_still_nothing():
    citizen = _citizen(1, (0.5,), blank_threshold=0.3)
    act = deterministic_pressure_action(citizen, gap=0.1, menu=_PETITION_ONLY_MENU, can_sign=True, can_launch=True)
    assert act == PressureAct.NOTHING


def test_petition_falls_back_to_mobilize_when_no_petition_action_is_available():
    citizen = _citizen(1, (0.5,), blank_threshold=0.3)
    act = deterministic_pressure_action(citizen, gap=0.9, menu=_BOTH_MENU, can_sign=False, can_launch=False)
    assert act == PressureAct.MOBILIZE


def test_petition_falls_back_to_wait_for_election_without_mobilization():
    citizen = _citizen(1, (0.5,), blank_threshold=0.3)
    act = deterministic_pressure_action(
        citizen, gap=0.9, menu=_PETITION_ONLY_MENU, can_sign=False, can_launch=False
    )
    assert act == PressureAct.WAIT_FOR_ELECTION


def test_both_levers_prefer_the_petition_over_mobilization():
    citizen = _citizen(1, (0.5,), blank_threshold=0.3)
    signable = deterministic_pressure_action(citizen, gap=0.9, menu=_BOTH_MENU, can_sign=True, can_launch=False)
    launchable = deterministic_pressure_action(citizen, gap=0.9, menu=_BOTH_MENU, can_sign=False, can_launch=True)
    assert signable == PressureAct.SIGN_PETITION
    assert launchable == PressureAct.LAUNCH_PETITION


def test_petition_facts_are_ignored_when_the_menu_disables_petitions():
    citizen = _citizen(1, (0.5,), blank_threshold=0.3)
    act = deterministic_pressure_action(
        citizen, gap=0.9, menu=_MOBILIZATION_MENU, can_sign=True, can_launch=True
    )
    assert act == PressureAct.MOBILIZE


def test_deterministic_pressure_action_mutates_nothing():
    citizen = _citizen(1, (0.5,), blank_threshold=0.3)
    before = (citizen.role, citizen.office, citizen.blank_threshold)
    deterministic_pressure_action(citizen, gap=0.9, menu=_BOTH_MENU, can_sign=True, can_launch=True)
    assert (citizen.role, citizen.office, citizen.blank_threshold) == before


# ── build_confidence_ballot (v4 Lot 5) ────────────────────────────────────

def test_build_confidence_ballot_keeps_within_the_voters_own_blank_threshold():
    voter = _citizen(1, (0.5,), priorities=(1.0,), blank_threshold=0.3)
    holder = _citizen(2, (0.5,), priorities=(1.0,))
    holder.revealed_position = (0.6,)  # distance 0.1 <= 0.3
    assert build_confidence_ballot(voter, holder) is True


def test_build_confidence_ballot_removes_beyond_it():
    voter = _citizen(1, (0.5,), priorities=(1.0,), blank_threshold=0.1)
    holder = _citizen(2, (0.5,), priorities=(1.0,))
    holder.revealed_position = (0.9,)  # distance 0.4 > 0.1
    assert build_confidence_ballot(voter, holder) is False


def test_build_confidence_ballot_raises_without_a_revealed_position():
    voter = _citizen(1, (0.5,), priorities=(1.0,))
    holder = _citizen(2, (0.5,), priorities=(1.0,))
    with pytest.raises(ValueError, match="revealed_position"):
        build_confidence_ballot(voter, holder)


def test_build_confidence_ballot_agrees_with_ballot_ranks_above_blank_on_the_deterministic_path():
    rng = np.random.default_rng(7)
    holder = _citizen(0, tuple(rng.uniform(0, 1, size=4)), priorities=tuple(rng.dirichlet(np.ones(4))))
    holder.pledged_platform = holder.issue_positions
    holder.revealed_position = holder.issue_positions
    voters = [
        _citizen(
            i,
            tuple(rng.uniform(0, 1, size=4)),
            priorities=tuple(rng.dirichlet(np.ones(4))),
            blank_threshold=float(rng.uniform(0, 1)),
        )
        for i in range(1, 21)
    ]
    for voter in voters:
        ballot = build_ranking(voter, [holder])
        assert build_confidence_ballot(voter, holder) == ballot_ranks_above_blank(ballot, candidate_label(holder))
