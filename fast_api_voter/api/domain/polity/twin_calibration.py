"""Calibrating Stage 4's mechanisms against their pre-registered facts (ADR-009, ADR-011,
ADR-012): the grids, the facts and the selection rules, as pure functions over what a
calibration run records. The scripts (`scripts/calibrate_*.py`) run the deterministic twin
and record; nothing here runs a simulation.
"""
from __future__ import annotations

import itertools
import math
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np


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


# ── S4.3: dynamic citizens (ADR-012) ──────────────────────────────────────

def _correlation(a: np.ndarray, b: np.ndarray) -> float | None:
    if len(a) < 2 or a.std() == 0 or b.std() == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def panel_correlation(panel: Mapping[int, np.ndarray], lag: int, first_year: int = 1) -> float | None:
    """One run's mean correlation, over citizens, of each latent factor between yearly
    snapshots `lag` years apart, over every start year from `first_year` with its pair."""
    values = [
        r for year in sorted(panel) if year >= first_year and year + lag in panel
        for k in range(panel[year].shape[1])
        if (r := _correlation(panel[year][:, k], panel[year + lag][:, k])) is not None
    ]
    return sum(values) / len(values) if values else None


def _mean(values: Sequence[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def panel_stability(panels: Sequence[Mapping[int, np.ndarray]], lag: int = 4, band: tuple[float, float] = (0.70, 0.90)) -> Fact:
    """ADR-012 D1: the four-year panel correlation, averaged over runs, within the band."""
    value = _mean([panel_correlation(panel, lag) for panel in panels])
    holds = value is not None and band[0] <= value <= band[1]
    return Fact("D1 panel stability", holds, f"four-year factor correlation {'–' if value is None else f'{value:.3f}'}")


def dispersion_kept(panels: Sequence[Mapping[int, np.ndarray]], first: int = 0, last: int = 8, floor: float = 0.8) -> Fact:
    """ADR-012 D2: each factor's spread across citizens at `last` over its spread at `first`,
    averaged over runs and factors, at least `floor`; the lowest single ratio is reported too."""
    ratios = [
        float(panel[last][:, k].std() / panel[first][:, k].std())
        for panel in panels if first in panel and last in panel
        for k in range(panel[first].shape[1]) if panel[first][:, k].std() > 0
    ]
    mean = _mean(ratios)
    return Fact("D2 no consensus collapse", mean is not None and mean >= floor,
                "–" if mean is None else f"spread kept {mean:.3f} on average (lowest {min(ratios):.3f})")


def neighbour_distance_ratio(factors: np.ndarray, pairs: np.ndarray) -> float | None:
    """Mean latent distance between graph neighbours over the mean distance between all pairs."""
    if len(pairs) == 0 or len(factors) < 2:
        return None
    neighbours = float(np.linalg.norm(factors[pairs[:, 0]] - factors[pairs[:, 1]], axis=1).mean())
    upper = np.triu_indices(len(factors), k=1)
    everyone = float(np.linalg.norm(factors[upper[0]] - factors[upper[1]], axis=1).mean())
    return neighbours / everyone if everyone else None


def homophily(ratios: Sequence[tuple[float | None, float | None]]) -> Fact:
    """ADR-012 D3: the neighbour distance ratio, averaged over runs, lower at the end than at the start."""
    start, end = _mean([r[0] for r in ratios]), _mean([r[1] for r in ratios])
    holds = start is not None and end is not None and end < start
    return Fact("D3 neighbour homophily", holds,
                "–" if start is None or end is None else f"neighbour/all-pairs distance {start:.3f} at the start, {end:.3f} at the end")


def distinct_presidents(winners: Sequence[Sequence[int]]) -> float | None:
    return _mean([float(len(set(run))) for run in winners])


def more_presidents(winners: Sequence[Sequence[int]], static: Sequence[Sequence[int]]) -> Fact:
    """ADR-012 D4: more distinct presidents per run, on average, than the static arm."""
    value, baseline = distinct_presidents(winners), distinct_presidents(static)
    holds = value is not None and baseline is not None and value > baseline
    return Fact("D4 more distinct presidents", holds,
                f"{'–' if value is None else f'{value:.2f}'} per run (static arm {'–' if baseline is None else f'{baseline:.2f}'})")


@dataclass(frozen=True)
class TickMood:
    """One tick of one run: the population's mean emotions and the pressure it produced."""

    seed: int
    tick: int
    anger: float
    anxiety: float
    enthusiasm: float
    pressure_actions: int
    mobilizations: int


def tercile_totals(moods: Sequence[TickMood], by: str, count: str) -> tuple[int, int]:
    """Within each run, its ticks ranked by `by` (ties to the earlier tick); the totals of
    `count` over the top third and the bottom third, pooled over runs."""
    runs: dict[int, list[TickMood]] = defaultdict(list)
    for mood in moods:
        runs[mood.seed].append(mood)
    top = bottom = 0
    for ticks in runs.values():
        ranked = sorted(ticks, key=lambda m: (getattr(m, by), m.tick))
        third = len(ranked) // 3
        if third:
            bottom += sum(getattr(m, count) for m in ranked[:third])
            top += sum(getattr(m, count) for m in ranked[-third:])
    return top, bottom


def discontent_mobilizes(moods: Sequence[TickMood]) -> Fact:
    """ADR-012 E1: more mobilizations in the angriest third of ticks than in the calmest."""
    top, bottom = tercile_totals(moods, "anger", "mobilizations")
    return Fact("E1 discontent mobilizes", top > bottom, f"mobilizations {top} in the angriest third, {bottom} in the calmest")


def hard_times_draw_in(moods: Sequence[TickMood]) -> Fact:
    """ADR-012 E2: more pressure_action events in the most anxious third of ticks than in the least."""
    top, bottom = tercile_totals(moods, "anxiety", "pressure_actions")
    return Fact("E2 hard times draw people in", top > bottom, f"pressure actions {top} in the most anxious third, {bottom} in the least")


@dataclass(frozen=True)
class Term:
    seed: int
    start: int
    """The tick the president was elected; a full term holds office until start + its length."""


def full_terms(seed: int, events: Sequence[Mapping[str, Any]], term_ticks: int) -> list[Term]:
    """The presidencies that held office for their whole term: neither recalled nor succeeded
    before `term_ticks` had passed.

    A successor elected at exactly start + term_ticks is the next term, so a re-election at the
    term's end still counts. A snap-election winner replaced at the next calendar election does
    not: it was never recalled, but counting it would read its "last year" from its successor's
    ticks. The twin never had such a term (its presidents were recalled after a median of two
    ticks); the LLM path, with one or two recalls in eight years, does."""
    starts = [int(e["tick"]) for e in events if e["event_type"] == "elected"]
    recalls = [int(e["tick"]) for e in events if e["event_type"] == "recalled"]
    return [
        Term(seed=seed, start=start) for start in starts
        if not any(start <= recall < start + term_ticks for recall in recalls)
        and not any(start < other < start + term_ticks for other in starts)
    ]


def honeymoon_decline(moods: Sequence[TickMood], terms: Sequence[Term], term_ticks: int, ticks_per_year: int) -> Fact:
    """ADR-012 E3: mean enthusiasm over a full term's first year above its last year's, in a
    majority of full terms."""
    by_tick = {(m.seed, m.tick): m.enthusiasm for m in moods}

    def year_total(seed: int, start: int) -> float | None:
        values = [by_tick.get((seed, start + t)) for t in range(ticks_per_year)]
        return None if None in values else sum(v for v in values if v is not None)

    pairs = [(year_total(t.seed, t.start), year_total(t.seed, t.start + term_ticks - ticks_per_year)) for t in terms]
    measured = [(first, last) for first, last in pairs if first is not None and last is not None]
    declines = sum(first > last for first, last in measured)
    return Fact("E3 honeymoon decline", bool(measured) and declines > len(measured) / 2,
                f"declined in {declines} of {len(measured)} full terms")


def closest_to(target: float, measure: str) -> Callable[[Arm], float]:
    """Selection key: distance of an arm's measure from `target` (a missing measure sorts last)."""
    def key(arm: Arm) -> float:
        value = arm.measures.get(measure)
        return math.inf if value is None else abs(value - target)
    return key


# ── S4.2: ordinary legislation (ADR-009) ──────────────────────────────────

@dataclass(frozen=True)
class PolicyTick:
    """A tick with an assembly and a sitting president: how far policy and the president's
    revealed position stand from the population's per-issue median (RMS per issue)."""

    seed: int
    tick: int
    policy_distance: float
    president_distance: float


def checks_moderate(ticks: Sequence[PolicyTick]) -> Fact:
    """ADR-009 L1: policy nearer the median than the sitting president, averaged over ticks."""
    policy = _mean([t.policy_distance for t in ticks])
    president = _mean([t.president_distance for t in ticks])
    holds = policy is not None and president is not None and policy < president
    reading = "–" if policy is None or president is None else f"policy {policy:.4f} from the median, president {president:.4f}"
    return Fact("L1 checks moderate policy", holds, reading)


def legislation_alive(enacted: Sequence[int], terms: Sequence[int], min_moving_runs: int = 9) -> Fact:
    """ADR-009 L2: at least one bill enacted per presidential term (pooled over runs), and
    policy moved in at least `min_moving_runs` runs. `enacted` and `terms` are per run."""
    per_term = _rate(sum(enacted), sum(terms))
    moving = sum(count > 0 for count in enacted)
    holds = per_term is not None and per_term >= 1 and moving >= min_moving_runs
    return Fact("L2 the institution is alive", holds,
                f"{'–' if per_term is None else f'{per_term:.2f}'} bills enacted per term; policy moved in {moving} of {len(enacted)} runs")


@dataclass(frozen=True)
class Draft:
    seed: int
    regime: str
    """"cohabitation", "unified" or "no_government"."""
    enacted: bool


def gridlock_under_cohabitation(drafts: Sequence[Draft], minimum: int = 20) -> Fact:
    """ADR-009 L3: a lower enacted share under cohabitation than under unified government,
    pooled; unmeasured -- and so not holding -- when either regime drafted fewer than `minimum`."""
    def share(regime: str) -> tuple[int, int]:
        bills = [d for d in drafts if d.regime == regime]
        return sum(d.enacted for d in bills), len(bills)

    (co_enacted, co_drafted), (un_enacted, un_drafted) = share("cohabitation"), share("unified")
    measured = co_drafted >= minimum and un_drafted >= minimum
    co_rate, un_rate = _rate(co_enacted, co_drafted), _rate(un_enacted, un_drafted)
    holds = measured and co_rate is not None and un_rate is not None and co_rate < un_rate
    reading = (f"enacted {co_enacted}/{co_drafted} ({_percent(co_rate)}) under cohabitation, "
               f"{un_enacted}/{un_drafted} ({_percent(un_rate)}) unified" + ("" if measured else "; unmeasured"))
    return Fact("L3 gridlock under cohabitation", holds, reading)


@dataclass(frozen=True)
class GovernmentSpell:
    """A coalition formed at one legislative election: its parties' combined vote share then,
    and at the next legislative election."""

    seed: int
    share_at_formation: float
    share_next: float


def mean_share_change(spells: Sequence[GovernmentSpell]) -> float | None:
    return _mean([s.share_next - s.share_at_formation for s in spells])


def cost_of_ruling(spells: Sequence[GovernmentSpell], baseline: Sequence[GovernmentSpell]) -> Fact:
    """ADR-009 L4: the governing parties' share falls on average, and by more than with no
    policy retrospection."""
    change, zero = mean_share_change(spells), mean_share_change(baseline)
    holds = change is not None and zero is not None and change < 0 and change < zero
    reading = ("–" if change is None or zero is None
               else f"governing share changes {100 * change:+.2f} points (retrospection 0: {100 * zero:+.2f})")
    return Fact("L4 cost of ruling", holds, reading)


def lowest_qualifying_weight(
    by_weight: Sequence[tuple[float, Sequence[GovernmentSpell]]], baseline: Sequence[GovernmentSpell],
) -> tuple[float | None, Fact]:
    """L4's pick: the smallest weight whose spells meet the cost of ruling, with its fact; the
    largest weight's failing fact when none does."""
    ordered = sorted(by_weight, key=lambda item: item[0])
    for weight, spells in ordered:
        fact = cost_of_ruling(spells, baseline)
        if fact.holds:
            return weight, fact
    return None, cost_of_ruling(ordered[-1][1], baseline) if ordered else Fact("L4 cost of ruling", False, "–")


def legislation_choice(arm: Arm) -> tuple[float, float]:
    """The pre-registered order: the lowest bill rate (the longest interval), then the smallest step."""
    return (-arm.setting["bill_interval_ticks"], arm.setting["max_bill_step"])
