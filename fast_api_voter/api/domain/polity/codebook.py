"""
api.domain.polity.codebook — the compression tables of design doc §3.7,
vote + candidacy-consideration + party-nomination + campaign-positioning +
coalition-decision slices (v2 increments 1-5), plus v4 Lot 1's upfront
reservation of the legitimacy/pressure palier's wire surface (representative
_response dt=6, pressure_action dt=10, and the binary confidence-vote ballot
format), plus v5 Lot 1's reservation of reaction_to_event (dt=8, §8).

Single source of truth: the `Literal[...]` types used for wire validation
(llm_schemas.py) and the human-readable table injected into the LLM's system
prompt (llm_behavior_engine.py) both derive from these enums, so the two
cannot silently drift apart — exactly the failure mode §3.7.0 calls out
("jamais une édition silencieuse de la version en cours").

`DecisionType` defines VOTE_CAST (1), CANDIDACY_CONSIDERED (2),
PARTY_NOMINATION_CHOICE (4), CAMPAIGN_POSITIONING (5), REPRESENTATIVE_RESPONSE
(6), COALITION_DECISION (9), and PRESSURE_ACTION (10). CANDIDACY_DECLARED (3)
is deliberately NOT a member: `candidacy_declared` already exists as a journal
`event_type` string (run_polity_simulation.py) marking the institutional
outcome (a party's chosen nominee) — it is not itself a second LLM decision,
since a single `candidacy_considered` call's `outcome=1` case (or, when a
party is contested, `party_nomination_choice`'s winner) is what produces it.
Code 7 (`petition_signature_decision`) is retired and must never be
reassigned — recorded here as a comment, not a member, so nothing can
accidentally reuse it. Code 8 (`reaction_to_event`) is reserved by v5 Lot 1
(§8) ahead of its own `decide_*` function (v5 Lot 4) — see below.

6, 8, and 10 are reserved here (v4 Lot 1 / v5 Lot 1) ahead of their actual
`decide_*` functions (v4 Lots 6-7, v5 Lot 4) — unlike every prior
increment's "the code only gains a member when the code that writes it
exists" discipline. This is a deliberate exception: each palier's own Lot 1
stands up its full wire surface (motifs, action/stance enums, the codebook
version) in one place before any subsequent lot builds behavior on top of
it. In practice none of these three codes is ever written to a journal
yet — `legitimacy.enabled`, every `pressure_menu` lever, and `events.enabled`
all default to `false`, and no `decide_*` function exists for any of them
until their own later lot — so this is inert reservation, not activation.
"""
from __future__ import annotations

from enum import IntEnum


class PolityCodebookError(ValueError):
    """Raised when a run's configured codebook_version doesn't match the
    one this code was written against — §3.7.0's frozen-artifact contract."""


CODEBOOK_VERSION = "1.4"  # bumped from "1.3" — v5 Lot 1 (§8): new decision
                           # type (8=reaction_to_event) and new enum members
                           # (EventType, ReactionMotif) change the wire
                           # surface, the same bump trigger v4 Lot 1 used for
                           # "1.1"->"1.2". Prior bump: "1.2"->"1.3" — a v4
                           # Lot 8 live acceptance-run finding: VoteMotif had
                           # no code for a sincere vote cast for an
                           # imperfect-but-tolerable candidate (every
                           # existing code names either a blank-vote reason or a
                           # strategic one), which measurably starved the model
                           # of a "just vote for them, they clear my threshold"
                           # option. See VoteMotif.ACCEPTABLE_MATCH.


class DecisionType(IntEnum):
    """§3.7.1 `decision_type` (`dt`). 7 is retired (formerly
    petition_signature_decision) and must never be reused. 6, 8, and 10 are
    reserved by v4 Lot 1 / v5 Lot 1 ahead of their own decide_* functions
    (v4 Lots 6-7, v5 Lot 4) — see this module's docstring for why that's a
    deliberate exception to every prior code's "member only once the code
    exists" discipline."""

    VOTE_CAST = 1
    CANDIDACY_CONSIDERED = 2
    PARTY_NOMINATION_CHOICE = 4
    CAMPAIGN_POSITIONING = 5
    REPRESENTATIVE_RESPONSE = 6
    REACTION_TO_EVENT = 8
    COALITION_DECISION = 9
    PRESSURE_ACTION = 10


class BallotFormat(IntEnum):
    """§3.7.1 `ballot_format` (`bf`). 2=approval, 3=scores remain reserved
    for methods no increment's default exercises (two_round, a ranking-
    family method). 4=binary is v4's confidence-vote mechanic (§7bis.4a) —
    resolved deterministically in ballot_and_aggregation.py (v4 Lot 5), never
    its own LLM decision type: §3.7.1 models a confidence vote as bf=4 on
    the EXISTING vote_cast dt=1, not a sixth decision shape."""

    RANKING = 1
    BINARY = 4


class EventType(IntEnum):
    """§3.7.1 `event_type` (reaction_to_event, dt=8, v5 §8). The two exogenous
    generators §8 names: SCANDAL is a Poisson-arrival event targeting the
    sitting president; ECONOMIC_SHOCK is a population-wide AR(1) climate
    reading crossing `events.economy_shock_threshold` (§16.3-style
    anti-saturation gate — not every tick's AR(1) value, only the ones that
    count as "majeur"). Reserved by v5 Lot 1 ahead of shock.py (Lot 2) and
    dt=8's own decide_* function (Lot 4)."""

    SCANDAL = 1
    ECONOMIC_SHOCK = 2


class VoteMotif(IntEnum):
    """§3.7.2 motif range 100-199 (Vote). 102 (SOCIAL_CONTAGION) and 103
    (RETROSPECTIVE_PUNISHMENT) require infrastructure this increment doesn't
    have yet (the social graph is v6; retrospective memory needs
    memory_window_terms, unused in v0/v1) — kept as valid codes per §3.7.2's
    "liste non figée", but expect 101/104/105 to dominate in practice.
    Record the observed distribution rather than pruning the enum.

    105 (ACCEPTABLE_MATCH) added in v4 Lot 8, live: a real acceptance run
    found every prior code named either a blank-vote reason (101) or a
    strategic one (104, defecting from a sincere favorite) — none of them
    covers the single most common real-world case, a voter whose favorite
    candidate clears their own blank_threshold and who simply votes for
    them, sincerely, without needing a special justification. Its absence
    is suspected to have measurably biased cast_votes toward blank at
    production scale -- see build_system_prompt's docstring in
    llm_behavior_engine.py for the full finding."""

    NO_MATCHING_PRIORITY = 101
    SOCIAL_CONTAGION = 102
    RETROSPECTIVE_PUNISHMENT = 103
    STRATEGIC_DEFECTION = 104
    ACCEPTABLE_MATCH = 105


VOTE_MOTIF_PROMPT_TABLE = "\n".join(f"{motif.value} = {motif.name}" for motif in VoteMotif)


class CandidacyOutcome(IntEnum):
    """§3.7.1 `outcome` (candidature)."""

    DECLINED = 0
    DECLARED = 1


class CandidacyMotif(IntEnum):
    """§3.7.2 motif range 200-299 (Candidature). 202 (IDEOLOGICAL_RUPTURE) is
    deliberately NOT a member here: it's the rupture path's own motif
    (attempt_rupture_candidacy, simple_rules.py), which stays fully
    deterministic and never calls the LLM — reusing 202 for a dominant-path
    decline would misattribute rupture semantics to a citizen who never took
    that path. 204/205 are new codes (§3.7.2's list is explicitly "non
    figée") for the decline-nuances a bare ambition_score threshold can't
    express — the actual reason this decision is LLM-governed instead of a
    threshold at all."""

    INSUFFICIENT_PERCEIVED_SUPPORT = 201
    AMBITION_THRESHOLD_MET = 203
    AMBITION_INSUFFICIENT = 204
    RISK_AVERSE_DEFERRAL = 205


CANDIDACY_MOTIF_PROMPT_TABLE = "\n".join(f"{motif.value} = {motif.name}" for motif in CandidacyMotif)


class PartyNominationMotif(IntEnum):
    """§3.7.2 motif range 200-299 (Candidature) — extended, not a new range.
    The design doc's §3.7.2 table never allocated a range to
    party_nomination_choice (dt=4) at all; reusing 200-299 (rather than
    inventing an unallocated block) follows the same precedent as
    CandidacyMotif's own 204/205 additions, and keeps "why did this citizen
    become a candidate" and "why THIS one among several" in one place. Codes
    206-209 map directly to the three signals build_party_nomination_user_prompt
    actually sends (ambition_score, perceived_support, platform_distance),
    plus one holistic catch-all — closed-enum per project convention, never
    free text."""

    HIGHEST_AMBITION = 206
    BROADEST_PERCEIVED_SUPPORT = 207
    CLOSEST_TO_PARTY_PLATFORM = 208
    STRATEGIC_ELECTABILITY = 209


PARTY_NOMINATION_MOTIF_PROMPT_TABLE = "\n".join(
    f"{motif.value} = {motif.name}" for motif in PartyNominationMotif
)


class CampaignMotif(IntEnum):
    """§3.7.2 motif range 600-699 (Campagne) — a NEW range, unlike
    party_nomination_choice's reuse of 200-299. Positioning strategy is a
    distinct concept from candidature itself (whether/who becomes a
    candidate): it's about how a already-confirmed nominee presents
    themselves. Each code maps directly to a signal
    build_positioning_user_prompt actually sends (own position, rival
    nominees, electorate mean) so the observed motif distribution is a real
    read on emergent strategy, not an arbitrary label."""

    SINCERE_CONVICTION = 601
    MEDIAN_VOTER_APPEAL = 602
    BASE_CONSOLIDATION = 603
    DIFFERENTIATION_FROM_RIVALS = 604


CAMPAIGN_MOTIF_PROMPT_TABLE = "\n".join(f"{motif.value} = {motif.name}" for motif in CampaignMotif)


class CoalitionAction(IntEnum):
    """§3.7.1 `action` (coalition), dt=9. Only JOIN/LEAVE are members: 3
    (maintain) is reserved for a later increment that re-evaluates a
    *standing* coalition across ticks (§3.1's "maintien et rupture", out of
    scope here — see llm_behavior_engine.decide_coalition's docstring); 4
    (propose) is reserved for the initiator role, which stays a
    deterministic institutional designation (simple_rules.tiebreak_key +
    parties.coalition_tiebreak) rather than an LLM output, the same
    procedural-gate precedent candidacy/nomination already set. Mirrors
    BallotFormat's "define only the exercised code" shape."""

    JOIN = 1
    LEAVE = 2


COALITION_ACTION_PROMPT_TABLE = "\n".join(f"{action.value} = {action.name}" for action in CoalitionAction)


class CoalitionMotif(IntEnum):
    """§3.7.2 motif range 500-599 (Coalition), explicitly "non figée". 501/502
    are the design doc's own codes, kept verbatim, for a `join`. 503
    COALITION_RUPTURE_DISAGREEMENT is deliberately NOT a member: it names
    leaving an *existing* coalition, and this increment only forms them —
    reusing it for a formation-time decline would misattribute rupture
    semantics to a party that was never in a government (the same argument
    CandidacyMotif uses to exclude 202). 504/505 are new codes in the same
    range for a `leave`, each mapped to a signal build_coalition_user_prompt
    actually sends (distance_to_initiator; own seats vs. the initiator's
    shortfall)."""

    IDEOLOGICAL_PROXIMITY = 501
    OFFICE_SEEKING = 502
    IDEOLOGICAL_DISTANCE_TOO_HIGH = 504
    NO_LEVERAGE_IN_GOVERNMENT = 505


COALITION_MOTIF_PROMPT_TABLE = "\n".join(f"{motif.value} = {motif.name}" for motif in CoalitionMotif)


class Stance(IntEnum):
    """§3.6.5 / §3.7.1 `stance` (representative_response, dt=6). A closed
    enum, not free text, so §7bis.4b's central behavioral question --
    premature concession to a weak signal vs. indifference until real
    institutional sanction -- is observable directly from the journal,
    without qualitative re-reading. COUNTER_MOBILIZATION is a valid, LLM-
    reachable value with no pro-incumbent citizen lever to pair it with in
    v4 (no "rally the base" action exists in PressureAct below) -- it is
    observable but mechanically inert until a later palier adds one."""

    CONCESSION = 1
    DEFIANCE = 2
    SILENCE = 3
    COUNTER_MOBILIZATION = 4


STANCE_PROMPT_TABLE = "\n".join(f"{stance.value} = {stance.name}" for stance in Stance)


class PressureAct(IntEnum):
    """§3.6.6 / §3.7.1 `action` (pressure_action, dt=10). 0 and 4 are always
    legal regardless of the active pressure_menu (§3.6.6's hard constraint);
    1/2/3 are gated by petition_enabled/petition_enabled/mobilization_enabled
    respectively -- enforced in llm_behavior_engine.py against the actual
    config, not here (the same "context-dependent, not Pydantic's job" split
    every prior decision type's validate_* function already uses)."""

    NOTHING = 0
    SIGN_PETITION = 1
    LAUNCH_PETITION = 2
    MOBILIZE = 3
    WAIT_FOR_ELECTION = 4


PRESSURE_ACT_PROMPT_TABLE = "\n".join(f"{act.value} = {act.name}" for act in PressureAct)


class ResponseMotif(IntEnum):
    """§3.7.2 motif range 300-399 (Pression) — representative_response's
    (dt=6) slice. 301/302/303 are the design doc's own codes, kept verbatim:
    each grounds a CONCESSION specifically, the representative yielding to a
    legible signal directly present in dt=6's own ctx (their own mandate
    deviation, visible street pressure, or an approaching legitimacy floor).
    304 RESIGNATION_NO_LEVERAGE and 305 DEFERRED_TO_ELECTION are deliberately
    NOT members here: both describe a CITIZEN's reasoning for inaction (see
    PressureMotif below), not a sitting representative's -- a citizen who
    feels they have no leverage is not the same fact as a representative who
    concedes nothing. 306 FOLLOWING_NEIGHBORS needs the v6 social graph and
    has no analogue for a single office-holder. 307-309 are new codes
    (§3.7.2's list is explicitly "non figée") for the three stances the
    design doc's own three codes cannot ground at all: defiance, silence,
    and counter-mobilization each need their own signal, not a borrowed
    concession-reason -- reusing a concession motif for the opposite
    reaction would make the motif distribution describe nothing."""

    MANDATE_DEVIATION_HIGH = 301
    STREET_PRESSURE_RESPONSE = 302
    LEGITIMACY_FLOOR_APPROACHING = 303
    IDEOLOGICAL_CONVICTION = 307
    STRATEGIC_AMBIGUITY = 308
    BASE_MOBILIZATION_APPEAL = 309


RESPONSE_MOTIF_PROMPT_TABLE = "\n".join(f"{motif.value} = {motif.name}" for motif in ResponseMotif)


class PressureMotif(IntEnum):
    """§3.7.2 motif range 300-399 (Pression) — pressure_action's (dt=10)
    slice. Overlaps ResponseMotif at 301 deliberately: a representative's
    self-awareness of their own deviation and a citizen's perception of that
    same deviation are two legitimately distinct readings of one underlying
    fact, not a collision (two separate enum classes, so there is no value
    conflict). 302 STREET_PRESSURE_RESPONSE and 306 FOLLOWING_NEIGHBORS are
    deliberately NOT members: dt=10's own ctx (§3.6.6's worked example)
    never includes the street_pressure aggregate at all -- §7bis.9f requires
    each citizen to decide alone, without seeing what others are doing, and
    leaking that aggregate into a citizen's own motif choice would
    contradict the atomized-regime baseline v4 exists partly to establish
    (v6's contagion regime is the comparison point). neighbors_acting is
    null before v6 for the same reason. 304/305 are the design doc's own
    codes, grounding act=0 (no leverage) and act=4 (deferred to election)
    respectively."""

    MANDATE_DEVIATION_HIGH = 301
    RESIGNATION_NO_LEVERAGE = 304
    DEFERRED_TO_ELECTION = 305


PRESSURE_MOTIF_PROMPT_TABLE = "\n".join(f"{motif.value} = {motif.name}" for motif in PressureMotif)


class ReactionMotif(IntEnum):
    """§3.7.2 motif range 400-499 (Événements exogènes) — reaction_to_event's
    (dt=8, v5 §8) slice. 401 SCANDAL_TRUST_EROSION and 402
    ECONOMIC_SHOCK_REACTION are the design doc's own two codes (§3.7.2's
    table), kept verbatim, each grounding a `salience_delta > 0` reaction to
    its own EventType. 403 EVENT_PERSONALLY_IRRELEVANT is a new code
    (§3.7.2's list is explicitly "non figée") grounding the
    `salience_delta == 0` branch -- a citizen who perceives the event but
    judges it doesn't concern them, the same "every reachable branch needs a
    code" discipline that produced ResponseMotif's 307-309. Only reachable
    via the LLM path (v5 Lot 4): the deterministic baseline
    (simple_rules.deterministic_reaction_to_event, v5 Lot 3) applies a flat,
    uniform salience_delta to every citizen by construction, so judging an
    event "irrelevant to me" requires citizen-level judgment 403 doesn't
    exist to serve on that path."""

    SCANDAL_TRUST_EROSION = 401
    ECONOMIC_SHOCK_REACTION = 402
    EVENT_PERSONALLY_IRRELEVANT = 403


REACTION_MOTIF_PROMPT_TABLE = "\n".join(f"{motif.value} = {motif.name}" for motif in ReactionMotif)


MOTIF_ENUMS: tuple[type[IntEnum], ...] = (
    VoteMotif,
    CandidacyMotif,
    PartyNominationMotif,
    CampaignMotif,
    CoalitionMotif,
    ResponseMotif,
    PressureMotif,
    ReactionMotif,
)


def motif_labels() -> dict[int, str]:
    """§3.7.2's motif code -> label table, flattened across every motif
    enum, for compaction.py's codebook JOIN (§3.7.4, v4 storage lot). Same
    iteration the *_PROMPT_TABLE constants above already use for each enum
    individually -- this module stays the single source of truth for what
    a code means; compaction.py never hand-copies a mapping.

    Flat and global because §3.7.2's "prefixe de categorie x 100"
    convention makes motif codes globally unique BY DESIGN -- unlike
    §3.7.1's per-field codes (role/office/act/stance/...), which are
    small, per-field code spaces and are deliberately NOT decoded here
    (see compaction.py's own docstring for that scope boundary).

    ResponseMotif and PressureMotif both define 301 = MANDATE_DEVIATION_HIGH,
    intentionally and with the same meaning (see PressureMotif's own
    docstring) -- that is a duplicate, not a collision, and collapses to
    one row here. A genuine collision (one code, two DIFFERENT labels)
    would silently mislabel events and, because compaction.py's codebook
    table is keyed on `code` alone, would fan out its decode JOIN into
    duplicate rows -- so it raises here, at the source, rather than being
    discovered as a wrong number in a distribution downstream.

    Returned sorted by code: compaction.py inserts this verbatim, and a
    deterministic order keeps two compactions of one journal
    query-comparable."""
    labels: dict[int, str] = {}
    for enum_cls in MOTIF_ENUMS:
        for member in enum_cls:
            existing = labels.get(int(member))
            if existing is not None and existing != member.name:
                raise PolityCodebookError(
                    f"motif code {int(member)} maps to both {existing!r} and "
                    f"{member.name!r} ({enum_cls.__name__}) — §3.7.2 codes are "
                    f"globally unique; a code is never reassigned"
                )
            labels[int(member)] = member.name
    return dict(sorted(labels.items()))


def check_codebook_version(config_version: str) -> None:
    if config_version != CODEBOOK_VERSION:
        raise PolityCodebookError(
            f"llm.codebook_version {config_version!r} does not match this code's "
            f"codebook version {CODEBOOK_VERSION!r} — regenerate or update one of them"
        )
