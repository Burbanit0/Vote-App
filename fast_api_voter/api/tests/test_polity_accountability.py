"""v4 Lots 2-5 — accountability.py: mandate_deviation, self_gap, term limits,
current_office_holders, the awakening gate, mobilization, and (Lot 5) the
petition state machine. Measurement/gating only through Lot 4 (§7bis.5/
§6bis.1/§7bis.9) -- none of that decides anything; Lots 6-7 are the first
real callers of most of it, deterministic_pressure_action (simple_rules.py)
is the first real caller of select_consulted's output. Lot 5's petition
functions are this module's first mutations.
"""
import pytest

from api.domain.polity.accountability import (
    applicable_pressure_act,
    awakening_threshold,
    current_office_holders,
    election_proximity,
    is_term_limited,
    launch_petition,
    mandate_deviation,
    petition_accepts_signatures,
    petition_has_expired,
    petition_is_launchable,
    petition_pressure,
    pledge_weights,
    reset_petition_state,
    resolve_petition,
    select_consulted,
    self_gap,
    sign_petition,
    ticks_to_election,
    update_street_pressure,
    weighted_euclidean,
)
from api.domain.polity.citizen import Citizen, Office, Role
from api.domain.polity.codebook import PressureAct
from api.domain.polity.config import (
    AwakeningConfig,
    AwakeningContextModulation,
    MandateConfig,
    PetitionConfig,
    StreetPressureConfig,
)
from api.domain.polity.simple_rules import _weighted_distance


def _citizen(citizen_id, positions, priorities=None, **kwargs):
    k = len(positions)
    priorities = priorities or tuple(1.0 / k for _ in range(k))
    return Citizen(
        citizen_id=citizen_id,
        issue_positions=tuple(positions),
        issue_priorities=tuple(priorities),
        blank_threshold=0.5,
        ambition_score=0.5,
        **kwargs,
    )


_FULL_PLATFORM_CONFIG = MandateConfig(
    enabled=True,
    pledge_scope="full_platform",
    pledge_top_k=5,
    deviation_metric="weighted_euclidean",
    deviation_log_threshold=0.1,
    max_response_delta=0.3,
    max_response_shifts=3,
)

_TOP_K_CONFIG = MandateConfig(
    enabled=True,
    pledge_scope="top_k_priorities",
    pledge_top_k=2,
    deviation_metric="weighted_euclidean",
    deviation_log_threshold=0.1,
    max_response_delta=0.3,
    max_response_shifts=3,
)


# ── weighted_euclidean ───────────────────────────────────────────────────

def test_weighted_euclidean_matches_simple_rules_weighted_distance():
    voter = _citizen(1, (0.2, 0.7), priorities=(0.6, 0.4))
    platform = (0.5, 0.1)
    assert weighted_euclidean(voter.issue_positions, platform, voter.issue_priorities) == _weighted_distance(
        voter, platform
    )


# ── mandate_deviation ────────────────────────────────────────────────────

def test_mandate_deviation_is_zero_when_platforms_are_equal():
    officeholder = _citizen(
        1, (0.5, 0.5), pledged_platform=(0.3, 0.3), revealed_position=(0.3, 0.3),
    )
    assert mandate_deviation(officeholder, _FULL_PLATFORM_CONFIG) == 0.0


def test_mandate_deviation_hand_computed_full_platform():
    officeholder = _citizen(
        1, (0.5, 0.5), priorities=(0.6, 0.4), pledged_platform=(0.0, 0.0), revealed_position=(0.5, 0.0),
    )
    # sqrt(0.6 * 0.5**2) = sqrt(0.15)
    assert mandate_deviation(officeholder, _FULL_PLATFORM_CONFIG) == pytest.approx((0.6 * 0.25) ** 0.5)


def test_top_k_priorities_zeroes_out_low_priority_dimensions():
    officeholder = _citizen(
        1, (0.0, 0.0, 0.0, 0.0), priorities=(0.4, 0.3, 0.2, 0.1),
        pledged_platform=(0.0, 0.0, 0.0, 0.0), revealed_position=(0.0, 0.0, 0.0, 0.5),
    )
    config = MandateConfig(**{**_TOP_K_CONFIG.__dict__, "pledge_top_k": 2})
    # dim 3 (priority 0.1) is outside the top-2 (dims 0, 1) -- fully zeroed.
    assert mandate_deviation(officeholder, config) == 0.0


def test_top_k_priorities_renormalizes_kept_weights_above_full_platform():
    officeholder = _citizen(
        1, (0.0, 0.0, 0.0, 0.0), priorities=(0.4, 0.3, 0.2, 0.1),
        pledged_platform=(0.0, 0.0, 0.0, 0.0), revealed_position=(0.5, 0.0, 0.0, 0.0),
    )
    top_k = MandateConfig(**{**_TOP_K_CONFIG.__dict__, "pledge_top_k": 2})
    full = MandateConfig(**{**_FULL_PLATFORM_CONFIG.__dict__})
    # top-2 weight on dim 0 renormalizes 0.4 -> 0.4/0.7, strictly above the
    # raw full-platform weight of 0.4 -- pledge_scope is a scope change, not
    # a scale change.
    assert mandate_deviation(officeholder, top_k) > mandate_deviation(officeholder, full)


def test_top_k_priorities_ties_broken_by_ascending_dimension_index():
    officeholder_dim0 = _citizen(
        1, (0.0, 0.0), priorities=(0.5, 0.5), pledged_platform=(0.0, 0.0), revealed_position=(0.5, 0.0),
    )
    officeholder_dim1 = _citizen(
        2, (0.0, 0.0), priorities=(0.5, 0.5), pledged_platform=(0.0, 0.0), revealed_position=(0.0, 0.5),
    )
    config = MandateConfig(**{**_TOP_K_CONFIG.__dict__, "pledge_top_k": 1})
    # A tie at priority 0.5 keeps dim 0 (ascending index), so a deviation on
    # dim 0 counts and a deviation on dim 1 is fully zeroed.
    assert mandate_deviation(officeholder_dim0, config) > 0.0
    assert mandate_deviation(officeholder_dim1, config) == 0.0


def test_pledge_top_k_larger_than_issue_count_degrades_to_full_platform():
    priorities = (0.5, 0.5)
    config = MandateConfig(**{**_TOP_K_CONFIG.__dict__, "pledge_top_k": 10})
    assert pledge_weights(priorities, config) == priorities


def test_unsupported_deviation_metric_raises():
    officeholder = _citizen(
        1, (0.5, 0.5), pledged_platform=(0.0, 0.0), revealed_position=(0.5, 0.5),
    )
    config = MandateConfig(**{**_FULL_PLATFORM_CONFIG.__dict__, "deviation_metric": "cosine"})
    with pytest.raises(NotImplementedError, match="deviation_metric"):
        mandate_deviation(officeholder, config)


def test_unsupported_pledge_scope_raises():
    with pytest.raises(NotImplementedError, match="pledge_scope"):
        pledge_weights((0.5, 0.5), MandateConfig(**{**_FULL_PLATFORM_CONFIG.__dict__, "pledge_scope": "median"}))


def test_mandate_deviation_raises_without_a_pledged_or_revealed_position():
    officeholder = _citizen(1, (0.5, 0.5))
    with pytest.raises(ValueError, match="pledged_platform"):
        mandate_deviation(officeholder, _FULL_PLATFORM_CONFIG)


# ── self_gap ──────────────────────────────────────────────────────────────

def test_self_gap_is_zero_when_citizen_sits_on_the_revealed_position():
    officeholder = _citizen(1, (0.5, 0.5), revealed_position=(0.3, 0.7))
    citizen = _citizen(2, (0.3, 0.7))
    assert self_gap(citizen, officeholder) == 0.0


def test_self_gap_hand_computed():
    officeholder = _citizen(1, (0.5, 0.5), revealed_position=(0.5, 0.0))
    citizen = _citizen(2, (0.0, 0.0), priorities=(0.6, 0.4))
    assert self_gap(citizen, officeholder) == pytest.approx((0.6 * 0.25) ** 0.5)


def test_self_gap_raises_without_a_revealed_position():
    officeholder = _citizen(1, (0.5, 0.5))
    citizen = _citizen(2, (0.3, 0.7))
    with pytest.raises(ValueError, match="revealed_position"):
        self_gap(citizen, officeholder)


# ── is_term_limited ──────────────────────────────────────────────────────

def test_is_term_limited_truth_table():
    below = _citizen(1, (0.5,), mandates_served=1)
    at_limit = _citizen(2, (0.5,), mandates_served=2)
    above = _citizen(3, (0.5,), mandates_served=3)
    assert is_term_limited(below, term_limit=2) is False
    assert is_term_limited(at_limit, term_limit=2) is True
    assert is_term_limited(above, term_limit=2) is True


def test_is_term_limited_with_no_limit_configured_is_always_false():
    prolific = _citizen(1, (0.5,), mandates_served=99)
    assert is_term_limited(prolific, term_limit=None) is False


# ── current_office_holders ───────────────────────────────────────────────

def test_current_office_holders_is_empty_with_no_president():
    citizens = [_citizen(1, (0.5,)), _citizen(2, (0.5,))]
    assert current_office_holders(citizens, Office.PRESIDENT) == []


def test_current_office_holders_returns_the_sitting_president():
    president = _citizen(1, (0.5,), role=Role.ELECTED, office=Office.PRESIDENT)
    elector = _citizen(2, (0.5,))
    assert current_office_holders([elector, president], Office.PRESIDENT) == [president]


def test_current_office_holders_is_sorted_by_citizen_id():
    higher = _citizen(5, (0.5,), role=Role.ELECTED, office=Office.PRESIDENT)
    lower = _citizen(2, (0.5,), role=Role.ELECTED, office=Office.PRESIDENT)
    result = current_office_holders([higher, lower], Office.PRESIDENT)
    assert [c.citizen_id for c in result] == [2, 5]


# ── ticks_to_election (v4 Lot 6) ─────────────────────────────────────────

def test_ticks_to_election_is_none_with_no_office_holder():
    assert ticks_to_election(tick=10, term_end_tick=None) is None


def test_ticks_to_election_mid_term():
    assert ticks_to_election(tick=4, term_end_tick=16) == 12


def test_ticks_to_election_one_tick_before_the_next_election():
    assert ticks_to_election(tick=15, term_end_tick=16) == 1


# ── election_proximity ───────────────────────────────────────────────────

def test_election_proximity_is_zero_with_no_office_holder():
    assert election_proximity(tick=10, term_end_tick=None, term_ticks=16) == 0.0


def test_election_proximity_is_zero_just_after_an_election():
    # tick == term_end_tick - term_ticks -> ticks_to_election == term_ticks
    assert election_proximity(tick=0, term_end_tick=16, term_ticks=16) == 0.0


def test_election_proximity_is_near_one_just_before_the_next_election():
    assert election_proximity(tick=15, term_end_tick=16, term_ticks=16) == pytest.approx(15 / 16)


def test_election_proximity_clamps_to_one_when_ticks_to_election_is_negative():
    assert election_proximity(tick=20, term_end_tick=16, term_ticks=16) == 1.0


@pytest.mark.parametrize(
    "tick,term_end_tick,term_ticks",
    [(0, 16, 16), (4, 16, 16), (15, 16, 16), (20, 16, 16), (10, None, 16)],
)
def test_election_proximity_is_unchanged_by_the_ticks_to_election_extraction(tick, term_end_tick, term_ticks):
    # Behavior-preserving refactor pin: election_proximity now delegates to
    # ticks_to_election, re-derived by hand here against the original formula.
    remaining = ticks_to_election(tick, term_end_tick)
    expected = 0.0 if remaining is None else max(0.0, min(1.0, 1.0 - remaining / term_ticks))
    assert election_proximity(tick, term_end_tick, term_ticks) == expected


# ── awakening_threshold ──────────────────────────────────────────────────

_MODULATION_ALL_ON = AwakeningContextModulation(
    mandate_deviation=True, ticks_to_election=True, neighbors_acting=False
)

_AWAKENING_CONFIG = AwakeningConfig(
    enabled=True,
    source="persona_base_threshold",
    context_modulation=_MODULATION_ALL_ON,
    modulation_amplitude=0.5,
    no_consultation_cap=True,
)


def test_awakening_threshold_with_zero_amplitude_returns_base_threshold_exactly():
    config = AwakeningConfig(**{**_AWAKENING_CONFIG.__dict__, "modulation_amplitude": 0.0})
    citizen = _citizen(1, (0.5,), base_threshold=0.4)
    for dev, prox in [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)]:
        assert awakening_threshold(citizen, mandate_dev=dev, proximity=prox, config=config) == pytest.approx(0.4)


def test_awakening_threshold_stays_within_the_amplitude_bounds():
    citizen = _citizen(1, (0.5,), base_threshold=0.4)
    amp = _AWAKENING_CONFIG.modulation_amplitude
    lo = 0.4 * (1 - amp)
    hi = 0.4 * (1 + amp)
    for dev, prox in [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)]:
        result = awakening_threshold(citizen, mandate_dev=dev, proximity=prox, config=_AWAKENING_CONFIG)
        assert lo - 1e-9 <= result <= hi + 1e-9


def test_awakening_threshold_higher_deviation_strictly_lowers_it():
    citizen = _citizen(1, (0.5,), base_threshold=0.4)
    low_dev = awakening_threshold(citizen, mandate_dev=0.1, proximity=0.5, config=_AWAKENING_CONFIG)
    high_dev = awakening_threshold(citizen, mandate_dev=0.9, proximity=0.5, config=_AWAKENING_CONFIG)
    assert high_dev < low_dev


def test_awakening_threshold_higher_proximity_strictly_raises_it():
    citizen = _citizen(1, (0.5,), base_threshold=0.4)
    far = awakening_threshold(citizen, mandate_dev=0.5, proximity=0.1, config=_AWAKENING_CONFIG)
    near = awakening_threshold(citizen, mandate_dev=0.5, proximity=0.9, config=_AWAKENING_CONFIG)
    assert near > far


def test_awakening_threshold_ignores_deviation_when_its_modulation_flag_is_off():
    modulation = AwakeningContextModulation(mandate_deviation=False, ticks_to_election=True, neighbors_acting=False)
    config = AwakeningConfig(**{**_AWAKENING_CONFIG.__dict__, "context_modulation": modulation})
    citizen = _citizen(1, (0.5,), base_threshold=0.4)
    low = awakening_threshold(citizen, mandate_dev=0.1, proximity=0.5, config=config)
    high = awakening_threshold(citizen, mandate_dev=0.9, proximity=0.5, config=config)
    assert low == pytest.approx(high)


def test_awakening_threshold_ignores_proximity_when_its_modulation_flag_is_off():
    modulation = AwakeningContextModulation(mandate_deviation=True, ticks_to_election=False, neighbors_acting=False)
    config = AwakeningConfig(**{**_AWAKENING_CONFIG.__dict__, "context_modulation": modulation})
    citizen = _citizen(1, (0.5,), base_threshold=0.4)
    far = awakening_threshold(citizen, mandate_dev=0.5, proximity=0.1, config=config)
    near = awakening_threshold(citizen, mandate_dev=0.5, proximity=0.9, config=config)
    assert far == pytest.approx(near)


def test_awakening_threshold_raises_when_neighbors_acting_is_enabled():
    modulation = AwakeningContextModulation(mandate_deviation=True, ticks_to_election=True, neighbors_acting=True)
    config = AwakeningConfig(**{**_AWAKENING_CONFIG.__dict__, "context_modulation": modulation})
    citizen = _citizen(1, (0.5,), base_threshold=0.4)
    with pytest.raises(NotImplementedError, match="neighbors_acting"):
        awakening_threshold(citizen, mandate_dev=0.0, proximity=0.0, config=config)


# ── select_consulted ──────────────────────────────────────────────────────

def test_select_consulted_returns_citizens_above_their_own_threshold_ascending():
    holder = _citizen(0, (0.5,), role=Role.ELECTED, office=Office.PRESIDENT, revealed_position=(0.5,))
    far = _citizen(9, (0.0,), base_threshold=0.1)   # large self_gap, low threshold -> consulted
    near = _citizen(2, (0.49,), base_threshold=0.1)  # tiny self_gap -> not consulted
    result = select_consulted(
        [holder, far, near], holder, tick=0, term_ticks=16, mandate_dev=0.0, awakening=_AWAKENING_CONFIG
    )
    assert [c.citizen_id for c, _gap in result] == [9]


def test_select_consulted_base_threshold_zero_consults_everyone_with_nonzero_gap():
    holder = _citizen(0, (0.5,), role=Role.ELECTED, office=Office.PRESIDENT, revealed_position=(0.5,))
    citizens = [holder] + [_citizen(i, (0.0,), base_threshold=0.0) for i in range(1, 4)]
    result = select_consulted(
        citizens, holder, tick=0, term_ticks=16, mandate_dev=0.0, awakening=_AWAKENING_CONFIG
    )
    assert [c.citizen_id for c, _gap in result] == [1, 2, 3]


def test_select_consulted_base_threshold_one_consults_nobody():
    holder = _citizen(0, (0.5,), role=Role.ELECTED, office=Office.PRESIDENT, revealed_position=(0.5,))
    citizens = [holder] + [_citizen(i, (0.0,), base_threshold=1.0) for i in range(1, 4)]
    result = select_consulted(
        citizens, holder, tick=0, term_ticks=16, mandate_dev=0.0, awakening=_AWAKENING_CONFIG
    )
    assert result == []


def test_select_consulted_never_includes_the_holder_even_with_a_nonzero_self_gap():
    holder = _citizen(
        0, (0.0,), role=Role.ELECTED, office=Office.PRESIDENT, revealed_position=(1.0,), base_threshold=0.0
    )
    result = select_consulted(
        [holder], holder, tick=0, term_ticks=16, mandate_dev=0.0, awakening=_AWAKENING_CONFIG
    )
    assert result == []


def test_select_consulted_is_a_pure_query_and_mutates_nothing():
    holder = _citizen(0, (0.5,), role=Role.ELECTED, office=Office.PRESIDENT, revealed_position=(0.5,))
    citizen = _citizen(1, (0.0,), base_threshold=0.0)
    before = (citizen.role, citizen.office, citizen.base_threshold)
    result_a = select_consulted(
        [holder, citizen], holder, tick=0, term_ticks=16, mandate_dev=0.0, awakening=_AWAKENING_CONFIG
    )
    result_b = select_consulted(
        [holder, citizen], holder, tick=0, term_ticks=16, mandate_dev=0.0, awakening=_AWAKENING_CONFIG
    )
    assert [c.citizen_id for c, _ in result_a] == [c.citizen_id for c, _ in result_b]
    assert (citizen.role, citizen.office, citizen.base_threshold) == before


def test_select_consulted_returns_empty_without_a_revealed_position():
    holder = _citizen(0, (0.5,), role=Role.ELECTED, office=Office.PRESIDENT)
    citizen = _citizen(1, (0.0,), base_threshold=0.0)
    assert select_consulted(
        [holder, citizen], holder, tick=0, term_ticks=16, mandate_dev=0.0, awakening=_AWAKENING_CONFIG
    ) == []


# ── update_street_pressure ───────────────────────────────────────────────

_STREET_PRESSURE_CONFIG = StreetPressureConfig(
    enabled=True, decay=0.85, weight_in_ecart=0.5, visible_to_representative=True
)


def test_update_street_pressure_hand_computed_one_step():
    result = update_street_pressure(0.2, 0.1, _STREET_PRESSURE_CONFIG)
    assert result == pytest.approx(0.85 * 0.2 + 0.1)


def test_update_street_pressure_converges_toward_rate_over_1_minus_decay():
    sp = 0.0
    for _ in range(300):
        sp = update_street_pressure(sp, 0.05, _STREET_PRESSURE_CONFIG)
    assert sp == pytest.approx(0.05 / (1 - 0.85), abs=1e-3)


def test_update_street_pressure_decays_toward_zero_with_no_rate():
    sp = 1.0
    for _ in range(300):
        sp = update_street_pressure(sp, 0.0, _STREET_PRESSURE_CONFIG)
    assert sp == pytest.approx(0.0, abs=1e-3)


# ── petition state machine (v4 Lot 5, §7bis.4a) ───────────────────────────

_PETITION_CONFIG = PetitionConfig(
    enabled=True,
    signature_threshold=0.25,
    cooldown_ticks=4,
    petition_lifespan_ticks=4,
    confidence_vote_format="binary",
    concurrent_allowed=False,
    weight_in_ecart=0.5,
)


def test_petition_pressure_is_zero_with_no_open_petition():
    holder = _citizen(1, (0.5,))
    assert petition_pressure(holder, population_size=100) == 0.0


def test_petition_pressure_is_signatures_over_population_size():
    holder = _citizen(1, (0.5,), petition_open_since_tick=0, petition_signers=frozenset({2, 3, 4}))
    assert petition_pressure(holder, population_size=100) == pytest.approx(0.03)


def test_launch_petition_records_the_launcher_as_its_first_signer():
    holder = _citizen(1, (0.5,))
    launcher = _citizen(2, (0.5,))
    launch_petition(holder, launcher, tick=5)
    assert holder.petition_open_since_tick == 5
    assert holder.petition_signers == frozenset({2})


def test_sign_petition_is_a_noop_for_an_existing_signer():
    holder = _citizen(1, (0.5,), petition_open_since_tick=0, petition_signers=frozenset({2}))
    signer = _citizen(2, (0.5,))
    sign_petition(holder, signer)
    assert holder.petition_signers == frozenset({2})


def test_sign_petition_adds_a_new_signer():
    holder = _citizen(1, (0.5,), petition_open_since_tick=0, petition_signers=frozenset({2}))
    signer = _citizen(3, (0.5,))
    sign_petition(holder, signer)
    assert holder.petition_signers == frozenset({2, 3})


def test_petition_accepts_signatures_on_its_launch_tick_and_through_its_window():
    holder = _citizen(1, (0.5,), petition_open_since_tick=10)
    for tick in (10, 11, 12, 13):
        assert petition_accepts_signatures(holder, tick, _PETITION_CONFIG) is True


def test_petition_stops_accepting_signatures_on_its_expiry_tick():
    holder = _citizen(1, (0.5,), petition_open_since_tick=10)
    assert petition_accepts_signatures(holder, 14, _PETITION_CONFIG) is False


def test_petition_accepts_signatures_is_false_with_no_open_petition():
    holder = _citizen(1, (0.5,))
    assert petition_accepts_signatures(holder, 10, _PETITION_CONFIG) is False


def test_petition_has_expired_exactly_at_lifespan_ticks():
    holder = _citizen(1, (0.5,), petition_open_since_tick=10)
    assert petition_has_expired(holder, 13, _PETITION_CONFIG) is False
    assert petition_has_expired(holder, 14, _PETITION_CONFIG) is True


def test_petition_has_expired_is_false_with_no_open_petition():
    holder = _citizen(1, (0.5,))
    assert petition_has_expired(holder, 10, _PETITION_CONFIG) is False


def test_petition_is_launchable_only_with_no_open_petition_and_no_cooldown():
    open_petition = _citizen(1, (0.5,), petition_open_since_tick=0)
    in_cooldown = _citizen(2, (0.5,), petition_cooldown_until_tick=10)
    clear = _citizen(3, (0.5,))
    assert petition_is_launchable(open_petition, tick=5) is False
    assert petition_is_launchable(in_cooldown, tick=5) is False
    assert petition_is_launchable(clear, tick=5) is True


def test_cooldown_blocks_launching_for_exactly_cooldown_ticks():
    holder = _citizen(1, (0.5,))
    resolve_petition(holder, tick=10, config=_PETITION_CONFIG)  # cooldown_until = 14
    for tick in (10, 11, 12, 13):
        assert petition_is_launchable(holder, tick) is False
    assert petition_is_launchable(holder, 14) is True


def test_an_active_cooldown_never_coexists_with_an_open_petition():
    holder = _citizen(1, (0.5,))
    resolve_petition(holder, tick=10, config=_PETITION_CONFIG)
    assert holder.petition_cooldown_until_tick is not None
    assert holder.petition_open_since_tick is None


def test_resolve_petition_clears_the_signatures_and_opens_the_cooldown():
    holder = _citizen(1, (0.5,), petition_open_since_tick=10, petition_signers=frozenset({2, 3}))
    resolve_petition(holder, tick=14, config=_PETITION_CONFIG)
    assert holder.petition_open_since_tick is None
    assert holder.petition_signers == frozenset()
    assert holder.petition_cooldown_until_tick == 18


def test_reset_petition_state_also_clears_the_cooldown():
    holder = _citizen(
        1, (0.5,),
        petition_open_since_tick=10,
        petition_signers=frozenset({2}),
        petition_cooldown_until_tick=20,
    )
    reset_petition_state(holder)
    assert holder.petition_open_since_tick is None
    assert holder.petition_signers == frozenset()
    assert holder.petition_cooldown_until_tick is None


# ── applicable_pressure_act (v4 Lot 7) ────────────────────────────────────

def test_a_launch_becomes_a_signature_once_a_petition_is_open():
    result = applicable_pressure_act(PressureAct.LAUNCH_PETITION, can_sign=True, can_launch=False)
    assert result == PressureAct.SIGN_PETITION


def test_a_launch_is_honoured_when_still_launchable():
    result = applicable_pressure_act(PressureAct.LAUNCH_PETITION, can_sign=False, can_launch=True)
    assert result == PressureAct.LAUNCH_PETITION


def test_a_sign_is_honoured_when_signable():
    result = applicable_pressure_act(PressureAct.SIGN_PETITION, can_sign=True, can_launch=False)
    assert result == PressureAct.SIGN_PETITION


def test_a_sign_with_nothing_to_sign_becomes_nothing():
    result = applicable_pressure_act(PressureAct.SIGN_PETITION, can_sign=False, can_launch=False)
    assert result == PressureAct.NOTHING


def test_a_launch_with_neither_available_becomes_nothing():
    result = applicable_pressure_act(PressureAct.LAUNCH_PETITION, can_sign=False, can_launch=False)
    assert result == PressureAct.NOTHING


def test_a_sign_falls_back_to_a_launch_when_nothing_is_open_but_launchable():
    # Reachable only if the model ignores its own frozen `available` hint
    # (chose SIGN_PETITION with no open petition) -- the symmetric case of
    # the LAUNCH->SIGN collision, resolved the same way: stay within the
    # petition lever rather than falling through to NOTHING.
    result = applicable_pressure_act(PressureAct.SIGN_PETITION, can_sign=False, can_launch=True)
    assert result == PressureAct.LAUNCH_PETITION


def test_acts_0_3_and_4_are_never_downgraded():
    for act in (PressureAct.NOTHING, PressureAct.MOBILIZE, PressureAct.WAIT_FOR_ELECTION):
        assert applicable_pressure_act(act, can_sign=False, can_launch=False) == act
        assert applicable_pressure_act(act, can_sign=True, can_launch=True) == act


def test_applicable_pressure_act_mutates_nothing():
    # Pure function: no Citizen argument at all, so there is nothing it
    # could mutate -- pinned anyway for symmetry with every other
    # accountability.py predicate's own purity test.
    before = (PressureAct.LAUNCH_PETITION, True, False)
    applicable_pressure_act(PressureAct.LAUNCH_PETITION, can_sign=True, can_launch=False)
    assert before == (PressureAct.LAUNCH_PETITION, True, False)


def test_applicable_pressure_act_agrees_with_the_deterministic_chain_on_petition_acts():
    # The whole justification for LAUNCH -> SIGN: it is exactly what
    # deterministic_pressure_action's own priority chain would return from
    # the same live facts, for a citizen whose gap already cleared the
    # NOTHING bar and whose menu already allows petitions.
    from api.domain.polity.config import PressureMenuConfig
    from api.domain.polity.simple_rules import deterministic_pressure_action

    # Only the two cases where the petition lever itself is still reachable:
    # when neither can_sign nor can_launch holds, deterministic_pressure_action
    # falls through to mobilize/wait, which applicable_pressure_act deliberately
    # never does (it would be the orchestrator picking a DIFFERENT lever on the
    # citizen's behalf) -- that divergence is intentional, not a disagreement.
    citizen = _citizen(1, (0.5,))  # default blank_threshold=0.5
    menu = PressureMenuConfig(petition_enabled=True, mobilization_enabled=False, electoral_only=False)
    for can_sign, can_launch in [(True, False), (False, True)]:
        deterministic_act = deterministic_pressure_action(
            citizen, gap=0.9, menu=menu, can_sign=can_sign, can_launch=can_launch
        )
        llm_act = applicable_pressure_act(PressureAct.LAUNCH_PETITION, can_sign=can_sign, can_launch=can_launch)
        assert llm_act == deterministic_act
