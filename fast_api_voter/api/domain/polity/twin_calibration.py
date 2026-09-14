"""Calibrating Stage 4's mechanisms against their pre-registered facts (ADR-009, ADR-011,
ADR-012): the grids, the facts and the selection rules, as pure functions over what a
calibration run records. The scripts (`scripts/calibrate_*.py`) run the deterministic twin
and record; nothing here runs a simulation.
"""
from __future__ import annotations

import itertools
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


def grid(axes: Mapping[str, Sequence[Any]]) -> list[dict[str, Any]]:
    """Every combination of the axes' values, the first axis varying slowest."""
    names = list(axes)
    return [dict(zip(names, values)) for values in itertools.product(*(axes[name] for name in names))]


@dataclass(frozen=True)
class Fact:
    name: str
    holds: bool
    reading: str
    """The measured values the verdict rests on, for the results doc."""


@dataclass(frozen=True)
class Arm:
    setting: dict[str, Any]
    facts: tuple[Fact, ...]
    measures: dict[str, float | None] = field(default_factory=dict)

    @property
    def qualifies(self) -> bool:
        return all(fact.holds for fact in self.facts)


def select(arms: Sequence[Arm], key: Callable[[Arm], Any]) -> Arm | None:
    """The qualifying arm that sorts first by `key`, or None when none qualifies."""
    qualifying = [arm for arm in arms if arm.qualifies]
    return min(qualifying, key=key) if qualifying else None


def _rate(hits: int, total: int) -> float | None:
    return hits / total if total else None


def _percent(value: float | None) -> str:
    return "–" if value is None else f"{100 * value:.1f}%"


# ── S4.1: the utility vote (ADR-011) ──────────────────────────────────────

@dataclass(frozen=True)
class Election:
    """One presidential election attempt: its ballots, the incumbent it judged, its winner."""

    seed: int
    tick: int
    voters: int
    ballots: int
    incumbent_id: int | None
    incumbent_record: float | None
    incumbent_standing: bool
    winner_id: int | None


@dataclass(frozen=True)
class FirstChoices:
    """Voters whose own party had a candidate in the field, and how many ranked one first."""

    eligible: int = 0
    own_party_first: int = 0

    def __add__(self, other: FirstChoices) -> FirstChoices:
        return FirstChoices(self.eligible + other.eligible, self.own_party_first + other.own_party_first)

    @property
    def share(self) -> float | None:
        return _rate(self.own_party_first, self.eligible)


def retrospective_voting(elections: Sequence[Election]) -> Fact:
    """ADR-011 fact 1: a standing incumbent with a record below 0 is re-elected less often
    than one with a record of 0 or more. Unmeasured, and so not holding, when either group
    never stood."""
    groups: dict[bool, list[bool]] = {True: [], False: []}
    for e in elections:
        if e.incumbent_standing and e.incumbent_record is not None:
            groups[e.incumbent_record < 0].append(e.winner_id == e.incumbent_id)
    low, high = groups[True], groups[False]
    low_rate, high_rate = _rate(sum(low), len(low)), _rate(sum(high), len(high))
    holds = low_rate is not None and high_rate is not None and low_rate < high_rate
    return Fact("retrospective voting", holds,
                f"re-elected {sum(low)}/{len(low)} ({_percent(low_rate)}) with a record below 0, "
                f"{sum(high)}/{len(high)} ({_percent(high_rate)}) with 0 or more")


def mean_turnout(elections: Sequence[Election]) -> float | None:
    turnouts = [e.ballots / e.voters for e in elections if e.voters]
    return sum(turnouts) / len(turnouts) if turnouts else None


def turnout_band(elections: Sequence[Election], low: float = 0.50, high: float = 0.85) -> Fact:
    """ADR-011 fact 2: mean presidential turnout within [50%, 85%]."""
    turnout = mean_turnout(elections)
    return Fact("turnout", turnout is not None and low <= turnout <= high, f"mean turnout {_percent(turnout)}")


def partisanship(choices: FirstChoices, zero: FirstChoices, ceiling: float = 0.90) -> Fact:
    """ADR-011 fact 3: the share of voters ranking their own party's candidate first is higher
    than the zero-weight arm's and below 90%. The share counts voters whose party had a
    candidate in the field; a blank first choice is not their party."""
    share, baseline = choices.share, zero.share
    holds = share is not None and baseline is not None and baseline < share < ceiling
    return Fact("partisanship", holds, f"own-party first choice {_percent(share)} (zero-weight arm {_percent(baseline)})")


def repeat_winner_share(elections: Sequence[Election]) -> float | None:
    """The share of won elections whose winner also won the run's previous won election."""
    winners: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for e in elections:
        if e.winner_id is not None:
            winners[e.seed].append((e.tick, e.winner_id))
    repeats = pairs = 0
    for sequence in winners.values():
        ordered = [winner for _, winner in sorted(sequence)]
        pairs += len(ordered) - 1
        repeats += sum(a == b for a, b in zip(ordered, ordered[1:]))
    return _rate(repeats, pairs)


def fewer_repeat_winners(elections: Sequence[Election], zero: Sequence[Election]) -> Fact:
    """ADR-011 fact 4, as restated before running: fewer elections won by the previous winner
    than under the zero-weight arm (see calibrate_utility_vote.py for why)."""
    share, baseline = repeat_winner_share(elections), repeat_winner_share(zero)
    holds = share is not None and baseline is not None and share < baseline
    return Fact("repeat winners (OBS-001)", holds, f"won by the previous winner {_percent(share)} (zero-weight arm {_percent(baseline)})")


def utility_vote_arm(
    setting: dict[str, Any], elections: Sequence[Election], choices: FirstChoices,
    zero_elections: Sequence[Election], zero_choices: FirstChoices,
) -> Arm:
    return Arm(
        setting=setting,
        facts=(retrospective_voting(elections), turnout_band(elections), partisanship(choices, zero_choices),
               fewer_repeat_winners(elections, zero_elections)),
        measures={"turnout": mean_turnout(elections), "own_party_first": choices.share,
                  "repeat_winners": repeat_winner_share(elections)},
    )


def utility_vote_choice(arm: Arm) -> tuple[float, float]:
    """The pre-registered order: least partisanship + approval, then turnout nearest 67.5%."""
    turnout = arm.measures.get("turnout")
    return (arm.setting["partisanship"] + arm.setting["approval"], abs((turnout if turnout is not None else 0.0) - 0.675))
