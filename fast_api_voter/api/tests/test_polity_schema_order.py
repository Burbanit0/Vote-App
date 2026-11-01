"""The candidate field orders (ADR-030). See api/domain/polity/schema_order.py."""
from __future__ import annotations

from api.domain.polity import llm_schemas
from api.domain.polity.schema_order import DECISION_SLOTS, DECISION_TYPES, RULES, rule_order


def test_the_slots_name_every_field_of_every_batch_decision_exactly() -> None:
    # A field added to a decision must be placed in a slot, or it would be sent at the tail, unmeasured.
    decisions = {name for name in dir(llm_schemas) if name.endswith("Decision") and "motif" in getattr(
        getattr(llm_schemas, name), "model_fields", {})}
    assert set(DECISION_SLOTS) == decisions == set(DECISION_TYPES)
    for title, slots in DECISION_SLOTS.items():
        named = [f for slot in slots for f in slot] + ["motif"]
        assert sorted(named) == sorted(getattr(llm_schemas, title).model_fields), title
        assert len(named) == len(set(named)), title


def test_a_rule_puts_the_id_first_then_its_three_slots_in_order() -> None:
    assert len(RULES) == len(set(RULES)) == 6
    assert rule_order("ResponseDecision", "mdx") == ("cid", "motif", "stance", "shifts")
    assert rule_order("ResponseDecision", "xdm") == ("cid", "shifts", "stance", "motif")  # the declared order
    assert rule_order("PressureDecision", "xdm") == ("cid", "target", "act", "motif")  # the declared order
    assert rule_order("CandidacyDecision", "dxm") == rule_order("CandidacyDecision", "xdm") == ("cid", "outcome", "motif")
