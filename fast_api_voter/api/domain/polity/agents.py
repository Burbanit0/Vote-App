"""api.domain.polity.agents -- the agent tier (ADR-014, plan-polity-agency-roadmap.md).

An agent is a citizen the model plays in the first person: a persona rendered from their
numbers, a memory that is a view over the journal, and a turn whose typed moves the kernel
validates and applies ("the model never mutates state"). The sitting president is the only
agent so far: one turn a tick restates their position and, when the agenda is theirs,
proposes a bill.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict, deque
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from itertools import accumulate
from pathlib import Path
from typing import Any, NamedTuple

from pydantic import BaseModel

from api.domain.polity.amendments import articles_text, validate_amendment, value_text
from api.domain.polity.citizen import Citizen
from api.domain.polity.codebook import CoalitionAction, CoalitionMotif
from api.domain.polity.config import ARTICLES, ISSUE_COUNT_NAMED, PolityConfig
from api.domain.polity.constitution import Proposal
from api.domain.polity.events import INSTITUTIONAL_EVENT_TYPES
from api.domain.polity.journal import JournalEvent
from api.domain.polity.llm_behavior_engine import (
    ResponseContext,
    _complete_and_decode_with_replay,
    _dynamic_max_tokens,
    _negotiation_converged,
    _profile,
    _provisional_coalition_seats,
    _validated,
    run_chunks,
    thinking_budget_body,
)
from api.domain.polity.llm_client import LlmClientProtocol, LlmResponseError, _decode_batch
from api.domain.polity.llm_schemas import (
    AMENDING_LEADER_TURN_JSON_SCHEMA,
    AMENDMENT_BALLOT_JSON_SCHEMA,
    FORUM_TURN_JSON_SCHEMA,
    LEADER_COALITION_TURN_JSON_SCHEMA,
    LEADER_TURN_JSON_SCHEMA,
    AmendingLeaderTurn,
    AmendmentBallot,
    CoalitionDecision,
    ForumTurn,
    IssueTarget,
    LeaderCoalitionTurn,
    LeaderTurn,
    PositionShift,
)
from api.domain.polity.parties import Party

_logger = logging.getLogger(__name__)

PRESIDENT_TURN = "president_turn"
NOMINEE_TURN = "nominee_turn"
AMENDMENT_VOTE = "amendment_vote"
FORUM_POST = "forum_post"
COALITION_TURN = "coalition_turn"
GAP_ISSUES = 3
"""A leader is told the issues on which the formateur's platform differs most from their own."""
FORUM_IDLE_TICKS, FEED_SIZE = 8, 8
"""A citizen who launched a petition stays on the forum this many ticks; a turn reads this many posts."""
_RETRY_TEMPERATURE = 0.3
_RETRY_SEED_BASE = 900_000_901
SPEECH_LIMIT, RATIONALE_LIMIT, NOTE_LIMIT, INITIATIVE_LIMIT = 400, 300, 200, 200
_SHOWN_PRECISION = 0.01
"""Values reach the agent with two decimals."""


class Issue(NamedTuple):
    name: str
    low: str
    """The pole at 0."""
    high: str
    """The pole at 1."""


ISSUES: tuple[Issue, ...] = (
    Issue("taxation", "low taxes", "high taxes"),
    Issue("public spending", "a lean state", "large public services"),
    Issue("welfare", "individual responsibility", "generous welfare"),
    Issue("labour", "a flexible labour market", "strong worker protection"),
    Issue("trade", "free trade", "protection of local industry"),
    Issue("immigration", "restrictive", "open"),
    Issue("policing", "civil liberties first", "law and order first"),
    Issue("environment", "growth first", "climate first"),
    Issue("energy", "fossil and nuclear", "renewables only"),
    Issue("housing", "the private market", "public housing"),
    Issue("healthcare", "private insurance", "universal public care"),
    Issue("education", "school choice", "a uniform public school"),
    Issue("regions", "a central state", "strong regions"),
    Issue("sovereignty", "national sovereignty", "international integration"),
    Issue("defence", "low military spending", "high military spending"),
    Issue("religion", "strict secularism", "a public role for religion"),
    Issue("social mores", "traditional values", "progressive values"),
    Issue("agriculture", "industrial farming", "small subsidised farms"),
    Issue("technology", "light regulation", "strict regulation"),
    Issue("direct democracy", "representative government", "frequent referendums"),
)
assert len(ISSUES) == ISSUE_COUNT_NAMED

_FIRST_NAMES = (
    "Alex", "Sam", "Robin", "Camille", "Dominique", "Charlie", "Jordan", "Morgan", "Sacha", "Maxime",
    "Andrea", "Noa", "Eden", "Lou", "Ariel", "Taylor", "Riley", "Casey", "Jamie", "Quinn", "Avery", "Remy",
)
_LAST_NAMES = (
    "Martin", "Bernard", "Dubois", "Moreau", "Laurent", "Garcia", "Rossi", "Novak", "Silva", "Weber", "Kowalski",
    "Jensen", "Costa", "Fischer", "Nguyen", "Haddad", "Okafor", "Tanaka", "Petrov", "Murphy", "Lindqvist", "Varga",
)


def agent_name(citizen: Citizen) -> str:
    cid = citizen.citizen_id
    return f"{_FIRST_NAMES[cid % len(_FIRST_NAMES)]} {_LAST_NAMES[cid // len(_FIRST_NAMES) % len(_LAST_NAMES)]}"


def issue_label(dimension: int) -> str:
    issue = ISSUES[dimension]
    return f"{dimension} {issue.name} ({issue.low} / {issue.high})"


def lean(dimension: int, value: float) -> str:
    """A position in words. The first live run (2026-09-28) had the president say "low taxes"
    while moving taxation to 0.82: an 8B model misreads a bare number against two poles."""
    issue = ISSUES[dimension]
    if value < 0.2:
        return f"strongly for {issue.low}"
    if value < 0.4:
        return f"leaning to {issue.low}"
    if value <= 0.6:
        return "in between"
    if value <= 0.8:
        return f"leaning to {issue.high}"
    return f"strongly for {issue.high}"


def persona(citizen: Citizen) -> str:
    """Who the agent is, from their numbers alone -- stable across ticks, so it sits in the
    system prompt and is served from the prefix cache. The numbers stay the kernel's truth."""
    top = sorted(range(len(ISSUES)), key=lambda d: (-citizen.issue_priorities[d], d))[:3]
    party = f"party {citizen.party_affiliation}" if citizen.party_affiliation is not None else "no party"
    views = "\n".join(
        f"- {issue_label(d)}: {citizen.issue_positions[d]:.2f}, {lean(d, citizen.issue_positions[d])}" for d in range(len(ISSUES))
    )
    return (
        f"You are {agent_name(citizen)} (citizen {citizen.citizen_id}), a member of {party}. "
        f"The issues you care most about: {', '.join(ISSUES[d].name for d in top)}. "
        f"Your ambition, from 0 to 1: {citizen.ambition_score:.2f}.\n"
        f"Your own convictions on each issue (0 = the first pole, 1 = the second):\n{views}"
    )


# ── memory ────────────────────────────────────────────────────────────────

_PUBLIC_EVENT_TYPES = INSTITUTIONAL_EVENT_TYPES | {"bill_voted", "bill_blocked", "bill_reviewed", "bill_enacted"}
_OWN_EVENT_TYPES = frozenset({"agent_turn", "legitimacy_updated", "amendment_vote", "forum_post", "coalition_decision"})


class AgentMemory:
    """What agents remember: a view over the journal, fed by Journal.tap as events are
    written and rebuilt from events.jsonl on resume -- never checkpointed. The public
    record is the last institutional events anyone could know of; an agent's own record is
    their last moves, notes to self and standings -- not their past speeches, which the
    model echoed back word for word (OBS-028: shown them, presidents repeated a speech
    exactly in two seeds of three; without, in none)."""

    def __init__(self, public_window: int = 16, own_window: int = 8) -> None:
        self.public: deque[JournalEvent] = deque(maxlen=public_window)
        self.own: defaultdict[int, deque[JournalEvent]] = defaultdict(lambda: deque(maxlen=own_window))
        self.posts: deque[JournalEvent] = deque(maxlen=public_window * 4)
        self.petitioned: dict[int, int] = {}
        """Each citizen who launched a petition, and when they last did."""

    def observe(self, event: JournalEvent) -> None:
        if event.event_type == "petition_launched" and event.citizen_id is not None:
            self.petitioned[event.citizen_id] = event.tick
        if event.payload.get("post") or event.payload.get("speech"):
            self.posts.append(event)
        if event.event_type in _OWN_EVENT_TYPES and event.citizen_id is not None:
            self.own[event.citizen_id].append(event)
        elif event.event_type in _PUBLIC_EVENT_TYPES:
            self.public.append(event)

    def replay(self, journal_path: Path) -> None:
        if journal_path.exists():
            with journal_path.open(encoding="utf-8") as handle:
                for line in handle:
                    self.observe(JournalEvent(**json.loads(line)))

    def recall(self, citizen_id: int) -> str:
        public = [f"- t{e.tick} {e.event_type}{_who(e)}: {_scalars(e.payload)}" for e in self.public]
        own = [_own_line(e) for e in self.own.get(citizen_id, ())]
        return (
            "Recent public events:\n" + ("\n".join(public) or "- none yet")
            + "\n\nYour recent record:\n" + ("\n".join(own) or "- nothing yet")
        )


    def recent_petitioners(self, tick: int) -> list[int]:
        """The citizens who launched a petition within FORUM_IDLE_TICKS, latest first."""
        recent = [(t, cid) for cid, t in self.petitioned.items() if tick - t < FORUM_IDLE_TICKS]
        return [cid for _, cid in sorted(recent, key=lambda p: (-p[0], p[1]))]

    def feed(self, reader: int, authors: frozenset[int]) -> str:
        """The last posts the reader can see: the president's and nominees' speeches, and the posts
        of `authors` -- never their own, which the model would echo (OBS-028)."""
        seen = [e for e in self.posts if e.citizen_id != reader and (e.event_type == "agent_turn" or e.citizen_id in authors)]
        lines = [
            f"- t{e.tick} the {e.payload['role']}: \"{e.payload['speech']}\"" if e.event_type == "agent_turn"
            else f"- t{e.tick} citizen {e.citizen_id}: \"{e.payload['post']}\""
            for e in seen[-FEED_SIZE:]
        ]
        return "On the forum:\n" + ("\n".join(lines) or "- nothing yet")


def _who(event: JournalEvent) -> str:
    return f" (citizen {event.citizen_id})" if event.citizen_id is not None else ""


def _scalars(payload: Mapping[str, Any]) -> str:
    """The payload's short fields, rounded; long lists are left to the journal."""
    shown: dict[str, Any] = {}
    for key, value in sorted(payload.items()):
        if isinstance(value, float):
            shown[key] = round(value, 2)
        elif isinstance(value, int | str | bool) or value is None:
            shown[key] = value
        elif isinstance(value, list) and len(value) <= 5 and all(isinstance(v, int | float) for v in value):
            shown[key] = [round(v, 2) for v in value]
    return json.dumps(shown, ensure_ascii=False)


def _own_line(event: JournalEvent) -> str:
    payload = event.payload
    if event.event_type == "legitimacy_updated":
        approval = f", approval {payload['approval']:.2f}" if "approval" in payload else ""
        return f"- t{event.tick} legitimacy {payload['legitimacy']:.2f}{approval}"
    if event.event_type == "amendment_vote":
        return f"- t{event.tick} you voted {payload['vote']} on changing {payload['article']}; note to self: \"{payload['note_to_self']}\""
    if event.event_type == "forum_post":
        return f"- t{event.tick} you {'posted' if payload['post'] else 'kept silent'}; note to self: \"{payload['note_to_self']}\""
    if event.event_type == "coalition_decision":
        return f"- t{event.tick} round {payload['round']} of the coalition talks you {'joined' if payload['action'] == CoalitionAction.JOIN.value else 'declined'}; note to self: \"{payload['note_to_self']}\""
    bill = f"; bill {describe_moves(payload['bill'])}" if payload["bill"] else ""
    return (
        f"- t{event.tick} you moved {describe_moves(payload['shifts']) or 'nothing'}{bill}; "
        f"note to self: \"{payload['note_to_self']}\""
    )


def describe_moves(moves: Sequence[Mapping[str, Any]]) -> str:
    """Journaled moves in words: `housing +0.10, taxation -0.05`."""
    return ", ".join(f"{ISSUES[int(m['dimension'])].name} {float(m['delta']):+.2f}" for m in moves)


# ── the president's turn ──────────────────────────────────────────────────

_ANSWER_FORMAT = (
    "Answer with one JSON object in the schema given. \"rationale\" is your private reasoning "
    f"(at most {RATIONALE_LIMIT} characters). \"positions\" names the position you now take on an issue "
    "({{\"dimension\": issue number, \"target\": a value from 0 to 1}}); an empty list keeps your stated position. "
    "\"bill\" names the policy you want on an issue, the same way; an empty list proposes no bill. "
    "\"speech\" is what you say in public "
    f"(at most {SPEECH_LIMIT} characters), \"note_to_self\" what you want to remember next tick (at most {NOTE_LIMIT}). "
    "If you want to do something these rules do not offer, describe it in \"other_initiative\" "
    f"(at most {INITIATIVE_LIMIT} characters): it will not happen, but it is recorded. Otherwise leave it empty."
)


def _amendment_rules(config: PolityConfig) -> str:
    chamber = config.sortition_chamber
    return (
        f"The constitution can be amended. Its articles:\n{articles_text(config)}\n"
        f"You may propose one amendment in a turn -- \"amendment\": {{\"article\": ..., \"value\": ..., \"reason\": "
        f"why, in a sentence}} -- when none is pending; leave \"amendment\" out otherwise. The next tick the chamber, "
        f"{chamber.seats} citizens drawn by lot, votes on it, each member for themselves; it is ratified when more than the "
        "share your briefing shows for that article vote yes, and holds from then on."
    )


def president_system_prompt(president: Citizen, config: PolityConfig) -> str:
    """The rules the president acts under and who they are; nothing tick-dependent, so the
    whole prompt is a stable prefix. It states the rules and never says what to do (C4)."""
    inst, mandate, legislation = config.institutions, config.mandate, config.legislation
    limit = "with no limit on terms" if inst.president_term_limit is None else f"for at most {inst.president_term_limit} terms"
    rules = [
        f"Each tick is a quarter of a year. The president is elected for {inst.president_term_years} years, {limit}.",
        "Each tick a poll measures your approval: the share of citizens who approve of your conduct -- the positions "
        "you state in office and the policy enacted during your term.",
        f"Each tick you may restate your position on up to {mandate.max_response_shifts} issues: name the position you "
        f"now take, and your stated position moves toward it by at most {mandate.max_response_delta:.2f}. The gap "
        "between what you pledged and what you now say is public.",
    ]
    if config.legitimacy.enabled:
        rules.append(
            "Your legitimacy follows your support and falls under petitions and street protest; below "
            f"{config.legitimacy.recall_floor:.2f} you are recalled."
        )
    if config.petition.enabled:
        rules.append(f"A petition signed by {config.petition.signature_threshold:.0%} of citizens forces a confidence vote on you.")
    if legislation.enabled:
        rules.append(
            f"When the agenda is yours you may propose one bill: name the policy you want on up to "
            f"{legislation.max_bill_dimensions} issues, and the bill moves policy toward it by at most "
            f"{legislation.max_bill_step:.2f} on each. It passes if parties holding more than "
            f"{legislation.assembly_majority_ratio:.0%} of the assembly's seats find it brings policy closer to their "
            "platforms; the sortition chamber may suspend it."
        )
    if config.agents.amendments:
        rules.append(_amendment_rules(config))
    return (
        "You are playing a citizen of a simulated democracy, in the first person.\n\n"
        f"{persona(president)}\n\n"
        "You are now its president. You want to govern by your convictions and to keep office; how you weigh the "
        "two is yours to decide.\n\nThe rules you act under:\n"
        + "\n".join(f"- {rule}" for rule in rules)
        + f"\n\n{_ANSWER_FORMAT}"
    )


@dataclass(frozen=True)
class PresidentBriefing:
    """What the president knows at the start of their turn -- the tick's user prompt."""

    tick: int
    ticks_per_year: int
    context: ResponseContext
    approval: float
    agenda_closed: str | None
    """Why no bill can be proposed this tick; None when the agenda is the president's."""
    policy: tuple[float, ...] | None
    public_median: tuple[float, ...]
    assembly_median: tuple[float, ...] | None
    pledge: tuple[float, ...]
    stated: tuple[float, ...]
    constitution: str | None = None
    """The constitution in force and whether an amendment can be proposed (amendments.constitution_text);
    None when the polity cannot amend itself."""


def president_user_prompt(briefing: PresidentBriefing, memory: str) -> str:
    ctx = briefing.context
    term = f"Your term ends in {ctx.ticks_left} ticks" if ctx.ticks_left is not None else "Your term has no set end"
    again = "you cannot run again" if ctx.lame_duck else "you may run again"
    standing = [f"approval {briefing.approval:.2f}"]
    if ctx.legitimacy is not None:
        standing.append(f"legitimacy {ctx.legitimacy:.2f}")
    if ctx.street is not None:
        standing.append(f"street pressure {ctx.street:.2f}")
    standing.append(f"gap from your pledge {ctx.mandate_dev:.2f}")
    agenda = "The agenda is yours: you may propose a bill this tick." if briefing.agenda_closed is None else f"No bill this tick: {briefing.agenda_closed}."
    header = "issue | policy now | you state | you pledged | public median | assembly median"
    rows = [
        " | ".join((
            issue_label(d),
            _value(briefing.policy, d), f"{briefing.stated[d]:.2f}", f"{briefing.pledge[d]:.2f}",
            f"{briefing.public_median[d]:.2f}", _value(briefing.assembly_median, d),
        ))
        for d in range(len(ISSUES))
    ]
    year, quarter = divmod(briefing.tick, briefing.ticks_per_year)
    constitution = f"\n\n{briefing.constitution}" if briefing.constitution is not None else ""
    return (
        f"Tick {briefing.tick} (year {year}, quarter {quarter + 1}). {term}; {again}.\n"
        f"Your standing: {', '.join(standing)}.\n{agenda}\n\n"
        f"The issues (0 = the first pole, 1 = the second):\n{header}\n" + "\n".join(rows)
        + f"{constitution}\n\n{memory}\n\nYour turn."
    )


def nominee_system_prompt(nominee: Citizen, config: PolityConfig) -> str:
    """A presidential nominee's rules of the campaign and who they are -- stable for the
    election, so a prefix. As for the president: the rules, never what to do (C4)."""
    inst, campaign = config.institutions, config.campaign
    rules = [
        f"The president is elected by {inst.presidential_method.replace('_', ' ')} for {inst.president_term_years} years.",
        "Each citizen ranks the candidates by how close their platforms are to the citizen's own views, weighted "
        "by what the citizen cares about; a candidate of the citizen's own party counts for more; a citizen who "
        "finds no candidate close enough votes blank, and one who finds the choice indifferent may stay home.",
        f"You may campaign on a platform: name the position you take on up to {campaign.max_positioning_shifts} issues, "
        f"and your platform moves toward it by at most {campaign.max_positioning_delta:.2f} on each.",
        "If elected, your platform is your pledge: the gap between it and what you later say is public, and "
        "citizens judge you on it.",
    ]
    return (
        "You are playing a citizen of a simulated democracy, in the first person.\n\n"
        f"{persona(nominee)}\n\n"
        "You are your party's nominee for president. You want to win and to govern by your convictions; how you "
        "weigh the two is yours to decide.\n\nThe rules of the campaign:\n"
        + "\n".join(f"- {rule}" for rule in rules)
        + f"\n\n{_ANSWER_FORMAT} There is no agenda to set during a campaign: leave \"bill\" empty."
    )


@dataclass(frozen=True)
class NomineeBriefing:
    """What a nominee knows when they campaign: the field and where the voters stand."""

    tick: int
    field: tuple[tuple[int, int | None], ...]
    """(citizen_id, party) of every candidate."""
    poll: Mapping[int, float]
    """Each candidate's share of first choices."""
    blank: float
    abstain: float
    platform: tuple[float, ...]
    public_median: tuple[float, ...]


def nominee_user_prompt(nominee: Citizen, briefing: NomineeBriefing) -> str:
    candidates = [
        f"- {'you' if cid == nominee.citizen_id else f'citizen {cid}'} ({f'party {party}' if party is not None else 'no party'}): "
        f"{briefing.poll.get(cid, 0.0):.0%} of first choices"
        for cid, party in briefing.field
    ]
    rows = [
        f"{issue_label(d)} | {briefing.platform[d]:.2f} | {briefing.public_median[d]:.2f}" for d in range(len(ISSUES))
    ]
    return (
        f"Tick {briefing.tick}: the presidential election is held this tick, after the campaign.\n"
        f"The poll, before the campaign (voting blank {briefing.blank:.0%}, staying home {briefing.abstain:.0%}):\n"
        + "\n".join(candidates)
        + "\n\nThe issues (0 = the first pole, 1 = the second):\nissue | your platform | public median\n"
        + "\n".join(rows) + "\n\nYour turn."
    )


def _value(values: Sequence[float] | None, dimension: int) -> str:
    return "-" if values is None else f"{values[dimension]:.2f}"


def seat_weighted_median(parties: Sequence[Party], seats: Mapping[int, int]) -> tuple[float, ...]:
    """Each issue's median of the seated parties' platforms, a party counting once per seat."""
    seated = [(p.platform, seats[p.party_id]) for p in parties if seats.get(p.party_id, 0) > 0]
    half = sum(weight for _, weight in seated) / 2

    def median(dimension: int) -> float:
        ordered = sorted((platform[dimension], weight) for platform, weight in seated)
        running = accumulate(weight for _, weight in ordered)
        return next(value for (value, _), total in zip(ordered, running) if total >= half)

    return tuple(median(d) for d in range(len(seated[0][0])))


def validate_turn(turn: LeaderTurn, config: PolityConfig, *, max_positions: int, agenda_open: bool) -> None:
    """The bounds the schema cannot know. How far a target is does not matter -- the kernel
    takes the bounded step toward it -- and a bill offered while the agenda is closed is not
    an error: the kernel ignores it."""
    _check_targets(turn.positions, max_positions, "positions")
    if agenda_open:
        _check_targets(turn.bill, config.legislation.max_bill_dimensions, "bill")
    if isinstance(turn, AmendingLeaderTurn) and turn.amendment is not None:
        validate_amendment(turn.amendment, config)


def _check_targets(targets: Sequence[IssueTarget], max_targets: int, what: str) -> None:
    if len(targets) > max_targets:
        raise LlmResponseError(f"{what}: {len(targets)} issues, at most {max_targets}")
    dimensions = [t.dimension for t in targets]
    if len(set(dimensions)) != len(dimensions):
        raise LlmResponseError(f"{what}: the same issue twice")
    if any(d >= len(ISSUES) for d in dimensions):
        raise LlmResponseError(f"{what}: no issue {max(dimensions)}")


def steps_toward(targets: Sequence[IssueTarget], current: Sequence[float], max_step: float) -> list[PositionShift]:
    """The moves the kernel takes: toward each target by at most max_step, none where the
    value already stands within half the precision the agent is shown (it echoes shown values)."""
    steps = [(t.dimension, max(-max_step, min(max_step, t.target - current[t.dimension]))) for t in targets]
    return [PositionShift(dimension=d, delta=delta) for d, delta in steps if abs(delta) >= _SHOWN_PRECISION / 2]


def decode_one[T: BaseModel](raw: str, model: type[T]) -> list[T]:
    return _decode_batch(raw, model, decisions=_one, unit=_no_unit, unit_label="turns", expected_units=[0])


def _one[T](item: T) -> list[T]:
    return [item]


def _no_unit(item: object) -> int:
    return 0


@dataclass(frozen=True)
class TurnOutcome[T: BaseModel]:
    turn: T | None
    """None when every attempt failed: the caller keeps the agent silent."""
    sampling_varied: bool
    call_id: str | None


def decide[T: BaseModel](
    agent: Citizen, *, decision_type: str, system_prompt: str, user_prompt: str, json_schema: dict[str, Any],
    decode: Callable[[str], list[T]], config: PolityConfig, client: LlmClientProtocol,
) -> TurnOutcome[T]:
    """One agent's model call, retried like any decision; a call every attempt of which failed
    is an outcome with no turn."""
    retry_info: dict[str, Any] = {}
    unit_ids = [agent.citizen_id]
    try:
        [turn] = _complete_and_decode_with_replay(
            client,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=json_schema,
            max_tokens=_dynamic_max_tokens(
                client, config, system_prompt=system_prompt, user_prompt=user_prompt, chunk_size=1,
                flat_allowance=_profile(config).chamber_think_allowance, decision_type=decision_type, unit_ids=unit_ids,
            ),
            think=True,
            decode=decode,
            replays=config.llm.max_batch_replays,
            extra_body=thinking_budget_body(config, decision_type),
            decision_type=decision_type,
            unit_ids=unit_ids,
            retry_temperature=_RETRY_TEMPERATURE,
            retry_seed_base=_RETRY_SEED_BASE,
            retry_info=retry_info,
            temperature=config.agents.turn_temperature or None,
        )
    except LlmResponseError as exc:
        _logger.error("%s: exhausted every recovery attempt for cid %s, who keeps their position: %s",
                      decision_type, agent.citizen_id, exc)
        return TurnOutcome(turn=None, sampling_varied=False, call_id=retry_info.get("call_id"))
    return TurnOutcome(turn=turn, sampling_varied=bool(retry_info.get("sampling_varied")), call_id=retry_info.get("call_id"))


def decide_turn(
    agent: Citizen, *, decision_type: str, system_prompt: str, user_prompt: str, max_positions: int, agenda_open: bool,
    config: PolityConfig, client: LlmClientProtocol,
) -> TurnOutcome[LeaderTurn]:
    """A leader's turn. The president's may carry an amendment when the polity can amend itself."""
    amending = config.agents.amendments and decision_type == PRESIDENT_TURN
    model = AmendingLeaderTurn if amending else LeaderTurn
    return decide(
        agent, decision_type=decision_type, system_prompt=system_prompt, user_prompt=user_prompt,
        json_schema=AMENDING_LEADER_TURN_JSON_SCHEMA if amending else LEADER_TURN_JSON_SCHEMA, config=config, client=client,
        decode=lambda raw: _validated(
            decode_one(raw, model), lambda t: validate_turn(t, config, max_positions=max_positions, agenda_open=agenda_open),
        ),
    )


def moves_payload(moves: Sequence[PositionShift]) -> list[dict[str, Any]]:
    return [{"dimension": m.dimension, "delta": m.delta} for m in moves]


def turn_words(turn: LeaderTurn | None) -> dict[str, str]:
    """The turn's free text, cut to the lengths the prompt asks for (a longer answer is kept,
    not refused: the words are a record, not a move)."""
    if turn is None:
        return {"speech": "", "rationale": "", "note_to_self": "", "other_initiative": ""}
    return {
        "speech": turn.speech[:SPEECH_LIMIT], "rationale": turn.rationale[:RATIONALE_LIMIT],
        "note_to_self": turn.note_to_self[:NOTE_LIMIT], "other_initiative": turn.other_initiative[:INITIATIVE_LIMIT],
    }


# ── the chamber's vote on an amendment ────────────────────────────────────

_BALLOT_FORMAT = (
    "Answer with one JSON object in the schema given. \"rationale\" is your private reasoning "
    f"(at most {RATIONALE_LIMIT} characters). \"vote\" is \"yes\" or \"no\". \"statement\" is what you say in "
    f"public (at most {SPEECH_LIMIT} characters), \"note_to_self\" what you want to remember (at most {NOTE_LIMIT})."
)


def ballot_system_prompt(member: Citizen, config: PolityConfig) -> str:
    """A chamber member's rules and who they are -- stable for the run, so a prefix. It says
    what the vote decides and never how to vote (C4)."""
    chamber = config.sortition_chamber
    return (
        "You are playing a citizen of a simulated democracy, in the first person.\n\n"
        f"{persona(member)}\n\n"
        f"You sit in the citizens' chamber: {chamber.seats} citizens drawn by lot, for {chamber.term_years} "
        "year(s). When the president proposes an amendment to the constitution, each member votes yes or no, "
        "for themselves: how you weigh your own convictions, your party and the public good is yours to decide. "
        "A member who does not vote counts against.\n\n"
        f"The articles of the constitution:\n{articles_text(config)}\n\n{_BALLOT_FORMAT}"
    )


def ballot_user_prompt(proposal: Proposal, *, tick: int, old: Any, members: int, memory: str) -> str:
    return (
        f"Tick {tick}. The president (citizen {proposal.proposer}) proposed at tick {proposal.tick} to change "
        f"{proposal.article} -- {ARTICLES[proposal.article].summary} -- from {value_text(old)} to "
        f"{value_text(proposal.value)}.\nTheir reason: \"{proposal.reason}\"\n"
        f"It is ratified if more than {proposal.threshold:.0%} of the {members} members vote yes.\n\n"
        f"{memory}\n\nYour vote."
    )


def decide_ballot(
    member: Citizen, *, system_prompt: str, user_prompt: str, config: PolityConfig, client: LlmClientProtocol,
) -> TurnOutcome[AmendmentBallot]:
    return decide(
        member, decision_type=AMENDMENT_VOTE, system_prompt=system_prompt, user_prompt=user_prompt,
        json_schema=AMENDMENT_BALLOT_JSON_SCHEMA, config=config, client=client,
        decode=lambda raw: decode_one(raw, AmendmentBallot),
    )


def ballot_words(ballot: AmendmentBallot | None) -> dict[str, str]:
    if ballot is None:
        return {"statement": "", "rationale": "", "note_to_self": ""}
    return {"statement": ballot.statement[:SPEECH_LIMIT], "rationale": ballot.rationale[:RATIONALE_LIMIT], "note_to_self": ballot.note_to_self[:NOTE_LIMIT]}


# ── the forum ─────────────────────────────────────────────────────────────

def forum_system_prompt(citizen: Citizen, config: PolityConfig) -> str:
    """A forum participant's rules and who they are -- stable for the run, so a prefix."""
    return (
        "You are playing a citizen of a simulated democracy, in the first person.\n\n"
        f"{persona(citizen)}\n\n"
        "Each tick you may say one thing on the public forum, or keep silent. You read what your neighbours, "
        "the president and, if you sit in the citizens' chamber, the other members posted. What you say and "
        "whether you say anything is yours to decide.\n\n"
        "Answer with one JSON object in the schema given. \"rationale\" is your private reasoning "
        f"(at most {RATIONALE_LIMIT} characters). \"post\" is your message (at most {SPEECH_LIMIT} characters); "
        f"leave it empty to keep silent. \"note_to_self\" is what you want to remember (at most {NOTE_LIMIT})."
        + (
            " If what you read has genuinely changed your mind on one issue, give its number as \"shift_issue\" and the "
            "pole you moved toward as \"shift_direction\" (\"low\" or \"high\"); otherwise -1 and \"none\". Do not move "
            "for the sake of it: most turns change nothing."
            if config.agents.stance_step > 0 else " Set \"shift_issue\" to -1 and \"shift_direction\" to \"none\"."
        )
    )


def forum_user_prompt(*, tick: int, member: bool, feed: str, memory: str) -> str:
    seat = " You sit in the citizens' chamber." if member else ""
    return f"Tick {tick}.{seat}\n\n{feed}\n\n{memory}\n\nYour turn."


def decide_forum(
    citizen: Citizen, *, system_prompt: str, user_prompt: str, config: PolityConfig, client: LlmClientProtocol,
) -> TurnOutcome[ForumTurn]:
    return decide(
        citizen, decision_type=FORUM_POST, system_prompt=system_prompt, user_prompt=user_prompt,
        json_schema=FORUM_TURN_JSON_SCHEMA, config=config, client=client, decode=lambda raw: decode_one(raw, ForumTurn),
    )


def forum_words(turn: ForumTurn | None) -> dict[str, str]:
    if turn is None:
        return {"post": "", "rationale": "", "note_to_self": ""}
    return {"post": turn.post[:SPEECH_LIMIT], "rationale": turn.rationale[:RATIONALE_LIMIT], "note_to_self": turn.note_to_self[:NOTE_LIMIT]}


# ── coalition talks between party leaders (ADR-019) ───────────────────────

def party_leader(party_id: int, citizens: Sequence[Citizen], taken: Collection[int] = ()) -> Citizen:
    """The party's most ambitious member (the lowest id on a tie), never one of `taken`; a party
    with no member is led by the most ambitious citizen."""
    members = [c for c in citizens if c.party_affiliation == party_id]
    return max((c for c in members or citizens if c.citizen_id not in taken), key=lambda c: (c.ambition_score, -c.citizen_id))


def coalition_system_prompt(leader: Citizen, party_id: int, config: PolityConfig) -> str:
    """The talks' rules and who the leader is -- stable for the run, so a prefix."""
    return (
        "You are playing a citizen of a simulated democracy, in the first person.\n\n"
        f"{persona(leader)}\n\n"
        f"You lead party {party_id}, which won seats in the new assembly. The leader of the largest party, the "
        f"formateur, is trying to form a government: a coalition holding more than {config.parties.coalition_majority_ratio:.0%} "
        "of the seats. Each round you answer the formateur, join the coalition or not, and tell the other leaders what you "
        f"think. You may change your answer from one round to the next. The talks end when no leader changes their answer, or "
        f"after {config.parties.coalition_max_negotiation_rounds} rounds. Without a majority there is no government. What is best "
        "for your party, your convictions and you is yours to decide.\n\n"
        "Answer with one JSON object in the schema given. \"rationale\" is your private reasoning "
        f"(at most {RATIONALE_LIMIT} characters). \"join\" is \"yes\" or \"no\". \"statement\" is what you say to the other "
        f"leaders (at most {SPEECH_LIMIT} characters). \"note_to_self\" is what you want to remember (at most {NOTE_LIMIT})."
    )


def _platform_gap(mine: Sequence[float], theirs: Sequence[float]) -> str:
    far = sorted(range(len(ISSUES)), key=lambda d: (-abs(mine[d] - theirs[d]), d))[:GAP_ISSUES]
    return "; ".join(f"{ISSUES[d].name} (you {lean(d, mine[d])}, they {lean(d, theirs[d])})" for d in far)


def coalition_user_prompt(
    *, tick: int, party_id: int, initiator: int, platforms: Mapping[int, Sequence[float]], seats: Mapping[int, int],
    threshold: float, round_number: int, provisional: int | None, others: str, memory: str,
) -> str:
    lines = [
        f"Tick {tick}, round {round_number}. The assembly has {sum(seats.values())} seats; a coalition needs more than "
        f"{threshold:.1f}. Your party holds {seats[party_id]}.",
        f"The formateur leads party {initiator}, with {seats[initiator]} seats. Where its platform differs most from yours: "
        f"{_platform_gap(platforms[party_id], platforms[initiator])}.",
    ]
    if provisional is not None:
        lines.append(f"The coalition now stands at {provisional} seats. The other leaders said:\n{others}")
    return "\n\n".join([*lines, memory, "Your turn."])


def decide_coalition_turn(
    leader: Citizen, *, system_prompt: str, user_prompt: str, config: PolityConfig, client: LlmClientProtocol,
) -> TurnOutcome[LeaderCoalitionTurn]:
    return decide(
        leader, decision_type=COALITION_TURN, system_prompt=system_prompt, user_prompt=user_prompt,
        json_schema=LEADER_COALITION_TURN_JSON_SCHEMA, config=config, client=client,
        decode=lambda raw: decode_one(raw, LeaderCoalitionTurn),
    )


def coalition_words(turn: LeaderCoalitionTurn | None) -> dict[str, str]:
    if turn is None:
        return {"statement": "", "rationale": "", "note_to_self": ""}
    return {"statement": turn.statement[:SPEECH_LIMIT], "rationale": turn.rationale[:RATIONALE_LIMIT], "note_to_self": turn.note_to_self[:NOTE_LIMIT]}


@dataclass(frozen=True)
class LeaderAnswer:
    """What one leader said in one round, for the journal: the decision itself is a CoalitionDecision."""

    leader: int
    words: dict[str, str]
    fallback: bool
    sampling_varied: bool
    call_id: str | None


def _pick_leaders(responders: Sequence[int], citizens: Sequence[Citizen]) -> dict[int, Citizen]:
    leaders: dict[int, Citizen] = {}
    for pid in responders:
        leaders[pid] = party_leader(pid, citizens, {leader.citizen_id for leader in leaders.values()})
    return leaders


def _others_said(
    pid: int, responders: Sequence[int], prior: dict[int, CoalitionDecision] | None, seats: dict[int, int], said: dict[int, str],
) -> str:
    if prior is None:
        return ""
    return "\n".join(
        f"- party {q} ({seats[q]} seats): {'join' if prior[q].action == CoalitionAction.JOIN.value else 'decline'}, \"{said[q]}\""
        for q in responders if q != pid
    )


def _leader_decision(pid: int, turn: LeaderCoalitionTurn | None, prior: dict[int, CoalitionDecision] | None) -> CoalitionDecision:
    """The leader's answer, or the previous one (declining in round 1) when they never answered."""
    if turn is not None:
        action = CoalitionAction.JOIN if turn.join == "yes" else CoalitionAction.LEAVE
    else:
        action = CoalitionAction(prior[pid].action) if prior is not None else CoalitionAction.LEAVE
    motif = CoalitionMotif.IDEOLOGICAL_PROXIMITY if action == CoalitionAction.JOIN else CoalitionMotif.IDEOLOGICAL_DISTANCE_TOO_HIGH
    return CoalitionDecision(party_id=pid, action=action.value, motif=motif.value)


def negotiate_leaders(
    client: LlmClientProtocol, responders: Sequence[int], initiator: int, party_platforms: dict[int, tuple[float, ...]],
    seats: dict[int, int], votes: dict[int, float], total_seats: int, threshold: float, config: PolityConfig,
    *, citizens: Sequence[Citizen], memory: AgentMemory, tick: int, answers: dict[tuple[int, int], LeaderAnswer],
) -> tuple[list[list[CoalitionDecision]], int | None, list[bool], list[str | None]]:
    """`decide_coalition`'s round loop with the parties' leaders in place of the crowd batch: each
    round every responding leader takes a turn of their own, in parallel, none seeing another's
    answer of the same round. It stops on the crowd's own rule (`_negotiation_converged`) or the
    round cap. A leader who never answers keeps their previous answer, or declines in round 1.
    `answers[(round, party_id)]` receives each leader's words for the journal."""
    leaders = _pick_leaders(responders, citizens)
    party_of = {leader.citizen_id: pid for pid, leader in leaders.items()}
    rounds: list[list[CoalitionDecision]] = []
    varied: list[bool] = []
    prior: dict[int, CoalitionDecision] | None = None
    provisional: int | None = None
    said: dict[int, str] = {}
    round_number = 0

    def answer(chunk: list[Citizen]) -> TurnOutcome[LeaderCoalitionTurn]:
        [leader] = chunk
        pid = party_of[leader.citizen_id]
        return decide_coalition_turn(
            leader, system_prompt=coalition_system_prompt(leader, pid, config), config=config, client=client,
            user_prompt=coalition_user_prompt(
                tick=tick, party_id=pid, initiator=initiator, platforms=party_platforms, seats=seats, threshold=threshold,
                round_number=round_number, provisional=provisional, memory=memory.recall(leader.citizen_id),
                others=_others_said(pid, responders, prior, seats, said),
            ),
        )

    while True:
        round_number += 1
        outcomes = run_chunks([[leaders[pid]] for pid in responders], answer, config.parallel.intra_run_workers)
        decisions = []
        for pid, outcome in zip(responders, outcomes):
            decisions.append(_leader_decision(pid, outcome.turn, prior))
            answers[(round_number, pid)] = LeaderAnswer(
                leaders[pid].citizen_id, coalition_words(outcome.turn), outcome.turn is None, outcome.sampling_varied, outcome.call_id,
            )
            said[pid] = answers[(round_number, pid)].words["statement"]
        rounds.append(decisions)
        varied.append(any(answers[(round_number, pid)].sampling_varied for pid in responders))
        current = {d.party_id: d for d in decisions}
        if _negotiation_converged(prior, current, responders) or round_number >= config.parties.coalition_max_negotiation_rounds:
            return rounds, None, varied, [None] * len(rounds)
        prior, provisional = current, _provisional_coalition_seats(current, initiator, seats)
