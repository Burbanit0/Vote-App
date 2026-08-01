"""Lot 4 — institutional_clock.py: the electoral calendar.

Contract (dev-plan-v0-worktree.md §3, Lot 4): over 120 ticks, exactly 8
presidential and 8 legislative elections, at the expected ticks; changing
the offset correctly shifts the second calendar.
"""
from api.domain.polity.config import load_config
from api.domain.polity.institutional_clock import ElectionType, InstitutionalClock


def _default_clock():
    config = load_config()
    return InstitutionalClock.from_config(config.institutions, config.run)


def test_default_config_produces_8_presidential_elections_at_expected_ticks():
    clock = _default_clock()
    assert clock.presidential_election_ticks() == [0, 16, 32, 48, 64, 80, 96, 112]


def test_default_config_produces_8_legislative_elections_at_expected_ticks():
    clock = _default_clock()
    assert clock.legislative_election_ticks() == [8, 24, 40, 56, 72, 88, 104, 120]


def test_election_at_reports_both_when_calendars_coincide():
    clock = InstitutionalClock(
        president_term_ticks=16, assembly_term_ticks=16, assembly_offset_ticks=0, total_ticks=120
    )
    assert clock.election_at(0) == ElectionType.BOTH
    assert clock.election_at(16) == ElectionType.BOTH
    assert clock.election_at(8) == ElectionType.NONE


def test_election_at_distinguishes_presidential_and_legislative():
    clock = _default_clock()
    assert clock.election_at(0) == ElectionType.PRESIDENTIAL
    assert clock.election_at(8) == ElectionType.LEGISLATIVE
    assert clock.election_at(1) == ElectionType.NONE


def test_zero_offset_makes_calendars_concurrent():
    clock = InstitutionalClock(
        president_term_ticks=16, assembly_term_ticks=16, assembly_offset_ticks=0, total_ticks=120
    )
    assert clock.presidential_election_ticks() == clock.legislative_election_ticks()


def test_changing_the_offset_shifts_the_legislative_calendar():
    concurrent = InstitutionalClock(
        president_term_ticks=16, assembly_term_ticks=16, assembly_offset_ticks=0, total_ticks=120
    )
    shifted = InstitutionalClock(
        president_term_ticks=16, assembly_term_ticks=16, assembly_offset_ticks=4, total_ticks=120
    )
    assert shifted.legislative_election_ticks() == [t + 4 for t in concurrent.legislative_election_ticks()]
    assert shifted.presidential_election_ticks() == concurrent.presidential_election_ticks()
