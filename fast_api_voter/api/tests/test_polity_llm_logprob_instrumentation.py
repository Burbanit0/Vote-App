"""
api/tests/test_polity_llm_logprob_instrumentation.py

Offline tests for llm_logprob_instrumentation.py -- plan-llm-protocol-and-
theory-program.md §5.C's "real hard problem": locating the field-relevant
token inside a real, xgrammar-constrained, possibly think=True completion.
No live server needed here; every TokenLogprob sequence below is
hand-built to exercise the two problems that module's own docstring names:
a reasoning-parser offset (content is a SUFFIX of the raw token stream,
not the whole of it) and arbitrary token/JSON-syntax boundary splits (a
BPE tokenizer has no reason to align its own token boundaries to JSON
punctuation).
"""
from __future__ import annotations

import math

import pytest

from api.domain.polity.llm_client import TokenLogprob
from api.domain.polity.llm_logprob_instrumentation import (
    DecisionTokenProbe,
    LogprobAlignmentError,
    binary_probability,
    candidate_probability,
    locate_decision_field_logprobs,
)


def _tok(token: str, logprob: float = 0.0, alternatives: dict[str, float] | None = None) -> TokenLogprob:
    return TokenLogprob(token=token, logprob=logprob, alternatives=alternatives if alternatives is not None else {token: logprob})


# ── locate_decision_field_logprobs ────────────────────────────────────────

def test_locates_a_single_decisions_field_value_token_think_false():
    content = '{"decisions":[{"cid":5,"blank":1,"motif":101}]}'
    tokens = [
        _tok('{"decisions":[{"cid":'),
        _tok("5"),
        _tok(',"blank":'),
        _tok("1", logprob=-0.02),
        _tok(',"motif":'),
        _tok("101"),
        _tok("}]}"),
    ]
    probes = locate_decision_field_logprobs(content, tokens, field="blank")
    assert probes == [DecisionTokenProbe(cid=5, token=_tok("1", logprob=-0.02))]


def test_locates_one_probe_per_decision_in_document_order():
    content = '{"decisions":[{"cid":1,"blank":0,"motif":102},{"cid":7,"blank":1,"motif":101}]}'
    tokens = [
        _tok('{"decisions":[{"cid":'),
        _tok("1"),
        _tok(',"blank":'),
        _tok("0", logprob=-1.5),
        _tok(',"motif":102},{"cid":'),
        _tok("7"),
        _tok(',"blank":'),
        _tok("1", logprob=-0.01),
        _tok(',"motif":101}]}'),
    ]
    probes = locate_decision_field_logprobs(content, tokens, field="blank")
    assert [p.cid for p in probes] == [1, 7]
    assert [p.token.token for p in probes] == ["0", "1"]
    assert probes[1].token.logprob == -0.01


def test_handles_a_leading_think_block_stripped_from_content_but_present_in_tokens():
    # Reproduces the exact misalignment this module exists to fix: `content`
    # (reasoning-parser-stripped) is only the tail of the raw generation,
    # and a token boundary here deliberately straddles </think> itself --
    # neither offset trick works unless both problems are solved together.
    content = '{"decisions":[{"cid":9,"blank":1,"motif":101}]}'
    tokens = [
        _tok("<think>hmm</th"),
        _tok('ink>{"de'),
        _tok('cisions":[{"cid":9,"bl'),
        _tok('ank":'),
        _tok("1", logprob=-0.3),
        _tok(',"motif":101}]}'),
    ]
    probes = locate_decision_field_logprobs(content, tokens, field="blank")
    assert probes == [DecisionTokenProbe(cid=9, token=_tok("1", logprob=-0.3))]


def test_locates_the_act_field_among_several_scalar_fields_per_decision():
    content = '{"decisions":[{"act":3,"cid":4,"motif":301,"target":8}]}'
    tokens = [
        _tok('{"decisions":[{"act":'),
        _tok("3", logprob=-0.7),
        _tok(',"cid":4,"motif":301,"target":8}]}'),
    ]
    probes = locate_decision_field_logprobs(content, tokens, field="act")
    assert probes == [DecisionTokenProbe(cid=4, token=_tok("3", logprob=-0.7))]


def test_value_char_offset_zero_is_uninformative_for_a_shared_leading_digit_motif_field():
    # Reproduces a real failure found live 2026-09-10: ReactionMotif's
    # 401/402/403 all share the leading "40" -- offset=0 (the default)
    # locates the SAME token regardless of which value follows.
    content = '{"decisions":[{"cid":1,"motif":402}]}'
    tokens = [_tok('{"decisions":[{"cid":1,"motif":'), _tok("4"), _tok("0"), _tok("2", logprob=-0.6), _tok("}]}")]
    probes = locate_decision_field_logprobs(content, tokens, field="motif")
    # The located token is "4" -- shared by 401/402/403, uninformative --
    # not what a caller actually wants, but not a crash either.
    assert probes[0].token.token == "4"


def test_value_char_offset_locates_the_actually_discriminating_digit():
    content = '{"decisions":[{"cid":1,"motif":402}]}'
    tokens = [_tok('{"decisions":[{"cid":1,"motif":'), _tok("4"), _tok("0"), _tok("2", logprob=-0.6), _tok("}]}")]
    probes = locate_decision_field_logprobs(content, tokens, field="motif", value_char_offset=2)
    assert probes == [DecisionTokenProbe(cid=1, token=_tok("2", logprob=-0.6))]


def test_value_char_offset_works_when_the_discriminating_digit_shares_a_token_with_others():
    # "40" and "2" as two tokens (not one-digit-per-token like the test
    # above) -- offset=2 must still land on the "2" token, not the "40" one.
    content = '{"decisions":[{"cid":1,"motif":402}]}'
    tokens = [_tok('{"decisions":[{"cid":1,"motif":'), _tok("40"), _tok("2", logprob=-0.6), _tok("}]}")]
    probes = locate_decision_field_logprobs(content, tokens, field="motif", value_char_offset=2)
    assert probes == [DecisionTokenProbe(cid=1, token=_tok("2", logprob=-0.6))]


def test_value_char_offset_out_of_range_raises():
    content = '{"decisions":[{"cid":1,"blank":1}]}'
    tokens = [_tok(content)]
    with pytest.raises(LogprobAlignmentError, match="value_char_offset"):
        locate_decision_field_logprobs(content, tokens, field="blank", value_char_offset=2)


def test_respects_a_custom_cid_field_and_decisions_key():
    content = '{"members":[{"mid":2,"stance":1}]}'
    tokens = [_tok('{"members":[{"mid":2,"stance":'), _tok("1", logprob=-0.4), _tok("}]}")]
    probes = locate_decision_field_logprobs(
        content, tokens, field="stance", decisions_key="members", cid_field="mid"
    )
    assert probes == [DecisionTokenProbe(cid=2, token=_tok("1", logprob=-0.4))]


def test_raises_when_content_is_not_a_substring_of_the_raw_token_stream():
    content = '{"decisions":[{"cid":1,"blank":0,"motif":102}]}'
    tokens = [_tok("something completely different")]
    with pytest.raises(LogprobAlignmentError, match="not a substring"):
        locate_decision_field_logprobs(content, tokens, field="blank")


def test_raises_when_field_occurrence_count_does_not_match_decision_count():
    # Two decisions, but only one has "blank" spelled out in the text
    # (contrived, but a real symptom of a schema/field mismatch caught
    # rather than silently under-reported).
    content = '{"decisions":[{"cid":1,"blank":0},{"cid":2,"motif":101}]}'
    tokens = [_tok(content)]
    with pytest.raises(LogprobAlignmentError, match="cannot align"):
        locate_decision_field_logprobs(content, tokens, field="blank")


def test_raises_when_a_decision_is_missing_the_cid_field():
    content = '{"decisions":[{"blank":1,"motif":101}]}'
    tokens = [_tok(content)]
    with pytest.raises(LogprobAlignmentError, match="cid"):
        locate_decision_field_logprobs(content, tokens, field="blank")


def test_raises_on_a_non_scalar_field_value_rather_than_misparsing_it():
    content = '{"decisions":[{"cid":1,"ranking":[1,2,3]}]}'
    tokens = [_tok(content)]
    with pytest.raises(LogprobAlignmentError, match="not followed by a scalar"):
        locate_decision_field_logprobs(content, tokens, field="ranking")


def test_locates_a_float_scalar_value():
    content = '{"decisions":[{"cid":3,"salience_delta":0.35,"motif":401}]}'
    tokens = [_tok('{"decisions":[{"cid":3,"salience_delta":'), _tok("0.35", logprob=-1.1), _tok(',"motif":401}]}')]
    probes = locate_decision_field_logprobs(content, tokens, field="salience_delta")
    assert probes == [DecisionTokenProbe(cid=3, token=_tok("0.35", logprob=-1.1))]


# ── binary_probability ─────────────────────────────────────────────────────

def test_binary_probability_normalizes_over_the_two_named_candidates():
    token = _tok("1", logprob=-0.05, alternatives={"1": -0.05, "0": -3.2, "unrelated": -9.0})
    p = binary_probability(token, true_value="1", false_value="0")
    expected = math.exp(-0.05) / (math.exp(-0.05) + math.exp(-3.2))
    assert p == pytest.approx(expected)


def test_binary_probability_returns_one_half_when_neither_candidate_was_captured():
    token = _tok("x", logprob=-0.01, alternatives={"x": -0.01, "y": -4.0})
    assert binary_probability(token, true_value="1", false_value="0") == 0.5


def test_binary_probability_treats_a_missing_candidate_as_zero_mass():
    token = _tok("1", logprob=-0.02, alternatives={"1": -0.02})
    assert binary_probability(token, true_value="1", false_value="0") == pytest.approx(1.0)


# ── candidate_probability ───────────────────────────────────────────────

def test_candidate_probability_reads_the_raw_exp_logprob():
    token = _tok("1", logprob=-0.1, alternatives={"1": -0.1, "2": -2.0, "3": -3.0, "4": -4.0})
    assert candidate_probability(token, "1") == pytest.approx(math.exp(-0.1))


def test_candidate_probability_is_not_renormalized_across_more_than_two_candidates():
    # A genuinely 4-way field: unlike binary_probability, no pair is
    # singled out -- each candidate's own raw probability stands alone,
    # so the four don't have to sum to 1 here (top_logprobs may not have
    # captured the server's full distribution).
    token = _tok("1", logprob=-0.1, alternatives={"1": -0.1, "2": -2.0})
    p1 = candidate_probability(token, "1")
    p2 = candidate_probability(token, "2")
    assert p1 == pytest.approx(math.exp(-0.1))
    assert p2 == pytest.approx(math.exp(-2.0))
    assert p1 + p2 != pytest.approx(1.0)


def test_candidate_probability_returns_zero_for_an_uncaptured_candidate():
    token = _tok("1", logprob=-0.1, alternatives={"1": -0.1})
    assert candidate_probability(token, "4") == 0.0
