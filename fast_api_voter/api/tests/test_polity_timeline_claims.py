"""Checkable narratives and story skeletons (S5.3). See api/domain/polity/timeline_claims.py."""
from __future__ import annotations

from typing import Any

import pytest

from api.domain.polity.events import INSTITUTIONAL_EVENT_TYPES
from api.domain.polity.run_digest import institutional_timeline
from api.domain.polity.timeline_claims import (
    Anchor,
    check_anchor,
    check_timeline,
    group_by_skeleton,
    parse_anchors,
    read_events_by_id,
    story_skeleton,
)

EVENTS: dict[int, dict[str, Any]] = {
    12: {"event_id": 12, "tick": 0, "event_type": "elected", "citizen_id": 459, "payload": {"office": "president", "forced": 0}},
    21: {"event_id": 21, "tick": 4, "event_type": "petition_expired", "citizen_id": 459,
         "payload": {"signatures": 56, "signed_ratio": 0.112, "office": "president"}},
    30: {"event_id": 30, "tick": 17, "event_type": "recalled", "citizen_id": 3,
         "payload": {"legitimacy": 0.08879, "trigger": "legitimacy_floor", "retained": False, "note": None}},
    31: {"event_id": 31, "tick": 17, "event_type": "pressure_action", "citizen_id": 8, "payload": {"act": 0}},
}


def test_anchors_are_parsed_with_their_line_and_every_kind_of_term() -> None:
    markdown = "Intro line.\nElected [e12: elected t0 c459] and later [e21] and [e30: t17 legitimacy=0.089 zz]."
    assert parse_anchors(markdown) == [
        Anchor(event_id=12, line=2, event_type="elected", tick=0, citizen_id=459),
        Anchor(event_id=21, line=2),
        Anchor(event_id=30, line=2, tick=17, payload={"legitimacy": "0.089"}, unparsed=("zz",)),
    ]


@pytest.mark.parametrize(
    ("markdown", "problems"),
    [
        ("[e12: elected t0 c459]", []),
        ("[e21: petition_expired signatures=56 signed_ratio=0.112]", []),
        ("[e30: recalled legitimacy=0.089 trigger=legitimacy_floor retained=false note=null]", []),
        ("[e99]", ["line 1 [e99]: no event 99 in the journal"]),
        ("[e12: recalled t4 c3]", [
            "line 1 [e12]: event_type is 'elected', not 'recalled'",
            "line 1 [e12]: tick is 0, not 4",
            "line 1 [e12]: citizen_id is 459, not 3",
        ]),
        ("[e21: signatures=65 quorum=3]", [
            "line 1 [e21]: payload signatures is 56, not 65",
            "line 1 [e21]: payload has no 'quorum'",
        ]),
        ("[e30: legitimacy=0.09 trigger=confidence_vote]", [
            "line 1 [e30]: payload legitimacy is 0.08879, not 0.09",
            "line 1 [e30]: payload trigger is 'legitimacy_floor', not confidence_vote",
        ]),
        ("[e21: signatures=many]", ["line 1 [e21]: payload signatures is 56, not many"]),
        ("[e12: elected mayor]", ["line 1 [e12]: unrecognised term 'mayor'"]),
    ],
)
def test_check_anchor_reports_exactly_what_the_journal_contradicts(markdown: str, problems: list[str]) -> None:
    [anchor] = parse_anchors(markdown)
    assert check_anchor(anchor, EVENTS) == problems


def test_check_timeline_counts_anchors_and_institutional_coverage() -> None:
    report = check_timeline("[e12: elected] then [e31] then [e30: t16]", EVENTS, INSTITUTIONAL_EVENT_TYPES)
    assert (report.anchors, report.institutional_events, report.institutional_anchored) == (3, 3, 2)
    assert report.problems == ["line 1 [e30]: tick is 17, not 16"]


def test_read_events_by_id_indexes_a_journal(tmp_path: Any) -> None:
    journal = tmp_path / "events.jsonl"
    journal.write_text('{"event_id": 0, "tick": 0}\n\n{"event_id": 1, "tick": 2}\n', encoding="utf-8")
    assert sorted(read_events_by_id(journal)) == [0, 1]


def test_the_digest_timeline_carries_event_ids_to_anchor_to() -> None:
    assert [entry["event_id"] for entry in institutional_timeline(list(EVENTS.values()))] == [12, 21, 30]


def _event(event_type: str, **payload: Any) -> dict[str, Any]:
    return {"event_type": event_type, "payload": payload}


def test_story_skeletons_keep_the_institutional_arc_at_two_grains() -> None:
    events = [
        _event("elected"), _event("pressure_action"), _event("confidence_vote_triggered"),
        _event("confidence_vote_result", retained=True), _event("recalled", trigger="legitimacy_floor"),
        _event("snap_election_triggered"), _event("election_no_winner"), _event("coalition_failed"),
        _event("confidence_vote_result", retained=False),
    ]
    assert story_skeleton(events) == (
        "elected", "confidence_vote_triggered", "confidence_vote:retained", "recalled:legitimacy_floor",
        "snap_election_triggered", "election_no_winner", "coalition_failed", "confidence_vote:lost",
    )
    assert story_skeleton(events, grain="terms") == ("elected", "recalled:legitimacy_floor", "election_no_winner")
    with pytest.raises(ValueError, match="unknown skeleton grain"):
        story_skeleton(events, grain="years")


def test_runs_are_grouped_by_skeleton_largest_group_first() -> None:
    groups = group_by_skeleton({
        "seed3": ("elected", "recalled:legitimacy_floor"), "seed1": ("elected", "elected"),
        "seed2": ("elected", "elected"), "seed4": ("elected",),
    })
    assert groups == [
        (("elected", "elected"), ["seed1", "seed2"]),
        (("elected",), ["seed4"]),
        (("elected", "recalled:legitimacy_floor"), ["seed3"]),
    ]
