"""
api.domain.polity.run_polity_simulation — orchestration (Lot 8).

Pure sequencing, no decision logic of its own (design doc §1): every choice
(who to nominate, who a citizen votes for, who forms a coalition) comes from
simple_rules.py; every count (a winner, a seat allocation) comes from
ballot_and_aggregation.py. This module only calls them in the right order,
once per tick, and journals what happened.
"""
from __future__ import annotations

from pathlib import Path

from api.domain.polity.ballot_and_aggregation import RANKED_METHODS, allocate_seats, get_presidential_winner
from api.domain.polity.citizen import Citizen, Office, Role, generate_population
from api.domain.polity.config import PolityConfig
from api.domain.polity.institutional_clock import ElectionType, InstitutionalClock
from api.domain.polity.journal import Journal
from api.domain.polity.parties import Party, initialize_parties
from api.domain.polity.simple_rules import (
    BLANK_LABEL,
    assign_party_affiliation,
    build_ranking,
    choose_party,
    citizen_id_from_label,
    declare_candidacy,
    form_coalition,
    select_party_nominee,
)


def run_simulation(config: PolityConfig, run_id: str | None = None) -> Path:
    """Run a full v0 simulation and return the path to its journal.

    president_term_limit/assembly_term_limit are both null in v0's shipped
    config and are themselves tagged [v4] there — v0 tracks
    Citizen.mandates_served (§3.1) but does not gate candidacy on it; that
    gate activates in v4 alongside the limits it reads.
    """
    if config.institutions.presidential_method not in RANKED_METHODS:
        raise NotImplementedError(
            f"presidential_method {config.institutions.presidential_method!r} needs a "
            "cardinal ballot builder — simple_rules.py only builds rankings in v0"
        )

    run_id = run_id or config.run.run_label
    citizens = generate_population(config.citizens, config.run.population_size, config.run.seed)
    parties = initialize_parties(citizens, config.parties.initial_count, config.run.seed)
    for citizen in citizens:
        citizen.party_affiliation = assign_party_affiliation(citizen, parties)

    clock = InstitutionalClock.from_config(config.institutions, config.run)

    with Journal.from_config(config.journal, run_id) as journal:
        for tick in range(clock.total_ticks + 1):
            election = clock.election_at(tick)
            if election in (ElectionType.PRESIDENTIAL, ElectionType.BOTH):
                _hold_presidential_election(citizens, parties, config, journal, tick)
            if election in (ElectionType.LEGISLATIVE, ElectionType.BOTH):
                seats, votes = _hold_legislative_election(citizens, parties, config, journal, tick)
                _form_and_journal_coalition(parties, seats, votes, config, journal, tick)

    return Path(config.journal.output_dir) / run_id / "events.jsonl"


def _declare_nominees(
    citizens: list[Citizen], parties: list[Party], config: PolityConfig, journal: Journal, tick: int
) -> list[Citizen]:
    nominees = []
    for party in parties:
        nominee = select_party_nominee(party.party_id, citizens, config.candidacy)
        if nominee is None:
            continue
        declare_candidacy(nominee)
        journal.write(
            tick=tick,
            event_type="candidacy_declared",
            payload={"party_id": party.party_id},
            citizen_id=nominee.citizen_id,
        )
        nominees.append(nominee)
    return nominees


def _hold_presidential_election(
    citizens: list[Citizen], parties: list[Party], config: PolityConfig, journal: Journal, tick: int
) -> None:
    nominees = _declare_nominees(citizens, parties, config, journal, tick)

    winner: Citizen | None = None
    if nominees:
        ballots = [build_ranking(voter, nominees) for voter in citizens]
        winner_label = get_presidential_winner(ballots, config.institutions.presidential_method)
        if winner_label is not None and winner_label != BLANK_LABEL:
            winner_id = citizen_id_from_label(winner_label)
            winner = next(c for c in nominees if c.citizen_id == winner_id)
            winner.role = Role.ELECTED
            winner.office = Office.PRESIDENT
            term_ticks = config.institutions.president_term_years * config.run.ticks_per_year
            winner.term_end_tick = tick + term_ticks
            winner.mandates_served += 1

    for nominee in nominees:
        if nominee is not winner:
            nominee.role = Role.ELECTOR
            nominee.pledged_platform = None
            nominee.revealed_position = None

    journal.write(
        tick=tick,
        event_type="elected" if winner is not None else "election_no_winner",
        payload={"office": Office.PRESIDENT.value},
        citizen_id=winner.citizen_id if winner is not None else None,
    )


def _hold_legislative_election(
    citizens: list[Citizen], parties: list[Party], config: PolityConfig, journal: Journal, tick: int
) -> tuple[dict[int, int], dict[int, float]]:
    votes: dict[int, float] = {party.party_id: 0.0 for party in parties}
    blank_count = 0
    for voter in citizens:
        choice = choose_party(voter, parties)
        if choice is None:
            blank_count += 1
        else:
            votes[choice] += 1.0

    raw_seats = allocate_seats(
        {str(party_id): count for party_id, count in votes.items()},
        total_seats=config.institutions.assembly_seats,
        method=config.institutions.seat_allocation,
        electoral_threshold=config.institutions.electoral_threshold,
    )
    seats = {int(party_id): count for party_id, count in raw_seats.items()}

    journal.write(
        tick=tick,
        event_type="legislative_result",
        payload={"seats": seats, "votes": votes, "blank_count": blank_count},
    )
    return seats, votes


def _form_and_journal_coalition(
    parties: list[Party],
    seats: dict[int, int],
    votes: dict[int, float],
    config: PolityConfig,
    journal: Journal,
    tick: int,
) -> None:
    platforms = {party.party_id: party.platform for party in parties}
    coalition = form_coalition(
        platforms, seats, votes, config.parties.coalition_tiebreak, config.parties.coalition_majority_ratio
    )
    journal.write(
        tick=tick,
        event_type="coalition_formed" if coalition is not None else "coalition_failed",
        payload={"coalition": coalition, "seats": seats},
    )
