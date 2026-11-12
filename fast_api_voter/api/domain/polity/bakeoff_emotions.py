"""ADR-012's prerequisite, read: does the model answer the same citizens as well with the emotion
fields in its prompt?

Pre-registered in plan-polity-build-order.md ("ADR-012's prerequisite, pre-registered before its
session"), signed off before the session. One session of the control model answers the emotions
bank (`bakeoff_cases.generate_emotions_bank`). It is accepted when both hold:

1. **Validity** -- `pressure_act_emotions` has at least as many valid answers as `pressure_act`;
2. **Accuracy** -- it answers at most one fewer of the same citizens correctly, with the paired
   per-citizen McNemar test reported.

`pressure_anger_sweep` is reported and never accepted on: the share of MOBILIZE at each anger level.

The two truth families ask the same 24 citizens one at a time, so a citizen's two cases pair by
the citizen's id. A citizen missing from either family is not paired, and is reported.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from api.domain.polity.bakeoff_bank import Case
from api.domain.polity.bakeoff_statistics import McNemarResult, mcnemar_exact
from api.domain.polity.codebook import PressureAct

PLAIN = "pressure_act"
FELT = "pressure_act_emotions"
SWEEP = "pressure_anger_sweep"
ACCURACY_TOLERANCE = 1
"""At most this many fewer citizens answered correctly with the emotion fields than without."""


@dataclass(frozen=True)
class SweepLevel:
    anger: float
    answered: int
    mobilize: int


@dataclass(frozen=True)
class EmotionsVerdict:
    valid_plain: int
    valid_felt: int
    cases_per_family: int
    correct_plain: int
    correct_felt: int
    paired_citizens: int
    unpaired_citizens: tuple[str, ...]
    mcnemar: McNemarResult
    sweep: tuple[SweepLevel, ...]

    @property
    def validity_holds(self) -> bool:
        return self.valid_felt >= self.valid_plain

    @property
    def accuracy_holds(self) -> bool:
        return self.correct_felt >= self.correct_plain - ACCURACY_TOLERANCE

    @property
    def accepted(self) -> bool:
        return self.validity_holds and self.accuracy_holds


def _acts_correct(answer: Any, should_act: bool) -> bool:
    """`pressure_act`'s own reading (bakeoff_scorecard._correct, match "acts"): any act but NOTHING
    counts as acting. An unanswered unit is wrong."""
    return answer is not None and bool(answer != int(PressureAct.NOTHING)) == should_act


def _by_citizen(cases: Iterable[Case], family: str) -> dict[str, tuple[Case, bool]]:
    return {unit: (case, expected) for case in cases if case.family == family for unit, expected in case.labels["truth"].items()}


def _valid(cases: list[Case], main: Mapping[str, Mapping[str, Any]], family: str) -> int:
    return sum(1 for case in cases if case.family == family and main.get(case.case_id, {}).get("valid"))


def _correct(main: Mapping[str, Mapping[str, Any]], case: Case, unit: str, expected: bool) -> bool:
    result = main.get(case.case_id)
    return result is not None and bool(result.get("valid")) and _acts_correct(result["answers"].get(unit), expected)


def _sweep_level(cases: list[Case], main: Mapping[str, Mapping[str, Any]], anger: float) -> SweepLevel:
    answers = [main[case.case_id]["answers"].get(str(unit))
               for case in cases if case.family == SWEEP and float(case.labels["t"]) == anger and case.case_id in main
               for unit in case.labels["units"]]
    answered = [a for a in answers if a is not None]
    return SweepLevel(anger=anger, answered=len(answered),
                      mobilize=sum(1 for a in answered if a == int(PressureAct.MOBILIZE)))


def read_verdict(cases: Iterable[Case], main: Mapping[str, Mapping[str, Any]]) -> EmotionsVerdict:
    """The verdict from a session's main-pass results, keyed by case id."""
    cases = list(cases)
    plain, felt = _by_citizen(cases, PLAIN), _by_citizen(cases, FELT)
    paired = sorted(set(plain) & set(felt), key=int)
    plain_outcomes = [_correct(main, plain[unit][0], unit, plain[unit][1]) for unit in paired]
    felt_outcomes = [_correct(main, felt[unit][0], unit, felt[unit][1]) for unit in paired]
    angers = sorted({float(case.labels["t"]) for case in cases if case.family == SWEEP})
    return EmotionsVerdict(
        valid_plain=_valid(cases, main, PLAIN), valid_felt=_valid(cases, main, FELT),
        cases_per_family=sum(1 for case in cases if case.family == PLAIN),
        correct_plain=sum(plain_outcomes), correct_felt=sum(felt_outcomes),
        paired_citizens=len(paired), unpaired_citizens=tuple(sorted(set(plain) ^ set(felt), key=int)),
        mcnemar=mcnemar_exact(plain_outcomes, felt_outcomes),
        sweep=tuple(_sweep_level(cases, main, anger) for anger in angers),
    )


def verdict_markdown(verdict: EmotionsVerdict, label: str) -> str:
    v = verdict
    lines = [
        "# ADR-012's prerequisite: the emotion fields in the pressure prompt",
        "",
        f"Session `{label}` on the emotions bank, read by `bakeoff_emotions.read_verdict` as pre-registered in "
        "`plan-polity-build-order.md` (\"ADR-012's prerequisite, pre-registered before its session\").",
        "",
        "## Verdict",
        "",
        ("**Accepted.** An LLM run may turn emotions on; Stage 4's step 5 proceeds." if v.accepted else
         "**Not accepted.** Emotions stay off on the LLM path; Stage 4's step 5 is reported as not run."),
        "",
        "| criterion | `pressure_act` | `pressure_act_emotions` | holds |",
        "|---|---:|---:|---|",
        f"| 1. valid answers | {v.valid_plain}/{v.cases_per_family} | {v.valid_felt}/{v.cases_per_family} "
        f"| {'yes' if v.validity_holds else '**no**'} |",
        f"| 2. citizens answered correctly (at most {ACCURACY_TOLERANCE} fewer) | {v.correct_plain}/{v.paired_citizens} "
        f"| {v.correct_felt}/{v.paired_citizens} | {'yes' if v.accuracy_holds else '**no**'} |",
        "",
        f"Paired McNemar over {v.paired_citizens} citizens: right only without the fields {v.mcnemar.first_only}, "
        f"right only with them {v.mcnemar.second_only}, exact p = {v.mcnemar.p_value:.4g}.",
    ]
    if v.unpaired_citizens:
        lines.append(f"Citizens asked in only one family, not paired: {', '.join(v.unpaired_citizens)}.")
    lines += ["", "## Reported, not accepted on: anger and mobilization", "",
              "| anger | answered | MOBILIZE | share |", "|---:|---:|---:|---:|"]
    for level in v.sweep:
        share = f"{level.mobilize / level.answered:.0%}" if level.answered else "–"
        lines.append(f"| {level.anger:g} | {level.answered} | {level.mobilize} | {share} |")
    return "\n".join(lines) + "\n"
