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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import accumulate
from pathlib import Path
from typing import Any, NamedTuple

from api.domain.polity.citizen import Citizen
from api.domain.polity.config import ISSUE_COUNT_NAMED, PolityConfig
from api.domain.polity.events import INSTITUTIONAL_EVENT_TYPES
from api.domain.polity.journal import JournalEvent
from api.domain.polity.llm_behavior_engine import (
    ResponseContext,
    _complete_and_decode_with_replay,
    _dynamic_max_tokens,
    _profile,
    _validated,
    thinking_budget_body,
)
from api.domain.polity.llm_client import LlmClientProtocol, LlmResponseError, _decode_batch
from api.domain.polity.llm_schemas import LEADER_TURN_JSON_SCHEMA, IssueTarget, LeaderTurn, PositionShift
from api.domain.polity.parties import Party

_logger = logging.getLogger(__name__)

PRESIDENT_TURN = "president_turn"
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
_OWN_EVENT_TYPES = frozenset({"agent_turn", "legitimacy_updated"})


class AgentMemory:
    """What agents remember: a view over the journal, fed by Journal.tap as events are
    written and rebuilt from events.jsonl on resume -- never checkpointed. The public
    record is the last institutional events anyone could know of; an agent's own record is
    their last turns and standings."""

    def __init__(self, public_window: int = 16, own_window: int = 8) -> None:
        self.public: deque[JournalEvent] = deque(maxlen=public_window)
        self.own: defaultdict[int, deque[JournalEvent]] = defaultdict(lambda: deque(maxlen=own_window))

    def observe(self, event: JournalEvent) -> None:
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
    bill = f"; bill {_moves(payload['bill'])}" if payload["bill"] else ""
    return (
        f"- t{event.tick} you said: \"{payload['speech']}\"; you moved {_moves(payload['shifts']) or 'nothing'}{bill}; "
        f"note to self: \"{payload['note_to_self']}\""
    )


def _moves(moves: Sequence[Mapping[str, Any]]) -> str:
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
    return (
        f"Tick {briefing.tick} (year {year}, quarter {quarter + 1}). {term}; {again}.\n"
        f"Your standing: {', '.join(standing)}.\n{agenda}\n\n"
        f"The issues (0 = the first pole, 1 = the second):\n{header}\n" + "\n".join(rows)
        + f"\n\n{memory}\n\nYour turn."
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


def validate_turn(turn: LeaderTurn, config: PolityConfig, *, agenda_open: bool) -> None:
    """The bounds the schema cannot know. How far a target is does not matter -- the kernel
    takes the bounded step toward it -- and a bill offered while the agenda is closed is not
    an error: the kernel ignores it."""
    _check_targets(turn.positions, config.mandate.max_response_shifts, "positions")
    if agenda_open:
        _check_targets(turn.bill, config.legislation.max_bill_dimensions, "bill")


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


def decode_turn(raw: str) -> list[LeaderTurn]:
    return _decode_batch(raw, LeaderTurn, decisions=_one, unit=_no_unit, unit_label="turns", expected_units=[0])


def _one(turn: LeaderTurn) -> list[LeaderTurn]:
    return [turn]


def _no_unit(turn: LeaderTurn) -> int:
    return 0


@dataclass(frozen=True)
class TurnOutcome:
    turn: LeaderTurn | None
    """None when every attempt failed: the caller keeps the president silent."""
    sampling_varied: bool
    call_id: str | None


def decide_turn(
    agent: Citizen, *, system_prompt: str, user_prompt: str, agenda_open: bool,
    config: PolityConfig, client: LlmClientProtocol,
) -> TurnOutcome:
    retry_info: dict[str, Any] = {}
    unit_ids = [agent.citizen_id]
    try:
        [turn] = _complete_and_decode_with_replay(
            client,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema=LEADER_TURN_JSON_SCHEMA,
            max_tokens=_dynamic_max_tokens(
                client, config, system_prompt=system_prompt, user_prompt=user_prompt, chunk_size=1,
                flat_allowance=_profile(config).chamber_think_allowance, decision_type=PRESIDENT_TURN, unit_ids=unit_ids,
            ),
            think=True,
            decode=lambda raw: _validated(decode_turn(raw), lambda t: validate_turn(t, config, agenda_open=agenda_open)),
            replays=config.llm.max_batch_replays,
            extra_body=thinking_budget_body(config, PRESIDENT_TURN),
            decision_type=PRESIDENT_TURN,
            unit_ids=unit_ids,
            retry_temperature=_RETRY_TEMPERATURE,
            retry_seed_base=_RETRY_SEED_BASE,
            retry_info=retry_info,
        )
    except LlmResponseError as exc:
        _logger.error("%s: exhausted every recovery attempt for cid %s, the president stays silent: %s",
                      PRESIDENT_TURN, agent.citizen_id, exc)
        return TurnOutcome(turn=None, sampling_varied=False, call_id=retry_info.get("call_id"))
    return TurnOutcome(turn=turn, sampling_varied=bool(retry_info.get("sampling_varied")), call_id=retry_info.get("call_id"))


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
