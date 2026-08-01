"""llm_schemas.py — Pydantic wire validation for the LLM's vote_cast decision
(design doc §3.6.1). Offline, no network — pure schema validation.
"""
import pytest
from pydantic import ValidationError

from api.domain.polity.codebook import VoteMotif
from api.domain.polity.llm_schemas import VOTE_CAST_JSON_SCHEMA, VoteCastBatch, VoteCastDecision


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
