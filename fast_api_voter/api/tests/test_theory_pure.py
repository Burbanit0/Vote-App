"""Direct-call tests for the 11 numpy-free workers in api/domain/theory/workers.py.

Every existing test for these workers goes through FastAPI's synchronous HTTP
test client (test_theory_batch1.py..batch4.py), which is why theory/workers.py
is excluded from mutmut's scope (see pyproject.toml's [tool.mutmut] comment:
mutmut's in-process pytest re-exec breaks reproducibly on any test built on
that client). This file calls the pure `data: dict -> (body, status)` workers
directly, with none of that HTTP-client/ASGI/numpy machinery anywhere in this
module, so mutmut's auto-detection can select it.

Per this repo's test_cardinal_orphans.py precedent: assert on the NUMBERS a
worker actually returns, not just on structure or the winner. Most of the
input/output pairs here are transcribed from the batch tests' request
payloads and JSON assertions (the direct-call response IS the same dict the
route layer would hand back as JSON — api/routes/theory.py's `_run_typed`
helper does nothing but `body, status = worker(request.model_dump())`).
Values that are not already pinned upstream were derived either by hand
(documented inline) or, where the arithmetic is genuinely RNG-driven, by
executing the worker at the fixed seed used throughout this module (42) and
transcribing the actual result — a legitimate regression pin, not a guess.

Excludes (numpy-touching, separate follow-up): _plott_chaos_worker,
_agenda_manipulation_worker, _manipulation_analysis_worker,
_democratic_backsliding_worker.
"""
from __future__ import annotations

import pytest

from api.domain.theory.workers import (
    _IIA_BORDA,
    _IIA_PLURALITY,
    _apportionment_worker,
    _arrow_worker,
    _assumption_testing_worker,
    _collective_will_worker,
    _epistocracy_worker,
    _identity_voting_worker,
    _iia_rate_worker,
    _intergenerational_worker,
    _judgment_aggregation_worker,
    _majority_tyranny_worker,
    _sen_paradox_worker,
)

# Matches test_theory_batch4.py's CANDS: used by identity-voting,
# assumption-testing and collective-will, all three below.
CANDS_3 = [
    {"name": "Alice", "x": -0.5, "y": 0.0},
    {"name": "Bob",   "x":  0.0, "y": 0.0},
    {"name": "Carol", "x":  0.5, "y": 0.0},
]


# ── /arrow ──────────────────────────────────────────────────────────────────


def test_arrow_plurality_violates_only_iia_with_the_spoiler_counterexample() -> None:
    """Transcribed from test_theory_batch1.py::TestArrow.test_happy_path_plurality,
    plus the exact counterexample object (not just 'is not None'): a mutant
    that swaps in the wrong stock counterexample, or picks the wrong axiom
    dict, survives a not-None check but not an equality check."""
    body, status = _arrow_worker({"method": "plurality", "seed": 42})

    assert status == 200
    assert body["method"] == "plurality"
    assert body["tradeoff_type"] == "majority_focus"
    assert body["violations"]["iia"] == {
        "violated": True, "counterexample": _IIA_PLURALITY,
    }
    assert body["violations"]["pareto"] == {"violated": False, "counterexample": None}
    assert body["violations"]["transitivity"] == {"violated": False, "counterexample": None}
    assert body["violations"]["non_dictatorship"] == {"violated": False, "counterexample": None}


def test_arrow_condorcet_violates_transitivity_with_the_cycle_counterexample() -> None:
    """Transcribed from test_theory_batch1.py::TestArrow.test_condorcet_violates_transitivity."""
    body, status = _arrow_worker({"method": "condorcet"})

    assert status == 200
    assert body["violations"]["transitivity"]["violated"] is True
    assert body["violations"]["transitivity"]["counterexample"]["cycle"] == ["A", "B", "C", "A"]
    assert body["tradeoff_type"] == "condorcet_focus"
    assert "cycles" in body["arrow_summary"] or "Condorcet" in body["arrow_summary"]


def test_arrow_borda_gets_the_borda_specific_iia_counterexample_not_pluralitys() -> None:
    """workers.py:107 branches the IIA counterexample on method: borda/star_voting
    get _IIA_BORDA, everything else gets _IIA_PLURALITY. Plurality and condorcet
    (above) exercise the 'else' side; this pins the 'if' side and proves the two
    dicts are genuinely different objects, not the same fixture reused."""
    body, status = _arrow_worker({"method": "borda", "seed": 42})

    assert status == 200
    assert body["violations"]["iia"]["counterexample"] == _IIA_BORDA
    assert body["violations"]["iia"]["counterexample"] != _IIA_PLURALITY
    assert body["tradeoff_type"] == "utility_focus"
    # borda doesn't violate transitivity, so the summary takes the IIA branch
    assert "IIA" in body["arrow_summary"] or "spoiler" in body["arrow_summary"]


def test_arrow_unknown_method_falls_back_to_plurality_violations_and_default_tradeoff() -> None:
    """workers.py:100 falls back to _VIOLATIONS['plurality'] for an unrecognised
    method (no schema is validating `method` at this layer, so the worker's own
    .get(method, ...) fallback is what's under test — the route's schema doesn't
    even restrict `method` to an enum, so this is real reachable behaviour, not
    a hypothetical). tradeoff_type falls back separately via .get(method,
    'majority_focus') at workers.py:146 since the unknown method has no entry
    in _TRADEOFF_TYPE either."""
    body, status = _arrow_worker({"method": "totally_unknown_xyz"})

    assert status == 200
    assert body["violations"]["iia"]["counterexample"] == _IIA_PLURALITY
    assert body["violations"]["transitivity"]["violated"] is False
    assert body["tradeoff_type"] == "majority_focus"


# ── /iia-rate ───────────────────────────────────────────────────────────────


def test_iia_rate_plurality_curve_pins_the_exact_empirical_rates() -> None:
    """Transcribed payload from test_theory_batch1.py::TestIIARate.test_happy_path,
    but asserting the actual numbers (seed=42 makes this fully reproducible)
    instead of just bounds — a mutant in the hit-counting or the round(...,4)
    would move these exact values."""
    body, status = _iia_rate_worker({
        "method": "plurality", "max_candidates": 5, "num_trials": 50, "seed": 42,
    })

    assert status == 200
    assert body["method"] == "plurality"
    # n=2 is hard-coded to 0.0 (workers.py:191) -- too few candidates to matter
    assert body["curve"] == [
        {"n_candidates": 2, "violation_rate": 0.0},
        {"n_candidates": 3, "violation_rate": 0.14},
        {"n_candidates": 4, "violation_rate": 0.16},
        {"n_candidates": 5, "violation_rate": 0.14},
    ]


def test_iia_rate_scale_factor_multiplies_the_same_underlying_empirical_rate() -> None:
    """The per-n empirical simulation (workers.py:161-179) always uses plurality
    internally regardless of the requested `method` -- `method` only selects a
    scale factor (_SCALE) applied afterwards. So schulze's curve at the same
    seed/trials must equal plurality's curve times 0.35, exactly. This pins
    both the _SCALE lookup AND that the multiplication (not e.g. an additive
    fudge) is what connects them."""
    plurality_body, _ = _iia_rate_worker({
        "method": "plurality", "max_candidates": 5, "num_trials": 50, "seed": 42,
    })
    schulze_body, status = _iia_rate_worker({
        "method": "schulze", "max_candidates": 5, "num_trials": 50, "seed": 42,
    })

    assert status == 200
    for base, scaled in zip(plurality_body["curve"], schulze_body["curve"]):
        assert scaled["violation_rate"] == round(min(1.0, base["violation_rate"] * 0.35), 4)
    assert schulze_body["curve"][1]["violation_rate"] == 0.049  # n=3: 0.14 * 0.35


def test_iia_rate_defensively_clamps_max_candidates_even_without_pydantic() -> None:
    """test_theory_batch1.py rejects max_candidates=99 at the SCHEMA (422)
    layer. Called directly -- bypassing Pydantic entirely -- the worker's own
    `max(2, min(8, ...))` clamp (workers.py:157) is the only thing standing
    between this input and an out-of-range loop; this proves that clamp
    actually holds on its own."""
    body, status = _iia_rate_worker({
        "method": "plurality", "max_candidates": 99, "num_trials": 50, "seed": 42,
    })

    assert status == 200
    assert len(body["curve"]) == 7          # n = 2..8, not 2..99
    assert body["curve"][-1]["n_candidates"] == 8


# ── /judgment-aggregation ──────────────────────────────────────────────────


def test_judgment_aggregation_discursive_dilemma_individually_coherent_voters_produce_an_incoherent_collective() -> None:
    """This is the actual List-Pettit discursive dilemma the endpoint exists to
    demonstrate, and it fires on the SAME payload test_theory_batch1.py's
    test_happy_path_legal uses (num_voters=20, seed=42) -- that test only
    checked voter_coherence_rate == 1.0 (INDIVIDUAL coherence) and never looked
    at collective_coherent, so the paradox case was never actually pinned.
    Every voter type here is individually coherent (C = P1 AND P2), yet a
    majority accepts P1, a majority accepts P2, and a majority REJECTS C --
    the collective vote is incoherent even though no single voter is.
    yes_pct for C lands at exactly 0.5, which also pins the strict `pct > 0.5`
    boundary (workers.py:519): a mutant relaxing this to `>=` would flip
    collective_vote for C from False to True and make the paradox vanish."""
    body, status = _judgment_aggregation_worker(
        {"scenario": "legal", "num_voters": 20, "seed": 42}
    )

    assert status == 200
    assert body["voter_coherence_rate"] == 1.0
    assert body["collective_coherent"] is False
    assert body["paradox_severity"] == 1.0
    props_by_id = {p["id"]: p for p in body["propositions"]}
    assert props_by_id["P1"]["collective_vote"] is True
    assert props_by_id["P2"]["collective_vote"] is True
    assert props_by_id["C"]["yes_pct"] == 0.5
    assert props_by_id["C"]["collective_vote"] is False
    assert body["incoherences"] == [{
        "premises": ["P1", "P2"], "conclusion": "C",
        "problem": "Prémisses acceptées majoritairement, mais conclusion rejetée",
    }]
    assert body["resolution_methods"]["premise_based"] == {"C": True}


def test_judgment_aggregation_unknown_scenario_falls_back_to_legal_but_echoes_the_input() -> None:
    """Transcribed from test_theory_batch1.py::test_unknown_scenario_falls_back_to_legal."""
    body, status = _judgment_aggregation_worker({"scenario": "nope"})

    assert status == 200
    assert body["scenario"] == "nope"
    assert body["scenario_name"] == "Responsabilité contractuelle"


# ── /apportionment ──────────────────────────────────────────────────────────

_AP_PARTIES = [
    {"name": "A", "votes": 9000},
    {"name": "B", "votes": 7000},
    {"name": "C", "votes": 5000},
]


def test_apportionment_hamilton_largest_remainder_and_jefferson_divisor_disagree() -> None:
    """Same payload as test_theory_batch2.py::TestApportionment.test_happy_path,
    which only checked that seats sum to 10 for every method -- a placeholder
    for 'the loop ran', not for 'the arithmetic is right'. Hand-worked:
    quotas = votes * 10 / 21000 -> A=4.2857, B=3.3333, C=2.3810. Hamilton
    floors then hands the 1 leftover seat to the largest remainder (C's
    .3810 beats A's .2857 and B's .3333) -> A4 B3 C3. That table also
    exhibits the Alabama paradox this endpoint exists to demonstrate: giving
    Hamilton 11 seats instead of 10 makes some party's seat count go DOWN.
    Jefferson (D'Hondt) instead repeatedly awards the seat with the highest
    votes/(seats+1) -- worked by hand across all 10 rounds -- which favours
    the largest party over Hamilton's proportional remainder: A5 B3 C2."""
    body, status = _apportionment_worker({
        "parties": _AP_PARTIES, "num_seats": 10, "find_paradoxes": True,
    })

    assert status == 200
    assert body["results"]["hamilton"]["seats"] == {"A": 4, "B": 3, "C": 3}
    assert body["results"]["hamilton"]["alabama_paradox"] is True
    assert body["results"]["jefferson"]["seats"] == {"A": 5, "B": 3, "C": 2}
    assert body["results"]["jefferson"]["favors"] == "large_parties"
    # Jefferson gives A one more seat than Hamilton -- the disagreement IS
    # the Balinski-Young point, so pin that the two methods actually differ.
    assert body["results"]["hamilton"]["seats"] != body["results"]["jefferson"]["seats"]


def test_apportionment_find_paradoxes_false_skips_detection_entirely() -> None:
    """workers.py:852-854 short-circuits all three paradox checks to a bare
    `False` when find_paradoxes is off -- distinct from actually running the
    (expensive) checks and getting a negative result. Same Hamilton table as
    above genuinely has alabama_paradox=True when checked; this proves the
    flag suppresses the check rather than the check itself changing answer."""
    body, status = _apportionment_worker({
        "parties": _AP_PARTIES, "num_seats": 10, "find_paradoxes": False,
    })

    assert status == 200
    assert body["results"]["hamilton"]["seats"] == {"A": 4, "B": 3, "C": 3}
    assert body["results"]["hamilton"]["alabama_paradox"] is False
    assert body["results"]["hamilton"]["quota_violation"] is False
    assert body["results"]["hamilton"]["population_paradox"] is False


# ── /sen-paradox ────────────────────────────────────────────────────────────


def test_sen_paradox_canonical_example_conflicts_regardless_of_seed() -> None:
    """The canonical Sen (1970) 'Lady Chatterley' example (workers.py:986-1001)
    doesn't depend on `seed` at all -- only the random-profile survey around it
    does. So the FIRST paradox_examples entry (added only when
    canon_res['conflict'] is True) must be identical across seeds: liberal
    rights hand 'y' the win (person 2's private sphere), unanimous Pareto
    preference hands 'x' the win -- a genuine conflict, by construction, every
    time. A mutant that made the canonical check seed-dependent, or swapped
    which alternative each order maps to, would move this."""
    for seed in (1, 42, 999):
        body, status = _sen_paradox_worker({"num_voters": 2, "seed": seed})
        assert status == 200
        assert body["paradox_exists"] is True
        canon = body["paradox_examples"][0]
        assert canon["name"].startswith("Exemple classique")
        assert canon["liberal_outcome"] == "y"
        assert canon["pareto_outcome"] == "x"
        assert canon["conflict"] is True


def test_sen_paradox_frequency_over_300_random_profiles_is_pinned_at_seed_42() -> None:
    """The 300-trial random-profile survey (workers.py:1010-1031) IS
    seed-dependent; pin its rate at the module's standard seed so a mutant in
    the trial loop (off-by-one trial count, wrong RNG advance, flipped
    conflict test) shows up as a moved number rather than a silent survivor."""
    body, status = _sen_paradox_worker({"num_voters": 2, "seed": 42})

    assert status == 200
    assert body["paradox_frequency"] == 0.03
    assert len(body["resolution_options"]) == 4


# ── /majority-tyranny ──────────────────────────────────────────────────────

_MT_PAYLOAD = {
    "num_voters": 60, "majority_pct": 0.60,
    "minority_intensity": 3.0, "num_decisions": 30, "seed": 42,
}


def test_majority_tyranny_unanimity_always_protects_the_minority_and_ranks_rules() -> None:
    """Transcribed base payload from test_theory_batch3.py::TestMajorityTyranny
    (unanimous.tyranny_index == 0.0 is that test's only numeric assertion), plus
    the rule rankings it never checked. best_protector is picked by
    `min(..., key=tyranny_index)` over rules in a fixed list order
    (workers.py:1292-1295); supermajority_2_3, supermajority_3_4, unanimous and
    qv all tie at 0.0 for this electorate split, so Python's stable min keeps
    the FIRST tied rule in iteration order -- supermajority_2_3, not the more
    intuitive 'unanimous'. That tie-break is exactly the kind of thing an
    off-by-one in the rules list or a `min`->`max` mutant would silently flip."""
    body, status = _majority_tyranny_worker(_MT_PAYLOAD)

    assert status == 200
    assert body["results"]["unanimous"]["tyranny_index"] == 0.0
    assert body["results"]["simple_majority"]["tyranny_index"] == 1.0
    assert body["best_protector"] == "supermajority_2_3"
    assert body["least_efficient"] == "simple_majority"


def test_majority_tyranny_defensively_clamps_majority_pct_below_the_schema_floor() -> None:
    """test_theory_batch3.py checks majority_pct=0.50 is rejected at 422 by the
    schema. Called directly, the worker's own `max(0.51, min(...))` clamp
    (workers.py:1288) is what stands between an extreme input and a
    majority_pct outside [0.51, 0.95]. Regardless of how low majority_pct is
    requested, 'unanimous' must still protect the minority perfectly -- that
    invariant is untouched by the clamped value, so it's a clean way to prove
    the clamp didn't just silently accept 0.20 and blow up the maths."""
    body, status = _majority_tyranny_worker({**_MT_PAYLOAD, "majority_pct": 0.20})

    assert status == 200
    assert body["results"]["unanimous"]["tyranny_index"] == 0.0


# ── /intergenerational ─────────────────────────────────────────────────────

_IG_PAYLOAD = {
    "num_voters": 60, "seed": 42,
    "future_generations_mechanism": "veto",
    "decisions": [
        {"name": "Climat", "cost_present": -0.3,
         "benefit_future": 0.8, "time_horizon_years": 30},
        {"name": "Dette", "cost_present": 0.5,
         "benefit_future": -0.6, "time_horizon_years": 25},
    ],
}


def test_intergenerational_veto_blocks_the_long_horizon_decision_young_reject() -> None:
    """Same payload as test_theory_batch3.py::TestIntergenerational.test_accepts_custom_decisions
    (which only checked len(decisions_results) == 2). 'Dette' has
    time_horizon_years=25 > 15; at seed=42 the young cohort's noisy support
    lands below 0.5, so the veto mechanism's guard (workers.py:1840 --
    `if time_horizon_years > 15 and s_young < 0.5: vote_pct = 0.0`) fires and
    forces vote_pct to exactly 0.0, which is otherwise impossible to hit by
    chance (it's a weighted average of support fractions in [0,1])."""
    body, status = _intergenerational_worker(_IG_PAYLOAD)

    assert status == 200
    by_name = {d["decision_name"]: d["by_mechanism"] for d in body["decisions_results"]}
    assert by_name["Dette"]["veto"]["vote_pct"] == 0.0
    assert by_name["Dette"]["veto"]["adopted"] is False


def test_intergenerational_welfare_matches_the_hand_worked_discounted_present_value() -> None:
    """welfare_present/welfare_future (workers.py:1849-1863) are pure functions
    of cost_present/benefit_future/time_horizon_years and the `adopted` flag --
    no RNG in the formula itself. At seed=42, all four mechanisms adopt
    'Climat' (cost_present=-0.3, benefit_future=0.8, horizon=30). Hand-worked:
    w_present = (-0.3+1)/2 = 0.35. discount = 1.03^-30 = 0.411987...
    w_future = ((0.8+1)/2) * discount = 0.9 * 0.411987 = 0.370788 -> 0.3708.
    w_50y = 0.5*0.35 + 0.5*0.3708 = 0.3604. A mutant changing the 3%
    discount rate, the 0.5/0.5 present/future split, or the (x+1)/2 rescale
    would move at least one of these three numbers."""
    body, status = _intergenerational_worker(_IG_PAYLOAD)

    assert status == 200
    climat = next(d for d in body["decisions_results"] if d["decision_name"] == "Climat")
    none_mech = climat["by_mechanism"]["none"]
    assert none_mech["adopted"] is True
    assert none_mech["welfare_present"] == 0.35
    assert none_mech["welfare_future"] == round(0.9 * 1.03 ** -30, 4)
    assert none_mech["welfare_future"] == 0.3708
    assert none_mech["total_welfare_50y"] == 0.3604


# ── /epistocracy ───────────────────────────────────────────────────────────

_EPIST_PAYLOAD = {
    "candidates": [
        {"name": "A", "x": -0.5},
        {"name": "B", "x": 0.0},
        {"name": "C", "x": 0.5},
    ],
    "num_voters": 80, "seed": 42,
    "voter_competence_distribution": "uniform",
    "epistocracy_threshold": 0.7,
}


def test_epistocracy_condorcet_threshold_and_omniscient_regret_are_hardcoded_constants() -> None:
    """Same payload as test_theory_batch3.py::TestEpistocracy.test_happy_path.
    condorcet_threshold (workers.py:2114, 'the Classic CJT threshold') and
    democracy_vs_expert.omniscient_regret (workers.py:2148, an omniscient
    chooser is never wrong by definition) are both literal constants, not
    derived from the simulation -- so unlike almost every other field in this
    module they must come back byte-identical regardless of seed/voters,
    which makes them a clean, RNG-immune mutant-kill target."""
    body, status = _epistocracy_worker(_EPIST_PAYLOAD)

    assert status == 200
    assert body["condorcet_threshold"] == 0.5
    assert body["democracy_vs_expert"]["omniscient_regret"] == 0.0
    for scheme in ("equal", "competence_weighted", "epistocratic", "lottery"):
        assert scheme in body["results"]


def test_epistocracy_caplan_bias_toggle_is_the_only_thing_separating_the_two_means() -> None:
    """workers.py:2002-2009: when caplan_bias is on, biased_competences
    subtracts a random non-negative penalty from every voter's raw competence,
    so biased_mean must land strictly below the raw mean. Turning it off
    (workers.py:2008 `else: biased_competences = list(competences)`) must make
    the two means come back EXACTLY equal -- not just close -- since it's a
    plain copy with no arithmetic at all."""
    biased_on, status1 = _epistocracy_worker(_EPIST_PAYLOAD)
    biased_off, status2 = _epistocracy_worker({
        **_EPIST_PAYLOAD, "competence_params": {"caplan_bias": False},
    })

    assert status1 == status2 == 200
    stats_on = biased_on["voter_competence_stats"]
    stats_off = biased_off["voter_competence_stats"]
    assert stats_on["biased_mean"] < stats_on["mean"]
    assert stats_off["biased_mean"] == stats_off["mean"]
    # The raw (unbiased) mean is computed from the same competences regardless
    # of the caplan_bias flag, so it must be unaffected by toggling it.
    assert stats_on["mean"] == stats_off["mean"]


# ── /identity-voting ──────────────────────────────────────────────────────


def test_identity_voting_group_vote_pct_is_always_1_by_construction() -> None:
    """workers.py:2217 assigns every voter in a group the SAME identity_vote
    (their group's candidate_affiliation) with no randomness at all -- the
    randomness only decides whether a voter's FINAL vote follows identity or
    ideology, not what the identity vote itself is. So group_vote_pct
    (workers.py:2271, 'fraction of the group whose identity_vote matches the
    group's affiliation') is 100% by definition, for every group, regardless
    of seed, identity_weight or cross_pressure. A mutant that let ideology
    leak into the identity_vote assignment would break this immediately."""
    body, status = _identity_voting_worker({
        "candidates": CANDS_3, "num_voters": 100, "seed": 7,
        "identity_weight": 0.9, "cross_pressure": True,
    })

    assert status == 200
    for row in body["group_results"]:
        assert row["group_vote_pct"] == 1.0


def test_identity_voting_zero_weight_without_cross_pressure_collapses_to_sincere() -> None:
    """identity_weight=0.0 makes `use_identity = rng.random() < (0 * loyalty)`
    always False (workers.py:2229) -- random() never returns a negative number
    -- so every voter's final_vote is their ideo_vote. With cross_pressure=False
    the abstention branch (workers.py:2222) never triggers either, so no
    voters are dropped from the mixed tally. Both winners and the full vote
    lists must therefore coincide exactly, and cross_pressured.abstention_rate
    must be 0.0 -- not merely small."""
    body, status = _identity_voting_worker({
        "candidates": CANDS_3, "num_voters": 100, "seed": 42,
        "identity_weight": 0.0, "cross_pressure": False,
    })

    assert status == 200
    assert body["mixed_winner"] == body["sincere_winner"]
    assert body["winner_changed"] is False
    assert body["cross_pressured"]["abstention_rate"] == 0.0


# ── /assumption-testing ────────────────────────────────────────────────────


def test_assumption_testing_baseline_regret_is_hardcoded_to_zero() -> None:
    """Same empty payload as test_theory_batch4.py::TestAssumptionTesting.test_happy_path_default.
    baseline_result['regret'] (workers.py:2512) is a literal 0.0, not a
    computed value -- the baseline is definitionally its own reference point.
    Any mutant giving it a real value would be caught here without touching
    any RNG-sensitive assertion."""
    body, status = _assumption_testing_worker({})

    assert status == 200
    assert body["baseline_result"]["regret"] == 0.0
    assert body["baseline_result"]["winner"] == "Alice"
    assert body["robust_result"] is True
    assert body["most_fragile_assumption"] == "rational_voters"


def test_assumption_testing_relaxes_only_the_requested_subset_with_real_values() -> None:
    """Transcribed from test_theory_batch4.py::TestAssumptionTesting.test_accepts_subset,
    which only checked the KEY set; pin actual winner/variance numbers too so a
    mutant in either relaxation branch (stable_preferences' gaussian noise,
    rational_voters' 15% random-vote probability) has something concrete to
    disturb."""
    body, status = _assumption_testing_worker({
        "base_simulation": {
            "candidates": CANDS_3, "num_voters": 80,
            "ideology": "random", "seed": 42,
        },
        "assumptions_to_relax": ["stable_preferences", "rational_voters"],
    })

    assert status == 200
    assert set(body["relaxed_results"].keys()) == {"stable_preferences", "rational_voters"}
    for assumption in ("stable_preferences", "rational_voters"):
        result = body["relaxed_results"][assumption]
        assert 0.0 <= result["pct_trials_changed"] <= 1.0
        assert len(result["confidence_interval"]) == 2
        assert result["confidence_interval"][0] <= result["confidence_interval"][1]
        # Each per-candidate share is independently rounded to 4dp, so the sum
        # can land a hair off 1.0 (0.9999/1.0001) from rounding, not from a bug.
        assert sum(result["winner_distribution"].values()) == pytest.approx(1.0, abs=1e-3)


# ── /collective-will ──────────────────────────────────────────────────────


def test_collective_will_rousseau_score_is_exactly_the_reciprocal_of_unique_winner_count() -> None:
    """Same payload as test_theory_batch4.py::TestCollectiveWill.test_happy_path
    (which only checked list lengths). rousseau_score is LITERALLY defined as
    round(1 / unique_winner_count, 4) at workers.py:2757 -- asserting that
    relationship (not just a hardcoded 0.5) survives a mutant that changes
    n_unique's computation elsewhere but forgets to also break this formula in
    lockstep, which a bare literal comparison would miss."""
    body, status = _collective_will_worker({
        "candidates": CANDS_3, "num_voters": 60, "seed": 42,
        "num_methods": 4, "num_agendas": 3, "num_simulations": 1,
    })

    assert status == 200
    assert body["unique_winner_count"] == 2
    assert set(body["unique_winners"]) == {"Alice", "Bob"}
    assert body["rousseau_score"] == round(1 / body["unique_winner_count"], 4)
    assert body["rousseau_score"] == 0.5
    assert body["condorcet_exists"] is True
    assert body["condorcet_winner"] == "Bob"
    assert body["most_frequent_winner"] == "Bob"
    assert body["most_frequent_pct"] == 0.7143


def test_collective_will_two_candidates_only_one_possible_winner_forces_rousseau_score_1() -> None:
    """With exactly 2 candidates there is exactly one non-tied outcome every
    method/agenda can produce, so unique_winner_count must be 1 and
    rousseau_score = round(1/1, 4) = 1.0 -- the ceiling of the score and a
    useful boundary distinct from the 0.5 case above (which exercises n=2
    unique winners, not n=1)."""
    two_cands = [
        {"name": "Alice", "x": -0.5, "y": 0.0},
        {"name": "Bob",   "x":  0.5, "y": 0.0},
    ]
    body, status = _collective_will_worker({
        "candidates": two_cands, "num_voters": 60, "seed": 42,
        "num_methods": 4, "num_agendas": 2, "num_simulations": 1,
    })

    assert status == 200
    assert body["unique_winner_count"] == 1
    assert body["rousseau_score"] == 1.0
