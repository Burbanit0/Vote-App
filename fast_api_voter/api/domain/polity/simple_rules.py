"""
api.domain.polity.simple_rules — the v0/v1 deterministic decision baseline
(Lot 6, resolves audit blocker A5; rupture path added for v1).

Three rules, each isolated and independently testable, matching
DEMARRAGE-polity-v0.md §2 and audit-precision-plan.md A5:

1. Vote: nearest candidate by issue-priority-weighted distance; blank if
   even the nearest candidate is farther than the voter's own tolerance.
2. Candidacy: `decide_candidacy` is design doc §2.4's dominant path
   (ambition-score threshold), used to filter party nominees. The rare
   "candidature de rupture" path (§2.4) is a separate function,
   `attempt_rupture_candidacy` — independent of perceived support by
   design, so it does not reuse `decide_candidacy` at all.
3. Coalition: nearest-ideological-neighbour aggregation until a majority of
   seats is reached, with every tiebreak explicit (DEMARRAGE §4) — a bare
   max()/min() on insertion order would make the byte-for-byte
   reproducibility test (Lot 8) depend on an implementation accident.
4. Pressure action (v4 Lot 4/5): `deterministic_pressure_action` is dt=10's
   §11.4 baseline, this module's first codebook.py consumer -- a simple,
   mechanical rule (like every rule above), not an attempt at realism;
   Lot 7's LLM is what replaces it behind config.llm.enabled. `v4 Lot 5`
   adds `build_confidence_ballot`, the deterministic per-citizen rule
   behind the binary confidence vote (§7bis.4a) -- deliberately NOT
   replaced by the LLM even when config.llm.enabled is true (§7bis.4a
   keeps it inside ballot_and_aggregation.py as bf=4 on vote_cast, never
   its own decision type; the roadmap's own top-level resolution).

This module is deliberately what llm_behavior_engine.py replaces in v2 — it
also stays on afterwards as the baseline against which the LLM's effect is
measured (§11.1 of the design doc): in v0/v1, mandate deviation is zero by
construction, since a candidate's revealed_position never diverges from
their pledged_platform.
"""
from __future__ import annotations

import math

import numpy as np

from api.domain.polity.citizen import Citizen, Office, Role
from api.domain.polity.codebook import EventType, PressureAct
from api.domain.polity.config import CandidacyConfig, EventsConfig, PressureMenuConfig
from api.domain.polity.parties import Party

CANDIDATE_LABEL_PREFIX = "citizen_"
BLANK_LABEL = "Blank"


def candidate_label(citizen: Citizen) -> str:
    return f"{CANDIDATE_LABEL_PREFIX}{citizen.citizen_id}"


def citizen_id_from_label(label: str) -> int:
    return int(label[len(CANDIDATE_LABEL_PREFIX):])


# ── 1. Vote rule ──────────────────────────────────────────────────────────

def weighted_distance(voter: Citizen, platform: tuple[float, ...]) -> float:
    """Euclidean distance weighted by the voter's own issue_priorities —
    positions live in [0, 1] per dimension and priorities sum to 1, so the
    result stays in [0, 1], comparable to blank_threshold.

    Public since v4 Lot 8, not just an internal build_ranking helper
    anymore: cast_votes's own prompt builder (llm_behavior_engine.py)
    precomputes this same per-voter-per-candidate distance and hands it to
    the model, rather than asking the LLM to derive it from 20-dimensional
    raw position/priority vectors -- a live acceptance run found the model
    could not reliably do that arithmetic itself and collapsed to voting
    blank for essentially the whole electorate. Importing this function
    directly (instead of a second implementation) is what makes the LLM
    path's notion of "acceptable" provably identical to the deterministic
    path's."""
    return math.sqrt(
        sum(
            weight * (voter_x - platform_x) ** 2
            for voter_x, platform_x, weight in zip(
                voter.issue_positions, platform, voter.issue_priorities
            )
        )
    )


def _candidate_platform(candidate: Citizen) -> tuple[float, ...]:
    if candidate.pledged_platform is None:
        raise ValueError(f"citizen {candidate.citizen_id} has not declared a candidacy")
    return candidate.pledged_platform


def build_ranking(
    voter: Citizen, candidates: list[Citizen], blank_label: str = BLANK_LABEL
) -> list[str]:
    """A sincere ranking for `voter` over `candidates`, blank spliced in.

    Mirrors simulation_metrics._insert_blank, with distance standing in for
    utility (lower is better instead of higher): candidates within the
    voter's blank_threshold are ranked above blank in ascending-distance
    order, candidates beyond it below. Ties in distance are broken by the
    lowest citizen_id — an explicit, deterministic tiebreak, never
    insertion order.
    """
    ranked = sorted(
        candidates,
        key=lambda c: (weighted_distance(voter, _candidate_platform(c)), c.citizen_id),
    )
    names = [candidate_label(c) for c in ranked]
    within_tolerance = sum(
        1 for c in ranked if weighted_distance(voter, _candidate_platform(c)) <= voter.blank_threshold
    )
    return names[:within_tolerance] + [blank_label] + names[within_tolerance:]


def ballot_ranks_above_blank(ballot: list[str], label: str, blank_label: str = BLANK_LABEL) -> bool:
    """v4 Lot 3 (§7.1's mandate_strength source): is `label` ranked above
    blank on this one ballot? Format-agnostic across both ballot builders:
    build_ranking always contains every candidate (a total partition around
    blank_label), so `label` is always present for the deterministic path.
    llm_behavior_engine.ballot_from_decision diverges -- an explicit blank
    vote collapses to [blank_label] alone, and a non-blank vote's ranking is
    truncated to the top 5 for fields >6 candidates, so `label` can be
    absent from a non-blank LLM ballot too. Absence is read as "not above
    blank" (never as "exclude this ballot") -- the only reading consistent
    with mandate_strength being a fraction of *cast* ballots, at the cost of
    a real, one-directional downward bias on the LLM path once a field
    exceeds 6 candidates (never triggered by the 5 shipped parties alone).

    Both builders guarantee blank_label is present; its absence is a
    contract violation, not a possible input, so it raises with a clear
    message rather than surfacing list.index's bare ValueError."""
    if blank_label not in ballot:
        raise ValueError(f"ballot {ballot!r} does not contain blank_label {blank_label!r}")
    if label not in ballot:
        return False
    return ballot.index(label) < ballot.index(blank_label)


def blank_share(ballots: list[list[str]], blank_label: str = BLANK_LABEL) -> float:
    """v4 Lot 9 (§6bis.2): blank_share(t), the fraction of cast ballots whose
    TOP preference is blank -- ballot[0] == blank_label. Uniform across both
    ballot builders: build_ranking splices blank_label first iff zero
    candidates clear the voter's own blank_threshold; ballot_from_decision's
    blank=1 collapses the ballot to [blank_label] alone, trivially first.
    Unlike ballot_ranks_above_blank, no LLM-truncation caveat applies here --
    that one is about a specific candidate's position, not blank's, and
    blank_label is always present by both builders' own contract.

    "Suffrages exprimés" reads as every cast ballot: this simulation has no
    abstention mechanic, every citizen votes in every election. Scoped to
    list[list[str]] only -- run_simulation's own opening guard already makes
    every score-format ballot (simple_score/star/median/majority_judgment)
    unreachable, so no dict-ballot branch exists here.

    Raises on an empty ballots list (no meaningful share over zero cast
    ballots, mirroring ballot_and_aggregation.confidence_keep_ratio) and on
    any ballot missing blank_label (a contract violation, mirroring
    ballot_ranks_above_blank's own guard)."""
    if not ballots:
        raise ValueError("blank_share: no ballots cast")
    for ballot in ballots:
        if blank_label not in ballot:
            raise ValueError(f"ballot {ballot!r} does not contain blank_label {blank_label!r}")
    return sum(1 for ballot in ballots if ballot[0] == blank_label) / len(ballots)


# ── Party affiliation (the natural complement to Lot 3's k-means platforms:
#    a citizen's initial party is whichever platform sits closest to them) ──

def assign_party_affiliation(citizen: Citizen, parties: list[Party]) -> int:
    return min(
        parties, key=lambda p: (math.dist(citizen.issue_positions, p.platform), p.party_id)
    ).party_id


def choose_party(voter: Citizen, parties: list[Party]) -> int | None:
    """Party-list analogue of build_ranking's vote rule (A5), for the
    legislative election (assembly_mode: party_list): nearest party
    platform by issue-priority-weighted distance, or blank (None) if even
    the nearest party is farther than the voter's own tolerance. Ties
    broken by the lowest party_id."""
    nearest = min(
        parties, key=lambda p: (weighted_distance(voter, p.platform), p.party_id)
    )
    if weighted_distance(voter, nearest.platform) > voter.blank_threshold:
        return None
    return nearest.party_id


# ── 2. Candidacy rule ─────────────────────────────────────────────────────

def decide_candidacy(citizen: Citizen, config: CandidacyConfig) -> bool:
    """Design doc §2.4 dominant path: ambition_score crosses a fixed
    threshold. The rare rupture path (attempt_rupture_candidacy, below) is
    entirely separate — it is independent of perceived support by design,
    so it never calls this function."""
    return citizen.ambition_score >= config.ambition_threshold


def sympathizer_ratio(citizen: Citizen, population: list[Citizen]) -> float:
    """Proxy for "parrainages simulés" (§2.3): the fraction of the
    population who would sincerely consider `citizen` an acceptable choice
    (within their own blank_threshold), reusing the same tolerance concept
    already used for voting rather than inventing a new one. No social graph
    to ground "simulated signatures"/"perceived support" more directly.

    Public (not module-private) since v2 increment 2: also the "perceived
    support" input signal llm_behavior_engine.decide_candidacies gives the
    LLM for the dominant candidacy path, alongside its existing use as the
    rupture path's signature-ratio gate below."""
    sympathizers = sum(
        1 for other in population
        if weighted_distance(other, citizen.issue_positions) <= other.blank_threshold
    )
    return sympathizers / len(population)


def ballot_access_signature_ratio(citizen: Citizen, population: list[Citizen]) -> float:
    """ADR-003's fix: §2.3's ballot-access threshold ("parrainages simulés"),
    for the rupture path's signature bar (rupture_signature_ratio) below —
    deliberately NOT sympathizer_ratio, which this excludes `citizen`
    themself from the count and that one does not.

    sympathizer_ratio is the right function for its own two call sites
    (llm_behavior_engine's "perceived support" signal): a citizen's own
    trivial self-agreement is a defensible part of "how the population would
    receive you" as an LLM input signal, and changing that function would
    perturb every LLM run's byte-identical journal, past and future, for a
    concern this ADR was never about.

    A signature one gives oneself is not a signature. Before this fix,
    sympathizer_ratio floored at 1/population_size (every citizen counts
    themselves), which made the bar structurally unreachable at
    population_size <= 200 and silently live above it (ADR-003). Excluding
    self removes that floor at every population size — 0 external
    sympathizers gives 0.0, not 1/n — rather than merely raising the
    population size at which the floor stops mattering."""
    signatures = sum(
        1 for other in population
        if other.citizen_id != citizen.citizen_id
        and weighted_distance(other, citizen.issue_positions) <= other.blank_threshold
    )
    return signatures / len(population)


def attempt_rupture_candidacy(
    citizen: Citizen,
    population: list[Citizen],
    parties: list[Party],
    config: CandidacyConfig,
    rng: np.random.Generator,
) -> bool:
    """Design doc §2.4 rare path: a citizen may declare independently of
    perceived support, gated by a per-tick draw against a probability that
    scales with the citizen's own ideological disagreement, plus a reduced
    signature bar (rupture_signature_ratio) — never by ambition_score or by
    decide_candidacy. The RNG is always drawn from when the path is
    enabled (win or lose the coin flip) so draw order — and therefore
    reproducibility — never depends on the outcome.

    Resolves Points ouverts #1 ("quelle fonction de l'écart idéologique") --
    see plan-rupture-candidacy-threshold.md: "écart" is weighted_distance
    to the citizen's OWN affiliated party's platform (already in [0, 1] by
    construction), not to an incumbent (would break this path's per-tick
    temporal symmetry) or to the population centroid (measures absolute
    extremity, not disaffection with the party system). party_affiliation
    is always a concrete party_id here (assign_party_affiliation, called
    once at population init, never returns None -- unlike choose_party,
    a different function for legislative vote choice) so there is no None
    case to handle. The distance modulates rupture_base_probability only,
    never rupture_signature_ratio -- that bar is ADR-003's generic,
    already-calibrated ballot-access filter, a distinct §2.3 concern from
    this §2.4 probability. At distance 0 (perfectly represented by one's
    own party) the multiplier is exactly 1.0, so a fully-aligned citizen's
    probability is byte-identical to pre-this-change v1 behavior."""
    if not config.rupture_path_enabled:
        return False
    affiliated_platform = next(p.platform for p in parties if p.party_id == citizen.party_affiliation)
    disagreement = weighted_distance(citizen, affiliated_platform)
    probability = config.rupture_base_probability * (1 + config.rupture_distance_multiplier * disagreement)
    if rng.random() >= probability:
        return False
    return ballot_access_signature_ratio(citizen, population) >= config.rupture_signature_ratio


def select_party_nominee(
    party_id: int, citizens: list[Citizen], config: CandidacyConfig
) -> Citizen | None:
    """Design doc §2.3: a party nominates exactly one candidate among its
    ambitious members. v0 has no LLM to arbitrate (§3.6.3 is v2+), so the
    nominee is the eligible citizen with the highest ambition_score, ties
    broken by the lowest citizen_id. Returns None if no member of this
    party clears the candidacy threshold this cycle."""
    eligible = [
        c for c in citizens if c.party_affiliation == party_id and decide_candidacy(c, config)
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda c: (c.ambition_score, -c.citizen_id))


def select_party_nominee_from_declared(
    party_id: int, citizens: list[Citizen], declared_cids: set[int]
) -> Citizen | None:
    """v2 increment 2's LLM-path counterpart to select_party_nominee: same
    filter shape (party match) and same tiebreak (highest ambition_score,
    lowest citizen_id), but eligibility comes from decide_candidacies'
    outcome=1 set instead of decide_candidacy's bare threshold —
    party_nomination_choice itself (design doc dt=4, arbitrating among
    several eligible members) stays this increment's deterministic tiebreak,
    out of scope for the LLM. select_party_nominee/decide_candidacy stay
    untouched, still the baseline for §11.4's comparison."""
    eligible = [c for c in citizens if c.party_affiliation == party_id and c.citizen_id in declared_cids]
    if not eligible:
        return None
    return max(eligible, key=lambda c: (c.ambition_score, -c.citizen_id))


def vacate_office(citizen: Citizen) -> None:
    """v4 Lot 2: extracted from _hold_presidential_election's inline reset
    (PR #130) -- needed at three call sites once Lot 3 (floor recall) and
    Lot 5 (lost confidence vote) exist, and three divergent copies is
    exactly how PR #130's bug came back the first time."""
    citizen.role = Role.ELECTOR
    citizen.office = Office.NONE
    citizen.term_end_tick = None


def declare_candidacy(citizen: Citizen) -> None:
    """v0 has no campaign strategizing: a candidate runs on their own
    sincere position. revealed_position is pinned equal to pledged_platform
    (design doc §7bis.5) — the deviation this enables is a v2+ LLM effect,
    zero by construction here."""
    citizen.role = Role.CANDIDATE
    citizen.pledged_platform = citizen.issue_positions
    citizen.revealed_position = citizen.issue_positions


# ── 3. Coalition rule ─────────────────────────────────────────────────────

def tiebreak_key(
    party_id: int, seats: dict[int, int], votes: dict[int, float], tiebreak: tuple[str, ...]
) -> tuple[float, ...]:
    """Public since v2 increment 5: also the initiator-designation rule
    llm_behavior_engine.decide_coalition reuses, so the LLM path and the
    deterministic baseline designate the same formateur (§3.7.1's `action=4
    propose` stays reserved-but-unused — see CoalitionAction, codebook.py)."""
    key: list[float] = []
    for criterion in tiebreak:
        if criterion == "seats":
            key.append(-float(seats.get(party_id, 0)))
        elif criterion == "votes":
            key.append(-float(votes.get(party_id, 0.0)))
        else:  # "party_id" — config.py already validated no other value can appear
            key.append(float(party_id))
    return tuple(key)


def form_coalition(
    party_platforms: dict[int, tuple[float, ...]],
    seats: dict[int, int],
    votes: dict[int, float],
    tiebreak: tuple[str, ...],
    majority_ratio: float,
) -> list[int] | None:
    """DEMARRAGE-polity-v0.md §4 — nearest-ideological-neighbour coalition
    formation. Returns the ordered list of party_ids in the governing
    coalition, or None if no coalition reaches a majority even after every
    seated party is added (§4 point 3 — journal as `coalition_failed`;
    logging is the caller's job, this function only reports the outcome).

    1. Initiator = the seated party ranked first by `tiebreak` (config:
       [seats, votes, party_id] — every level explicit, never a bare
       max()/min() on dict insertion order).
    2. Remaining seated parties are added in ascending distance from the
       initiator's platform until the coalition crosses `majority_ratio`
       of all seats; ties in distance broken by seats descending, then
       party_id (this second cascade never includes votes — a distinct,
       fixed rule from the initiator's).
    """
    governing = [pid for pid, s in seats.items() if s > 0]
    if not governing:
        return None

    total_seats = sum(seats.values())
    majority_threshold = majority_ratio * total_seats

    initiator = min(governing, key=lambda pid: tiebreak_key(pid, seats, votes, tiebreak))
    coalition = [initiator]
    coalition_seats = seats[initiator]
    if coalition_seats > majority_threshold:
        return coalition

    remaining = [pid for pid in governing if pid != initiator]
    remaining.sort(
        key=lambda pid: (
            math.dist(party_platforms[pid], party_platforms[initiator]),
            -seats[pid],
            pid,
        )
    )
    for pid in remaining:
        coalition.append(pid)
        coalition_seats += seats[pid]
        if coalition_seats > majority_threshold:
            return coalition

    return None


# ── 4. Pressure action rule ─────────────────────────────────────────────

def deterministic_pressure_action(
    citizen: Citizen,
    gap: float,
    menu: PressureMenuConfig,
    *,
    can_sign: bool = False,
    can_launch: bool = False,
) -> PressureAct:
    """v4 Lot 4/5, dt=10's §11.4 baseline for a citizen already past the
    awakening gate (accountability.select_consulted) -- this function never
    decides WHO is consulted, only what a consulted citizen does. `gap` and
    the two petition-availability facts are pre-computed by the caller and
    passed in, not recomputed here, precisely so this module never imports
    accountability.py -- the "who decides" module stays free of the "what
    is the institutional state" module. `can_sign`/`can_launch` are ignored
    entirely when `menu.petition_enabled` is false: `menu.petition_enabled`
    is the single authoritative gate, so a caller that computes the facts
    without consulting the menu still cannot produce an out-of-menu act.

    Gates MOBILIZE (and, from Lot 5, the petition actions) on the citizen's
    own blank_threshold (already the "unacceptable to me" bar on the same
    weighted-distance scale as self_gap, per build_ranking) rather than
    acting unconditionally: verified numerically that a sustained
    mobilization rate amplifies into an L drop by ~33x at the shipped
    decay/weight_in_ecart values, so an unconditional rule would crash L to
    its floor on the first tick of every term and make "L moves and
    recovers" untestable. This also keeps act=0 genuinely reachable under
    electoral_only, not just theoretically legal (§16.3: "y compris
    act=0").

    Priority chain when both petition_enabled and mobilization_enabled are
    true (the "both" modality of §7bis.2's 4-way menu): sign an open,
    unsigned petition; else launch one if none is open and the target
    isn't in cooldown; else mobilize; else wait for the election. Petition
    outranks mobilization because it is the only lever with an
    institutional consequence (it can trigger a binding confidence vote),
    while mobilization "ne déclenche rien automatiquement, il rend
    visible" (§7bis.4b) -- and because the REVERSE order makes "both"
    behaviorally identical to mobilization-only (a petition would never be
    launched), collapsing one of the menu's four modalities before Lot 8
    can compare them. This rigid preference is the §11.4 BASELINE ONLY --
    Lot 7's LLM sees the whole menu and arbitrates freely; the contrast
    between a rigid preference and a free arbitration is what the palier
    exists to measure."""
    if gap < citizen.blank_threshold:
        return PressureAct.NOTHING
    if menu.petition_enabled:
        if can_sign:
            return PressureAct.SIGN_PETITION
        if can_launch:
            return PressureAct.LAUNCH_PETITION
    if menu.mobilization_enabled:
        return PressureAct.MOBILIZE
    return PressureAct.WAIT_FOR_ELECTION


# ── 5. Confidence-vote ballot rule (v4 Lot 5, §7bis.4a) ─────────────────

def build_confidence_ballot(voter: Citizen, holder: Citizen) -> bool:
    """True = keep. Reuses build_ranking/choose_party's acceptability bar:
    keep iff weighted_distance(voter, holder.revealed_position) is within
    voter.blank_threshold -- identical math to accountability.self_gap,
    kept local so this module's dependency set is unchanged (see
    deterministic_pressure_action's own reasoning for the same choice).
    Raises if the holder has no revealed_position (a contract violation:
    every officeholder gets one at candidacy declaration).

    Uses revealed_position, not pledged_platform: the referendum is on the
    maintien of the representative AS THEY ACTUALLY ARE. Through Lot 5,
    revealed_position == pledged_platform always (declare_candidacy pins
    them equal, and nothing diverges them until Lot 6's
    representative_response exists) -- so on the deterministic path,
    build_confidence_ballot(voter, holder) is EXACTLY
    ballot_ranks_above_blank(build_ranking(voter, [holder, ...]),
    candidate_label(holder)): build_ranking's own "above blank" cutoff is
    this same `<=` comparison, and because it is a strict partition (every
    within-tolerance candidate sorts before every out-of-tolerance one), a
    candidate's position relative to blank depends only on that
    candidate's own distance, never on who else is in the field. This
    makes keep_ratio (ballot_and_aggregation.confidence_keep_ratio) equal
    to mandate_strength for the whole term on the deterministic path --
    proven, not assumed, and pinned by test. Lot 6 is what breaks this,
    deliberately: once revealed_position can drift, the confidence vote
    decouples from the election and becomes a live sanction."""
    if holder.revealed_position is None:
        raise ValueError(f"citizen {holder.citizen_id} has no revealed_position")
    return weighted_distance(voter, holder.revealed_position) <= voter.blank_threshold


# ── 6. reaction_to_event baseline (v5 Lot 3, §8) ────────────────────────

def deterministic_reaction_to_event(event_type: EventType, config: EventsConfig, *, magnitude: float = 0.0) -> float:
    """v5 Lot 3, dt=8's §11.4 baseline: a flat, population-wide salience_delta,
    applied identically to every citizen by the caller -- no Citizen
    parameter here at all (stricter than deterministic_pressure_action's
    per-citizen `gap`), because dt=8's own baseline makes no per-citizen
    judgment by construction (this is also why ReactionMotif.
    EVENT_PERSONALLY_IRRELEVANT=403 is structurally unreachable on this
    path). SCANDAL returns config.scandal_magnitude verbatim -- deliberately
    NOT additionally capped by max_reaction_delta (EventsConfig's own
    docstring: the two fields must stay analytically separable, even where
    shipped defaults happen to match). ECONOMIC_SHOCK scales by the realized
    AR(1) magnitude, capped at max_reaction_delta -- NOT normalized by
    economy_shock_threshold (that would saturate to the cap on every call,
    since this branch only ever runs once the threshold is already
    crossed)."""
    if event_type is EventType.SCANDAL:
        return config.scandal_magnitude
    if event_type is EventType.ECONOMIC_SHOCK:
        return config.max_reaction_delta * min(1.0, abs(magnitude))
    raise ValueError(f"unhandled EventType: {event_type!r}")
