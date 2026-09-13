"""Lot 4 — institutional_clock.py: the electoral calendar.

Contract (dev-plan-v0-worktree.md §3, Lot 4): over 120 ticks, exactly 8
presidential and 8 legislative elections, at the expected ticks; changing
the offset correctly shifts the second calendar.
"""
from api.domain.polity.config import load_config
from api.domain.polity.institutional_clock import ElectionType, InstitutionalClock, Phase


def _default_clock():
    config = load_config()
    return InstitutionalClock.from_config(config.institutions, config.run, config.sortition_chamber)


def test_default_config_produces_8_presidential_elections_at_expected_ticks():
    clock = _default_clock()
    assert clock.presidential_election_ticks() == [0, 16, 32, 48, 64, 80, 96, 112]


def test_default_config_produces_8_legislative_elections_at_expected_ticks():
    clock = _default_clock()
    assert clock.legislative_election_ticks() == [8, 24, 40, 56, 72, 88, 104, 120]


def test_election_at_reports_both_when_calendars_coincide():
    clock = InstitutionalClock(
        president_term_ticks=16, assembly_term_ticks=16, assembly_offset_ticks=0, total_ticks=120,
        sortition_term_ticks=4,
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
        president_term_ticks=16, assembly_term_ticks=16, assembly_offset_ticks=0, total_ticks=120,
        sortition_term_ticks=4,
    )
    assert clock.presidential_election_ticks() == clock.legislative_election_ticks()


def test_changing_the_offset_shifts_the_legislative_calendar():
    concurrent = InstitutionalClock(
        president_term_ticks=16, assembly_term_ticks=16, assembly_offset_ticks=0, total_ticks=120,
        sortition_term_ticks=4,
    )
    shifted = InstitutionalClock(
        president_term_ticks=16, assembly_term_ticks=16, assembly_offset_ticks=4, total_ticks=120,
        sortition_term_ticks=4,
    )
    assert shifted.legislative_election_ticks() == [t + 4 for t in concurrent.legislative_election_ticks()]
    assert shifted.presidential_election_ticks() == concurrent.presidential_election_ticks()


# ── v6b Lot 2: is_sortition_rotation (§6bis.3) ────────────────────────────

def test_is_sortition_rotation_matches_the_modular_schedule():
    clock = InstitutionalClock(
        president_term_ticks=16, assembly_term_ticks=16, assembly_offset_ticks=8, total_ticks=120,
        sortition_term_ticks=4,
    )
    assert clock.is_sortition_rotation(0) is True
    assert clock.is_sortition_rotation(4) is True
    assert clock.is_sortition_rotation(8) is True
    assert clock.is_sortition_rotation(1) is False
    assert clock.is_sortition_rotation(2) is False
    assert clock.is_sortition_rotation(3) is False


# ── Track E, absorbed by S4.4: declaration and nomination bound the presidential campaign ──

def test_a_staggered_election_declares_when_its_campaign_opens_and_nominates_on_its_last_tick():
    clock = _default_clock()  # presidential elections at 0, 16, 32, ..., 112; campaigns of 4 ticks
    assert clock.is_presidential_declaration_tick(12) is True   # 16 - 4
    assert clock.is_presidential_nomination_tick(15) is True    # 16 - 1
    assert clock.is_presidential_declaration_tick(28) is True   # 32 - 4
    assert clock.is_presidential_nomination_tick(31) is True    # 32 - 1


def test_declaration_and_nomination_ticks_are_false_off_the_window():
    clock = _default_clock()
    assert clock.is_presidential_declaration_tick(11) is False
    assert clock.is_presidential_declaration_tick(13) is False
    assert clock.is_presidential_nomination_tick(14) is False
    assert clock.is_presidential_nomination_tick(16) is False


def _clock(term: int, campaign: int, total: int = 32) -> InstitutionalClock:
    return InstitutionalClock(
        president_term_ticks=term, assembly_term_ticks=term, assembly_offset_ticks=0, total_ticks=total,
        sortition_term_ticks=4, presidential_campaign_ticks=campaign,
    )


def test_a_campaign_never_reaches_back_to_the_previous_election_and_can_be_one_tick_or_none():
    assert [t for t in range(9) if _clock(4, 4).is_presidential_declaration_tick(t)] == [1, 5]  # clamped to term - 1
    assert [t for t in range(9) if _clock(4, 1).is_presidential_declaration_tick(t)] == [3, 7]
    assert [t for t in range(9) if _clock(4, 1).is_presidential_nomination_tick(t)] == [3, 7]  # the same tick
    assert not any(_clock(4, 0).is_presidential_declaration_tick(t) or _clock(4, 0).is_presidential_nomination_tick(t) for t in range(9))


def test_the_tick_zero_election_never_gets_a_staggered_window():
    # There is no tick -2 or -1 -- the very first election has no runway to
    # stagger into, so it always stays atomic regardless of config. The
    # tick loop itself never visits a negative tick, but the guard is
    # explicit (election_tick >= 2) rather than incidental, so it is
    # pinned directly here.
    clock = _default_clock()
    assert clock.is_presidential_declaration_tick(-2) is False
    assert clock.is_presidential_nomination_tick(-1) is False


def test_declaration_tick_excludes_an_election_past_the_runs_own_end():
    # total_ticks=17: a presidential election every 16 ticks would fall at
    # 0 and 16 (both in range) and then 32 (never reached) -- declaring at
    # tick 30 for that phantom election would be pure waste.
    clock = InstitutionalClock(
        president_term_ticks=16, assembly_term_ticks=16, assembly_offset_ticks=0, total_ticks=17,
        sortition_term_ticks=4, presidential_campaign_ticks=2,
    )
    assert clock.is_presidential_declaration_tick(14) is True  # real: election at 16, in range
    assert clock.is_presidential_declaration_tick(30) is False  # phantom: election at 32, out of range


def test_shipped_config_rotation_coincides_with_every_election():
    # v6b Lot 2's own finding: sortition_term_ticks=4 divides evenly into
    # president_term_ticks=16, assembly_term_ticks=16, and
    # assembly_offset_ticks=8 -- every presidential AND legislative election
    # tick is ALSO a rotation tick at the shipped defaults, the common case,
    # not an edge case.
    clock = _default_clock()
    for tick in clock.presidential_election_ticks():
        assert clock.is_sortition_rotation(tick) is True
    for tick in clock.legislative_election_ticks():
        assert clock.is_sortition_rotation(tick) is True


# ── S4.4: the phase clock ─────────────────────────────────────────────────

def test_the_shipped_calendar_has_four_tick_presidential_and_two_tick_legislative_campaigns():
    clock = _default_clock()  # presidential at 0, 16, ...; legislative at 8, 24, ..., 120
    names = {t: clock.phase(t).name for t in range(18)}
    assert [t for t, name in names.items() if name == "election"] == [0, 8, 16]
    assert [t for t, name in names.items() if name == "campaign"] == [6, 7, 12, 13, 14, 15]
    assert (clock.phase(12).presidential_campaign, clock.phase(12).legislative_campaign) == (True, False)
    assert (clock.phase(7).presidential_campaign, clock.phase(7).legislative_campaign) == (False, True)
    assert clock.phase(13) == Phase(election=ElectionType.NONE, presidential_campaign=True, legislative_campaign=False,
                                    ticks_to_presidential=3, ticks_to_legislative=11)
    assert clock.phase(8).election is ElectionType.LEGISLATIVE and clock.phase(11).name == "governing"


def test_after_the_last_presidential_election_there_is_no_presidential_campaign():
    clock = _default_clock()
    last = clock.phase(118)
    assert (last.ticks_to_presidential, last.presidential_campaign, last.legislative_campaign) == (None, False, True)
    assert clock.phase(120).name == "election" and clock.phase(120).ticks_to_legislative == 0
    assert clock.phase(-1).ticks_to_presidential is None


def test_campaigns_for_different_elections_can_overlap():
    clock = InstitutionalClock(
        president_term_ticks=16, assembly_term_ticks=16, assembly_offset_ticks=2, total_ticks=32,
        sortition_term_ticks=4, presidential_campaign_ticks=4, legislative_campaign_ticks=4,
    )
    both = clock.phase(15)  # presidential at 16, legislative at 18
    assert (both.presidential_campaign, both.legislative_campaign, both.name) == (True, True, "campaign")
    assert clock.phase(17).legislative_campaign and not clock.phase(17).presidential_campaign
