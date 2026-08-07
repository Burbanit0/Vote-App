"""
api.domain.polity.run_polity_simulation — orchestration (Lot 8).

Pure sequencing, no decision logic of its own (design doc §1): every choice
(who to nominate, who a citizen votes for, who forms a coalition) comes from
simple_rules.py or, when config.llm.enabled, llm_behavior_engine.py's LLM
replacements (voting since increment 1, the dominant candidacy path since
increment 2); every count (a winner, a seat allocation) comes from
ballot_and_aggregation.py. This module only calls them in the right order,
once per tick, and journals what happened.

_declare_nominees_llm (increment 2) journals candidacy_considered for every
evaluated citizen -- including declines, which the deterministic
_declare_nominees never records at all -- plus nomination_lost for any
LLM-approved citizen who doesn't win their party's (still deterministic)
tiebreak, so their story isn't silently absent from the journal (design doc
§16.3).
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import numpy as np

from api.domain.polity.ballot_and_aggregation import RANKED_METHODS, allocate_seats, get_presidential_winner
from api.domain.polity.citizen import Citizen, Office, Role, generate_population
from api.domain.polity.config import PolityConfig
from api.domain.polity.institutional_clock import ElectionType, InstitutionalClock
from api.domain.polity.journal import Journal
from api.domain.polity.llm_behavior_engine import cast_votes, decide_candidacies, resolve_ranking_cids
from api.domain.polity.llm_client import LlmClientProtocol, OllamaJsonClient
from api.domain.polity.parties import Party, initialize_parties
from api.domain.polity.simple_rules import (
    BLANK_LABEL,
    assign_party_affiliation,
    attempt_rupture_candidacy,
    build_ranking,
    choose_party,
    citizen_id_from_label,
    declare_candidacy,
    form_coalition,
    select_party_nominee,
    select_party_nominee_from_declared,
)


def run_simulation(
    config: PolityConfig, run_id: str | None = None, llm_client: LlmClientProtocol | None = None
) -> Path:
    """Run a full simulation and return the path to its journal.

    president_term_limit/assembly_term_limit are both null in v0's shipped
    config and are themselves tagged [v4] there — v0 tracks
    Citizen.mandates_served (§3.1) but does not gate candidacy on it; that
    gate activates in v4 alongside the limits it reads.

    `llm_client` is additive (default None) so every pre-v2 caller and test
    is unaffected. When `config.llm.enabled` is true and no client was
    injected, a real OllamaJsonClient is constructed for the run's
    lifetime and closed here; an injected client (tests) is never closed —
    it belongs to the caller.
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
    # Independent stream from population/party generation (same pattern as
    # Lot 2/3): a fresh default_rng per concern, so enabling rupture draws
    # never perturbs the citizens/parties already generated above.
    rupture_rng = np.random.default_rng(config.run.seed)

    with Journal.from_config(config.journal, run_id) as journal, _llm_client_scope(config, llm_client) as client:
        for tick in range(clock.total_ticks + 1):
            _attempt_rupture_candidacies(citizens, config, journal, tick, rupture_rng)
            election = clock.election_at(tick)
            if election in (ElectionType.PRESIDENTIAL, ElectionType.BOTH):
                _hold_presidential_election(citizens, parties, config, journal, tick, client)
            if election in (ElectionType.LEGISLATIVE, ElectionType.BOTH):
                seats, votes = _hold_legislative_election(citizens, parties, config, journal, tick)
                _form_and_journal_coalition(parties, seats, votes, config, journal, tick)

    return Path(config.journal.output_dir) / run_id / "events.jsonl"


@contextmanager
def _llm_client_scope(config: PolityConfig, llm_client: LlmClientProtocol | None) -> Iterator[LlmClientProtocol | None]:
    if llm_client is not None:
        yield llm_client
        return
    if not config.llm.enabled:
        yield None
        return
    with OllamaJsonClient.from_config(config.llm, seed=config.run.seed) as owned_client:
        yield owned_client


def _attempt_rupture_candidacies(
    citizens: list[Citizen], config: PolityConfig, journal: Journal, tick: int, rng: np.random.Generator
) -> None:
    """Design doc §2.4 rare path: evaluated every tick (not just election
    ticks — rupture_base_probability is a per-tick draw), for every citizen
    currently an elector. A successful attempt declares immediately and the
    citizen sits as Role.CANDIDATE until the next presidential election
    picks them up (_hold_presidential_election), mirroring how a party
    nominee's declaration already works within a single election tick."""
    for citizen in citizens:
        if citizen.role != Role.ELECTOR:
            continue
        if attempt_rupture_candidacy(citizen, citizens, config.candidacy, rng):
            declare_candidacy(citizen)
            journal.write(
                tick=tick,
                event_type="candidacy_declared",
                payload={"path": "rupture"},
                citizen_id=citizen.citizen_id,
            )


def _declare_nominees(
    citizens: list[Citizen],
    parties: list[Party],
    config: PolityConfig,
    journal: Journal,
    tick: int,
    llm_client: LlmClientProtocol | None,
) -> list[Citizen]:
    if config.llm.enabled:
        return _declare_nominees_llm(citizens, parties, config, journal, tick, llm_client)
    nominees = []
    for party in parties:
        nominee = select_party_nominee(party.party_id, citizens, config.candidacy)
        if nominee is None:
            continue
        declare_candidacy(nominee)
        journal.write(
            tick=tick,
            event_type="candidacy_declared",
            payload={"party_id": party.party_id, "path": "dominant"},
            citizen_id=nominee.citizen_id,
        )
        nominees.append(nominee)
    return nominees


def _declare_nominees_llm(
    citizens: list[Citizen],
    parties: list[Party],
    config: PolityConfig,
    journal: Journal,
    tick: int,
    llm_client: LlmClientProtocol | None,
) -> list[Citizen]:
    """v2 increment 2's LLM path: decide_candidacies replaces
    decide_candidacy's bare threshold for the dominant-path eligibility
    filter only -- select_party_nominee_from_declared's tiebreak among the
    LLM-approved considerers stays the same deterministic
    (ambition_score, -citizen_id) rule select_party_nominee already uses
    (party_nomination_choice, design doc dt=4, stays out of scope).

    Journals candidacy_considered for every evaluated citizen (declared or
    not) -- new in this increment; the deterministic path above never
    records non-candidacies at all. Also journals nomination_lost for every
    LLM-approved citizen who doesn't win their party's tiebreak, so their
    story isn't silently absent from the journal (design doc §16.3)."""
    assert llm_client is not None  # guaranteed by _llm_client_scope when llm.enabled
    outcome = decide_candidacies(citizens, config, llm_client)
    for decision in outcome.decisions:
        journal.write(
            tick=tick,
            event_type="candidacy_considered",
            payload={"outcome": decision.outcome, "path": "dominant"},
            citizen_id=decision.cid,
            motif=str(decision.motif),
            codebook_version=config.llm.codebook_version,
        )
    declared_cids = {decision.cid for decision in outcome.decisions if decision.outcome == 1}

    nominees = []
    for party in parties:
        party_declared_cids = {
            c.citizen_id for c in citizens
            if c.party_affiliation == party.party_id and c.citizen_id in declared_cids
        }
        nominee = select_party_nominee_from_declared(party.party_id, citizens, declared_cids)
        lost_cids = party_declared_cids - ({nominee.citizen_id} if nominee is not None else set())
        for cid in lost_cids:
            journal.write(
                tick=tick,
                event_type="nomination_lost",
                payload={"party_id": party.party_id},
                citizen_id=cid,
            )
        if nominee is None:
            continue
        declare_candidacy(nominee)
        journal.write(
            tick=tick,
            event_type="candidacy_declared",
            payload={"party_id": party.party_id, "path": "dominant"},
            citizen_id=nominee.citizen_id,
        )
        nominees.append(nominee)
    return nominees


def _hold_presidential_election(
    citizens: list[Citizen],
    parties: list[Party],
    config: PolityConfig,
    journal: Journal,
    tick: int,
    llm_client: LlmClientProtocol | None,
) -> None:
    nominees = _declare_nominees(citizens, parties, config, journal, tick, llm_client)
    nominee_ids = {c.citizen_id for c in nominees}
    standing_rupture_candidates = sorted(
        (c for c in citizens if c.role == Role.CANDIDATE and c.citizen_id not in nominee_ids),
        key=lambda c: c.citizen_id,
    )
    nominees = nominees + standing_rupture_candidates

    winner: Citizen | None = None
    if nominees:
        if config.llm.enabled:
            assert llm_client is not None  # guaranteed by _llm_client_scope when llm.enabled
            outcome = cast_votes(citizens, nominees, config, llm_client)
            ballots = outcome.ballots
            for decision in outcome.decisions:
                journal.write(
                    tick=tick,
                    event_type="vote_cast",
                    payload={"blank": decision.blank, "ranking": resolve_ranking_cids(decision, nominees)},
                    citizen_id=decision.cid,
                    motif=str(decision.motif),
                    codebook_version=config.llm.codebook_version,
                )
        else:
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
