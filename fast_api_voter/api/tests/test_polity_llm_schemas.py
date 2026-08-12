"""llm_schemas.py — Pydantic wire validation for the LLM's vote_cast (design
doc §3.6.1) and candidacy_considered (§3.6.2) decisions. Offline, no
network — pure schema validation.
"""
import pytest
from pydantic import ValidationError

from api.domain.polity.codebook import (
    CampaignMotif,
    CandidacyMotif,
    CoalitionAction,
    CoalitionMotif,
    PartyNominationMotif,
    ResponseMotif,
    Stance,
    VoteMotif,
)
from api.domain.polity.llm_schemas import (
    CANDIDACY_JSON_SCHEMA,
    COALITION_JSON_SCHEMA,
    PARTY_NOMINATION_JSON_SCHEMA,
    POSITIONING_JSON_SCHEMA,
    RESPONSE_JSON_SCHEMA,
    VOTE_CAST_JSON_SCHEMA,
    CandidacyBatch,
    CandidacyDecision,
    CoalitionBatch,
    CoalitionDecision,
    PartyNominationBatch,
    PartyNominationDecision,
    PositioningBatch,
    PositioningDecision,
    ResponseBatch,
    ResponseDecision,
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


def _positioning_decision(**overrides):
    base = {"cid": 1, "shifts": [{"dimension": 0, "delta": 0.1}], "motif": 602}
    base.update(overrides)
    return base


def test_valid_positioning_decision_round_trips():
    decision = PositioningDecision.model_validate(_positioning_decision())
    assert decision.cid == 1
    assert len(decision.shifts) == 1
    assert decision.shifts[0].dimension == 0
    assert decision.shifts[0].delta == 0.1


def test_positioning_decision_with_empty_shifts_is_valid():
    decision = PositioningDecision.model_validate(_positioning_decision(shifts=[]))
    assert decision.shifts == []


def test_positioning_decision_rejects_duplicate_dimensions():
    with pytest.raises(ValidationError, match="same dimension"):
        PositioningDecision.model_validate(
            _positioning_decision(shifts=[{"dimension": 0, "delta": 0.1}, {"dimension": 0, "delta": -0.2}])
        )


def test_positioning_decision_rejects_more_than_five_shifts():
    with pytest.raises(ValidationError):
        PositioningDecision.model_validate(
            _positioning_decision(shifts=[{"dimension": i, "delta": 0.1} for i in range(6)])
        )


def test_positioning_unknown_motif_raises():
    with pytest.raises(ValidationError):
        PositioningDecision.model_validate(_positioning_decision(motif=605))


def test_positioning_unknown_extra_key_raises():
    with pytest.raises(ValidationError):
        PositioningDecision.model_validate({**_positioning_decision(), "extra_field": True})


def test_positioning_empty_decisions_list_raises():
    with pytest.raises(ValidationError):
        PositioningBatch.model_validate({"decisions": []})


def test_positioning_batch_round_trips_multiple_decisions():
    batch = PositioningBatch.model_validate(
        {"decisions": [_positioning_decision(cid=1), _positioning_decision(cid=2, shifts=[])]}
    )
    assert [d.cid for d in batch.decisions] == [1, 2]


def test_positioning_motif_literal_matches_campaign_motif_enum_exactly():
    literal_values = set(PositioningDecision.model_fields["motif"].annotation.__args__)  # type: ignore[union-attr]
    assert literal_values == {member.value for member in CampaignMotif}


def test_positioning_json_schema_marks_shifts_as_required():
    decision_schema = POSITIONING_JSON_SCHEMA["$defs"]["PositioningDecision"]
    assert "shifts" in decision_schema["required"]
    assert decision_schema.get("additionalProperties") is False


def test_positioning_json_schema_batch_forbids_additional_properties():
    assert POSITIONING_JSON_SCHEMA.get("additionalProperties") is False


def _coalition_decision(**overrides):
    base = {"party_id": 0, "action": 1, "motif": 501}
    base.update(overrides)
    return base


def test_valid_coalition_decision_round_trips_join():
    decision = CoalitionDecision.model_validate(_coalition_decision())
    assert decision.party_id == 0
    assert decision.action == 1
    assert decision.motif == 501


def test_valid_coalition_decision_round_trips_leave():
    decision = CoalitionDecision.model_validate(_coalition_decision(action=2, motif=504))
    assert decision.action == 2
    assert decision.motif == 504


def test_coalition_action_outside_join_leave_is_rejected():
    with pytest.raises(ValidationError):
        CoalitionDecision.model_validate(_coalition_decision(action=3))
    with pytest.raises(ValidationError):
        CoalitionDecision.model_validate(_coalition_decision(action=4))


def test_coalition_unknown_motif_raises():
    with pytest.raises(ValidationError):
        CoalitionDecision.model_validate(_coalition_decision(motif=999))


def test_coalition_motif_503_is_rejected():
    # 503 (COALITION_RUPTURE_DISAGREEMENT) is reserved for the deferred
    # maintenance/rupture palier, never a formation-time decline — pinned
    # so a future accidental reuse is visible.
    with pytest.raises(ValidationError):
        CoalitionDecision.model_validate(_coalition_decision(action=2, motif=503))


def test_coalition_join_with_decline_motif_raises():
    with pytest.raises(ValidationError, match="action=1"):
        CoalitionDecision.model_validate(_coalition_decision(action=1, motif=504))
    with pytest.raises(ValidationError, match="action=1"):
        CoalitionDecision.model_validate(_coalition_decision(action=1, motif=505))


def test_coalition_leave_with_join_motif_raises():
    with pytest.raises(ValidationError, match="action=2"):
        CoalitionDecision.model_validate(_coalition_decision(action=2, motif=501))
    with pytest.raises(ValidationError, match="action=2"):
        CoalitionDecision.model_validate(_coalition_decision(action=2, motif=502))


def test_coalition_both_valid_action_motif_pairings_accepted():
    CoalitionDecision.model_validate(_coalition_decision(action=1, motif=501))
    CoalitionDecision.model_validate(_coalition_decision(action=1, motif=502))
    CoalitionDecision.model_validate(_coalition_decision(action=2, motif=504))
    CoalitionDecision.model_validate(_coalition_decision(action=2, motif=505))


def test_coalition_unknown_extra_key_raises():
    with pytest.raises(ValidationError):
        CoalitionDecision.model_validate({**_coalition_decision(), "extra_field": True})


def test_coalition_empty_decisions_list_raises():
    with pytest.raises(ValidationError):
        CoalitionBatch.model_validate({"decisions": []})


def test_coalition_batch_round_trips_multiple_decisions():
    batch = CoalitionBatch.model_validate(
        {"decisions": [_coalition_decision(party_id=0), _coalition_decision(party_id=1, action=2, motif=504)]}
    )
    assert [d.party_id for d in batch.decisions] == [0, 1]


def test_coalition_action_literal_matches_coalition_action_enum_exactly():
    literal_values = set(CoalitionDecision.model_fields["action"].annotation.__args__)  # type: ignore[union-attr]
    assert literal_values == {member.value for member in CoalitionAction}


def test_coalition_motif_literal_matches_coalition_motif_enum_exactly():
    literal_values = set(CoalitionDecision.model_fields["motif"].annotation.__args__)  # type: ignore[union-attr]
    assert literal_values == {member.value for member in CoalitionMotif}


def test_coalition_json_schema_marks_action_and_motif_as_required():
    decision_schema = COALITION_JSON_SCHEMA["$defs"]["CoalitionDecision"]
    assert "action" in decision_schema["required"]
    assert "motif" in decision_schema["required"]
    assert decision_schema.get("additionalProperties") is False


def test_coalition_json_schema_batch_forbids_additional_properties():
    assert COALITION_JSON_SCHEMA.get("additionalProperties") is False


def _response_decision(**overrides):
    base = {"cid": 1, "shifts": [{"dimension": 0, "delta": 0.1}], "stance": 1, "motif": 301}
    base.update(overrides)
    return base


def test_valid_response_decision_round_trips_a_concession():
    decision = ResponseDecision.model_validate(_response_decision())
    assert decision.cid == 1
    assert decision.stance == 1
    assert len(decision.shifts) == 1
    assert decision.shifts[0].dimension == 0
    assert decision.shifts[0].delta == 0.1


def test_response_silence_with_shifts_raises():
    with pytest.raises(ValidationError, match="stance=3"):
        ResponseDecision.model_validate(_response_decision(stance=3, motif=308))


def test_response_silence_with_no_shifts_is_accepted():
    decision = ResponseDecision.model_validate(_response_decision(shifts=[], stance=3, motif=308))
    assert decision.shifts == []


def test_response_concession_with_no_shifts_raises():
    with pytest.raises(ValidationError, match="stance=1"):
        ResponseDecision.model_validate(_response_decision(shifts=[], stance=1, motif=301))


def test_response_defiance_accepts_both_an_empty_and_a_non_empty_shift_list():
    ResponseDecision.model_validate(_response_decision(shifts=[], stance=2, motif=307))
    ResponseDecision.model_validate(_response_decision(stance=2, motif=307))


def test_response_concession_with_a_defiance_motif_raises():
    with pytest.raises(ValidationError, match="stance=1"):
        ResponseDecision.model_validate(_response_decision(stance=1, motif=307))


def test_response_defiance_with_a_concession_motif_raises():
    with pytest.raises(ValidationError, match="stance=2"):
        ResponseDecision.model_validate(_response_decision(stance=2, motif=301))


def test_response_every_valid_stance_motif_pairing_is_accepted():
    ResponseDecision.model_validate(_response_decision(stance=1, motif=301))
    ResponseDecision.model_validate(_response_decision(stance=1, motif=302))
    ResponseDecision.model_validate(_response_decision(stance=1, motif=303))
    ResponseDecision.model_validate(_response_decision(shifts=[], stance=2, motif=307))
    ResponseDecision.model_validate(_response_decision(shifts=[], stance=3, motif=308))
    ResponseDecision.model_validate(_response_decision(shifts=[], stance=4, motif=309))


def test_response_duplicate_dimension_raises():
    with pytest.raises(ValidationError, match="same dimension"):
        ResponseDecision.model_validate(
            _response_decision(shifts=[{"dimension": 0, "delta": 0.1}, {"dimension": 0, "delta": -0.2}])
        )


def test_response_more_than_five_shifts_raises():
    with pytest.raises(ValidationError):
        ResponseDecision.model_validate(_response_decision(shifts=[{"dimension": i, "delta": 0.01} for i in range(6)]))


def test_response_motif_304_305_306_are_rejected():
    # Deliberately excluded from ResponseMotif (see codebook.py's own
    # docstring): 304/305 describe a CITIZEN's inaction, not a sitting
    # representative's; 306 needs the v6 social graph.
    for motif in (304, 305, 306):
        with pytest.raises(ValidationError):
            ResponseDecision.model_validate(_response_decision(motif=motif))


def test_response_unknown_extra_key_raises():
    with pytest.raises(ValidationError):
        ResponseDecision.model_validate({**_response_decision(), "extra_field": True})


def test_response_empty_decisions_list_raises():
    with pytest.raises(ValidationError):
        ResponseBatch.model_validate({"decisions": []})


def test_response_batch_round_trips_multiple_decisions():
    batch = ResponseBatch.model_validate(
        {"decisions": [_response_decision(cid=1), _response_decision(cid=2, shifts=[], stance=3, motif=308)]}
    )
    assert [d.cid for d in batch.decisions] == [1, 2]


def test_response_stance_literal_matches_stance_enum_exactly():
    literal_values = set(ResponseDecision.model_fields["stance"].annotation.__args__)  # type: ignore[union-attr]
    assert literal_values == {member.value for member in Stance}


def test_response_motif_literal_matches_response_motif_enum_exactly():
    literal_values = set(ResponseDecision.model_fields["motif"].annotation.__args__)  # type: ignore[union-attr]
    assert literal_values == {member.value for member in ResponseMotif}


def test_response_json_schema_marks_shifts_stance_and_motif_as_required():
    decision_schema = RESPONSE_JSON_SCHEMA["$defs"]["ResponseDecision"]
    assert "shifts" in decision_schema["required"]
    assert "stance" in decision_schema["required"]
    assert "motif" in decision_schema["required"]
    assert decision_schema.get("additionalProperties") is False


def test_response_json_schema_batch_forbids_additional_properties():
    assert RESPONSE_JSON_SCHEMA.get("additionalProperties") is False
