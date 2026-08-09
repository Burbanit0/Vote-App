"""codebook.py — the vote-decision slice of design doc §3.7's compression tables.

Contract: the codebook is a frozen, versioned artifact (§3.7.0) — a version
mismatch must be a loud error, and decision_type 7 (retired) must never be
reassigned.
"""
import pytest

from api.domain.polity.codebook import (
    CANDIDACY_MOTIF_PROMPT_TABLE,
    CODEBOOK_VERSION,
    VOTE_MOTIF_PROMPT_TABLE,
    BallotFormat,
    CandidacyMotif,
    CandidacyOutcome,
    DecisionType,
    PolityCodebookError,
    VoteMotif,
    check_codebook_version,
)


def test_check_codebook_version_accepts_the_matching_version():
    check_codebook_version(CODEBOOK_VERSION)  # must not raise


def test_check_codebook_version_rejects_a_mismatch():
    with pytest.raises(PolityCodebookError, match="1.0"):
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


def test_vote_motif_has_exactly_the_four_documented_codes():
    assert {member.value for member in VoteMotif} == {101, 102, 103, 104}


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
