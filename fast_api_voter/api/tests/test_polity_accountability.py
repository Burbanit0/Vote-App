"""v4 Lot 2 — accountability.py: mandate_deviation, self_gap, term limits,
current_office_holders. Measurement-only primitives (§7bis.5/§6bis.1) — none
of this decides anything; Lots 3-7 are the first real callers of most of it.
"""
import pytest

from api.domain.polity.accountability import (
    current_office_holders,
    is_term_limited,
    mandate_deviation,
    pledge_weights,
    self_gap,
    weighted_euclidean,
)
from api.domain.polity.citizen import Citizen, Office, Role
from api.domain.polity.config import MandateConfig
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
