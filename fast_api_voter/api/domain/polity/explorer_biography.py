"""One citizen's story for the run explorer's biography panel, built on
run_explorer.citizen_biography's reading of who took part in an event: what they did,
sorted into roles, candidacies, votes, pressure acts and petitions, each entry with its
motif decoded and the model's rationale cut short.

What others did about a citizen is counted per tick rather than listed: a president of a
population of 500 is the target of thousands of pressure acts, signatures and reactions to
their scandals, and is named on every ballot that ranks them; the panel needs how much came
when, not each one.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal

from api.domain.polity.codebook import motif_labels
from api.domain.polity.run_explorer import RunView, citizen_census, citizen_events
from api.domain.polity.run_macro import Scalar

RATIONALE_LIMIT = 280
Section = Literal["roles", "candidacies", "votes", "pressure_acts", "petitions", "other"]
SECTIONS: tuple[Section, ...] = ("roles", "candidacies", "votes", "pressure_acts", "petitions", "other")

_SECTION_OF: Mapping[str, Section] = {
    **dict.fromkeys(("elected", "recalled", "mandate_pledge_declared", "representative_response", "legitimacy_updated",
                     "mandate_deviation_recorded", "sortition_rotation", "chamber_deliberation"), "roles"),
    **dict.fromkeys(("candidacy_considered", "candidacy_declared", "nomination_lost", "party_nomination_choice",
                     "campaign_positioning", "election_invalidated"), "candidacies"),
    "vote_cast": "votes",
    "pressure_action": "pressure_acts",
    **dict.fromkeys(("petition_launched", "petition_signed", "petition_expired", "confidence_vote_triggered",
                     "confidence_vote_result"), "petitions"),
}
_RECEIVED_AS = {"pressure_action": "target", "petition_signed": "target", "reaction_to_event": "target", "vote_cast": "listed"}


@dataclass(frozen=True)
class BiographyEntry:
    tick: int
    event_type: str
    role: str
    """"actor", "target" or "listed" (run_explorer's reading)"""
    motif: int | None
    motif_label: str | None
    rationale: str | None
    details: Mapping[str, Scalar]


@dataclass(frozen=True)
class Received:
    tick: int
    event_type: str
    code: int | None
    """The pressure act, the rank the ballots gave this citizen (0 = first choice), or the exogenous
    event reacted to (1 scandal, 2 economic shock); None for a signature."""
    count: int


@dataclass(frozen=True)
class CensusYear:
    year: int
    role: str
    office: str
    party: int | None


@dataclass(frozen=True)
class Biography:
    citizen_id: int
    sections: Mapping[Section, tuple[BiographyEntry, ...]]
    received: tuple[Received, ...]
    census: tuple[CensusYear, ...]


@lru_cache(maxsize=1)
def _labels() -> dict[int, str]:
    return motif_labels()


def _motif(value: Any) -> tuple[int | None, str | None]:
    try:
        code = int(value)
    except (TypeError, ValueError):
        return None, None
    return code, _labels().get(code)


def _rationale(text: Any) -> str | None:
    if not isinstance(text, str) or not text:
        return None
    return text if len(text) <= RATIONALE_LIMIT else text[: RATIONALE_LIMIT - 1].rstrip() + "…"


def _entry(event: Mapping[str, Any], role: str) -> BiographyEntry:
    motif, label = _motif(event.get("motif"))
    payload = event.get("payload") or {}
    return BiographyEntry(
        tick=int(event["tick"]), event_type=str(event["event_type"]), role=role, motif=motif, motif_label=label,
        rationale=_rationale(event.get("rationale")),
        details={k: v for k, v in sorted(payload.items()) if isinstance(v, int | float | str | bool) or v is None},
    )


def _received_code(event: Mapping[str, Any], citizen_id: int) -> int | None:
    payload = event.get("payload") or {}
    if event["event_type"] == "vote_cast":
        return list(payload["ranking"]).index(citizen_id)
    code = payload.get("event_type") if event["event_type"] == "reaction_to_event" else payload.get("act")
    return int(code) if code is not None else None


def build_biography(view: RunView, citizen_id: int) -> Biography:
    sections: dict[Section, list[BiographyEntry]] = {section: [] for section in SECTIONS}
    received: Counter[tuple[int, str, int | None]] = Counter()
    for event, role in citizen_events(view, citizen_id):
        event_type = str(event["event_type"])
        if _RECEIVED_AS.get(event_type) == role:
            received[(int(event["tick"]), event_type, _received_code(event, citizen_id))] += 1
            continue
        sections[_SECTION_OF.get(event_type, "other")].append(_entry(event, role))
    return Biography(
        citizen_id=citizen_id,
        sections={section: tuple(entries) for section, entries in sections.items()},
        received=tuple(Received(tick=t, event_type=kind, code=code, count=n) for (t, kind, code), n in sorted(
            received.items(), key=lambda item: (item[0][0], item[0][1], -1 if item[0][2] is None else item[0][2]))),
        census=tuple(
            CensusYear(year=int(row["year"]), role=str(row["role"]), office=str(row["office"]), party=row["party_affiliation"])
            for row in citizen_census(view, citizen_id)
        ),
    )
