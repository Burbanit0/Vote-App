"""Tests of the prompt builders archived in polity_archived_builders.py.

Moved out of api/tests/test_polity_llm_behavior_engine.py, unchanged but for imports: not collected by CI
(testpaths is api/tests). Run on demand: pytest scripts/archive/test_archived_prompt_builders.py -o addopts="".
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from api.domain.polity.llm_behavior_engine import (
    build_candidacy_system_prompt_toon,
    build_pressure_system_prompt,
)
from api.tests.test_polity_llm_behavior_engine import (
    _config_with_llm_enabled,
    _population,
    _pressure_citizen,
    _pressure_context,
)

sys.path.insert(0, str(Path(__file__).parent))

from polity_archived_builders import (  # noqa: E402
    build_candidacy_system_prompt_toon_calibrated,
    build_coalition_system_prompt_calibrated,
    build_pressure_system_prompt_toon,
    build_pressure_user_prompt_toon,
)


# ── build_candidacy_system_prompt_toon_calibrated (Track B3, 2026-09-11) ────

def test_calibrated_candidacy_prompt_states_the_population_mean_ambition():
    prompt = build_candidacy_system_prompt_toon_calibrated(_population(3), mean_ambition=0.2013)
    assert "0.2013" in prompt


def test_calibrated_candidacy_prompt_is_additive_not_a_replacement():
    # Same "enumerate the full expected cid list verbatim + self-check" and
    # same TOON worked example as the uncalibrated version -- only the
    # population-mean sentence is new.
    citizens = _population(3)
    prompt = build_candidacy_system_prompt_toon_calibrated(citizens, mean_ambition=0.2)
    assert "[0,1,2]" in prompt and "EXACTEMENT ces 3" in prompt
    assert "citizens[N]{cid,ambition_score,perceived_support}:" in prompt
    assert "0,0.52,0.31" in prompt  # the worked example, unchanged


def test_calibrated_candidacy_prompt_differs_from_uncalibrated_only_in_the_added_sentence():
    citizens = _population(3)
    uncalibrated_lines = set(build_candidacy_system_prompt_toon(citizens).splitlines())
    calibrated_lines = set(build_candidacy_system_prompt_toon_calibrated(citizens, mean_ambition=0.2).splitlines())
    assert uncalibrated_lines <= calibrated_lines
    added = calibrated_lines - uncalibrated_lines
    assert len(added) == 1
    assert "0.2000" in next(iter(added))


def test_calibrated_candidacy_prompt_states_no_prescribed_action():
    # C4: the ADDED sentence must situate a score against the population,
    # never tell the model what that should mean for the decision -- no
    # threshold, no "declare only if above this". Scoped to the added
    # sentence alone (not the whole prompt): the pre-existing motif table
    # legitimately contains "ambition_threshold_met", which is a real motif
    # code, not a prescribed rule this fix introduces.
    citizens = _population(1)
    uncalibrated_lines = set(build_candidacy_system_prompt_toon(citizens).splitlines())
    calibrated_lines = set(build_candidacy_system_prompt_toon_calibrated(citizens, mean_ambition=0.2).splitlines())
    added_sentence = next(iter(calibrated_lines - uncalibrated_lines)).lower()
    forbidden = ["seuil", "threshold", "si superieur", "si le score", "declare seulement", "ne te presente que"]
    for term in forbidden:
        assert term not in added_sentence


# ── build_coalition_system_prompt_calibrated (Track B2, 2026-09-11) ─────

def test_calibrated_coalition_prompt_states_the_mean_inter_party_distance():
    # 3 seated parties (initiator + 2 responders) on a single dimension:
    # 0.0, 0.3, 0.9. Pairwise distances: |0-0.3|=0.3, |0-0.9|=0.9,
    # |0.3-0.9|=0.6 -- mean = (0.3+0.9+0.6)/3 = 0.6.
    platforms = {0: (0.0,), 1: (0.3,), 2: (0.9,)}
    prompt = build_coalition_system_prompt_calibrated(
        [1, 2], initiator=0, initiator_seats=30, total_seats=100, majority_seats_threshold=50.0,
        party_platforms=platforms,
    )
    assert "0.6000" in prompt


def test_calibrated_coalition_prompt_includes_the_initiator_in_the_mean():
    # Verifies the mean is over {initiator} | responders, not responders
    # alone: with the initiator EXCLUDED the mean of a single pair (1, 2)
    # would be a different, wrong number (0.6) than the true 3-party mean
    # (0.6 coincidentally matches above; use an asymmetric case here so a
    # bug that drops the initiator cannot pass by accident).
    platforms = {0: (0.0,), 1: (1.0,), 2: (1.0,)}
    # Correct (initiator included): pairs (0,1)=1.0, (0,2)=1.0, (1,2)=0.0 -> mean=0.6667
    # Wrong (initiator excluded): only pair (1,2)=0.0 -> mean=0.0
    prompt = build_coalition_system_prompt_calibrated(
        [1, 2], initiator=0, initiator_seats=30, total_seats=100, majority_seats_threshold=50.0,
        party_platforms=platforms,
    )
    assert "0.6667" in prompt
    assert "0.0000" not in prompt


def test_calibrated_coalition_prompt_is_additive_not_a_replacement():
    platforms = {0: (0.0,), 1: (0.3,), 2: (0.9,)}
    prompt = build_coalition_system_prompt_calibrated(
        [1, 2], initiator=0, initiator_seats=30, total_seats=100, majority_seats_threshold=50.0,
        party_platforms=platforms,
    )
    assert "[1,2]" in prompt and "EXACTEMENT ces 2 party_id" in prompt
    assert "100" in prompt and "50.0" in prompt and "30" in prompt
    assert "1 = JOIN" in prompt and "501 = IDEOLOGICAL_PROXIMITY" in prompt
    assert "501" in prompt and "502" in prompt and "504" in prompt and "505" in prompt


def test_calibrated_coalition_prompt_contains_no_coalition_theory_framing():
    platforms = {0: (0.0,), 1: (0.3,), 2: (0.9,)}
    prompt = build_coalition_system_prompt_calibrated(
        [1, 2], initiator=0, initiator_seats=30, total_seats=100, majority_seats_threshold=50.0,
        party_platforms=platforms,
    )
    forbidden = ["minimal", "minimale", "stable", "small coalition", "petite coalition", "prefer", "privilegie"]
    lowered = prompt.lower()
    for term in forbidden:
        assert term not in lowered


def test_calibrated_coalition_prompt_round_one_is_byte_identical_to_omitting_round_number():
    platforms = {0: (0.0,), 1: (0.3,), 2: (0.9,)}
    args = ([1, 2], 0, 30, 100, 50.0, platforms)
    assert (
        build_coalition_system_prompt_calibrated(*args, round_number=1)
        == build_coalition_system_prompt_calibrated(*args)
    )


# ── build_pressure_*_prompt_toon (§5.E, diagnostic-only) ─────────────────

def _toon_pressure_context(cid, **overrides):
    return _pressure_context(cid, available=(0, 4), **overrides)


def test_pressure_user_prompt_toon_hoists_shared_facts_into_one_call_row():
    citizens = [_pressure_citizen(0), _pressure_citizen(1)]
    contexts = {
        0: _toon_pressure_context(0, target=7, mandate_dev=0.15, ticks_to_election=12, self_gap=0.08),
        1: _toon_pressure_context(1, target=7, mandate_dev=0.15, ticks_to_election=12, self_gap=1.42),
    }
    toon = build_pressure_user_prompt_toon(citizens, contexts)
    lines = toon.splitlines()
    assert lines[0] == "call[1]{target,mandate_dev,ticks_to_election}:"
    assert lines[1] == "7,0.15,12"
    assert lines[2] == "pressure[2]{cid,self_gap}:"
    assert lines[3] == "0,0.08"
    assert lines[4] == "1,1.42"


def test_pressure_user_prompt_toon_rejects_a_heterogeneous_target():
    citizens = [_pressure_citizen(0), _pressure_citizen(1)]
    contexts = {
        0: _toon_pressure_context(0, target=7),
        1: _toon_pressure_context(1, target=8),  # different target -- not a call-level constant here
    }
    with pytest.raises(ValueError, match="call-level constants"):
        build_pressure_user_prompt_toon(citizens, contexts)


def test_pressure_user_prompt_toon_rejects_an_open_menu():
    citizen = _pressure_citizen(0)
    context = _pressure_context(0, available=(0, 1, 2, 3, 4))  # not the shipped closed menu
    with pytest.raises(ValueError, match="closed menu"):
        build_pressure_user_prompt_toon([citizen], {0: context})


def test_pressure_user_prompt_toon_rejects_an_open_petition():
    citizen = _pressure_citizen(0)
    context = _toon_pressure_context(0, petition_open=True)
    with pytest.raises(ValueError, match="petition"):
        build_pressure_user_prompt_toon([citizen], {0: context})


def test_pressure_user_prompt_toon_rejects_a_tracked_neighbors_acting():
    citizen = _pressure_citizen(0)
    context = _toon_pressure_context(0, neighbors_acting=0.3)
    with pytest.raises(ValueError, match="neighbors_acting"):
        build_pressure_user_prompt_toon([citizen], {0: context})


def test_pressure_system_prompt_toon_still_enumerates_every_expected_cid():
    consulted = [_pressure_citizen(0), _pressure_citizen(1)]
    config = _config_with_llm_enabled()
    prompt = build_pressure_system_prompt_toon(consulted, config)
    assert "[0,1]" in prompt
    assert "EXACTEMENT ces 2" in prompt


def test_pressure_system_prompt_toon_explains_the_two_section_format():
    prompt = build_pressure_system_prompt_toon([_pressure_citizen(0)], _config_with_llm_enabled())
    assert "call[1]{target,mandate_dev,ticks_to_election}:" in prompt
    assert "pressure[N]{cid,self_gap}:" in prompt
    assert "7,0.15,12" in prompt  # the worked example


def test_pressure_system_prompt_toon_differs_from_json_only_in_the_ctx_explanation():
    # Isolates the format change: the menu constraint, legal-act table,
    # motif table, and expected-cid self-check must survive unchanged.
    consulted = [_pressure_citizen(0), _pressure_citizen(1)]
    config = _config_with_llm_enabled()
    json_lines = set(build_pressure_system_prompt(consulted, config).splitlines())
    toon_lines = set(build_pressure_system_prompt_toon(consulted, config).splitlines())
    shared = json_lines & toon_lines
    assert "Motifs valides (code court obligatoire) :" in shared
    assert any("CONTRAINTE ABSOLUE" in line for line in shared)


def test_toon_pressure_call_constants_rejects_a_null_ticks_to_election():
    from types import SimpleNamespace

    from polity_archived_builders import _toon_pressure_call_constants

    ctx = SimpleNamespace(target=1, mandate_dev=0.2, ticks_to_election=None)
    with pytest.raises(ValueError, match="null ticks_to_election"):
        _toon_pressure_call_constants([ctx, ctx])
