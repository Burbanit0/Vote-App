"""codebook.py — the vote-decision slice of design doc §3.7's compression tables.

Contract: the codebook is a frozen, versioned artifact (§3.7.0) — a version
mismatch must be a loud error, and decision_type 7 (retired) must never be
reassigned.
"""
import pytest

from api.domain.polity.codebook import (
    CODEBOOK_VERSION,
    VOTE_MOTIF_PROMPT_TABLE,
    BallotFormat,
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


def test_ranking_is_ballot_format_1():
    assert BallotFormat.RANKING == 1


def test_vote_motif_has_exactly_the_four_documented_codes():
    assert {member.value for member in VoteMotif} == {101, 102, 103, 104}


def test_vote_motif_prompt_table_is_derived_from_the_enum_not_hand_typed():
    for motif in VoteMotif:
        assert f"{motif.value} = {motif.name}" in VOTE_MOTIF_PROMPT_TABLE
    assert VOTE_MOTIF_PROMPT_TABLE.count("\n") == len(VoteMotif) - 1
