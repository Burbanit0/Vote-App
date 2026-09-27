"""api.domain.polity.accountability — §7bis.5/§6bis.1/§7bis.9/§7bis.4a:
mandate deviation, term limits, the awakening gate, mobilization
aggregation, and (v4 Lot 5) the petition state machine. Measurement/gating
only through Lot 4: `mandate_deviation` is information (§7bis.5), the
awakening gate decides only WHO is consulted, never WHAT they decide
(§7bis.9d) -- `deterministic_pressure_action` (simple_rules.py) and, from
Lot 7, the LLM own that. Lot 5 adds this module's first *mutations*
(launch/sign/resolve/reset a petition) -- kept here, next to the
predicates that guard them, rather than inlined at the one call site, so
each has exactly one implementation (the same reasoning that produced
`vacate_office` in Lot 2). Lot 6 adds the LLM decision that reads
`mandate_deviation`/`is_term_limited`. Lot 7 adds this module's first
`codebook` import: `applicable_pressure_act` reconciles a decided
`PressureAct` (frozen pre-loop, from the LLM) with live petition state at
application time -- see its own docstring for why this can never be a
batch-rejecting check. v6 Lot 3 adds this module's first `social_graph`
import: `neighbors_acting` aggregates the per-citizen Granovetter-style
contagion signal (§5), read by `awakening_threshold`'s own new fourth term
and by `pressure_action`'s (dt=10) `ctx` -- still a sampling-gate input
only, never a decision, same §7bis.9d discipline as every other term here.
v6b Lot 3 adds this module's first `Citizen.chamber_position` reader:
`chamber_deviation` is dt=11's own comparable quantity to `mandate_deviation`,
for a citizen who never pledged anything. v6b's production-wiring lot adds
`unified_mandate_deviation`, the full-priority twin of `mandate_deviation`
on the same weighting basis `chamber_deviation` already uses -- reporting
only, journaled alongside the shipped top-k-scoped value, never read by
`écart(t)`, the awakening gate, or any `ctx`.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from api.domain.polity.citizen import Citizen, Office
from api.domain.polity.codebook import PressureAct
from api.domain.polity.config import (
    AwakeningConfig,
    EventsConfig,
    MandateConfig,
    PetitionConfig,
    StreetPressureConfig,
)
from api.domain.polity.social_graph import SocialGraph
from api.domain.polity.metrics import signed_ratio

_SUPPORTED_DEVIATION_METRICS = {"weighted_euclidean"}


def weighted_euclidean(a: Sequence[float], b: Sequence[float], weights: Sequence[float]) -> float:
    """sqrt(sum(w * (x-y)**2)) -- same math as simple_rules.weighted_distance,
    generalized to two arbitrary points instead of a citizen's own position.
    Not a refactor of that function this lot; test_polity_accountability.py
    pins the two implementations equal instead."""
    return math.sqrt(sum(w * (x - y) ** 2 for x, y, w in zip(a, b, weights)))


def current_office_holders(citizens: list[Citizen], office: Office) -> list[Citizen]:
    """Presidency returns 0-or-1 citizens today (Office.DEPUTY is never
    assigned) -- generalizes later without touching call sites."""
    return sorted((c for c in citizens if c.office is office), key=lambda c: c.citizen_id)


def current_sortition_members(citizens: list[Citizen]) -> list[Citizen]:
    """v6b Lot 3 (§6bis.3): the sortition-chamber analogue of
    current_office_holders -- a seated member is never an Office/Role
    concept (see sortition_chamber.py's own docstring), so this filters on
    sortition_seat_until_tick instead of office. Ascending citizen_id, same
    ordering convention as every cohort-builder in this module."""
    return sorted((c for c in citizens if c.sortition_seat_until_tick is not None), key=lambda c: c.citizen_id)


def chamber_deviation(member: Citizen) -> float:
    """v6b Lot 3 (§6bis.3): the sortition-chamber analogue of
    mandate_deviation -- a drawn citizen never campaigns, so there is no
    pledged_platform to diverge from; the comparable quantity is the
    member's own currently-stated chamber_position against their own
    sincere issue_positions, weighted by their own issue_priorities (same
    weighted_euclidean primitive mandate_deviation/self_gap already use).
    Raises if chamber_position is None (never seated), mirroring self_gap's
    own raise-on-missing-position guard."""
    if member.chamber_position is None:
        raise ValueError(f"citizen {member.citizen_id} has no chamber_position")
    return weighted_euclidean(member.issue_positions, member.chamber_position, member.issue_priorities)


def pledge_weights(priorities: Sequence[float], config: MandateConfig) -> tuple[float, ...]:
    """§7bis.5's pledge_scope. full_platform passes priorities through
    unchanged (already sums to 1, dirichlet-drawn). top_k_priorities keeps
    only the pledge_top_k highest-priority dimensions (ties broken by
    ascending dimension index for determinism) and RENORMALIZES the
    survivors to sum to 1 -- without this, pledge_scope would silently
    become a scale change (a top-5 subset of dirichlet weights sums to
    ~0.25-0.3) rather than a scope change, and deviation_log_threshold
    would mean two different things depending on scope.

    KNOWN METRIC DESIGN BUG (found 2026-08-22, v6b Lot 4's second acceptance
    run, shipped default pledge_scope=top_k_priorities): a dimension outside
    the officeholder's own top-k priority set gets weight exactly 0.0 here,
    which means mandate_deviation is STRUCTURALLY BLIND to drift on that
    dimension -- not merely under-weighted, invisible. Live-verified: a
    presided term drifted revealed_position on 3 dimensions from ~0.1-0.8 to
    the [0,1] clamp ceiling (raw unweighted distance ~1.0 across the
    platform), while mandate_deviation read exactly 0.0 for the entire term,
    because those 3 dimensions never fell in that officeholder's own top-5.
    This was never a bug in what top_k_priorities computes -- it is doing
    exactly what its own docstring says -- but nothing here ever warned a
    caller that "did they keep their stated top-priority promises" and "how
    much did their overall position move" are DIFFERENT questions, and that
    mandate_deviation only answers the first one. Comparing mandate_deviation
    against a full-priority-weighted quantity computed elsewhere (e.g.
    chamber_deviation, which weights by the FULL issue_priorities vector,
    never top-k) is therefore not apples-to-apples, and a caller that treats
    a flat mandate_deviation series as "no real drift happened" can be
    completely wrong. Not fixed here -- pledge_scope=top_k_priorities is
    still the shipped default and this function's own behavior is
    unchanged. Since the v6b production-wiring lot, the apples-to-apples
    comparator is journaled in band: unified_mandate_deviation is computed
    at the same call sites and written to the journal as "unified_deviation"
    on both representative_response and mandate_deviation_recorded, so a
    caller no longer has to recompute it by hand. See traceability.md's own
    polity row for the cross-reference."""
    if config.pledge_scope == "full_platform":
        return tuple(priorities)
    if config.pledge_scope != "top_k_priorities":
        raise NotImplementedError(f"mandate.pledge_scope {config.pledge_scope!r} not supported")

    k = min(config.pledge_top_k, len(priorities))
    top_k_dims = {
        dim
        for dim, _ in sorted(enumerate(priorities), key=lambda item: (-item[1], item[0]))[:k]
    }
    kept = [p if dim in top_k_dims else 0.0 for dim, p in enumerate(priorities)]
    total = sum(kept)
    if total <= 0.0:
        return tuple(kept)
    return tuple(p / total for p in kept)


def mandate_deviation(officeholder: Citizen, config: MandateConfig) -> float:
    """§7bis.5: distance(pledged_platform, revealed_position(t)), weighted by
    the officeholder's own issue_priorities per pledge_weights. Provably 0
    throughout Lots 2-5: nothing sets revealed_position independently from
    pledged_platform until Lot 6's representative_response exists.

    KNOWN METRIC DESIGN BUG under the shipped pledge_scope=top_k_priorities:
    can read exactly 0.0 even with large, real, saturating drift, if that
    drift lands entirely outside the officeholder's own top-5 priority
    dimensions -- see pledge_weights's own docstring for the live-verified
    case. unified_mandate_deviation (below) is the full-priority-weighted
    comparator, journaled alongside this value's own output since the v6b
    production-wiring lot -- no recomputation needed."""
    if config.deviation_metric not in _SUPPORTED_DEVIATION_METRICS:
        raise NotImplementedError(f"mandate.deviation_metric {config.deviation_metric!r} not supported")
    if officeholder.pledged_platform is None or officeholder.revealed_position is None:
        raise ValueError(f"citizen {officeholder.citizen_id} has no pledged_platform/revealed_position")
    weights = pledge_weights(officeholder.issue_priorities, config)
    return weighted_euclidean(officeholder.pledged_platform, officeholder.revealed_position, weights)


def unified_mandate_deviation(officeholder: Citizen) -> float:
    """mandate_deviation on the FULL, untruncated issue_priorities -- provably
    identical to mandate_deviation(officeholder, <config with
    pledge_scope="full_platform">), since pledge_weights returns
    tuple(priorities) unchanged on that branch (pinned by
    test_unified_mandate_deviation_equals_mandate_deviation_under_full_platform_scope).
    This is the SAME weighting basis chamber_deviation already uses -- the
    entire reason this function exists: the elected and sortition sides of
    §6bis.3's own comparison must be on one basis to be compared at all
    (v6b Lot 4, THEORY.md §10.9).

    Config-free for the same reason chamber_deviation is: there is nothing
    to configure, it IS the full-priority basis. Accepted cost: unlike
    mandate_deviation, this skips deviation_metric validation --
    _SUPPORTED_DEVIATION_METRICS has exactly one member today; if a second
    metric ever ships, both functions gain the parameter together.

    Measurement only. Never feeds écart(t), the awakening gate, or any ctx
    -- compose_ecart/select_consulted/_pressure_context/_response_context
    all keep reading mandate_deviation's own top-k-scoped value, unchanged.
    Journaled (v6b, production-wiring lot) as "unified_deviation" on
    representative_response and mandate_deviation_recorded, alongside the
    shipped top_k-scoped value -- never replacing it (see pledge_weights'
    own "KNOWN METRIC DESIGN BUG" docstring for why the two answer different
    questions)."""
    if officeholder.pledged_platform is None or officeholder.revealed_position is None:
        raise ValueError(f"citizen {officeholder.citizen_id} has no pledged_platform/revealed_position")
    return weighted_euclidean(officeholder.pledged_platform, officeholder.revealed_position, officeholder.issue_priorities)


def self_gap(citizen: Citizen, officeholder: Citizen) -> float:
    """A citizen's own perceived distance between what they want
    (issue_positions) and what they're currently getting (the officeholder's
    revealed_position), weighted by the citizen's OWN priorities -- a
    different axis from mandate_deviation (the officeholder's own promise vs
    delivery). Full platform only: top-k is a pledge-specific concept, not a
    citizen's personal-gap concept. Unused until Lot 4's awakening gate."""
    if officeholder.revealed_position is None:
        raise ValueError(f"citizen {officeholder.citizen_id} has no revealed_position")
    return weighted_euclidean(citizen.issue_positions, officeholder.revealed_position, citizen.issue_priorities)


def is_term_limited(citizen: Citizen, term_limit: int | None) -> bool:
    """§6bis.1: a hard, always-on candidacy block, independent of the LLM --
    `term_limit=None` (shipped default) means illimité, always False. Doubles
    as the `lame_duck` predicate for a sitting officeholder (Lot 6 ctx)."""
    return term_limit is not None and citizen.mandates_served >= term_limit


def ticks_to_election(tick: int, term_end_tick: int | None) -> int | None:
    """term_end_tick - tick, or None with no sitting officeholder. Two real
    consumers (v4 Lot 6): election_proximity (which delegates here) and
    dt=6's ResponseContext.ticks_left. No InstitutionalClock needed --
    term_end_tick is only ever assigned at a presidential election tick, to
    exactly tick_of_election + president_term_years*ticks_per_year, so it
    already IS the next scheduled presidential election; a recall (Lot 3)
    clears it via vacate_office, so a stale value is unreachable. Lot 4
    already proved the range is [1, president_term_ticks] for a sitting
    holder (the accountability phase runs after the election block, so 0 is
    unreachable) -- never 0, never negative, in the caller's own tests."""
    if term_end_tick is None:
        return None
    return term_end_tick - tick


def election_proximity(tick: int, term_end_tick: int | None, term_ticks: int) -> float:
    """v4 Lot 4 (§7bis.9c): 1 - ticks_to_election/term_ticks, clamped [0,1].
    0.0 with no sitting officeholder (term_end_tick is None)."""
    remaining = ticks_to_election(tick, term_end_tick)
    if remaining is None:
        return 0.0
    return max(0.0, min(1.0, 1.0 - remaining / term_ticks))


def awakening_threshold(
    citizen: Citizen,
    *,
    mandate_dev: float,
    proximity: float,
    neighbors_acting: float = 0.0,
    config: AwakeningConfig,
) -> float:
    """§7bis.9c: base_threshold * f(context), f bounded to [1-amp, 1+amp].
    Visible mandate deviation LOWERS the threshold (easier to trigger);
    proximity to the next election RAISES it (less reason to act outside
    the ballot). Each term is included only when its own
    context_modulation flag is true. event_salience (v5 Lot 3, §8) lowers
    the threshold, symmetric with mandate_deviation -- read directly off
    `citizen.event_salience`, no new parameter needed: unlike mandate_dev/
    proximity (officeholder-level facts with no natural per-citizen home,
    threaded in by the caller), event_salience already lives on the
    citizen this function is already given.

    neighbors_acting (v6 Lot 3, §5/§7bis.9c) LOWERS the threshold too --
    Granovetter-style threshold diffusion read as another continuous
    modulation of the same gate, never a hard rule (§3.3/§7bis.9d: the gate
    decides who is ASKED, never what they decide). Unlike mandate_dev/
    event_salience, this one genuinely has no natural per-citizen home --
    it depends on the TARGET (which officeholder) as well as the citizen,
    so the caller (accountability.neighbors_acting, computed once per
    holder over the whole population) threads it in exactly like
    mandate_dev/proximity. Defaults to 0.0 so every pre-v6-Lot-3 caller
    keeps compiling and behaving identically."""
    amp = config.modulation_amplitude
    f = 1.0
    if config.context_modulation.mandate_deviation:
        f -= amp * mandate_dev
    if config.context_modulation.ticks_to_election:
        f += amp * proximity
    if config.context_modulation.event_salience:
        f -= amp * citizen.event_salience
    if config.context_modulation.neighbors_acting:
        f -= amp * neighbors_acting
    f = max(1.0 - amp, min(1.0 + amp, f))
    return citizen.base_threshold * f


def neighbors_acting(
    citizens: Sequence[Citizen],
    target: int,
    graph: SocialGraph,
    mobilized_last_tick: Mapping[int, int],
) -> dict[int, float]:
    """§5/§7bis.9c (v6 Lot 3): for every citizen, the fraction of their OWN
    social-graph neighbors whose most recently APPLIED pressure_action was
    MOBILIZE, specifically against `target` -- the same officeholder this
    citizen is currently being asked about, not "against anyone" (§7bis.4a's
    petition lever is the institutional, consequential channel; §7bis.4b's
    mobilization is the expressive, visibility-only one the design doc's own
    "déjà mobilisée" wording names specifically -- sign/launch don't count).

    One tick of lag by construction: `mobilized_last_tick` is built by the
    CALLER from the PREVIOUS tick's own applied acts (decide_pressure_actions
    batches an entire cohort's decisions in one frozen call, so a neighbor's
    SAME-tick decision cannot be seen yet) -- the same structural lag
    dt=6's own street_pressure reading uses (v4 Lot 6).

    An isolated citizen (graph.neighbors[cid] == frozenset()) gets 0.0,
    never a divide-by-zero or None -- a real, documented SocialGraph state
    (social_graph.py's own docstring), a legitimate "no visible pressure"
    fact. Computed for EVERY citizen, not just an already-consulted cohort,
    because select_consulted itself needs each candidate's own fraction
    before it knows who will be consulted."""
    result: dict[int, float] = {}
    for citizen in citizens:
        cid = citizen.citizen_id
        neighbor_ids = graph.neighbors.get(cid, frozenset())
        if not neighbor_ids:
            result[cid] = 0.0
            continue
        acting = sum(1 for neighbor_id in neighbor_ids if mobilized_last_tick.get(neighbor_id) == target)
        result[cid] = acting / len(neighbor_ids)
    return result


def select_consulted(
    citizens: list[Citizen],
    holder: Citizen,
    *,
    tick: int,
    term_ticks: int,
    mandate_dev: float,
    awakening: AwakeningConfig,
    neighbors_acting: Mapping[int, float] | None = None,
) -> list[tuple[Citizen, float]]:
    """§7bis.9d: the awakening gate -- a sampling GATE, never a decision. A
    citizen is consulted iff self_gap > their own awakening_threshold
    (strict, per the roadmap's own resolution). Excludes `holder`
    unconditionally (not relying on self_gap(holder, holder) happening to
    be 0 -- campaign_positioning's LLM path can diverge a nominee's
    revealed_position before they win, giving a president a nonzero
    self-gap against their own current revealed position). No RNG, no cap
    (no_consultation_cap is TRANCHÉ true), ascending citizen_id.

    `neighbors_acting` (v6 Lot 3) is the per-citizen fraction the module-
    level function of the same name already computed once for this holder
    -- None (the default) behaves exactly like "no social graph", 0.0 for
    every citizen, preserving every pre-v6-Lot-3 call site unmodified."""
    if holder.revealed_position is None:
        return []
    proximity = election_proximity(tick, holder.term_end_tick, term_ticks)
    consulted = []
    for citizen in citizens:
        if citizen.citizen_id == holder.citizen_id:
            continue
        gap = self_gap(citizen, holder)
        frac = neighbors_acting.get(citizen.citizen_id, 0.0) if neighbors_acting else 0.0
        threshold = awakening_threshold(
            citizen, mandate_dev=mandate_dev, proximity=proximity, neighbors_acting=frac, config=awakening
        )
        if gap > threshold:
            consulted.append((citizen, gap))
    return sorted(consulted, key=lambda pair: pair[0].citizen_id)


def update_street_pressure(previous: float, rate: float, config: StreetPressureConfig) -> float:
    """§7bis.4b: decay_rue * street_pressure(t-1) + mobilization_rate(t).
    Deliberately unclamped -- update_legitimacy already owns the [0,1]
    clamp on L itself; double-guarding the same invariant here would be
    redundant. Its realized steady-state max exceeds 1.0 under the shipped
    distribution (see scripts/awakening_calibration_results.md)."""
    return config.decay * previous + rate


def update_event_salience(previous: float, delta: float, config: EventsConfig) -> float:
    """v5 Lot 3 (§8): salience_decay * event_salience(t-1) + delta -- exact
    same shape as update_street_pressure. Deliberately unclamped: the clamp
    that matters lives on awakening_threshold's own f(context), not here
    (same reasoning as street_pressure/shock.py's x(t))."""
    return config.salience_decay * previous + delta


# ── v4 Lot 5: petition state machine (§7bis.4a) ─────────────────────────
#
# At most one open petition per target (petition.concurrent_allowed is
# TRANCHÉ false), so the three officeholder-scoped Citizen fields
# (petition_open_since_tick/petition_signers/petition_cooldown_until_tick)
# express the whole state. Every mutator below rebinds those fields on
# `holder` rather than mutating in place -- frozenset has no in-place
# mutator anyway, and the rebind keeps every write here symmetric with how
# street_pressure/legitimacy_capital are already updated at the one call
# site in run_polity_simulation.py.


def petition_pressure(holder: Citizen, population_size: int) -> float:
    """§7bis.6's petition_pressure(t) == §7bis.4a's signed_ratio(t): 0.0
    with no open petition, else signatures / population_size. This is
    écart(t)'s first term, computed fresh at step 4 (and again, unchanged,
    at step 5's threshold check -- signatures only change at step 2)."""
    if holder.petition_open_since_tick is None:
        return 0.0
    return signed_ratio(len(holder.petition_signers), population_size)


def petition_accepts_signatures(holder: Citizen, tick: int, config: PetitionConfig) -> bool:
    """Open AND still inside its petition_lifespan_ticks window, counting
    the launch tick itself as the first collecting tick -- a petition
    launched at t0 is signable at t0 .. t0+lifespan-1."""
    if holder.petition_open_since_tick is None:
        return False
    return tick - holder.petition_open_since_tick < config.petition_lifespan_ticks


def petition_has_expired(holder: Citizen, tick: int, config: PetitionConfig) -> bool:
    """The complement of petition_accepts_signatures once a petition
    exists: open AND its window has elapsed. Step 5 checks the threshold
    before this, so an expiry is only ever recorded for a petition that
    never crossed signature_threshold in its whole window."""
    if holder.petition_open_since_tick is None:
        return False
    return tick - holder.petition_open_since_tick >= config.petition_lifespan_ticks


def petition_is_launchable(holder: Citizen, tick: int) -> bool:
    """No open petition AND not inside a post-resolution cooldown (strict
    `<`, so the blackout is exactly cooldown_ticks ticks long). An active
    cooldown and an open petition never coexist (resolve_petition only
    ever sets the cooldown at the same moment it clears the petition), so
    this reduces to just the cooldown check whenever a petition IS open."""
    if holder.petition_open_since_tick is not None:
        return False
    return holder.petition_cooldown_until_tick is None or tick >= holder.petition_cooldown_until_tick


def launch_petition(holder: Citizen, launcher: Citizen, tick: int) -> None:
    """§7bis.4a act=2: opens a petition against `holder`, effective this
    tick. The launcher's own dissatisfaction seeds the signature set --
    a petition born at signed_ratio 0.0 despite having just been
    deliberately created would make its own launcher's motive invisible
    to signed_ratio, and it makes act=1 structurally unavailable to the
    launcher afterwards (they are already a signer)."""
    holder.petition_open_since_tick = tick
    holder.petition_signers = frozenset({launcher.citizen_id})


def sign_petition(holder: Citizen, signer: Citizen) -> None:
    """§7bis.4a act=1: idempotent by construction -- signing twice adds
    the same id to the set a second time, a no-op."""
    holder.petition_signers = holder.petition_signers | {signer.citizen_id}


def resolve_petition(holder: Citizen, tick: int, config: PetitionConfig) -> None:
    """Clears the open petition and its signatures, and opens the
    cooldown -- called by BOTH terminal branches (signature_threshold
    crossed -> confidence vote, or lifespan expired). The design doc
    attaches cooldown_ticks only to the successful branch; extending it to
    expiry too is a documented extension (v4 Lot 5), not a literal
    reading -- without it the same cohort relaunches an identical petition
    the tick after expiry, forever, making petition_lifespan_ticks a
    no-op and petition_expired a meaningless metric. Read as a rate limit
    on petitions against a target, not a reward for succeeding."""
    holder.petition_open_since_tick = None
    holder.petition_signers = frozenset()
    holder.petition_cooldown_until_tick = tick + config.cooldown_ticks


def reset_petition_state(holder: Citizen) -> None:
    """Election-time reset (called from _hold_presidential_election,
    gated on config.petition.enabled), unlike resolve_petition also
    CLEARS the cooldown -- a new mandate is a clean slate, including for
    an incumbent recalled by a confidence vote in a previous term. Same
    officeholder-scoped-field pattern as legitimacy_capital/
    mandate_strength/street_pressure (Lots 3-4): a re-elected incumbent
    must not inherit a previous term's open petition, signatures, or
    cooldown, since those were cast against a mandate that no longer
    exists. A DEFEATED incumbent's stale petition state is deliberately
    NOT cleared here (Lot 3's precedent: current_office_holders filters by
    office, so nothing reads it again; post-mortem journal legibility is a
    feature, not an oversight)."""
    holder.petition_open_since_tick = None
    holder.petition_signers = frozenset()
    holder.petition_cooldown_until_tick = None


def applicable_pressure_act(act: PressureAct, *, can_sign: bool, can_launch: bool) -> PressureAct:
    """v4 Lot 7. Reconciles a DECIDED act (frozen pre-loop, from the LLM)
    with LIVE petition state at the moment it is applied. Within one tick,
    `tick` is constant, so the only reachable divergence is: a petition
    was opened earlier in THIS tick's own consulted loop, so a later
    citizen's LAUNCH is no longer possible (petition.concurrent_allowed is
    TRANCHÉ false) but a SIGN now is. LAUNCH -> SIGN is exactly what
    deterministic_pressure_action returns from the same live facts
    (simple_rules.py), preserves the citizen's chosen LEVER, and keeps
    signed_ratio an honest count. Never converts a petition act into
    MOBILIZE or WAIT_FOR_ELECTION -- that would be the orchestrator
    choosing a DIFFERENT lever on the citizen's behalf, the behavioral
    prescription §3.3 refuses. 0/3/4 are always honored: they have no
    institutional object to go stale against. The caller's JOURNAL records
    the decided act (what the model chose); the adjacent petition event
    (or its absence) records the effect (what actually happened) -- this
    function only computes the latter, never journals anything itself."""
    if act in (PressureAct.SIGN_PETITION, PressureAct.LAUNCH_PETITION):
        if can_sign:
            return PressureAct.SIGN_PETITION
        if can_launch:
            return PressureAct.LAUNCH_PETITION
        return PressureAct.NOTHING
    return act
