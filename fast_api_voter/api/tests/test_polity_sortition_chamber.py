"""sortition_chamber.py — §6bis.3's two-tier selection primitive (v6b Lot 2).

Contract: strict pool (never served, not the sitting president) is used
while it can fill `seats`; once it can't, eligibility relaxes to "not
currently seated" -- v6b Lot 2's own measured pool-exhaustion finding.
"""
import numpy as np

from api.domain.polity.citizen import Citizen, Office
from api.domain.polity.config import SortitionChamberConfig
from api.domain.polity.sortition_chamber import select_sortition_chamber

_CONFIG = SortitionChamberConfig(
    enabled=True,
    seats=3,
    term_years=1,
    renewable=False,
    selection="uniform_random",
    overlaps_with_assembly=False,
    veto_power="suspensive_limited",
    veto_delay_ticks=2,
)


def _citizen(citizen_id: int, **kwargs) -> Citizen:
    return Citizen(
        citizen_id=citizen_id,
        issue_positions=(0.5,),
        issue_priorities=(1.0,),
        blank_threshold=0.5,
        ambition_score=0.5,
        **kwargs,
    )


def _config(**overrides) -> SortitionChamberConfig:
    return SortitionChamberConfig(**{**_CONFIG.__dict__, **overrides})


def test_strict_pool_excludes_citizens_who_already_served():
    citizens = [_citizen(i, sortition_terms_served=1 if i < 5 else 0) for i in range(10)]
    drawn, relaxed = select_sortition_chamber(citizens, _config(seats=3), np.random.default_rng(0))
    assert relaxed is False
    assert set(drawn).isdisjoint(range(5))
    assert len(drawn) == 3


def test_strict_pool_excludes_the_sitting_president():
    citizens = [_citizen(i) for i in range(10)]
    citizens[7].office = Office.PRESIDENT
    drawn, relaxed = select_sortition_chamber(citizens, _config(seats=9), np.random.default_rng(0))
    assert relaxed is False
    assert 7 not in drawn
    assert len(drawn) == 9


def test_relaxed_pool_triggers_exactly_when_the_strict_pool_is_too_small():
    # 10 citizens, 8 already served -- strict pool has 2, seats=3 -> relax.
    citizens = [_citizen(i, sortition_terms_served=1 if i < 8 else 0) for i in range(10)]
    drawn, relaxed = select_sortition_chamber(citizens, _config(seats=3), np.random.default_rng(0))
    assert relaxed is True
    assert len(drawn) == 3


def test_relaxed_pool_does_not_trigger_when_the_strict_pool_exactly_fills_seats():
    citizens = [_citizen(i, sortition_terms_served=1 if i < 7 else 0) for i in range(10)]
    drawn, relaxed = select_sortition_chamber(citizens, _config(seats=3), np.random.default_rng(0))
    assert relaxed is False
    assert len(drawn) == 3


def test_draw_size_is_capped_at_the_pool_size_even_when_relaxed():
    # Everyone excluded (all president -- unrealistic but exercises the
    # empty-pool path cleanly): pool is empty even relaxed.
    citizens = [_citizen(i, office=Office.PRESIDENT) for i in range(5)]
    drawn, relaxed = select_sortition_chamber(citizens, _config(seats=3), np.random.default_rng(0))
    assert drawn == []
    assert relaxed is True


def test_drawn_ids_are_ascending_and_distinct():
    citizens = [_citizen(i) for i in range(20)]
    drawn, _ = select_sortition_chamber(citizens, _config(seats=7), np.random.default_rng(1))
    assert drawn == sorted(drawn)
    assert len(set(drawn)) == len(drawn)


def test_same_seed_produces_the_same_draw():
    citizens = [_citizen(i) for i in range(20)]
    drawn_a, _ = select_sortition_chamber(citizens, _config(seats=7), np.random.default_rng(42))
    drawn_b, _ = select_sortition_chamber(citizens, _config(seats=7), np.random.default_rng(42))
    assert drawn_a == drawn_b


def test_a_relaxed_draw_can_reselect_a_previously_served_citizen():
    # Deliberate softening of "non-renewable" once the strict pool is
    # exhausted -- pinned so it isn't mistaken for a bug later.
    citizens = [_citizen(i, sortition_terms_served=1) for i in range(5)]
    drawn, relaxed = select_sortition_chamber(citizens, _config(seats=3), np.random.default_rng(0))
    assert relaxed is True
    assert len(drawn) == 3
