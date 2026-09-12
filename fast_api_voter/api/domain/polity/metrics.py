"""
api.domain.polity.metrics — the v0 subset of output metrics (Lot 9, design
doc §10), three v4 (Lots 4-5) ratio helpers, and eight more v4 (Lot 8) rows
now that indexer.py exists and is their caller.

Effective number of parties, cohabitation rate, coalition lifespans are
computable without an LLM or legitimacy (both off in v0). mobilization_rate/
consultation_rate/signed_ratio were added ad hoc in Lots 4/5 because both
run_polity_simulation.py (real-time, per tick) and the calibration scripts
(post-hoc, from a journal) needed the exact same ratios.

Pure functions over caller-assembled observations, not journal readers:
indexer.py replays the raw journal into the shapes these functions take —
this module contains no journal-reading and no event-type knowledge, per
its own contract (quoted in indexer.py's module docstring).

Zero-denominator convention: 0.0 where zero is a meaningful reading (an
empty cohort has an inaction rate of 0, a tick with no cast petition
signature-events has nobody to divide by so the caller simply doesn't call
this for that tick), None where the quantity is genuinely UNDEFINED (no
petition was ever launched; no lame-duck term ever existed) -- see
indexer.py's own "a metric whose flag is off is None, never 0.0" rule,
extended here to "a metric with an empty denominator that isn't a legitimate
zero is also None".
"""
from __future__ import annotations

from typing import Sequence


def effective_number_of_parties(seats: dict[int, int]) -> float:
    """Laakso & Taagepera (1979): N = 1 / sum(share_i^2) over seat shares.
    2 parties at 50/50 seats -> N = 2.0 (the dev-plan's own worked example)."""
    total = sum(seats.values())
    if total == 0:
        return 0.0
    return 1.0 / sum((s / total) ** 2 for s in seats.values())


def is_cohabitation(president_party_id: int | None, coalition: list[int] | None) -> bool:
    """design doc §6: cohabitation is a president whose own party is not
    part of the governing coalition. Neither a vacant presidency nor a
    failed coalition (coalition_failed, §4 point 3) counts as cohabitation
    — there is no government to be at odds with the president."""
    if president_party_id is None or coalition is None:
        return False
    return president_party_id not in coalition


def cohabitation_rate(observations: list[bool]) -> float:
    """Fraction of observed periods (design doc §10: cumulative) under
    cohabitation. Each observation should weight equal time (e.g. one tick,
    or one inter-election period of fixed length) — this function does not
    itself weight by duration."""
    if not observations:
        return 0.0
    return sum(observations) / len(observations)


def coalition_lifespans(events: list[tuple[int, list[int] | None]], total_ticks: int) -> list[int]:
    """`events`: chronological (tick, coalition) pairs, one per legislative
    election, coalition None for a coalition_failed outcome. Returns the
    duration in ticks of each coalition that actually formed — until the
    next legislative election, or until the end of the run for the last
    one. A coalition_failed event produces no lifespan entry."""
    lifespans = []
    for i, (tick, coalition) in enumerate(events):
        if coalition is None:
            continue
        next_tick = events[i + 1][0] if i + 1 < len(events) else total_ticks
        lifespans.append(next_tick - tick)
    return lifespans


def mobilization_rate(participants: int, population_size: int) -> float:
    """§7bis.4b: participants(t) / population_size -- the count of act=3
    (MOBILIZE) decisions this tick, over the full population, not just the
    consulted cohort (mobilization_rate is capped by the consultation rate,
    it is not measured against it)."""
    if population_size == 0:
        return 0.0
    return participants / population_size


def consultation_rate(consulted: int, population_size: int) -> float:
    """§7bis.9c: fraction of the population past the awakening gate this
    tick -- the calibration gate's headline number."""
    if population_size == 0:
        return 0.0
    return consulted / population_size


def signed_ratio(signatures: int, population_size: int) -> float:
    """§7bis.4a: signed_ratio(t) = signatures cumulées / population_size --
    the petition analogue of mobilization_rate, same zero-population guard.
    Two real consumers: run_polity_simulation.py in real time (via
    accountability.petition_pressure) and scripts/calibrate_petition.py
    post-hoc from journal counts (v4 Lot 5)."""
    if population_size == 0:
        return 0.0
    return signatures / population_size


# ── v4 Lot 8: the six §10 rows indexer.py newly gates, plus mean_legitimacy
# and recall_frequency (§10 rows with no dedicated [v4] metrics flag of
# their own -- they're implied by legitimacy_updated/recalled existing) ──

def mean_legitimacy(values: Sequence[float]) -> float:
    """§10's "trajectoire de légitimité moyenne", one tick's worth. Callers
    (indexer.py) never pass an empty sequence -- a tick with no
    legitimacy_updated event is a vacant tick and is simply absent from the
    series, never a 0.0 reading (0.0 is a claim: "legitimacy is at rock
    bottom", which is false for a tick with no officeholder at all)."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def office_occupancy(presided_ticks: int, total_ticks: int) -> float:
    """Track A5 (2026-09-11, lets-build-a-solid-spicy-otter.md): fraction of
    the run's own ticks with a sitting president. Promoted from an ad-hoc,
    LLM-path-only computation in scripts/run_v6b_acceptance.py (which could
    only read it off mandate_deviation's own "ctx" series, so it was null
    on every deterministic-engine run) to a real metric derived from
    `terms` directly -- Track 0b's own finding is exactly why this needed
    to work on both engines: a deterministic-engine control run showed
    WORSE occupancy (0.273) than its LLM twin (0.515) on the same seed, and
    the ad-hoc formula could not have measured the deterministic side at
    all.

    `total_ticks + 1` is the denominator, not `total_ticks`: the tick loop
    is inclusive of `total_ticks` (`range(0, total_ticks + 1)`), so a run
    configured for `total_ticks` actually executes `total_ticks + 1`
    distinct ticks (0 through total_ticks) -- the same convention
    run_v6b_acceptance.py's own formula already used. `presided_ticks` is
    the caller's job (indexer.py sums `term.end_tick - term.start_tick`
    across `segment_terms`'s own output, the same quantity mandate_
    deviation_coverage's "recorded" branch already computes as
    `presided_estimate` -- reused, not reinvented).

    KNOWN, ACCEPTED IMPRECISION at one boundary: `segment_terms` closes a
    still-open term at the run's own end with `end_tick=total_ticks`
    (exclusive, the SAME convention every other term uses), so a president
    who holds office for the entire run without ever being recalled reports
    `total_ticks / (total_ticks + 1)`, not a clean 1.0 -- the accountability
    phase genuinely runs for tick `total_ticks` too, and this formula does
    not count it. Not fixed here: `segment_terms`'s own exclusive-end
    convention is shared by every metric and by run_digest.py, and correcting
    one caller's boundary without touching the function every other reader
    depends on would make this metric agree with none of them. The error is
    always exactly one tick, always in the same direction (undercount, never
    over), and vanishes at any real total_ticks scale that matters here."""
    if total_ticks < 0:
        raise ValueError("office_occupancy requires total_ticks >= 0")
    return presided_ticks / (total_ticks + 1)


def recall_frequency(recalls: int, terms: int) -> float:
    """§10's "fréquence de rappel": recalls ÷ terms observed (a term that
    ends by a scheduled election, not a recall, still counts in the
    denominator -- the base rate is over terms, not over recalls alone)."""
    if terms == 0:
        return 0.0
    return recalls / terms


def inaction_rate(inactive: int, consulted: int) -> float:
    """§7bis.3 / §10's "taux d'inaction des mécontents": #{act == 0} ÷
    #{pressure_action events} for one tick. §7bis.3 calls this "probablement
    le résultat le plus intéressant du modèle" -- it is meaningless against
    a deterministic baseline where inaction is a bare threshold, and only
    becomes a measurement once a model chooses it (v4 Lot 7's own framing)."""
    if consulted == 0:
        return 0.0
    return inactive / consulted


def pressure_lever_mix(acts: Sequence[int]) -> dict[int, float]:
    """§7bis.3 / §10's "répartition des leviers actionnés": normalized share
    of each PressureAct (0..4) among decided (not applied) acts -- v4 Lot 7's
    own distinction between what a citizen chose and what actually happened
    once applicable_pressure_act resolved it against live petition state.
    Every one of the five keys is always present, 0.0 for an act that never
    occurred this period, so a caller never has to guard a missing key."""
    mix = {act: 0.0 for act in range(5)}
    if not acts:
        return mix
    total = len(acts)
    for act in acts:
        mix[act] += 1.0
    return {act: count / total for act, count in mix.items()}


def petition_success_rate(triggered: int, launched: int) -> float | None:
    """§7bis.4a / §10's "taux de pétition aboutie": confidence_vote_triggered
    ÷ petition_launched -- a petition "aboutit" once it reaches its
    signature threshold and forces a confidence vote, per §7bis.4a's own
    framing ("une pétition qui n'atteint pas son seuil ... expire -- et cet
    échec est lui-même une donnée"). Deliberately NOT the removal rate (see
    indexer.py's own petition_removal_rate, a distinct second number).
    `None`, not 0.0, when no petition was ever launched -- the rate is
    undefined, not zero, with nothing to have succeeded or failed."""
    if launched == 0:
        return None
    return triggered / launched


def stance_distribution(stances: Sequence[int]) -> dict[int, float]:
    """§3.6.5 / §10's "distribution des stance": normalized share of each
    Stance (1..4) among representative_response decisions. All four keys
    always present, 0.0 for a stance that never occurred this period."""
    dist = {stance: 0.0 for stance in range(1, 5)}
    if not stances:
        return dist
    total = len(stances)
    for stance in stances:
        dist[stance] += 1.0
    return {stance: count / total for stance, count in dist.items()}


def lame_duck_deviation_delta(lame_duck: Sequence[float], eligible: Sequence[float]) -> float | None:
    """§6bis.1 / §10's "lame_duck_deviation_delta": mean(deviation over
    lame-duck terms) − mean(deviation over re-eligible terms). `None`, not
    0.0, whenever either side has no observed term -- at the shipped
    president_term_limit: null every term is re-eligible, so this is `None`
    for the shipped acceptance configs by construction, not a bug."""
    if not lame_duck or not eligible:
        return None
    return (sum(lame_duck) / len(lame_duck)) - (sum(eligible) / len(eligible))


def blank_vote_rate(blank_count: int, ballots: int) -> float:
    """§10's "taux de vote blanc": blank ballots ÷ ballots cast, at one
    election."""
    if ballots == 0:
        return 0.0
    return blank_count / ballots
