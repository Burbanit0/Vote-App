"""The pre-registered rule (ADR-030) that turns order-bank sessions into each decision's field order.

`schema_order` holds the candidates; this module reads the sessions `scripts/check_schema_order.py` ran.
"""
from __future__ import annotations

import dataclasses
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from api.domain.polity.bakeoff_bank import LOGPROB_GATE_FAMILY, Case, CaseBank
from api.domain.polity.bakeoff_runner import request_resolver, schema_resolver
from api.domain.polity.bakeoff_scorecard import Session, truth_outcomes
from api.domain.polity.bakeoff_statistics import holm_adjust, mcnemar_exact
from api.domain.polity.llm_client import _inline_refs, _wire_names
from api.domain.polity.schema_order import DECISION_SLOTS, DECISION_TYPES

NOISE_LIMIT = 0.10
"""A family whose answers differ on more than this share of units between the two control sessions (same
bytes) cannot show an order effect; its decision type keeps its current order."""
ALPHA = 0.05
DEGENERATE_SHARE = 0.95
"""An answer given to this share of units or more is a collapse, unless the control already gives one
answer to MIXED_SHARE of units or more."""
MIXED_SHARE = 0.80


def table_order(table: Mapping[str, Sequence[str]], title: str) -> tuple[str, ...]:
    """The order `table` sends `title`'s fields in: as listed, or alphabetically when it is not listed."""
    fields = [f for slot in DECISION_SLOTS[title] for f in slot] + ["motif"]
    return tuple(_wire_names(dict.fromkeys(fields), table.get(title, ())))


@dataclass(frozen=True)
class Candidate:
    rule: str
    order: tuple[str, ...]
    score: int
    trials: int
    control_score: int
    control_b_score: int
    first_only: int
    second_only: int
    p_value: float
    p_holm: float = 1.0
    failures: tuple[str, ...] = ()

    @property
    def wins(self) -> bool:
        return (not self.failures and self.first_only > self.second_only and self.p_holm < ALPHA
                and self.score > self.control_b_score)


@dataclass(frozen=True)
class Verdict:
    title: str
    decision_type: str
    primary: str
    noise: float | None
    current: tuple[str, ...]
    chosen: tuple[str, ...]
    reason: str
    candidates: tuple[Candidate, ...] = field(default=())


def _units(cases: Sequence[Case], session: Session, primary: str) -> dict[Any, Any]:
    """The primary measure, unit by unit: correct or not (a truth family), or valid or not (`validity`)."""
    main = session.by_case()
    if primary == "validity":
        return {c.case_id: main[c.case_id]["valid"] for c in cases if c.case_id in main}
    return truth_outcomes([c for c in cases if c.family == primary], main)


def _answers(cases: Sequence[Case], session: Session, primary: str) -> dict[Any, Any]:
    """Each unit's answer in a ground-truth family (`primary`), as JSON ("null" when unanswered)."""
    main = session.by_case()
    return {(c.case_id, unit): json.dumps((main.get(c.case_id) or {}).get("answers", {}).get(unit))
            for c in cases if c.family == primary for unit in c.labels["truth"]}


def noise(cases: Sequence[Case], a: Session, b: Session, primary: str) -> float | None:
    """The share of units two sessions sent the same bytes disagree on, read on the primary measure itself
    (validity, or the answer); a unit neither session answered says nothing and is left out."""
    measure = _units if primary == "validity" else _answers
    first, second = measure(cases, a, primary), measure(cases, b, primary)
    common = [k for k in set(first) & set(second) if not first[k] == second[k] == "null"]
    return sum(first[k] != second[k] for k in common) / len(common) if common else None


def _max_share(cases: Sequence[Case], session: Session, primary: str) -> float:
    counts = Counter(_answers(cases, session, primary).values())
    total = sum(counts.values())
    return max(counts.values()) / total if total else 0.0


def primary_measure(cases: Sequence[Case]) -> str:
    """A decision type's ground-truth family with the most units, or its validity when it has none."""
    truth = Counter(c.family for c in cases if c.labels["kind"] == "truth" for _ in c.labels["truth"])
    return truth.most_common(1)[0][0] if truth else "validity"


def _guard_failures(cases: Sequence[Case], session: Session, control: Session, primary: str) -> tuple[str, ...]:
    """Why a candidate may not win whatever its score: a significant validity drop, or a collapse onto one answer
    where the control gives a mix. Validity as the primary measure is the score itself, not a guard."""
    if primary == "validity":
        return ()
    failures = []
    valid, control_valid = _units(cases, session, "validity"), _units(cases, control, "validity")
    both = sorted(set(valid) & set(control_valid))
    check = mcnemar_exact([valid[k] for k in both], [control_valid[k] for k in both])
    if check.second_only > check.first_only and check.p_value < ALPHA:
        failures.append("validity significantly worse")
    if _max_share(cases, session, primary) >= DEGENERATE_SHARE and _max_share(cases, control, primary) < MIXED_SHARE:
        failures.append("collapsed onto one answer")
    return tuple(failures)


def _candidate(rule: str, order: tuple[str, ...], cases: Sequence[Case], session: Session,
               controls: tuple[Session, Session], primary: str) -> Candidate:
    mine, control, control_b = (_units(cases, s, primary) for s in (session, *controls))
    common = sorted(set(mine) & set(control) & set(control_b), key=str)  # one set of units for all three
    test = mcnemar_exact([mine[k] for k in common], [control[k] for k in common])
    return Candidate(
        rule=rule, order=order, score=sum(mine[k] for k in common), trials=len(common),
        control_score=sum(control[k] for k in common),
        control_b_score=sum(control_b[k] for k in common),
        first_only=test.first_only, second_only=test.second_only, p_value=test.p_value,
        failures=_guard_failures(cases, session, controls[0], primary),
    )


def recorded_order(session: Session) -> dict[str, tuple[str, ...]]:
    """The wire order a session sent. Sessions from before it was recorded all ran with an empty WIRE_ORDER."""
    return {title: tuple(order) for title, order in session.metadata.get("wire_order", {}).items()}


def _distinct_orders(title: str, keep: tuple[str, ...],
                     candidates: Mapping[str, tuple[Mapping[str, Sequence[str]], Session]]) -> dict[tuple[str, ...], list[tuple[str, Session]]]:
    """The candidates that send `title` something other than `keep`, grouped by the order they send: arms
    sending the same order are one hypothesis, not several, so Holm counts it once."""
    by_order: dict[tuple[str, ...], list[tuple[str, Session]]] = {}
    for name, (table, session) in sorted(candidates.items()):
        if table_order(table, title) != keep:
            by_order.setdefault(table_order(table, title), []).append((name, session))
    return by_order


def _tested(title: str, keep: tuple[str, ...], cases: Sequence[Case], controls: tuple[Session, Session],
            candidates: Mapping[str, tuple[Mapping[str, Sequence[str]], Session]], primary: str) -> list[Candidate]:
    """Every distinct candidate order for `title`, scored against the controls, with its Holm-adjusted p."""
    found = [_candidate(" = ".join(name for name, _ in group), order, cases, group[0][1], controls, primary)
             for order, group in _distinct_orders(title, keep, candidates).items()]
    adjusted = holm_adjust({c.rule: c.p_value for c in found}) if found else {}
    return [dataclasses.replace(c, p_holm=adjusted[c.rule]) for c in found]


def _verdict(title: str, decision_type: str, cases: Sequence[Case], controls: tuple[Session, Session],
             candidates: Mapping[str, tuple[Mapping[str, Sequence[str]], Session]], keep: tuple[str, ...]) -> Verdict:
    if not cases:
        return Verdict(title, decision_type, "-", None, keep, keep, "not in the bank")
    primary = primary_measure(cases)
    floor = noise(cases, *controls, primary)
    if floor is None or floor > NOISE_LIMIT:
        return Verdict(title, decision_type, primary, floor, keep, keep, "too noisy to tell")
    found = _tested(title, keep, cases, controls, candidates, primary)
    winners = sorted((c for c in found if c.wins), key=lambda c: (-c.score, c.rule))
    if not winners:
        return Verdict(title, decision_type, primary, floor, keep, keep, "no candidate beats the control", tuple(found))
    return Verdict(title, decision_type, primary, floor, keep, winners[0].order, f"{winners[0].rule} beats the control", tuple(found))


def decide(bank: CaseBank, controls: tuple[Session, Session],
           candidates: Mapping[str, tuple[Mapping[str, Sequence[str]], Session]]) -> list[Verdict]:
    """One verdict per decision class: the candidate order that beats the control on the type's primary
    measure (paired McNemar, Holm across that type's distinct candidate orders, p < 0.05), and again against the second
    control session, without a validity drop or a collapse onto one answer. When none does, or the primary
    measure is too noisy to tell, the controls' order stays: no change without evidence. The first control is
    the one the candidates ran right after, on the same server instance."""
    current = recorded_order(controls[0])
    if recorded_order(controls[1]) != current:
        raise ValueError("the two controls sent different wire orders: they are not the same control")
    scored = [c for c in bank.cases if c.family != LOGPROB_GATE_FAMILY]
    return [_verdict(title, decision_type, [c for c in scored if c.decision_type == decision_type], controls,
                     candidates, table_order(current, title))
            for title, decision_type in DECISION_TYPES.items()]


def proposed_table(verdicts: Sequence[Verdict]) -> dict[str, tuple[str, ...]]:
    """WIRE_ORDER as the verdicts leave it: only the classes not sent alphabetically."""
    return {v.title: v.chosen for v in verdicts if v.chosen != tuple(sorted(v.chosen))}


def _content(schema: dict[str, Any], request: Mapping[str, Any]) -> str:
    return json.dumps({"schema": _inline_refs(schema), "request": request}, sort_keys=True, default=str)


def isolation_violations(bank: CaseBank, arms: Sequence[str]) -> list[str]:
    """Each (arm, decision type) where the arm sends a case anything but the control's content in another key
    order: a schema or request change through the arm's own resolvers, not only its wire order."""
    base_schema, base_request = schema_resolver(bank, None), request_resolver(None)
    violations = []
    for arm in arms:
        schema_for, request_for = schema_resolver(bank, arm), request_resolver(arm)
        differs = {c.decision_type for c in bank.cases
                   if _content(schema_for(c), request_for(c)) != _content(base_schema(c), base_request(c))}
        violations += [f"{arm}: {decision_type}" for decision_type in sorted(differs)]
    return violations
