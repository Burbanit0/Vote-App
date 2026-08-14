"""codebook.py — the vote-decision slice of design doc §3.7's compression tables.

Contract: the codebook is a frozen, versioned artifact (§3.7.0) — a version
mismatch must be a loud error, and decision_type 7 (retired) must never be
reassigned.
"""
import re

import pytest

from api.domain.polity.codebook import (
    CAMPAIGN_MOTIF_PROMPT_TABLE,
    CANDIDACY_MOTIF_PROMPT_TABLE,
    COALITION_ACTION_PROMPT_TABLE,
    COALITION_MOTIF_PROMPT_TABLE,
    CODEBOOK_VERSION,
    PARTY_NOMINATION_MOTIF_PROMPT_TABLE,
    PRESSURE_ACT_PROMPT_TABLE,
    PRESSURE_MOTIF_PROMPT_TABLE,
    RESPONSE_MOTIF_PROMPT_TABLE,
    STANCE_PROMPT_TABLE,
    VOTE_MOTIF_PROMPT_TABLE,
    BallotFormat,
    CampaignMotif,
    CandidacyMotif,
    CandidacyOutcome,
    CoalitionAction,
    CoalitionMotif,
    DecisionType,
    PartyNominationMotif,
    PolityCodebookError,
    PressureAct,
    PressureMotif,
    ResponseMotif,
    Stance,
    VoteMotif,
    check_codebook_version,
)


def test_check_codebook_version_accepts_the_matching_version():
    check_codebook_version(CODEBOOK_VERSION)  # must not raise


def test_check_codebook_version_rejects_a_mismatch():
    with pytest.raises(PolityCodebookError, match=re.escape(CODEBOOK_VERSION)):
        check_codebook_version("0.9")


def test_decision_type_never_reassigns_the_retired_code_7():
    assert 7 not in {member.value for member in DecisionType}


def test_vote_cast_is_decision_type_1():
    assert DecisionType.VOTE_CAST == 1


def test_candidacy_considered_is_decision_type_2():
    assert DecisionType.CANDIDACY_CONSIDERED == 2


def test_decision_type_does_not_yet_define_candidacy_declared():
    assert 3 not in {member.value for member in DecisionType}


def test_ranking_is_ballot_format_1():
    assert BallotFormat.RANKING == 1


def test_vote_motif_has_exactly_the_five_documented_codes():
    assert {member.value for member in VoteMotif} == {101, 102, 103, 104, 105}


def test_vote_motif_prompt_table_is_derived_from_the_enum_not_hand_typed():
    for motif in VoteMotif:
        assert f"{motif.value} = {motif.name}" in VOTE_MOTIF_PROMPT_TABLE
    assert VOTE_MOTIF_PROMPT_TABLE.count("\n") == len(VoteMotif) - 1


def test_candidacy_outcome_has_exactly_the_two_documented_codes():
    assert {member.value for member in CandidacyOutcome} == {0, 1}


def test_candidacy_motif_never_reuses_the_rupture_paths_code_202():
    assert 202 not in {member.value for member in CandidacyMotif}


def test_candidacy_motif_has_exactly_the_four_documented_codes():
    assert {member.value for member in CandidacyMotif} == {201, 203, 204, 205}


def test_candidacy_motif_prompt_table_is_derived_from_the_enum_not_hand_typed():
    for motif in CandidacyMotif:
        assert f"{motif.value} = {motif.name}" in CANDIDACY_MOTIF_PROMPT_TABLE
    assert CANDIDACY_MOTIF_PROMPT_TABLE.count("\n") == len(CandidacyMotif) - 1


def test_party_nomination_choice_is_decision_type_4():
    assert DecisionType.PARTY_NOMINATION_CHOICE == 4


def test_party_nomination_motif_never_reuses_a_candidacy_motif_code():
    assert {member.value for member in PartyNominationMotif}.isdisjoint(
        {member.value for member in CandidacyMotif}
    )


def test_party_nomination_motif_has_exactly_the_four_documented_codes():
    assert {member.value for member in PartyNominationMotif} == {206, 207, 208, 209}


def test_party_nomination_motif_prompt_table_is_derived_from_the_enum_not_hand_typed():
    for motif in PartyNominationMotif:
        assert f"{motif.value} = {motif.name}" in PARTY_NOMINATION_MOTIF_PROMPT_TABLE
    assert PARTY_NOMINATION_MOTIF_PROMPT_TABLE.count("\n") == len(PartyNominationMotif) - 1


def test_campaign_positioning_is_decision_type_5():
    assert DecisionType.CAMPAIGN_POSITIONING == 5


def test_campaign_motif_occupies_its_own_range_not_the_candidature_block():
    assert {member.value for member in CampaignMotif}.isdisjoint(
        {member.value for member in CandidacyMotif} | {member.value for member in PartyNominationMotif}
    )


def test_campaign_motif_has_exactly_the_four_documented_codes():
    assert {member.value for member in CampaignMotif} == {601, 602, 603, 604}


def test_campaign_motif_prompt_table_is_derived_from_the_enum_not_hand_typed():
    for motif in CampaignMotif:
        assert f"{motif.value} = {motif.name}" in CAMPAIGN_MOTIF_PROMPT_TABLE
    assert CAMPAIGN_MOTIF_PROMPT_TABLE.count("\n") == len(CampaignMotif) - 1


def test_coalition_decision_is_decision_type_9():
    assert DecisionType.COALITION_DECISION == 9


def test_coalition_action_has_exactly_join_and_leave():
    assert {member.value for member in CoalitionAction} == {1, 2}


def test_coalition_action_prompt_table_is_derived_from_the_enum_not_hand_typed():
    for action in CoalitionAction:
        assert f"{action.value} = {action.name}" in COALITION_ACTION_PROMPT_TABLE
    assert COALITION_ACTION_PROMPT_TABLE.count("\n") == len(CoalitionAction) - 1


def test_coalition_motif_never_reuses_the_rupture_disagreement_code_503():
    assert 503 not in {member.value for member in CoalitionMotif}


def test_coalition_motif_lives_entirely_inside_the_500s_range():
    assert all(500 <= member.value <= 599 for member in CoalitionMotif)


def test_coalition_motif_has_exactly_the_four_documented_codes():
    assert {member.value for member in CoalitionMotif} == {501, 502, 504, 505}


def test_coalition_motif_prompt_table_is_derived_from_the_enum_not_hand_typed():
    for motif in CoalitionMotif:
        assert f"{motif.value} = {motif.name}" in COALITION_MOTIF_PROMPT_TABLE
    assert COALITION_MOTIF_PROMPT_TABLE.count("\n") == len(CoalitionMotif) - 1


def test_codebook_version_matches_the_shipped_config():
    from api.domain.polity.config import load_config

    assert load_config().llm.codebook_version == CODEBOOK_VERSION


# ── v4 Lot 1: dt=6/dt=10 reservation, BallotFormat.BINARY, 300-range motifs ──

def test_representative_response_is_decision_type_6():
    assert DecisionType.REPRESENTATIVE_RESPONSE == 6


def test_pressure_action_is_decision_type_10():
    assert DecisionType.PRESSURE_ACTION == 10


def test_decision_type_does_not_yet_define_reaction_to_event_8():
    assert 8 not in {member.value for member in DecisionType}


def test_binary_is_ballot_format_4():
    assert BallotFormat.BINARY == 4


def test_stance_has_exactly_the_four_documented_codes():
    assert {member.value for member in Stance} == {1, 2, 3, 4}


def test_pressure_act_has_exactly_the_five_documented_codes():
    assert {member.value for member in PressureAct} == {0, 1, 2, 3, 4}


def test_pressure_act_prompt_table_lists_every_act():
    for act in PressureAct:
        assert f"{act.value} = {act.name}" in PRESSURE_ACT_PROMPT_TABLE
    assert PRESSURE_ACT_PROMPT_TABLE.count("\n") == len(PressureAct) - 1


def test_stance_prompt_table_lists_every_stance():
    for stance in Stance:
        assert f"{stance.value} = {stance.name}" in STANCE_PROMPT_TABLE
    assert STANCE_PROMPT_TABLE.count("\n") == len(Stance) - 1


def test_response_motif_lives_entirely_inside_the_300s_range():
    assert all(300 <= member.value <= 399 for member in ResponseMotif)


def test_response_motif_never_reuses_the_citizen_only_codes():
    # 304 (no leverage) and 305 (deferred to election) describe a citizen's
    # inaction, not a sitting representative's -- 306 needs the v6 social
    # graph, which has no analogue for a single office-holder.
    assert {304, 305, 306}.isdisjoint({member.value for member in ResponseMotif})


def test_response_motif_prompt_table_is_derived_from_the_enum_not_hand_typed():
    for motif in ResponseMotif:
        assert f"{motif.value} = {motif.name}" in RESPONSE_MOTIF_PROMPT_TABLE
    assert RESPONSE_MOTIF_PROMPT_TABLE.count("\n") == len(ResponseMotif) - 1


def test_pressure_motif_lives_entirely_inside_the_300s_range():
    assert all(300 <= member.value <= 399 for member in PressureMotif)


def test_pressure_motif_never_reuses_the_representative_only_or_v6_codes():
    # 302 (street pressure) would leak the aggregate mobilization signal into
    # a citizen's own decision, breaking §7bis.9f's atomized regime; 306
    # needs the v6 social graph.
    assert {302, 306}.isdisjoint({member.value for member in PressureMotif})


def test_pressure_motif_prompt_table_is_derived_from_the_enum_not_hand_typed():
    for motif in PressureMotif:
        assert f"{motif.value} = {motif.name}" in PRESSURE_MOTIF_PROMPT_TABLE
    assert PRESSURE_MOTIF_PROMPT_TABLE.count("\n") == len(PressureMotif) - 1


def test_response_and_pressure_motif_share_the_mandate_deviation_code():
    # Deliberate overlap at 301: a representative's own awareness of their
    # deviation and a citizen's perception of that same fact are two
    # legitimately distinct readings, not a collision -- two separate enum
    # classes, so there's no value conflict either.
    assert ResponseMotif.MANDATE_DEVIATION_HIGH.value == PressureMotif.MANDATE_DEVIATION_HIGH.value == 301
