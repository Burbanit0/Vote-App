"""Checkable narratives (S5.3): TIMELINE.md claims anchored to journal events, and a
mechanical check of those anchors against events.jsonl.

A run narrative is written by a model from the digest, and the narrator's rule "never
state a number that is not in the digest" was, until this, enforced by nobody. An anchor
turns a sentence's factual core into something a script can check:

    Citizen 3 was elected at tick 16 [e2204: elected t16 c3].
    The petition expired with 56 signatures [e1180: petition_expired t4 signatures=56].

`[e<event_id>]` alone asserts the event exists. After a colon, in any order: an event
type, `t<tick>`, `c<citizen_id>`, and `key=value` for payload values (numbers compare
with a 0.001 tolerance, so a narrative can round to three decimals). The prose around an
anchor is not checked -- only what the anchor states.

Story skeletons put a run's institutional arc -- elections, term endings, recalls,
coalitions, petitions reaching a vote -- into one comparable string, so runs of a sweep
can be grouped by the story they tell rather than read one by one.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from api.domain.polity.events import ALL_EVENT_TYPES

_ANCHOR_RE = re.compile(r"\[e(\d+)(?::([^\]]*))?\]")
_FLOAT_TOLERANCE = 1e-3


@dataclass(frozen=True)
class Anchor:
    event_id: int
    line: int
    event_type: str | None = None
    tick: int | None = None
    citizen_id: int | None = None
    payload: dict[str, str] = field(default_factory=dict)
    unparsed: tuple[str, ...] = ()


def _parse_term(term: str, fields: dict[str, Any]) -> bool:
    """Fill `fields` from one anchor term; False when the term means nothing."""
    if term in ALL_EVENT_TYPES:
        fields["event_type"] = term
    elif re.fullmatch(r"t\d+", term):
        fields["tick"] = int(term[1:])
    elif re.fullmatch(r"c\d+", term):
        fields["citizen_id"] = int(term[1:])
    elif re.fullmatch(r"[a-z_]+=\S+", term):
        key, value = term.split("=", 1)
        fields["payload"][key] = value
    else:
        return False
    return True


def parse_anchors(markdown: str) -> list[Anchor]:
    anchors = []
    for line_number, line in enumerate(markdown.splitlines(), start=1):
        for match in _ANCHOR_RE.finditer(line):
            fields: dict[str, Any] = {"payload": {}}
            unparsed = [term for term in (match.group(2) or "").split() if not _parse_term(term, fields)]
            anchors.append(Anchor(event_id=int(match.group(1)), line=line_number, unparsed=tuple(unparsed), **fields))
    return anchors


def _value_matches(stated: str, actual: Any) -> bool:
    if isinstance(actual, bool) or actual is None:
        return stated.lower() == str(actual).lower() or (actual is None and stated == "null")
    if isinstance(actual, (int, float)):
        try:
            return abs(float(stated) - float(actual)) <= _FLOAT_TOLERANCE
        except ValueError:
            return False
    return stated == str(actual)


def check_anchor(anchor: Anchor, events_by_id: Mapping[int, Mapping[str, Any]]) -> list[str]:
    """What the journal contradicts in one anchor; empty when it holds."""
    where = f"line {anchor.line} [e{anchor.event_id}]"
    event = events_by_id.get(anchor.event_id)
    if event is None:
        return [f"{where}: no event {anchor.event_id} in the journal"]
    problems = [f"{where}: unrecognised term {term!r}" for term in anchor.unparsed]
    for name, stated in (("event_type", anchor.event_type), ("tick", anchor.tick), ("citizen_id", anchor.citizen_id)):
        if stated is not None and event.get(name) != stated:
            problems.append(f"{where}: {name} is {event.get(name)!r}, not {stated!r}")
    payload = event.get("payload") or {}
    for key, stated_value in anchor.payload.items():
        if key not in payload:
            problems.append(f"{where}: payload has no {key!r}")
        elif not _value_matches(stated_value, payload[key]):
            problems.append(f"{where}: payload {key} is {payload[key]!r}, not {stated_value}")
    return problems


def read_events_by_id(journal: Path) -> dict[int, dict[str, Any]]:
    events: dict[int, dict[str, Any]] = {}
    with journal.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                event = json.loads(line)
                events[int(event["event_id"])] = event
    return events


@dataclass(frozen=True)
class ClaimReport:
    anchors: int
    problems: list[str]
    institutional_events: int
    institutional_anchored: int


def check_timeline(markdown: str, events_by_id: Mapping[int, Mapping[str, Any]], institutional: Iterable[str]) -> ClaimReport:
    """Every anchor checked, plus how much of the run's institutional record the
    narrative anchors -- a story that anchors nothing passes vacuously, and says so."""
    anchors = parse_anchors(markdown)
    institutional_types = set(institutional)
    institutional_ids = {eid for eid, e in events_by_id.items() if e.get("event_type") in institutional_types}
    return ClaimReport(
        anchors=len(anchors),
        problems=[problem for anchor in anchors for problem in check_anchor(anchor, events_by_id)],
        institutional_events=len(institutional_ids),
        institutional_anchored=len(institutional_ids & {a.event_id for a in anchors}),
    )


# ── story skeletons ───────────────────────────────────────────────────────

def _skeleton_token(event: Mapping[str, Any]) -> str | None:
    event_type = event.get("event_type")
    payload = event.get("payload") or {}
    if event_type == "recalled":
        return f"recalled:{payload.get('trigger')}"
    if event_type == "confidence_vote_result":
        return "confidence_vote:" + ("retained" if payload.get("retained") else "lost")
    if event_type in ("elected", "election_no_winner", "election_invalidated", "snap_election_triggered",
                      "coalition_formed", "coalition_failed", "confidence_vote_triggered"):
        return str(event_type)
    return None


_TERM_TOKENS = ("elected", "election_no_winner", "recalled:")


def story_skeleton(events: Iterable[Mapping[str, Any]], *, grain: str = "full") -> tuple[str, ...]:
    """The institutional arc, in journal order, with no ticks or ids: two runs whose
    elections, recalls, confidence votes and coalitions came in the same sequence tell
    the same story at this grain, whatever the timing.

    `grain="terms"` keeps only who took and lost office -- elections and recalls -- so
    runs that differ only in how many confidence votes a president survived group
    together."""
    tokens = [token for event in events if (token := _skeleton_token(event)) is not None]
    if grain == "terms":
        tokens = [token for token in tokens if token.startswith(_TERM_TOKENS)]
    elif grain != "full":
        raise ValueError(f"unknown skeleton grain {grain!r} (full, terms)")
    return tuple(tokens)


def group_by_skeleton(skeletons: Mapping[str, Sequence[str]]) -> list[tuple[tuple[str, ...], list[str]]]:
    """Runs sharing a skeleton, largest group first (ties by skeleton)."""
    groups: dict[tuple[str, ...], list[str]] = {}
    for run_id, skeleton in sorted(skeletons.items()):
        groups.setdefault(tuple(skeleton), []).append(run_id)
    return sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))
