"""
api/tests/test_polity_llm_toon_encoding.py

Offline tests for llm_toon_encoding.py -- plan-llm-protocol-and-theory-
program.md §5.E's input-only TOON encoder.
"""
from __future__ import annotations

import pytest

from api.domain.polity.llm_toon_encoding import encode_toon_array


def test_encodes_the_header_and_one_row_per_record():
    out = encode_toon_array("citizens", ["cid", "ambition_score"], [[0, 0.5], [1, 0.62]])
    assert out == "citizens[2]{cid,ambition_score}:\n0,0.5\n1,0.62"


def test_header_declares_the_real_row_count_including_zero():
    out = encode_toon_array("citizens", ["cid"], [])
    assert out == "citizens[0]{cid}:"


def test_field_order_in_the_header_matches_the_row_order():
    out = encode_toon_array("x", ["a", "b", "c"], [[1, 2, 3]])
    assert out.splitlines()[0] == "x[1]{a,b,c}:"
    assert out.splitlines()[1] == "1,2,3"


def test_raises_on_a_row_with_the_wrong_width():
    with pytest.raises(ValueError, match="row 1 has 1"):
        encode_toon_array("citizens", ["cid", "ambition_score"], [[0, 0.5], [1]])


def test_floats_use_repr_not_str_formatting():
    out = encode_toon_array("x", ["v"], [[1e-05]])
    assert out.splitlines()[1] == repr(1e-05)


def test_rejects_bool_values_to_avoid_true_false_vs_one_zero_ambiguity():
    with pytest.raises(TypeError, match="bool"):
        encode_toon_array("x", ["flag"], [[True]])


def test_ints_render_without_a_decimal_point():
    out = encode_toon_array("citizens", ["cid"], [[7]])
    assert out.splitlines()[1] == "7"
