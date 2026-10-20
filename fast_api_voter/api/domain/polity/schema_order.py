"""Which order each decision's fields are sent in (ADR-030): the candidates, and the rule that picks one.

The model writes an object's fields in the order the schema sends them, and that order changes its answers
(EXP-025: `motif` first made every consulted citizen act). So the order is measured, not reasoned about:
`scripts/check_schema_order.py` runs every candidate on the order bank, and `bakeoff_order.decide` applies a
rule written before any run to the sessions. Its verdict is what `llm_client.WIRE_ORDER` may hold.
"""
from __future__ import annotations

import itertools

DECISION_SLOTS: dict[str, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
    # class title: (who it is about, the decision, what hangs on the decision); `motif` is the fourth slot
    "VoteCastDecision": (("cid",), ("blank",), ("ranking",)),
    "CandidacyDecision": (("cid",), ("outcome",), ()),
    "PartyNominationDecision": (("party_id",), ("winner_position",), ()),
    "PositioningDecision": (("cid",), ("shifts",), ()),
    "ResponseDecision": (("cid",), ("stance",), ("shifts",)),
    "PressureDecision": (("cid",), ("act",), ("target",)),
    "ReactionDecision": (("cid",), ("salience_delta",), ()),
    "ChamberDecision": (("cid",), ("shifts",), ()),
    "CoalitionDecision": (("party_id",), ("action",), ()),
}
"""Every batch decision class, its fields split into slots. A test checks it names each class's fields
exactly, so a field added to a decision fails there instead of landing at the tail unmeasured."""

DECISION_TYPES: dict[str, str] = {
    "VoteCastDecision": "vote_cast", "CandidacyDecision": "candidacy_considered",
    "PartyNominationDecision": "party_nomination_choice", "PositioningDecision": "campaign_positioning",
    "ResponseDecision": "representative_response", "PressureDecision": "pressure_action",
    "ReactionDecision": "reaction_to_event", "ChamberDecision": "chamber_deliberation",
    "CoalitionDecision": "coalition_decision",
}

_SLOTS = {"d": 1, "x": 2}  # decision, dependents; "m" is motif
RULES = tuple("".join(p) for p in itertools.permutations("dxm"))
"""The candidates: the id first, then the six orders of decision (d), dependents (x) and motif (m)."""


def rule_order(title: str, rule: str) -> tuple[str, ...]:
    slots = DECISION_SLOTS[title]
    fields: list[str] = list(slots[0])
    for code in rule:
        fields += ["motif"] if code == "m" else list(slots[_SLOTS[code]])
    return tuple(fields)


def rule_table(rule: str) -> dict[str, tuple[str, ...]]:
    return {title: rule_order(title, rule) for title in DECISION_SLOTS}
