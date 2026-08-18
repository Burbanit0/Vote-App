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

import logging
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np

from api.domain.polity.accountability import (
    applicable_pressure_act,
    current_office_holders,
    current_sortition_members,
    is_term_limited,
    launch_petition,
    mandate_deviation,
    neighbors_acting as compute_neighbors_acting,
    petition_accepts_signatures,
    petition_has_expired,
    petition_is_launchable,
    petition_pressure,
    reset_petition_state,
    resolve_petition,
    select_consulted,
    sign_petition,
    ticks_to_election,
    update_event_salience,
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
from api.domain.polity.codebook import BallotFormat, EventType, PressureAct, ReactionMotif
from api.domain.polity.compaction import compact_run
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
    ChamberContext,
    PressureContext,
    ReactionContext,
    ResponseContext,
    cast_votes,
    decide_campaign_positioning,
    decide_candidacies,
    decide_chamber_deliberation,
    decide_coalition,
    decide_party_nominations,
    decide_pressure_actions,
    decide_reaction_to_event,
    decide_representative_response,
    menu_acts,
    resolve_ranking_cids,
)
from api.domain.polity.llm_client import LlmClientProtocol, build_json_client
from api.domain.polity.llm_schemas import PressureDecision, ReactionDecision
from api.domain.polity.metrics import mobilization_rate
from api.domain.polity.parties import Party, initialize_parties
from api.domain.polity.shock import economic_shock_step, scandal_arrival
from api.domain.polity.sortition_chamber import select_sortition_chamber
from api.domain.polity.simple_rules import (
    BLANK_LABEL,
    assign_party_affiliation,
    attempt_rupture_candidacy,
    blank_share,
    build_confidence_ballot,
    build_ranking,
    choose_party,
    citizen_id_from_label,
    declare_candidacy,
    deterministic_pressure_action,
    deterministic_reaction_to_event,
    form_coalition,
    select_party_nominee,
    select_party_nominee_from_declared,
    vacate_office,
)
from api.domain.polity.social_graph import SocialGraph, generate_social_graph

_logger = logging.getLogger(__name__)

_WARM_UP_SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}
"""Deliberately NOT one of llm_schemas.py's real decision schemas: the
warm-up call below exists purely to exercise a GPU inference pass through
each endpoint shape before any real decision runs, never to decode a
meaningful answer. A trivial, domain-independent schema keeps that
separation obvious -- reusing e.g. PRESSURE_JSON_SCHEMA would require
fabricating a fake citizen/target/act just to satisfy validation, and would
blur an infra warm-up with an actual polity decision."""


def _warm_up_llm_client(client: LlmClientProtocol) -> None:
    """Reliability fix, GPU inference: a freshly loaded Ollama model's
    FIRST inference pass is measurably non-deterministic -- confirmed
    empirically (scripts/llm_batching_determinism_results_gpu.md, "cold
    start vs warm" section): the same prompt, same seed, temperature=0,
    issued right after a cold model load, produces a different raw
    completion than every subsequent call with that same prompt, which are
    then perfectly reproducible among themselves. Since every real
    acceptance run's very first LLM call is a real, journaled decision
    (typically candidacy_considered), that one-time coin flip would
    otherwise land on something that matters and cascades downstream (a
    different nominee count observed directly in this project's own
    investigation).

    Issues one throwaway call through EACH endpoint shape --
    think=True (/v1/chat/completions) and think=False (native /api/chat,
    see llm_client.py's own module docstring for why these are two
    genuinely different request paths) -- so whichever one the pipeline's
    real first call happens to use, it is already warm. Confirmed
    empirically that a fixed warm-up call, applied after a forced-cold
    state, makes the subsequent real call deterministic and repeatable
    across independent cold-start cycles (same results doc) -- "warm" is
    path-dependent, not one universal state, but a CONSISTENT procedure is
    what §4 reproducibility actually needs, not literal agreement with an
    arbitrary prior warm history.

    Does not, on its own, protect a call in the middle of a multi-hour run
    from a cold-start reintroduced by Ollama's idle keep_alive timeout --
    confirmed empirically that keep_alive is silently ignored when sent on
    the OpenAI-compat endpoint (same failure mode as num_ctx, see
    ollama_context_window_results.md), so that half of the fix is the
    container-level OLLAMA_KEEP_ALIVE env var documented in
    polity_config.yaml's llm.base_url comment, not application code.

    Best-effort and deliberately never fatal: a warm-up call failing (for
    any reason) is logged and swallowed, not allowed to abort a run over
    what is not itself part of the simulation -- and never journaled, for
    the same reason LLM replay attempts aren't (v4 Lot 8): this is about
    the inference host, not the polity."""
    for think in (True, False):
        try:
            client.complete_json(
                system_prompt="Reply with the required JSON object.",
                user_prompt="{}",
                json_schema=_WARM_UP_SCHEMA,
                max_tokens=32,
                think=think,
            )
        except Exception as exc:  # noqa: BLE001
            _logger.warning("LLM warm-up call (think=%s) failed, continuing anyway: %s", think, exc)


@dataclass(frozen=True)
class PendingRerun:
    """v4 Lot 9 (§6bis.2): local, run-scoped state for the invalidate ->
    rerun -> bar cycle, deliberately NOT a Citizen field: unlike every other
    officeholder-scoped piece of state this project has added since Lot 3
    (legitimacy_capital, street_pressure, petition state), an invalidated
    election has no officeholder to attach state to by construction. Held as
    a plain local in run_simulation's scope, threaded into and back out of
    _hold_presidential_election and into _attempt_rupture_candidacies every
    tick -- the same register as rupture_rng, the one other piece of
    cross-tick local state this module already carries.

    `attempt` is the rerun's own 1-indexed number: the ORIGINAL scheduled
    election is never tracked as a PendingRerun at all (there is no pending
    state until the first invalidation). attempt=1 is the first rerun,
    attempt=2 the second. Attempts 1..reelection_max_attempts get the full
    invalidation check; attempt reelection_max_attempts+1 is FORCED (see
    _is_forced_attempt) -- §6bis.2's "au-delà, un résultat est forcé".

    `barred_candidate_ids` unions the candidate set of every invalidated
    election within this one cycle, but ONLY when
    config.institutions.barred_from_immediate_rerun is true -- that key is
    its own toggle, independent of blank_vote_competitive (shipped true,
    the doc's own recommended default, but a real comparison arm). Cleared
    (the whole PendingRerun discarded, back to None) the instant the cycle
    resolves: a real winner elected, or the forced attempt's outcome
    (winner or election_no_winner) accepted.

    `next_tick` REPLACES the fixed calendar for the presidency while this is
    active (see run_simulation's own tick loop), rather than being OR'd into
    it -- OR-ing a rerun tick into the fixed calendar is reachable at
    non-default reelection_delay_ticks/president_term_years combinations
    and produces two independent elections for one vacancy, with no journal
    event marking the discard."""

    attempt: int
    next_tick: int
    barred_candidate_ids: frozenset[int]


def _is_forced_attempt(pending_rerun: PendingRerun | None, config: PolityConfig) -> bool:
    return pending_rerun is not None and pending_rerun.attempt > config.institutions.reelection_max_attempts


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
    injected, a real client for `config.llm.provider` is constructed (v4
    vLLM switch, §15bis.6 — see llm_client.build_json_client) for the
    run's lifetime and closed here; an injected client (tests) is never
    closed — it belongs to the caller.

    When `config.journal.index_after_run` is true (shipped default), the
    finished journal is compacted into a `.duckdb` file beside it (v4
    storage lot, §16.6 — see compaction.compact_run) after the journal is
    closed, never before: §16.1's hard rule is that compaction is strictly
    post-run, so the hot regime never reads, indexes, or queries the
    journal, and an interrupted run still leaves an exploitable JSONL with
    no half-written `.duckdb` beside it.
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

    clock = InstitutionalClock.from_config(config.institutions, config.run, config.sortition_chamber)
    # Independent stream from population/party generation (same pattern as
    # Lot 2/3): a fresh default_rng per concern, so enabling rupture draws
    # never perturbs the citizens/parties already generated above.
    rupture_rng = np.random.default_rng(config.run.seed)
    # v5 Lot 2 (§8): a third independent stream, never reusing rupture_rng --
    # same "fresh default_rng per concern" reasoning as above. rupture_rng
    # already draws unconditionally every tick for every elector (before the
    # is_term_limited/barred-set check, specifically so a gated citizen
    # never shifts the stream); coupling v5's draws into that stream would
    # either entangle two unrelated mechanisms' RNG consumption for no
    # benefit, or -- if inserted only when events.enabled -- violate
    # rupture_rng's own existing, tested draw-position contract for every
    # run that doesn't enable events. Fixed intra-stream draw order inside
    # _run_exogenous_events: scandal arrival before the AR(1) innovation.
    events_rng = np.random.default_rng(config.run.seed)
    # v6b Lot 2 (§6bis.3): a fourth independent stream -- unlike `graph`
    # below (generated once, no persistent stream name needed), sortition
    # selection draws repeatedly, every rotation tick, so it needs the
    # rupture_rng/events_rng-style persistent stream. Drawn from only
    # inside select_sortition_chamber, only on a rotation tick, only when
    # sortition_chamber.enabled -- undrawn otherwise.
    sortition_rng = np.random.default_rng(config.run.seed)
    # v4 Lot 9 (§6bis.2): None whenever blank_vote_competitive is off (the
    # shipped default) or no cycle is currently open -- see PendingRerun's
    # own docstring for why this is a plain local, not a Citizen field.
    pending_rerun: PendingRerun | None = None
    # v5 Lot 2 (§8): the AR(1) economic-climate variable, x(t) -- population-
    # wide, no natural Citizen owner, so a bare local in the same register as
    # rupture_rng/pending_rerun rather than a Citizen field. Reassigned from
    # _run_exogenous_events's return value every tick. Deliberately
    # unclamped -- see shock.economic_shock_step's own docstring.
    economy_x: float = 0.0
    # v6 Lot 2/3 (§5): generated once, population-structural (evolving is
    # TRANCHÉ rejected at config-parse time, so this never changes mid-run).
    # None whenever social_graph.enabled is off (the shipped default) --
    # every reader below treats None as "no graph" and behaves identically
    # to pre-v6-Lot-3 code.
    graph: SocialGraph | None = None
    if config.social_graph.enabled:
        graph = generate_social_graph(config.social_graph, config.run.population_size, config.run.seed)
    # v6 Lot 3 (§5/§7bis.9c): citizen_id -> target citizen_id, for every
    # citizen whose APPLIED pressure_action was MOBILIZE on the most
    # recently completed tick -- a bare local in the same register as
    # economy_x, fully REPLACED (never accumulated) every tick by
    # _run_accountability_phase's own return value, so it always reflects
    # exactly one completed tick. The one-tick lag mirrors dt=6's own
    # street_pressure lag (v4 Lot 6): decide_pressure_actions batches an
    # entire cohort's decisions in one frozen call, so a neighbor's SAME-
    # tick decision cannot be seen by construction.
    mobilized_last_tick: Mapping[int, int] = {}

    with Journal.from_config(config.journal, run_id) as journal, _llm_client_scope(config, llm_client) as client:
        for tick in range(clock.total_ticks + 1):
            barred_ids = pending_rerun.barred_candidate_ids if pending_rerun is not None else frozenset()
            _attempt_rupture_candidacies(citizens, config, journal, tick, rupture_rng, barred_candidate_ids=barred_ids)
            exogenous = _run_exogenous_events(citizens, config, journal, tick, events_rng, economy_x)
            economy_x = exogenous.economy_x
            election = clock.election_at(tick)
            # While a rerun is pending, the fixed presidential calendar is
            # SUSPENDED, not OR'd with the rerun tick -- see PendingRerun's
            # own docstring for why a union reintroduces a double-election
            # pathology. This reduces to today's exact
            # `election in (PRESIDENTIAL, BOTH)` check whenever
            # pending_rerun is None, which is always true when
            # blank_vote_competitive is off.
            if pending_rerun is not None:
                hold_president = tick == pending_rerun.next_tick
            else:
                hold_president = election in (ElectionType.PRESIDENTIAL, ElectionType.BOTH)
            if hold_president:
                pending_rerun = _hold_presidential_election(
                    citizens, parties, config, journal, tick, client, pending_rerun
                )
            if election in (ElectionType.LEGISLATIVE, ElectionType.BOTH):
                seats, votes = _hold_legislative_election(citizens, parties, config, journal, tick)
                _form_and_journal_coalition(parties, seats, votes, config, journal, tick, client)
            if config.sortition_chamber.enabled and clock.is_sortition_rotation(tick):
                _run_sortition_rotation(citizens, config, journal, tick, sortition_rng)
            if config.sortition_chamber.enabled:
                _run_chamber_deliberation(citizens, config, journal, tick, client)
            mobilized_last_tick = _run_accountability_phase(
                citizens, config, journal, tick, client,
                exogenous=exogenous, graph=graph, mobilized_last_tick=mobilized_last_tick,
            )

    journal_path = Path(config.journal.output_dir) / run_id / "events.jsonl"
    if config.journal.enabled and config.journal.index_after_run:
        compact_run(journal_path, config)
    return journal_path


@contextmanager
def _llm_client_scope(config: PolityConfig, llm_client: LlmClientProtocol | None) -> Iterator[LlmClientProtocol | None]:
    """v4 vLLM switch (§15bis.6): dispatch on config.llm.provider via
    llm_client.build_json_client, rather than always constructing an
    OllamaJsonClient. Ordering unchanged and still load-bearing: an
    injected client always short-circuits first (tests), then a disabled
    LLM path yields None regardless of provider (so `provider: api` +
    `enabled: false` still loads and runs), and only then does dispatch
    happen — so an unsupported/unimplemented provider (currently only
    "api") now fails HERE, at run start, rather than at the first decision
    inside llm_behavior_engine._check_supported. Earlier and cheaper.

    GPU reliability fix: _warm_up_llm_client runs exactly once, only on a
    real, owned client -- never on an injected one (tests always inject a
    fake client, which must never make a real HTTP call) -- and always
    before the caller's first real decision, so a cold-model non-
    determinism (see that function's own docstring) never lands on
    something journaled."""
    if llm_client is not None:
        yield llm_client
        return
    if not config.llm.enabled:
        yield None
        return
    with build_json_client(config.llm, seed=config.run.seed) as owned_client:
        _warm_up_llm_client(owned_client)
        yield owned_client


def _attempt_rupture_candidacies(
    citizens: list[Citizen],
    config: PolityConfig,
    journal: Journal,
    tick: int,
    rng: np.random.Generator,
    barred_candidate_ids: frozenset[int] = frozenset(),
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
        # is_term_limited (and, since v4 Lot 9, the §6bis.2 barred set) is
        # checked AFTER the draw, never before: skipping the call for a
        # gated citizen would shift the RNG stream and break byte-for-byte
        # reproducibility for any non-null president_term_limit or any run
        # where a rerun cycle is open (v4 Lot 2, §6bis.1 / Lot 9, §6bis.2).
        declared = attempt_rupture_candidacy(citizen, citizens, config.candidacy, rng)
        if (
            declared
            and not is_term_limited(citizen, config.institutions.president_term_limit)
            and citizen.citizen_id not in barred_candidate_ids
        ):
            declare_candidacy(citizen)
            journal.write(
                tick=tick,
                event_type="candidacy_declared",
                payload={"path": "rupture"},
                citizen_id=citizen.citizen_id,
            )


@dataclass(frozen=True)
class ExogenousEventsOutcome:
    """v5 Lot 3 (§8): the per-tick facts _run_accountability_phase's own
    step 0 needs about the tick _run_exogenous_events just processed.
    WITHIN-TICK only -- built fresh every tick and consumed a few
    statements later in the SAME tick body, unlike PendingRerun/economy_x
    which are genuinely threaded across tick boundaries (only this
    struct's own economy_x field continues to be, via the same bare-float
    local Lot 2 established). scandal_target is captured HERE, at draw
    time -- never recomputed downstream from current_office_holders a
    second time, which would silently disagree with scandal_occurred's own
    already-journaled target on any tick where a same-tick presidential
    election runs between this call and _run_accountability_phase's own
    (later) holders lookup."""

    economy_x: float
    scandal_fired: bool
    scandal_target: int | None
    shock_crossed: bool


def _run_exogenous_events(
    citizens: list[Citizen],
    config: PolityConfig,
    journal: Journal,
    tick: int,
    rng: np.random.Generator,
    economy_x: float,
) -> ExogenousEventsOutcome:
    """v5 Lot 2 (§8): the two exogenous generators, evaluated every tick --
    unconditional, before any election dispatch, the same anchor point
    _attempt_rupture_candidacies already establishes. Deliberately outside
    _run_accountability_phase and independent of it: this function never
    calls select_consulted/awakening_threshold.

    A scandal is drawn from unconditionally whenever scandal_enabled is
    true, regardless of whether a president currently exists -- vacancy is
    a TARGET-RESOLUTION fact (current_office_holders may return []), never
    a reason to skip the draw itself, matching v4's own "vacancy is a
    first-class state" precedent. `target` is null on a vacancy, mirroring
    election_invalidated's own explicit citizen_id=None precedent."""
    scandal_fired = scandal_arrival(rng, config.events)
    scandal_target: int | None = None
    if scandal_fired:
        holders = current_office_holders(citizens, Office.PRESIDENT)
        scandal_target = holders[0].citizen_id if holders else None
        journal.write(
            tick=tick,
            event_type="scandal_occurred",
            payload={"target": scandal_target},
            citizen_id=scandal_target,
        )

    economy_x = economic_shock_step(economy_x, rng, config.events)
    # Explicit re-check of economic_shock_enabled, not just the value
    # comparison (mirrors mandate_deviation_recorded's own redundant
    # config.mandate.enabled check): with economic_shock_enabled=False,
    # economy_x is frozen at its seeded 0.0 forever, but a config with
    # economy_shock_threshold=0.0 (legal -- _get_ratio allows the boundary)
    # would make abs(0.0) >= 0.0 true on EVERY tick without this guard,
    # silently resurrecting a "disabled" mechanism's journal footprint.
    shock_crossed = (
        config.events.economic_shock_enabled and abs(economy_x) >= config.events.economy_shock_threshold
    )
    if shock_crossed:
        journal.write(
            tick=tick,
            event_type="economic_shock_tick",
            payload={"x": economy_x, "threshold": config.events.economy_shock_threshold},
        )

    return ExogenousEventsOutcome(
        economy_x=economy_x, scandal_fired=scandal_fired, scandal_target=scandal_target, shock_crossed=shock_crossed
    )


def _declare_nominees(
    citizens: list[Citizen],
    parties: list[Party],
    config: PolityConfig,
    journal: Journal,
    tick: int,
    llm_client: LlmClientProtocol | None,
    barred_candidate_ids: frozenset[int] = frozenset(),
) -> list[Citizen]:
    if config.llm.enabled:
        # barred_candidate_ids intentionally NOT passed here, extending the
        # same asymmetry term limits already have on this path (see below).
        return _declare_nominees_llm(citizens, parties, config, journal, tick, llm_client)
    # Term limits (v4 Lot 2, §6bis.1) and, since Lot 9, the §6bis.2 barred
    # set are enforced only on this deterministic branch.
    # _declare_nominees_llm reuses `citizens` unfiltered to compute
    # decide_campaign_positioning's electorate_mean over the FULL population
    # -- pre-filtering it here would silently change that already-shipped
    # LLM path's context. Verified directly (Lot 9): this asymmetry was
    # never actually closed by Lot 6/7 as originally anticipated -- Lot 6
    # added lame_duck to dt=6's *response* context, not to nomination
    # filtering -- so Lot 9 extends the same, still-open gap in the same
    # direction rather than fixing it. Closing it (for both term limits and
    # the barred set together) is a legitimate, separately-scoped follow-up.
    eligible = [
        c
        for c in citizens
        if not is_term_limited(c, config.institutions.president_term_limit)
        and c.citizen_id not in barred_candidate_ids
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
    pending_rerun: PendingRerun | None = None,
) -> PendingRerun | None:
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

    barred_ids = pending_rerun.barred_candidate_ids if pending_rerun is not None else frozenset()
    nominees = _declare_nominees(citizens, parties, config, journal, tick, llm_client, barred_candidate_ids=barred_ids)
    nominee_ids = {c.citizen_id for c in nominees}
    standing_rupture_candidates = sorted(
        (c for c in citizens if c.role == Role.CANDIDATE and c.citizen_id not in nominee_ids),
        key=lambda c: c.citizen_id,
    )
    nominees = nominees + standing_rupture_candidates

    winner: Citizen | None = None
    invalidated = False
    blank_share_value: float | None = None
    all_candidate_ids: set[int] = set()
    if nominees:
        all_candidate_ids = {c.citizen_id for c in nominees}
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

        # v4 Lot 9 (§6bis.2): the deterministic-enclave threshold check --
        # no LLM, no RNG, just the ballots already built above. A forced
        # attempt (beyond reelection_max_attempts) skips the check entirely
        # and accepts whatever get_presidential_winner returns, "pour éviter
        # la boucle infinie".
        if config.institutions.blank_vote_competitive and not _is_forced_attempt(pending_rerun, config):
            blank_share_value = blank_share(ballots)
            if blank_share_value > config.institutions.blank_invalidation_threshold:
                invalidated = True

        if not invalidated:
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

    # Fires unconditionally whenever winner is None -- including the
    # invalidated case, which is exactly what makes barred candidates
    # already Role.ELECTOR again by the time the next tick's (now
    # barred-aware) candidacy gates run, with no separate reset needed.
    for nominee in nominees:
        if nominee is not winner:
            nominee.role = Role.ELECTOR
            nominee.pledged_platform = None
            nominee.revealed_position = None

    if invalidated:
        new_attempt = (pending_rerun.attempt if pending_rerun is not None else 0) + 1
        barred_next = (
            (barred_ids | all_candidate_ids) if config.institutions.barred_from_immediate_rerun else frozenset()
        )
        new_pending_rerun = PendingRerun(
            attempt=new_attempt,
            next_tick=tick + config.institutions.reelection_delay_ticks,
            barred_candidate_ids=barred_next,
        )
        journal.write(
            tick=tick,
            event_type="election_invalidated",
            payload={
                "office": Office.PRESIDENT.value,
                "blank_share": blank_share_value,
                "threshold": config.institutions.blank_invalidation_threshold,
                "attempt": new_attempt,
                "candidate_ids": sorted(all_candidate_ids),
                "barred_candidate_ids": sorted(barred_next),
                "next_attempt_tick": new_pending_rerun.next_tick,
            },
            citizen_id=None,
        )
        return new_pending_rerun

    journal.write(
        tick=tick,
        event_type="elected" if winner is not None else "election_no_winner",
        payload={
            "office": Office.PRESIDENT.value,
            # §6bis.2: additive, always both-or-neither, and gated on
            # `nominees` (not just blank_vote_competitive) -- these two keys
            # describe the invalidation check's own bookkeeping, which is
            # meaningless when there was no candidate field to measure
            # blank_share against (nominees empty -> a PendingRerun could
            # never have been created either, so attempt/forced would be a
            # constant 0/0 carrying no information). This is what keeps a
            # config where nominees never exist a true byte-for-byte no-op
            # even with blank_vote_competitive=true, not merely a config
            # where the mechanism happens not to trigger.
            **(
                {
                    "attempt": pending_rerun.attempt if pending_rerun is not None else 0,
                    "forced": int(_is_forced_attempt(pending_rerun, config)),
                }
                if config.institutions.blank_vote_competitive and nominees
                else {}
            ),
        },
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
    return None


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
    neighbors_acting_by_cid: Mapping[int, float] | None = None,
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
    see PressureContext's own docstring.

    `neighbors_acting_by_cid` (v6 Lot 3) is the SAME dict select_consulted's
    own caller already computed once per holder via
    accountability.neighbors_acting -- reused here, never recomputed,
    exactly the "compute once, thread the value" precedent mandate_dev/
    deviation already established. None (the default, when the graph is
    off) means the caller passes no dict at all -- PressureContext.
    neighbors_acting then stays None, never 0.0 (null means "not tracked",
    per this project's own established rule)."""
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
        neighbors_acting=(
            neighbors_acting_by_cid.get(citizen.citizen_id) if neighbors_acting_by_cid is not None else None
        ),
    )


def _run_reaction_to_event(
    citizens: list[Citizen],
    event_type: EventType,
    config: PolityConfig,
    journal: Journal,
    tick: int,
    llm_client: LlmClientProtocol | None,
    *,
    target: int | None,
    magnitude: float = 0.0,
) -> None:
    """v5 Lot 3's step-0 baseline, now with an LLM branch under
    config.llm.enabled (v5 Lot 4, dt=8). Population-wide: loops over the
    WHOLE `citizens` list, never `holders`. Called once per firing
    event_type from _run_accountability_phase's step 0 -- a tick where
    both scandal_fired and shock_crossed fire calls this twice, in the
    fixed scandal-then-shock order Lot 3 established, so "a tick where
    both fire stays deterministic byte for byte" continues to describe
    the LLM path too.

    No additional config.events.enabled gate (Lot 3's own precedent,
    restated): this function only ever runs inside `if exogenous.
    scandal_fired:`/`if exogenous.shock_crossed:`, both of which already
    imply events.enabled=True (config.py's own cross-field rule) -- a
    second explicit conjunct here could never disagree. Likewise no
    second config.llm.enabled conjunct beyond the one below: unlike dt=6/
    dt=10, this branch needs no section flag (mandate.enabled/
    awakening.enabled) alongside it, since events.enabled is already
    structurally guaranteed the moment this function is ever called.

    `contexts` is built HERE, before decide_reaction_to_event runs, and
    read again below AFTER it returns for the journal write -- never
    rebuilt from a citizen's (by-then-mutated) event_salience. This is
    why decide_reaction_to_event takes contexts as a caller-supplied
    mapping rather than building it internally: the journal write must
    record the SAME pre-update value the model saw, not a value re-read
    after this loop has already mutated event_salience for earlier
    citizens in citizen_id order."""
    if event_type is EventType.SCANDAL:
        grounding_motif = ReactionMotif.SCANDAL_TRUST_EROSION
    elif event_type is EventType.ECONOMIC_SHOCK:
        grounding_motif = ReactionMotif.ECONOMIC_SHOCK_REACTION
    else:
        raise ValueError(f"unhandled EventType: {event_type!r}")

    reaction_decisions: dict[int, ReactionDecision] | None = None
    contexts: dict[int, ReactionContext] = {}
    if config.llm.enabled:
        assert llm_client is not None  # guaranteed by _llm_client_scope when llm.enabled
        contexts = {c.citizen_id: ReactionContext(cid=c.citizen_id, event_salience=c.event_salience) for c in citizens}
        outcome = decide_reaction_to_event(
            citizens, contexts, event_type, config, llm_client, target=target, magnitude=magnitude
        )
        reaction_decisions = {d.cid: d for d in outcome.decisions}

    for citizen in citizens:
        if reaction_decisions is None:
            delta = deterministic_reaction_to_event(event_type, config.events, magnitude=magnitude)
            motif = str(grounding_motif)
            extra: dict[str, object] = {}
        else:
            decision = reaction_decisions[citizen.citizen_id]
            delta = decision.salience_delta
            motif = str(decision.motif)
            extra = {"ctx": contexts[citizen.citizen_id].to_payload()}
        citizen.event_salience = update_event_salience(citizen.event_salience, delta, config.events)
        payload: dict[str, object] = {"event_type": int(event_type), "target": target, "salience_delta": delta, **extra}
        if event_type is EventType.ECONOMIC_SHOCK:
            payload["magnitude"] = magnitude
        journal.write(
            tick=tick,
            event_type="reaction_to_event",
            payload=payload,
            citizen_id=citizen.citizen_id,
            motif=motif,
            codebook_version=config.llm.codebook_version,
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


def _run_sortition_rotation(
    citizens: list[Citizen], config: PolityConfig, journal: Journal, tick: int, rng: np.random.Generator,
) -> None:
    """v6b Lot 2 (§6bis.3): whole-chamber rotation. Called from the tick
    loop AFTER both election blocks -- at the shipped defaults,
    sortition_term_ticks=4 divides evenly into president_term_ticks=16,
    assembly_term_ticks=16 and assembly_offset_ticks=8, so every
    presidential AND legislative election tick is ALSO a rotation tick
    (confirmed by direct calculation, not an edge case). Running this after
    both election blocks means the eligible pool reflects that SAME tick's
    own finalized office holder -- a newly-elected president is correctly
    excluded from the same-tick sortition draw, mirroring why
    _run_accountability_phase itself already runs last.

    Vacates every currently-seated member BEFORE drawing (select_sortition_
    chamber's own pool computation assumes nobody is currently seated).
    `vacated` in the journal payload is the pre-vacate roster, so one event
    carries the full transition (mirrors recalled/election_invalidated's
    own "one event, full transition" register)."""
    vacated = sorted(c.citizen_id for c in citizens if c.sortition_seat_until_tick is not None)
    for citizen in citizens:
        if citizen.sortition_seat_until_tick is not None:
            citizen.sortition_seat_until_tick = None

    drawn, relaxed = select_sortition_chamber(citizens, config.sortition_chamber, rng)
    by_id = {c.citizen_id: c for c in citizens}
    for cid in drawn:
        member = by_id[cid]
        member.sortition_seat_until_tick = tick + config.sortition_chamber.term_years * config.run.ticks_per_year
        member.sortition_terms_served += 1
        # v6b Lot 3 (§6bis.3): fresh start each term -- a redrawn member
        # (Lot 2's relaxed-pool fallback) must not inherit a previous,
        # unrelated term's own drift.
        member.chamber_position = member.issue_positions

    journal.write(
        tick=tick,
        event_type="sortition_rotation",
        payload={"seated": drawn, "vacated": vacated, "pool_relaxed": int(relaxed)},
    )


def _run_chamber_deliberation(
    citizens: list[Citizen], config: PolityConfig, journal: Journal, tick: int,
    llm_client: LlmClientProtocol | None,
) -> None:
    """v6b Lot 3 (§6bis.3, dt=11): dispatched directly from the tick loop,
    NEVER nested inside _run_accountability_phase. That function's own
    early-return guard (`if not (mandate.enabled or legitimacy.enabled or
    awakening.enabled): return {}`) has no sortition_chamber.enabled
    disjunct and was never going to get one -- the chamber is
    architecturally independent of the presidency's own accountability
    loop (no officeholder, no écart(t), no legitimacy reaches it, per
    §6bis.3's own insulation requirement). Runs every tick the chamber is
    enabled, not just rotation ticks -- mirrors dt=6's own "every tick, not
    just an election tick" cadence, the cleanest comparison against the
    president's own per-tick representative_response.

    No deterministic fallback function exists for llm.enabled=False:
    chamber_position is pinned to issue_positions at seating time
    (_run_sortition_rotation) and nothing else in the codebase ever
    touches it without this call, so "no delta" is already true by
    construction -- the absence of this call IS the fallback, exactly
    _run_representative_responses's own precedent for dt=6."""
    if not config.llm.enabled:
        return
    members = current_sortition_members(citizens)
    if not members:
        return
    assert llm_client is not None  # guaranteed by _llm_client_scope when llm.enabled
    contexts: dict[int, ChamberContext] = {}
    for m in members:
        assert m.sortition_seat_until_tick is not None  # guaranteed by current_sortition_members's own filter
        contexts[m.citizen_id] = ChamberContext(cid=m.citizen_id, ticks_left=m.sortition_seat_until_tick - tick)
    outcome = decide_chamber_deliberation(members, contexts, config, llm_client)
    decisions = {d.cid: d for d in outcome.decisions}
    for member in members:
        decision = decisions[member.citizen_id]
        member.chamber_position = outcome.positions[member.citizen_id]
        journal.write(
            tick=tick,
            event_type="chamber_deliberation",
            payload={
                "shifts": [{"dimension": s.dimension, "delta": s.delta} for s in decision.shifts],
                "ctx": contexts[member.citizen_id].to_payload(),
            },
            citizen_id=member.citizen_id,
            motif=str(decision.motif),
            codebook_version=config.llm.codebook_version,
        )


def _run_accountability_phase(
    citizens: list[Citizen],
    config: PolityConfig,
    journal: Journal,
    tick: int,
    llm_client: LlmClientProtocol | None = None,
    exogenous: ExogenousEventsOutcome | None = None,
    graph: SocialGraph | None = None,
    mobilized_last_tick: Mapping[int, int] | None = None,
) -> Mapping[int, int]:
    """v4 Lots 2-6, v5 Lots 3-4 -- §7bis.7's full per-tick sequence: step 0
    (v5 Lot 3/4, §8: population-wide reaction_to_event, LLM-driven under
    config.llm.enabled since Lot 4, deterministic otherwise, before
    anything officeholder-scoped) -> step 1 (representative_response +
    mandate_deviation, measurement) -> step 2 (awaken -> pressure_action)
    -> step 3 (aggregate pressure) -> step 4 (update L(t)) -> step 5
    (petition threshold) -> step 6 (hard floor). Step 7 (the
    representative's own one-tick-delayed reading of street_pressure) is
    what step 1's representative_response call consumes on the FOLLOWING
    tick -- see _run_representative_responses's own docstring for exactly
    how the lag is structural, not incidental.

    `exogenous` is additive (default None) so every pre-v5-Lot-3 direct
    call to this function is unaffected -- None is silently equivalent to
    "nothing fired this tick" (see step 0's own guard below). The real
    tick loop always supplies a genuine ExogenousEventsOutcome, firing or
    not; only direct-call unit tests that don't care about step 0 rely on
    the default.

    Called last in the tick body, after both election blocks, so a
    same-tick newly-elected president's mandate_pledge_declared/L0 are
    already on record before this phase runs for them -- frozen
    journal-byte ordering: reaction_to_event (v5 Lot 3, population-wide,
    ascending citizen_id, scandal branch before economic-shock branch) ->
    representative_response (all holders, ascending citizen_id) -> then,
    per holder: mandate_deviation_recorded (if any) ->
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
    longer than the cooldown, so it cannot bind here regardless.

    `graph`/`mobilized_last_tick` are v6 Lot 3 additions (§5/§7bis.9c),
    both additive with None-safe defaults so every pre-v6-Lot-3 direct call
    keeps compiling and behaving identically. Returns a FRESH
    `Mapping[int, int]` (citizen_id -> target citizen_id) built from this
    tick's own APPLIED MOBILIZE decisions -- a full replace, never merged
    with the incoming `mobilized_last_tick`, so it always reflects exactly
    one completed tick for the caller to thread into the next tick's own
    call (the same one-tick-lag contract accountability.neighbors_acting's
    own docstring describes). The early-return path returns `{}`: when
    every accountability mechanic is off, nothing this tick could have
    mobilized either."""
    if not (config.mandate.enabled or config.legitimacy.enabled or config.awakening.enabled):
        return {}
    term_ticks = config.institutions.president_term_years * config.run.ticks_per_year
    holders = current_office_holders(citizens, Office.PRESIDENT)  # built once, as before
    new_mobilized: dict[int, int] = {}  # v6 Lot 3: this tick's own applied MOBILIZE decisions
    # v5 Lot 3/4 (§8) -- step 0, before step 1: population-wide, never
    # officeholder-scoped (dt=8 is not select_consulted-gated), so
    # _run_reaction_to_event loops over `citizens`, not `holders`, and
    # needs nothing `holders` produces. Fixed processing order -- scandal
    # branch before economic-shock branch -- mirrors _run_exogenous_events's
    # own fixed draw order, so a tick where both fire stays deterministic
    # byte for byte (LLM-decided or not). Deterministic-path payload shape
    # is asymmetric per event_type, mirroring scandal_occurred/
    # economic_shock_tick's own asymmetric raw payloads (Lot 2): SCANDAL
    # carries `target`, no `magnitude`; ECONOMIC_SHOCK carries `magnitude`,
    # target is always null (systemic, no single object). Both journal
    # motif=401/402 unconditionally even without an LLM (deliberate
    # divergence from pressure_action's own deterministic branch, which
    # leaves motif=None): unlike an LLM's stated reason, these motifs
    # encode WHICH generator fired, a fact already certain either way.
    if exogenous is not None:
        if exogenous.scandal_fired:
            _run_reaction_to_event(
                citizens, EventType.SCANDAL, config, journal, tick, llm_client, target=exogenous.scandal_target
            )
        if exogenous.shock_crossed:
            _run_reaction_to_event(
                citizens, EventType.ECONOMIC_SHOCK, config, journal, tick, llm_client,
                target=None, magnitude=exogenous.economy_x,
            )
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
            # v6 Lot 3 (§5): computed once per holder, over the WHOLE
            # population -- select_consulted needs every candidate
            # citizen's own fraction, not just the eventually-consulted
            # cohort's. {} whenever graph is None (no social graph), which
            # neighbors_acting_by_cid.get(..., 0.0) below treats identically
            # to "no contagion signal".
            neighbors_acting_by_cid: dict[int, float] = (
                compute_neighbors_acting(citizens, holder.citizen_id, graph, mobilized_last_tick or {})
                if graph is not None
                else {}
            )
            consulted = select_consulted(
                citizens,
                holder,
                tick=tick,
                term_ticks=term_ticks,
                mandate_dev=deviation or 0.0,
                awakening=config.awakening,
                neighbors_acting=neighbors_acting_by_cid,
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
                        neighbors_acting_by_cid=neighbors_acting_by_cid if graph is not None else None,
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
                    new_mobilized[citizen.citizen_id] = holder.citizen_id  # v6 Lot 3: for NEXT tick's own read
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

    return new_mobilized
