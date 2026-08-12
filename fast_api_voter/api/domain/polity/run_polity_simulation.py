"""
api.domain.polity.run_polity_simulation — orchestration (Lot 8).

Pure sequencing, no decision logic of its own (design doc §1): every choice
(who to nominate, who a citizen votes for, who forms a coalition) comes from
simple_rules.py or, when config.llm.enabled, llm_behavior_engine.py's LLM
replacements (voting since increment 1, the dominant candidacy path since
increment 2, contested-party arbitration since increment 3, campaign
positioning since increment 4, coalition willingness since increment 5);
every count (a winner, a seat allocation) comes from
ballot_and_aggregation.py. This module only calls them in the right order,
once per tick, and journals what happened.

_declare_nominees_llm journals candidacy_considered for every evaluated
citizen (increment 2) -- including declines, which the deterministic
_declare_nominees never records at all -- plus party_nomination_choice for
every *contested* party (increment 3, 2+ declared candidates) and
nomination_lost for any LLM-approved citizen who doesn't win their party's
nomination (contested: the LLM's choice; uncontested: still the
deterministic tiebreak), so their story isn't silently absent from the
journal (design doc §16.3). Since increment 4, it also runs
decide_campaign_positioning on the tick's finalized nominee list, overwrites
their pledged_platform/revealed_position with the resolved (possibly
shifted) position, and journals campaign_positioning per nominee --
including sincere ones (empty shifts), so "chose not to strategize" is as
visible as any other outcome.

_form_and_journal_coalition_llm (increment 5) journals one coalition_decision
event per seated, non-initiator party (dt=9), then the aggregate
coalition_formed/coalition_failed event in its existing, unchanged shape --
the deterministic path's journal bytes do not change at all. Unlike every
other decision type, the deterministic path (_form_and_journal_coalition)
was previously called unconditionally, with no config.llm.enabled gate at
all; this increment adds that gate, mirroring _declare_nominees's existing
if/else split.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import numpy as np

from api.domain.polity.accountability import (
    applicable_pressure_act,
    current_office_holders,
    is_term_limited,
    launch_petition,
    mandate_deviation,
    petition_accepts_signatures,
    petition_has_expired,
    petition_is_launchable,
    petition_pressure,
    reset_petition_state,
    resolve_petition,
    select_consulted,
    sign_petition,
    ticks_to_election,
    update_street_pressure,
)
from api.domain.polity.ballot_and_aggregation import (
    RANKED_METHODS,
    allocate_seats,
    confidence_keep_ratio,
    get_presidential_winner,
    resolve_confidence_vote,
)
from api.domain.polity.citizen import Citizen, Office, Role, generate_population
from api.domain.polity.codebook import BallotFormat, PressureAct
from api.domain.polity.config import PolityConfig
from api.domain.polity.institutional_clock import ElectionType, InstitutionalClock
from api.domain.polity.journal import Journal
from api.domain.polity.legitimacy import (
    compose_ecart,
    crosses_floor,
    initial_legitimacy,
    mandate_strength,
    update_legitimacy,
)
from api.domain.polity.llm_behavior_engine import (
    PressureContext,
    ResponseContext,
    cast_votes,
    decide_campaign_positioning,
    decide_candidacies,
    decide_coalition,
    decide_party_nominations,
    decide_pressure_actions,
    decide_representative_response,
    menu_acts,
    resolve_ranking_cids,
)
from api.domain.polity.llm_client import LlmClientProtocol, OllamaJsonClient
from api.domain.polity.llm_schemas import PressureDecision
from api.domain.polity.metrics import mobilization_rate
from api.domain.polity.parties import Party, initialize_parties
from api.domain.polity.simple_rules import (
    BLANK_LABEL,
    assign_party_affiliation,
    attempt_rupture_candidacy,
    build_confidence_ballot,
    build_ranking,
    choose_party,
    citizen_id_from_label,
    declare_candidacy,
    deterministic_pressure_action,
    form_coalition,
    select_party_nominee,
    select_party_nominee_from_declared,
    vacate_office,
)


def run_simulation(
    config: PolityConfig, run_id: str | None = None, llm_client: LlmClientProtocol | None = None
) -> Path:
    """Run a full simulation and return the path to its journal.

    president_term_limit is null in the shipped config (illimité), but is
    now enforced when set (v4 Lot 2, §6bis.1): a citizen with
    mandates_served >= term_limit cannot be nominated again on the
    deterministic candidacy path (assembly_term_limit stays unread —
    legislative elections are party-list, no per-citizen candidacy check
    exists to gate).

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
                _form_and_journal_coalition(parties, seats, votes, config, journal, tick, client)
            _run_accountability_phase(citizens, config, journal, tick, client)

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
        # is_term_limited is checked AFTER the draw, never before: skipping
        # the call for term-limited citizens would shift the RNG stream and
        # break byte-for-byte reproducibility for any non-null
        # president_term_limit (v4 Lot 2, §6bis.1).
        declared = attempt_rupture_candidacy(citizen, citizens, config.candidacy, rng)
        if declared and not is_term_limited(citizen, config.institutions.president_term_limit):
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
    # Term limits (v4 Lot 2, §6bis.1) are enforced only on this deterministic
    # branch. _declare_nominees_llm reuses `citizens` unfiltered to compute
    # decide_campaign_positioning's electorate_mean over the FULL population
    # -- pre-filtering it here would silently change that already-shipped
    # LLM path's context. Closed in Lot 6/7, when lame_duck enters dt=6's
    # ctx and llm_behavior_engine.py is back in scope anyway.
    eligible = [
        c for c in citizens if not is_term_limited(c, config.institutions.president_term_limit)
    ]
    nominees = []
    for party in parties:
        nominee = select_party_nominee(party.party_id, eligible, config.candidacy)
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
    """v2 increment 2/3's LLM path: decide_candidacies replaces
    decide_candidacy's bare threshold for the dominant-path eligibility
    filter; decide_party_nominations replaces select_party_nominee_from_declared's
    deterministic tiebreak, but only for *contested* parties (2+ declared
    candidates this tick) -- a party with 0 or 1 declared candidate has
    nothing to arbitrate, so it keeps using the deterministic tiebreak
    exactly as before (also the only path when llm.enabled=False).

    Journals candidacy_considered for every evaluated citizen (declared or
    not) -- the deterministic path above never records non-candidacies at
    all. Journals party_nomination_choice for every contested party.
    Journals nomination_lost for every LLM-approved citizen who doesn't win
    their party's nomination, so their story isn't silently absent from the
    journal (design doc §16.3)."""
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

    nomination_outcome = decide_party_nominations(citizens, parties, declared_cids, config, llm_client)
    motif_by_party = {decision.party_id: decision.motif for decision in nomination_outcome.decisions}
    citizens_by_id = {c.citizen_id: c for c in citizens}

    nominees = []
    for party in parties:
        party_declared_cids = {
            c.citizen_id for c in citizens
            if c.party_affiliation == party.party_id and c.citizen_id in declared_cids
        }
        nominee: Citizen | None
        if party.party_id in nomination_outcome.winners:
            nominee = citizens_by_id[nomination_outcome.winners[party.party_id]]
            journal.write(
                tick=tick,
                event_type="party_nomination_choice",
                payload={"party_id": party.party_id, "contenders": sorted(party_declared_cids)},
                citizen_id=nominee.citizen_id,
                motif=str(motif_by_party[party.party_id]),
                codebook_version=config.llm.codebook_version,
            )
        else:
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

    parties_by_id = {party.party_id: party for party in parties}
    positioning_outcome = decide_campaign_positioning(nominees, citizens, parties_by_id, config, llm_client)
    positioning_by_cid = {decision.cid: decision for decision in positioning_outcome.decisions}
    for nominee in nominees:
        new_platform = positioning_outcome.platforms.get(nominee.citizen_id)
        if new_platform is None:
            continue
        nominee.pledged_platform = new_platform
        nominee.revealed_position = new_platform
        positioning_decision = positioning_by_cid[nominee.citizen_id]
        journal.write(
            tick=tick,
            event_type="campaign_positioning",
            payload={
                "shifts": [
                    {"dimension": shift.dimension, "delta": shift.delta} for shift in positioning_decision.shifts
                ]
            },
            citizen_id=nominee.citizen_id,
            motif=str(positioning_decision.motif),
            codebook_version=config.llm.codebook_version,
        )
    return nominees


def _hold_presidential_election(
    citizens: list[Citizen],
    parties: list[Party],
    config: PolityConfig,
    journal: Journal,
    tick: int,
    llm_client: LlmClientProtocol | None,
) -> None:
    # The outgoing president's term always ends exactly at this tick
    # (InstitutionalClock schedules the next presidential election at
    # term_end_tick by construction -- president_term_years*ticks_per_year
    # after the winning tick, same arithmetic as the term_end_tick assignment
    # below), regardless of whether this election produces a new winner.
    # Without this reset a past president keeps role=ELECTED/office=PRESIDENT
    # forever once not immediately re-nominated, so a later election leaves
    # two citizens simultaneously holding Office.PRESIDENT -- nothing reads
    # this state today, but "who currently holds office" must be a real
    # invariant for any future increment that does (representative_response,
    # term limits, legitimacy). A re-elected incumbent is simply reset here
    # and re-promoted below, same as any other winner.
    for outgoing in citizens:
        if outgoing.office == Office.PRESIDENT:
            vacate_office(outgoing)

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
            if config.legitimacy.enabled:
                # Independent of config.mandate.enabled: m only needs
                # ballots/winner_label, not pledge/deviation tracking. No
                # new journal event here -- this same tick's
                # legitimacy_updated (in _run_accountability_phase) records
                # it, including mandate_strength in its own payload.
                winner.mandate_strength = mandate_strength(ballots, winner_label)
                winner.legitimacy_capital = initial_legitimacy(winner.mandate_strength)
            if config.street_pressure.enabled:
                # A re-elected incumbent must not carry over a previous
                # term's accumulated street pressure (v4 Lot 4, §7bis.4b).
                winner.street_pressure = 0.0
            if config.petition.enabled:
                # A re-elected incumbent must not inherit their previous
                # term's open petition, signatures or cooldown -- the
                # signatures were cast against a mandate that no longer
                # exists (v4 Lot 5, §7bis.4a). A DEFEATED incumbent's stale
                # petition state is deliberately not cleared here -- same
                # precedent as pledged_platform/revealed_position above.
                reset_petition_state(winner)

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
    if winner is not None and config.mandate.enabled:
        # §7bis.5: journaled at election, separately from the per-tick
        # accountability phase's mandate_deviation_recorded. lame_duck is
        # written here (not just derivable at Lot 6 prompt time) so a
        # journal-only analyst can compute §6bis.1's lame_duck_deviation_delta
        # without needing president_term_limit from the run's config file.
        assert winner.pledged_platform is not None  # declare_candidacy always sets it
        journal.write(
            tick=tick,
            event_type="mandate_pledge_declared",
            payload={
                "office": Office.PRESIDENT.value,
                "pledged_platform": list(winner.pledged_platform),
                "mandates_served": winner.mandates_served,
                "lame_duck": is_term_limited(winner, config.institutions.president_term_limit),
            },
            citizen_id=winner.citizen_id,
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
    llm_client: LlmClientProtocol | None,
) -> None:
    if config.llm.enabled:
        _form_and_journal_coalition_llm(parties, seats, votes, config, journal, tick, llm_client)
        return
    platforms = {party.party_id: party.platform for party in parties}
    coalition = form_coalition(
        platforms, seats, votes, config.parties.coalition_tiebreak, config.parties.coalition_majority_ratio
    )
    journal.write(
        tick=tick,
        event_type="coalition_formed" if coalition is not None else "coalition_failed",
        payload={"coalition": coalition, "seats": seats},
    )


def _form_and_journal_coalition_llm(
    parties: list[Party],
    seats: dict[int, int],
    votes: dict[int, float],
    config: PolityConfig,
    journal: Journal,
    tick: int,
    llm_client: LlmClientProtocol | None,
) -> None:
    """v2 increment 5's LLM path: decide_coalition replaces form_coalition's
    nearest-neighbour greedy aggregation with one join/leave decision per
    seated, non-initiator party. The initiator designation, the majority
    rule, and the ordering in which willing partners are added stay
    deterministic (see assemble_coalition) -- the LLM contributes
    willingness and nothing else. Journals one coalition_decision per
    responder, then the aggregate coalition_formed/coalition_failed event in
    its existing, unchanged shape, so metrics.py needs no changes."""
    assert llm_client is not None  # guaranteed by _llm_client_scope when llm.enabled
    outcome = decide_coalition(parties, seats, votes, config, llm_client)
    for decision in outcome.decisions:
        journal.write(
            tick=tick,
            event_type="coalition_decision",
            payload={"party_id": decision.party_id, "action": decision.action, "initiator": outcome.initiator},
            motif=str(decision.motif),
            codebook_version=config.llm.codebook_version,
        )
    journal.write(
        tick=tick,
        event_type="coalition_formed" if outcome.coalition is not None else "coalition_failed",
        payload={"coalition": outcome.coalition, "seats": seats},
    )


def _response_context(holder: Citizen, config: PolityConfig, tick: int) -> ResponseContext:
    """v4 Lot 6: the single place the LAGGED street_pressure read happens
    (holder.street_pressure still holds whatever update_street_pressure
    wrote at step 3 of the PREVIOUS tick -- this function is always called
    before this tick's own step 2/3 mutations run, see
    _run_representative_responses), and the single place each ctx field's
    own gate is applied: L only under legitimacy.enabled, street only under
    street_pressure.enabled AND street_pressure.visible_to_representative
    (Lot 1 reserved that key with the comment "signal injecté au prompt
    (§3.6.5)"; this is its first reader -- turning it off is a real
    experimental arm, a representative blind to the street). A disabled
    quantity is None, never 0.0 -- see ResponseContext's own docstring."""
    legitimacy = holder.legitimacy_capital if config.legitimacy.enabled else None
    street = (
        holder.street_pressure
        if config.street_pressure.enabled and config.street_pressure.visible_to_representative
        else None
    )
    mandate_dev = 0.0
    if holder.pledged_platform is not None and holder.revealed_position is not None:
        mandate_dev = mandate_deviation(holder, config.mandate)
    return ResponseContext(
        cid=holder.citizen_id,
        legitimacy=legitimacy,
        mandate_dev=mandate_dev,
        street=street,
        lame_duck=is_term_limited(holder, config.institutions.president_term_limit),
        ticks_left=ticks_to_election(tick, holder.term_end_tick),
    )


def _can_sign(holder: Citizen, citizen: Citizen, tick: int, config: PolityConfig) -> bool:
    """v4 Lot 7: the exact expression the per-tick consulted loop already
    used inline since Lot 5, extracted purely so the frozen pre-loop read
    (_pressure_context) and the live per-citizen read inside the loop are
    provably the same expression rather than two copies that can drift --
    behavior-preserving, pinned by the existing Lot 5 tests."""
    return (
        petition_accepts_signatures(holder, tick, config.petition)
        and citizen.citizen_id not in holder.petition_signers
    )


def _pressure_context(
    citizen: Citizen,
    holder: Citizen,
    gap: float,
    *,
    tick: int,
    mandate_dev: float,
    config: PolityConfig,
    can_sign: bool,
    can_launch: bool,
) -> PressureContext:
    """v4 Lot 7: the single place dt=10's ctx and its frozen menu
    availability are built. `gap` is select_consulted's own returned
    self_gap and `mandate_dev` the deviation already computed once for
    this holder this tick -- neither is recomputed. `available` =
    menu_acts(config.pressure_menu) intersected with this citizen's frozen
    petition facts (can_sign/can_launch, themselves already live-read by
    the caller before this tick's consulted loop runs, so they describe
    the same instant every other citizen's ctx was frozen at). NO
    street_pressure and NO signature count reach this object (§7bis.9f) --
    see PressureContext's own docstring."""
    available = set(menu_acts(config.pressure_menu))
    if not can_sign:
        available.discard(int(PressureAct.SIGN_PETITION))
    if not can_launch:
        available.discard(int(PressureAct.LAUNCH_PETITION))
    return PressureContext(
        cid=citizen.citizen_id,
        target=holder.citizen_id,
        self_gap=gap,
        mandate_dev=mandate_dev,
        ticks_to_election=ticks_to_election(tick, holder.term_end_tick),
        available=tuple(sorted(available)),
        petition_open=holder.petition_open_since_tick is not None,
        petition_expires_at_tick=(
            holder.petition_open_since_tick + config.petition.petition_lifespan_ticks
            if holder.petition_open_since_tick is not None
            else None
        ),
        already_signed=citizen.citizen_id in holder.petition_signers,
    )


def _run_representative_responses(
    holders: list[Citizen],
    config: PolityConfig,
    journal: Journal,
    tick: int,
    llm_client: LlmClientProtocol | None,
) -> None:
    """§7bis.7 step 1 + step 7 (v4 Lot 6, dt=6): the sitting representative's
    reaction to the pressure of the PREVIOUS tick, then this tick's update of
    revealed_position.

    THE ONE-TICK LAG LIVES HERE, AND IT LIVES IN THIS FUNCTION'S POSITION.
    Every ctx value is read and frozen into a ResponseContext (via
    _response_context) before the caller's per-holder loop runs, i.e.
    before this tick's select_consulted/update_street_pressure/petition
    mutations -- so holder.street_pressure still holds the value written at
    step 3 of tick t-1. §7bis.7's Note d'ordonnancement: "le représentant
    réagit donc toujours à une pression du tick précédent, jamais
    simultanément -- ce décalage d'un tick évite une boucle de rétroaction
    instantanée non résoluble". Moving this call below the per-holder loop
    would silently break that.

    ctx.mandate_dev is the PRE-decision deviation (what the representative
    knows when deciding); the caller's own mandate_deviation call, later in
    _run_accountability_phase's per-holder loop, measures the POST-decision
    one and journals it -- two different numbers on purpose, and the pair
    is §6bis.1's lame-duck experiment.

    No deterministic fallback function exists for this gate being off: with
    config.llm.enabled false, nothing in the codebase can ever diverge
    revealed_position from pledged_platform (declare_candidacy pins them
    equal, and only decide_representative_response/decide_campaign_positioning
    ever touch either afterwards), so "no delta, stance=silence" is already
    true by construction -- the absence of this call IS the fallback."""
    assert llm_client is not None  # guaranteed by _llm_client_scope when llm.enabled
    respondents = [h for h in holders if h.pledged_platform is not None and h.revealed_position is not None]
    if not respondents:
        return
    contexts = {h.citizen_id: _response_context(h, config, tick) for h in respondents}
    outcome = decide_representative_response(respondents, contexts, config, llm_client)
    decisions = {d.cid: d for d in outcome.decisions}
    for holder in respondents:
        decision = decisions[holder.citizen_id]
        holder.revealed_position = outcome.positions[holder.citizen_id]
        journal.write(
            tick=tick,
            event_type="representative_response",
            payload={
                "office": Office.PRESIDENT.value,
                "stance": decision.stance,
                "shifts": [{"dimension": s.dimension, "delta": s.delta} for s in decision.shifts],
                "ctx": contexts[holder.citizen_id].to_payload(),
            },
            citizen_id=holder.citizen_id,
            motif=str(decision.motif),
            codebook_version=config.llm.codebook_version,
        )


def _run_accountability_phase(
    citizens: list[Citizen],
    config: PolityConfig,
    journal: Journal,
    tick: int,
    llm_client: LlmClientProtocol | None = None,
) -> None:
    """v4 Lots 2-6 -- §7bis.7's full per-tick sequence: step 1
    (representative_response + mandate_deviation, measurement) -> step 2
    (awaken -> pressure_action) -> step 3 (aggregate pressure) -> step 4
    (update L(t)) -> step 5 (petition threshold) -> step 6 (hard floor).
    Step 7 (the representative's own one-tick-delayed reading of
    street_pressure) is what step 1's representative_response call
    consumes on the FOLLOWING tick -- see _run_representative_responses's
    own docstring for exactly how the lag is structural, not incidental.

    Called last in the tick body, after both election blocks, so a
    same-tick newly-elected president's mandate_pledge_declared/L0 are
    already on record before this phase runs for them -- frozen
    journal-byte ordering: representative_response (all holders, ascending
    citizen_id) -> then, per holder: mandate_deviation_recorded (if any) ->
    [pressure_action, then petition_launched|petition_signed if that
    citizen's act produced one] x N (ascending citizen_id) ->
    legitimacy_updated -> [confidence_vote_triggered +
    confidence_vote_result] | petition_expired (mutually exclusive) ->
    recalled (if any). representative_response events are PREPENDED to the
    tick's block, never interleaved with the rest -- this is what keeps the
    Lot 3/4/5 ordering contract intact byte-for-byte whenever this lot's
    own gate (config.llm.enabled and config.mandate.enabled) is off. The
    petition-lifecycle events are interleaved immediately after their own
    citizen's pressure_action -- they describe the same atomic act by the
    same citizen, same adjacency _declare_nominees_llm already uses for
    candidacy_considered -> candidacy_declared. street_pressure(t) and
    petition_pressure(t), both computed at step 3, feed écart(t) at the
    SAME tick; only the representative's own reading of street_pressure is
    deferred a tick.

    config.mandate.enabled, config.legitimacy.enabled and
    config.awakening.enabled are independent toggles (Lot 1's cross-field
    rules only require pressure levers to imply legitimacy.enabled AND, as
    of Lot 4, awakening.enabled) -- gated separately below.
    mandate_deviation is measured whenever either mandate.enabled OR a
    nonzero passive_erosion_weight could consume it, even if mandate.enabled
    alone is false: only the mandate_deviation_recorded *journal write*
    stays gated on mandate.enabled, so a configured erosion term is never
    silently zeroed just because pledge/deviation tracking itself is off.
    The `can_sign`/`can_launch` facts passed into deterministic_pressure_action
    are computed unconditionally (they are False by construction on default
    state) -- menu.petition_enabled inside that function is the single
    authoritative gate, not a second one that could disagree.

    Step 5/6 same-tick collision (§7bis.7: the floor wins on priority):
    `floor_fires` is captured immediately after legitimacy_updated, BEFORE
    step 5 runs -- step 5 then always runs in full (never short-circuited),
    so confidence_vote_triggered/confidence_vote_result are never silently
    dropped on the exact ticks where citizen pressure is most intense. The
    priority is therefore about ATTRIBUTION (which trigger the recalled
    event names), not about which mechanism physically fires -- the office
    is vacated exactly once either way. recall_cooldown_ticks stays
    unconsumed this lot: after vacate_office, current_office_holders
    returns nothing for that office, so a repeat recall isn't representable
    until a new president exists at the next scheduled election -- far
    longer than the cooldown, so it cannot bind here regardless."""
    if not (config.mandate.enabled or config.legitimacy.enabled or config.awakening.enabled):
        return
    term_ticks = config.institutions.president_term_years * config.run.ticks_per_year
    holders = current_office_holders(citizens, Office.PRESIDENT)  # built once, as before
    if config.llm.enabled and config.mandate.enabled:  # §7bis.7 step 1 (v4 Lot 6)
        _run_representative_responses(holders, config, journal, tick, llm_client)
    for holder in holders:
        deviation: float | None = None
        if (
            (config.mandate.enabled or config.legitimacy.passive_erosion_weight > 0.0)
            and holder.pledged_platform is not None
            and holder.revealed_position is not None
        ):
            deviation = mandate_deviation(holder, config.mandate)
        if config.mandate.enabled and deviation is not None and deviation > config.mandate.deviation_log_threshold:
            journal.write(
                tick=tick,
                event_type="mandate_deviation_recorded",
                payload={"office": Office.PRESIDENT.value, "deviation": deviation},
                citizen_id=holder.citizen_id,
            )

        if config.awakening.enabled:
            consulted = select_consulted(
                citizens,
                holder,
                tick=tick,
                term_ticks=term_ticks,
                mandate_dev=deviation or 0.0,
                awakening=config.awakening,
            )
            decisions: dict[int, PressureDecision] | None = None
            contexts: dict[int, PressureContext] = {}
            if config.llm.enabled and consulted:  # §7bis.7 step 2 (v4 Lot 7)
                assert llm_client is not None  # guaranteed by _llm_client_scope when llm.enabled
                contexts = {
                    citizen.citizen_id: _pressure_context(
                        citizen,
                        holder,
                        gap,
                        tick=tick,
                        mandate_dev=deviation or 0.0,
                        config=config,
                        can_sign=_can_sign(holder, citizen, tick, config),
                        can_launch=petition_is_launchable(holder, tick),
                    )
                    for citizen, gap in consulted  # ALL frozen before any act applies
                }
                outcome = decide_pressure_actions([c for c, _ in consulted], contexts, config, llm_client)
                decisions = {d.cid: d for d in outcome.decisions}
            participants = 0
            for citizen, gap in consulted:
                can_sign = _can_sign(holder, citizen, tick, config)  # LIVE, re-read per citizen
                can_launch = petition_is_launchable(holder, tick)  # LIVE, re-read per citizen
                motif: str | None = None
                if decisions is None:
                    decided = deterministic_pressure_action(
                        citizen, gap, config.pressure_menu, can_sign=can_sign, can_launch=can_launch
                    )
                    act = decided
                    payload_extra: dict[str, object] = {}
                else:
                    decision = decisions[citizen.citizen_id]
                    decided = PressureAct(decision.act)
                    act = applicable_pressure_act(decided, can_sign=can_sign, can_launch=can_launch)
                    payload_extra = {"ctx": contexts[citizen.citizen_id].to_payload()}
                    motif = str(decision.motif)
                if act is PressureAct.MOBILIZE:
                    participants += 1
                journal.write(
                    tick=tick,
                    event_type="pressure_action",
                    payload={"target": holder.citizen_id, "act": int(decided), **payload_extra},
                    citizen_id=citizen.citizen_id,
                    motif=motif,
                    codebook_version=config.llm.codebook_version if motif else "",
                )
                if act is PressureAct.LAUNCH_PETITION:
                    launch_petition(holder, citizen, tick)
                    journal.write(
                        tick=tick,
                        event_type="petition_launched",
                        payload={
                            "target": holder.citizen_id,
                            "signatures": len(holder.petition_signers),
                            "signed_ratio": petition_pressure(holder, config.run.population_size),
                            "expires_at_tick": tick + config.petition.petition_lifespan_ticks,
                        },
                        citizen_id=citizen.citizen_id,
                    )
                elif act is PressureAct.SIGN_PETITION:
                    sign_petition(holder, citizen)
                    journal.write(
                        tick=tick,
                        event_type="petition_signed",
                        payload={
                            "target": holder.citizen_id,
                            "signatures": len(holder.petition_signers),
                            "signed_ratio": petition_pressure(holder, config.run.population_size),
                        },
                        citizen_id=citizen.citizen_id,
                    )
            if config.street_pressure.enabled:
                holder.street_pressure = update_street_pressure(
                    holder.street_pressure,
                    mobilization_rate(participants, config.run.population_size),
                    config.street_pressure,
                )

        if not config.legitimacy.enabled:
            continue
        ecart = compose_ecart(
            petition_pressure(holder, config.run.population_size),
            holder.street_pressure,
            deviation or 0.0,
            petition_weight=config.petition.weight_in_ecart,
            street_weight=config.street_pressure.weight_in_ecart,
            passive_erosion_weight=config.legitimacy.passive_erosion_weight,
        )
        holder.legitimacy_capital = update_legitimacy(
            holder.legitimacy_capital, holder.mandate_strength, ecart, config.legitimacy
        )
        journal.write(
            tick=tick,
            event_type="legitimacy_updated",
            payload={
                "office": Office.PRESIDENT.value,
                "legitimacy": holder.legitimacy_capital,
                "mandate_strength": holder.mandate_strength,
                "ecart": ecart,
            },
            citizen_id=holder.citizen_id,
        )
        floor_fires = crosses_floor(holder.legitimacy_capital, config.legitimacy)

        lost_confidence = False
        if holder.petition_open_since_tick is not None:  # step 5
            ratio = petition_pressure(holder, config.run.population_size)
            if ratio >= config.petition.signature_threshold:
                journal.write(
                    tick=tick,
                    event_type="confidence_vote_triggered",
                    payload={
                        "office": Office.PRESIDENT.value,
                        "opened_at_tick": holder.petition_open_since_tick,
                        "signatures": len(holder.petition_signers),
                        "signed_ratio": ratio,
                    },
                    citizen_id=holder.citizen_id,
                )
                ballots = [build_confidence_ballot(c, holder) for c in citizens]
                retained = resolve_confidence_vote(ballots, config.petition.confidence_vote_format)
                journal.write(
                    tick=tick,
                    event_type="confidence_vote_result",
                    payload={
                        "office": Office.PRESIDENT.value,
                        "bf": int(BallotFormat.BINARY),
                        "ballots": len(ballots),
                        "keep": sum(ballots),
                        "keep_ratio": confidence_keep_ratio(ballots),
                        "retained": retained,
                    },
                    citizen_id=holder.citizen_id,
                )
                resolve_petition(holder, tick, config.petition)
                lost_confidence = not retained
            elif petition_has_expired(holder, tick, config.petition):
                journal.write(
                    tick=tick,
                    event_type="petition_expired",
                    payload={
                        "office": Office.PRESIDENT.value,
                        "opened_at_tick": holder.petition_open_since_tick,
                        "signatures": len(holder.petition_signers),
                        "signed_ratio": ratio,
                        "signature_threshold": config.petition.signature_threshold,
                    },
                    citizen_id=holder.citizen_id,
                )
                resolve_petition(holder, tick, config.petition)

        if floor_fires:  # step 6, floor wins the attribution
            journal.write(
                tick=tick,
                event_type="recalled",
                payload={
                    "office": Office.PRESIDENT.value,
                    "legitimacy": holder.legitimacy_capital,
                    "recall_floor": config.legitimacy.recall_floor,
                    "trigger": "legitimacy_floor",
                },
                citizen_id=holder.citizen_id,
            )
            vacate_office(holder)
        elif lost_confidence:
            journal.write(
                tick=tick,
                event_type="recalled",
                payload={
                    "office": Office.PRESIDENT.value,
                    "legitimacy": holder.legitimacy_capital,
                    "recall_floor": config.legitimacy.recall_floor,
                    "trigger": "confidence_vote",
                },
                citizen_id=holder.citizen_id,
            )
            vacate_office(holder)
