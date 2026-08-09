"""llm_schemas.py — Pydantic wire validation for the LLM's vote_cast (design
doc §3.6.1) and candidacy_considered (§3.6.2) decisions. Offline, no
network — pure schema validation.
"""
import pytest
from pydantic import ValidationError

from api.domain.polity.codebook import CandidacyMotif, PartyNominationMotif, VoteMotif
from api.domain.polity.llm_schemas import (
    CANDIDACY_JSON_SCHEMA,
    PARTY_NOMINATION_JSON_SCHEMA,
    VOTE_CAST_JSON_SCHEMA,
    CandidacyBatch,
    CandidacyDecision,
    PartyNominationBatch,
    PartyNominationDecision,
    VoteCastBatch,
    VoteCastDecision,
)


def _decision(**overrides):
    base = {"cid": 1, "blank": 0, "ranking": [2, 3], "motif": 101}
    base.update(overrides)
    return base


def test_valid_decision_round_trips():
    decision = VoteCastDecision.model_validate(_decision())
    assert decision.cid == 1
    assert decision.ranking == [2, 3]


def test_blank_one_with_nonempty_ranking_raises():
    with pytest.raises(ValidationError, match="blank=1"):
        VoteCastDecision.model_validate(_decision(blank=1, ranking=[2]))


def test_blank_zero_with_empty_ranking_raises():
    with pytest.raises(ValidationError, match="blank=0"):
        VoteCastDecision.model_validate(_decision(blank=0, ranking=[]))


def test_blank_one_with_empty_ranking_is_valid():
    decision = VoteCastDecision.model_validate(_decision(blank=1, ranking=[]))
    assert decision.blank == 1
    assert decision.ranking == []


def test_duplicate_cid_in_ranking_raises():
    with pytest.raises(ValidationError, match="duplicate"):
        VoteCastDecision.model_validate(_decision(ranking=[2, 2]))


def test_unknown_motif_raises():
    with pytest.raises(ValidationError):
        VoteCastDecision.model_validate(_decision(motif=105))


def test_motif_as_string_is_rejected():
    # Pydantic v2's Literal[int, ...] does not lax-coerce a quoted string —
    # pinned here so a future change (deliberate or accidental) is visible.
    # If Lot 0's live spike shows qwen3:8b actually emits a quoted motif
    # under JSON-schema mode, add a `mode="before"` coercing validator then.
    with pytest.raises(ValidationError):
        VoteCastDecision.model_validate(_decision(motif="101"))


def test_unknown_extra_key_raises():
    with pytest.raises(ValidationError):
        VoteCastDecision.model_validate({**_decision(), "extra_field": True})


def test_empty_decisions_list_raises():
    with pytest.raises(ValidationError):
        VoteCastBatch.model_validate({"decisions": []})


def test_batch_round_trips_multiple_decisions():
    batch = VoteCastBatch.model_validate({"decisions": [_decision(cid=1), _decision(cid=2, blank=1, ranking=[])]})
    assert [d.cid for d in batch.decisions] == [1, 2]


def test_motif_literal_matches_vote_motif_enum_exactly():
    literal_values = set(VoteCastDecision.model_fields["motif"].annotation.__args__)  # type: ignore[union-attr]
    assert literal_values == {member.value for member in VoteMotif}


def test_json_schema_marks_ranking_as_required():
    decision_schema = VOTE_CAST_JSON_SCHEMA["$defs"]["VoteCastDecision"]
    assert "ranking" in decision_schema["required"]
    assert decision_schema.get("additionalProperties") is False


def test_json_schema_batch_forbids_additional_properties():
    assert VOTE_CAST_JSON_SCHEMA.get("additionalProperties") is False


def _candidacy_decision(**overrides):
    base = {"cid": 1, "outcome": 1, "motif": 203}
    base.update(overrides)
    return base


def test_valid_candidacy_decision_round_trips():
    decision = CandidacyDecision.model_validate(_candidacy_decision())
    assert decision.cid == 1
    assert decision.outcome == 1


def test_candidacy_unknown_motif_raises():
    with pytest.raises(ValidationError):
        CandidacyDecision.model_validate(_candidacy_decision(motif=105))


def test_candidacy_motif_202_is_rejected():
    # 202 (IDEOLOGICAL_RUPTURE) is reserved for the rupture path, which
    # never reaches the LLM — pinned so a future accidental reuse is visible.
    with pytest.raises(ValidationError):
        CandidacyDecision.model_validate(_candidacy_decision(motif=202))


def test_candidacy_unknown_extra_key_raises():
    with pytest.raises(ValidationError):
        CandidacyDecision.model_validate({**_candidacy_decision(), "extra_field": True})


def test_candidacy_empty_decisions_list_raises():
    with pytest.raises(ValidationError):
        CandidacyBatch.model_validate({"decisions": []})


def test_candidacy_batch_round_trips_multiple_decisions():
    batch = CandidacyBatch.model_validate(
        {"decisions": [_candidacy_decision(cid=1), _candidacy_decision(cid=2, outcome=0, motif=201)]}
    )
    assert [d.cid for d in batch.decisions] == [1, 2]


def test_candidacy_motif_literal_matches_candidacy_motif_enum_exactly():
    literal_values = set(CandidacyDecision.model_fields["motif"].annotation.__args__)  # type: ignore[union-attr]
    assert literal_values == {member.value for member in CandidacyMotif}


def test_candidacy_json_schema_marks_outcome_as_required():
    decision_schema = CANDIDACY_JSON_SCHEMA["$defs"]["CandidacyDecision"]
    assert "outcome" in decision_schema["required"]
    assert decision_schema.get("additionalProperties") is False


def test_candidacy_json_schema_batch_forbids_additional_properties():
    assert CANDIDACY_JSON_SCHEMA.get("additionalProperties") is False


def _nomination_decision(**overrides):
    base = {"party_id": 0, "winner_position": 1, "motif": 206}
    base.update(overrides)
    return base


def test_valid_party_nomination_decision_round_trips():
    decision = PartyNominationDecision.model_validate(_nomination_decision())
    assert decision.party_id == 0
    assert decision.winner_position == 1


def test_party_nomination_winner_position_must_be_at_least_one():
    with pytest.raises(ValidationError):
        PartyNominationDecision.model_validate(_nomination_decision(winner_position=0))


def test_party_nomination_unknown_motif_raises():
    with pytest.raises(ValidationError):
        PartyNominationDecision.model_validate(_nomination_decision(motif=205))  # a CandidacyMotif code, not ours


def test_party_nomination_unknown_extra_key_raises():
    with pytest.raises(ValidationError):
        PartyNominationDecision.model_validate({**_nomination_decision(), "extra_field": True})


def test_party_nomination_empty_decisions_list_raises():
    with pytest.raises(ValidationError):
        PartyNominationBatch.model_validate({"decisions": []})


def test_party_nomination_batch_round_trips_multiple_decisions():
    batch = PartyNominationBatch.model_validate(
        {"decisions": [_nomination_decision(party_id=0), _nomination_decision(party_id=1, motif=207)]}
    )
    assert [d.party_id for d in batch.decisions] == [0, 1]


def test_party_nomination_motif_literal_matches_party_nomination_motif_enum_exactly():
    literal_values = set(PartyNominationDecision.model_fields["motif"].annotation.__args__)  # type: ignore[union-attr]
    assert literal_values == {member.value for member in PartyNominationMotif}


def test_party_nomination_json_schema_marks_winner_position_as_required():
    decision_schema = PARTY_NOMINATION_JSON_SCHEMA["$defs"]["PartyNominationDecision"]
    assert "winner_position" in decision_schema["required"]
    assert decision_schema.get("additionalProperties") is False


def test_party_nomination_json_schema_batch_forbids_additional_properties():
    assert PARTY_NOMINATION_JSON_SCHEMA.get("additionalProperties") is False
