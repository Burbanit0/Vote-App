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
from api.domain.polity.bakeoff_scorecard import Session, truth_outcomes
from api.domain.polity.bakeoff_statistics import holm_adjust, mcnemar_exact
from api.domain.polity.llm_client import _canonical, _inline_refs
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
    listed = tuple(table.get(title, ()))
    return tuple(f for f in listed if f in fields) + tuple(sorted(f for f in fields if f not in listed))


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
    main = session.by_case()
    if primary == "validity":
        return {c.case_id: json.dumps(main[c.case_id]["answers"], sort_keys=True) for c in cases if c.case_id in main}
    return {(c.case_id, unit): json.dumps((main.get(c.case_id) or {}).get("answers", {}).get(unit))
            for c in cases if c.family == primary for unit in c.labels["truth"]}


def noise(cases: Sequence[Case], a: Session, b: Session, primary: str) -> float | None:
    """The share of units answered differently by two sessions sent the same bytes."""
    first, second = _answers(cases, a, primary), _answers(cases, b, primary)
    common = set(first) & set(second)
    return sum(first[k] != second[k] for k in common) / len(common) if common else None


def _max_share(cases: Sequence[Case], session: Session, primary: str) -> float:
    counts = Counter(_answers(cases, session, primary).values())
    total = sum(counts.values())
    return max(counts.values()) / total if total else 0.0


def primary_measure(cases: Sequence[Case]) -> str:
    """A decision type's ground-truth family with the most units, or its validity when it has none."""
    truth = Counter(c.family for c in cases if c.labels["kind"] == "truth" for _ in c.labels["truth"])
    return truth.most_common(1)[0][0] if truth else "validity"


def _candidate(rule: str, order: tuple[str, ...], cases: Sequence[Case], session: Session,
               controls: tuple[Session, Session], primary: str) -> Candidate:
    mine, control = _units(cases, session, primary), _units(cases, controls[0], primary)
    common = sorted(set(mine) & set(control), key=str)
    test = mcnemar_exact([mine[k] for k in common], [control[k] for k in common])
    failures = []
    if primary != "validity":
        valid, control_valid = _units(cases, session, "validity"), _units(cases, controls[0], "validity")
        both = sorted(set(valid) & set(control_valid))
        check = mcnemar_exact([valid[k] for k in both], [control_valid[k] for k in both])
        if check.second_only > check.first_only and check.p_value < ALPHA:
            failures.append("validity significantly worse")
        if _max_share(cases, session, primary) >= DEGENERATE_SHARE and _max_share(cases, controls[0], primary) < MIXED_SHARE:
            failures.append("collapsed onto one answer")
    return Candidate(
        rule=rule, order=order, score=sum(mine[k] for k in common), trials=len(common),
        control_score=sum(control[k] for k in common),
        control_b_score=sum(v for k, v in _units(cases, controls[1], primary).items() if k in mine),
        first_only=test.first_only, second_only=test.second_only, p_value=test.p_value, failures=tuple(failures),
    )


def decide(bank: CaseBank, controls: tuple[Session, Session],
           candidates: Mapping[str, tuple[Mapping[str, Sequence[str]], Session]],
           current: Mapping[str, Sequence[str]]) -> list[Verdict]:
    """One verdict per decision class: the candidate order that beats the control on the type's primary
    measure (paired McNemar, Holm across that type's distinct candidate orders, p < 0.05), and again against the second
    control session, without a validity drop or a collapse onto one answer. When none does, or the primary
    measure is too noisy to tell, the current order stays: no change without evidence."""
    verdicts = []
    scored = [c for c in bank.cases if c.family != LOGPROB_GATE_FAMILY]
    for title, decision_type in DECISION_TYPES.items():
        cases = [c for c in scored if c.decision_type == decision_type]
        keep = table_order(current, title)
        if not cases:
            verdicts.append(Verdict(title, decision_type, "-", None, keep, keep, "not in the bank"))
            continue
        primary = primary_measure(cases)
        floor = noise(cases, *controls, primary)
        if floor is None or floor > NOISE_LIMIT:
            verdicts.append(Verdict(title, decision_type, primary, floor, keep, keep, "too noisy to tell"))
            continue
        by_order: dict[tuple[str, ...], list[tuple[str, Session]]] = {}
        for name, (table, session) in sorted(candidates.items()):
            if table_order(table, title) != keep:
                by_order.setdefault(table_order(table, title), []).append((name, session))
        # Arms that send this class the same order are one hypothesis, not several: Holm counts it once.
        found = [_candidate(" = ".join(name for name, _ in group), order, cases, group[0][1], controls, primary)
                 for order, group in by_order.items()]
        adjusted = holm_adjust({c.rule: c.p_value for c in found}) if found else {}
        found = [dataclasses.replace(c, p_holm=adjusted[c.rule]) for c in found]
        winners = sorted((c for c in found if c.wins), key=lambda c: (-c.score, c.rule))
        chosen = winners[0].order if winners else keep
        reason = f"{winners[0].rule} beats the control" if winners else "no candidate beats the control"
        verdicts.append(Verdict(title, decision_type, primary, floor, keep, chosen, reason, tuple(found)))
    return verdicts


def proposed_table(verdicts: Sequence[Verdict]) -> dict[str, tuple[str, ...]]:
    """WIRE_ORDER as the verdicts leave it: only the classes not sent alphabetically."""
    return {v.title: v.chosen for v in verdicts if v.chosen != tuple(sorted(v.chosen))}


def _content(schema: dict[str, Any], table: Mapping[str, Sequence[str]]) -> Any:
    def norm(node: Any) -> Any:
        if isinstance(node, dict):
            return {k: sorted(v) if k == "required" else norm(v) for k, v in sorted(node.items())}
        return [norm(item) for item in node] if isinstance(node, list) else node
    return norm(json.loads(json.dumps(_canonical(_inline_refs(schema), table))))


def isolation_violations(bank: CaseBank, tables: Mapping[str, Mapping[str, Sequence[str]]]) -> list[str]:
    """Each (arm, decision type) whose request differs from the alphabetical one in anything but key order."""
    return [f"{name}: {decision_type}" for name, table in sorted(tables.items())
            for decision_type, schema in sorted(bank.schemas.items()) if _content(schema, table) != _content(schema, {})]
