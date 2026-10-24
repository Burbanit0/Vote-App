"""Trajectory metrics (docs/plan/polity/plan-scenarios-v1.md, step 1): a run's history as numbers, so two
runs can be told apart and an ensemble's variety measured instead of asserted.

Pure functions over the journal (events), the yearly census (snapshots) and the terms the indexer cut. A
figure the journal does not hold is absent (None), never estimated: a presidential margin exists only where
a vote_intention_poll was journaled (the exploration profile), polarization only where snapshots.jsonl sits
beside the journal.

The archetype rules and their thresholds are a first cut: explicit, applied in ARCHETYPE_RULES order (first
match wins), and meant to be re-cut once the catalogue (plan-scenarios-v1, step 6) shows what runs do. They
were cut on eight-year runs, and a rule of the form "at some point this reached X" is satisfied by every run
given enough years (a thirty-year run always has an election with a volatility of 0.4 and a mean that moved
0.1), so a run is labelled block by block: it is cut into blocks of ARCHETYPE_BLOCK_YEARS to twice that, the
rules read each block as if it were a run, and the run takes its most common block label (ADR-035).
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from itertools import combinations
from typing import Any

import numpy as np

from api.domain.polity.indexer import Term
from api.domain.polity.metrics import effective_number_of_parties
from api.domain.polity.run_macro import build_macro

Series = dict[str, list[float | None]]
"""One list per feature, indexed by census year."""

FEATURES: tuple[str, ...] = ("legitimacy", "enp_seats", "turnout", "dispersion", "bimodality", "mean_shift", "pressure", "volatility")
"""The yearly series a trajectory vector is made of, in this order."""

RECALL_ENDINGS = frozenset({"legitimacy_floor", "confidence_vote"})

# Archetype thresholds (first cut; see the module docstring).
COLLAPSE_OCCUPANCY = 0.5
ENTRENCHMENT_HOLD = 3
RECALL_CYCLE_RECALLS = 2
FRAGMENTATION_ENP = 8.0
REALIGNMENT_SPREADS = 0.5
"""ADR-037: a realignment is the population's mean moving this many of its own spreads (the standard deviation along its first
principal axis, at the first census of the block) from where it started. Half a spread is a medium effect (Cohen's d).
Until ADR-037 the threshold was a fixed 0.1 in issue units, which 89% of the catalogue's 15-year runs crossed."""
CHURN_VOLATILITY = 0.4
ALTERNATION_COUNT = 2
ARCHETYPE_BLOCK_YEARS = 8
ARCHETYPE_VERSION = 3
"""1: the rules read the whole run. 2: they read it block by block (ADR-035). 3: a realignment is measured against the
population's own spread, not a fixed distance (ADR-037). Written to every digest, so labels of
different rules are not mixed in one ensemble unseen."""


PLAUSIBILITY_BAND: Mapping[str, tuple[float, float]] = {
    "enp_seats": (1.5, 8.0), "turnout": (0.5, 0.85), "volatility": (0.05, 0.30), "panel_stability": (0.70, 0.90),
}
"""Generic European party-system facts, as a band a run should not leave: ENP by seats at the last
legislative election, mean turnout, mean legislative volatility (Pedersen), and the four-year correlation of
each latent factor across citizens (ADR-012's D1: a static population scores 1.0, churn with no memory near
0). A filter against absurd runs, not a target."""
PANEL_YEARS = 4

DIVERGENCE_ENTROPY_BITS = 1.0
DIVERGENCE_LARGEST_SHARE = 0.5
DIVERGENCE_PLAUSIBLE_SHARE = 2 / 3


# ── per run ───────────────────────────────────────────────────────────────


def pedersen_volatility(before: Mapping[Any, float], after: Mapping[Any, float]) -> float | None:
    """Half the sum of absolute vote-share changes over every party that stood in either election (Pedersen
    1979). None when either election counted no votes."""
    totals = (sum(before.values()), sum(after.values()))
    if min(totals) <= 0:
        return None
    return 0.5 * sum(abs(before.get(p, 0.0) / totals[0] - after.get(p, 0.0) / totals[1]) for p in set(before) | set(after))


def _votes(event: Mapping[str, Any]) -> dict[str, float]:
    return {str(party): float(votes) for party, votes in event["payload"]["votes"].items()}


def legislative_points(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Per legislative election: ENP by seats (None when no party was seated), whether one party held a
    majority, whether any party was seated, and the Pedersen volatility against the previous election (None at
    the first)."""
    results = [e for e in events if e["event_type"] == "legislative_result"]
    rows: list[dict[str, Any]] = []
    for previous, current in zip([None, *results], results):
        seats = {int(k): float(v) for k, v in current["payload"]["seats"].items()}
        total = sum(seats.values())
        rows.append({
            "tick": int(current["tick"]),
            "enp_seats": effective_number_of_parties(seats) if total > 0 else None,
            "majority": any(s > total / 2 for s in seats.values()) if total > 0 else False,
            "seated": total > 0,
            "volatility": None if previous is None else pedersen_volatility(_votes(previous), _votes(current)),
        })
    return rows


def election_points(events: Sequence[Mapping[str, Any]], population: int, last_tick: int) -> list[dict[str, Any]]:
    """Per presidential vote held: the tick, the winner (None without one) and the turnout, read off the
    explorer's own election points (run_macro) so the two never disagree on what a held vote is."""
    return [
        {"tick": point.tick, "winner": point.winner, "turnout": point.turnout}
        for point in build_macro(events, population, last_tick).elections if point.turnout is not None
    ]


def presidential_margins(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Per vote-intention poll (journaled at each presidential election of the exploration profile): the
    leader's first-choice share and the margin over the runner-up (the whole share with a single candidate)."""
    rows = []
    for e in events:
        if e["event_type"] == "vote_intention_poll":
            shares = sorted((float(s["share"]) for s in e["payload"]["shares"]), reverse=True)
            leader = shares[0] if shares else None
            rows.append({
                "tick": int(e["tick"]), "candidates": len(shares), "leader_share": leader,
                "margin": shares[0] - shares[1] if len(shares) > 1 else leader,
            })
    return rows


def polarization(positions: np.ndarray) -> dict[str, float | None]:
    """The population's spread along its own first principal axis: `dispersion` is the standard deviation of
    the scores, `bimodality` Sarle's coefficient on them, (skewness² + 1) / (excess kurtosis + correction):
    5/9 for a uniform, higher for two camps, lower for one. None below four citizens (undefined) and for a
    population with no spread."""
    n = len(positions)
    if n < 4:
        return {"dispersion": None, "bimodality": None}
    centred = positions - positions.mean(axis=0)
    _, _, axes = np.linalg.svd(centred, full_matrices=False)
    scores = centred @ axes[0]
    sd = float(scores.std(ddof=1))
    if sd == 0.0:
        return {"dispersion": 0.0, "bimodality": None}
    z = (scores - scores.mean()) / sd
    skewness = float((z**3).mean())
    kurtosis = float((z**4).mean()) - 3.0
    correction = 3.0 * (n - 1) ** 2 / ((n - 2) * (n - 3))
    return {"dispersion": sd, "bimodality": (skewness**2 + 1.0) / (kurtosis + correction)}


def polarization_by_year(snapshots: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Per census year: the polarization of the issue positions and how far the population's mean has moved
    from the first census (`mean_shift`, Euclidean over the issues)."""
    by_year: dict[int, list[Sequence[float]]] = defaultdict(list)
    for row in snapshots:
        by_year[int(row["year"])].append(row["issue_positions"])
    rows: list[dict[str, Any]] = []
    first_mean: np.ndarray | None = None
    for year in sorted(by_year):
        positions = np.asarray(by_year[year], dtype=float)
        mean = positions.mean(axis=0)
        if first_mean is None:
            first_mean = mean
        rows.append({"year": year, **polarization(positions), "mean_shift": float(np.linalg.norm(mean - first_mean))})
    return rows


def _factors_by_year(snapshots: Sequence[Mapping[str, Any]]) -> dict[int, dict[int, Sequence[float]]]:
    """Each census year's latent factors by citizen; rows without factors (a static population) are left out."""
    by_year: dict[int, dict[int, Sequence[float]]] = defaultdict(dict)
    for row in snapshots:
        if row.get("latent_factors") is not None:
            by_year[int(row["year"])][int(row["citizen_id"])] = row["latent_factors"]
    return by_year


def _factor_correlations(before: np.ndarray, after: np.ndarray) -> list[float]:
    """Pearson's r between two censuses for each factor nobody is constant on (else it is undefined)."""
    return [
        float(np.corrcoef(before[:, k], after[:, k])[0, 1])
        for k in range(before.shape[1]) if before[:, k].std() > 0 and after[:, k].std() > 0
    ]


def panel_stability(
    snapshots: Sequence[Mapping[str, Any]], replaced: Sequence[tuple[int, int]] = (), ticks_per_year: int = 4,
) -> float | None:
    """ADR-012's D1: across citizens, the correlation of each latent factor between yearly censuses
    PANEL_YEARS apart (years 1 to 5 up to 4 to 8), averaged over the pairs and the factors. A panel follows the
    same people, so a slot whose citizen was replaced between the two censuses (`replaced`: (tick, citizen_id),
    ADR-035; a replacement falls after its tick's census) is left out of that pair. None where the census
    carries no latent factors (a static population: dynamics off), no pair of censuses of the same
    citizens is that far apart, or nobody varies on a factor."""
    by_year = _factors_by_year(snapshots)
    correlations: list[float] = []
    for year, census in sorted(by_year.items()):
        later = by_year.get(year + PANEL_YEARS)
        if later is not None and set(later) == set(census):
            leavers = {who for tick, who in replaced if year * ticks_per_year <= tick < (year + PANEL_YEARS) * ticks_per_year}
            ids = sorted(set(census) - leavers)
            if leavers and len(ids) < 3:  # too few left to correlate
                continue
            correlations += _factor_correlations(
                np.array([census[i] for i in ids], dtype=float), np.array([later[i] for i in ids], dtype=float),
            )
    return _mean(correlations)


def office_summary(terms: Sequence[Term]) -> dict[str, Any]:
    """Who held office and how it changed hands: alternations (consecutive terms with another holder),
    re-elections (the same holder after a term that ended at an election), recalls (terms ended at the floor
    or by a lost confidence vote), the longest run of terms one holder kept through elections, and the mean
    term length in ticks."""
    pairs = list(zip(terms, terms[1:]))
    return {
        "terms": len(terms),
        "distinct_holders": len({t.holder_id for t in terms}),
        "alternations": sum(a.holder_id != b.holder_id for a, b in pairs),
        "reelections": sum(_reelected(a, b) for a, b in pairs),
        "recalls": sum(t.ended_by in RECALL_ENDINGS for t in terms),
        "longest_hold": _longest_hold(terms),
        "mean_term_ticks": _mean([float(t.end_tick - t.start_tick) for t in terms]),
    }


def _reelected(before: Term, after: Term) -> bool:
    return before.holder_id == after.holder_id and before.ended_by == "election"


def _longest_hold(terms: Sequence[Term]) -> int:
    """The most terms one holder kept in a row through elections."""
    streak = best = 1 if terms else 0
    for before, after in zip(terms, terms[1:]):
        streak = streak + 1 if _reelected(before, after) else 1
        best = max(best, streak)
    return best


Summary = Mapping[str, Any]
"""trajectory_summary's dict, the input of every rule below."""


def _enp_by_seats(summary: Summary) -> list[float]:
    return [row["enp_seats"] for row in summary["legislative"] if row["enp_seats"] is not None]


def _is_collapse(summary: Summary) -> bool:
    return summary["office_occupancy"] < COLLAPSE_OCCUPANCY or any(not row["seated"] for row in summary["legislative"])


def _is_entrenchment(summary: Summary) -> bool:
    return bool(summary["office"]["longest_hold"] >= ENTRENCHMENT_HOLD or summary["refused_to_leave"])


def _is_recall_cycle(summary: Summary) -> bool:
    return bool(summary["office"]["recalls"] >= RECALL_CYCLE_RECALLS)


def _is_fragmentation(summary: Summary) -> bool:
    enp = _enp_by_seats(summary)
    return len(enp) >= 2 and enp[-1] >= FRAGMENTATION_ENP and enp[-1] > enp[0]


def _is_dominant_party(summary: Summary) -> bool:
    return len(summary["legislative"]) >= 2 and all(row["majority"] for row in summary["legislative"])


def largest_relative_shift(polarization: Sequence[Mapping[str, Any]]) -> float:
    """The largest `mean_shift` of the censuses, in units of the first census's `dispersion`; 0 when the first census has
    none (fewer than four citizens, or no spread), since a shift cannot be measured against nothing."""
    spread = polarization[0]["dispersion"] if polarization else None
    return max(row["mean_shift"] for row in polarization) / spread if spread else 0.0


def _is_realignment(summary: Summary) -> bool:
    return largest_relative_shift(summary["polarization"]) >= REALIGNMENT_SPREADS


def _is_churn(summary: Summary) -> bool:
    volatilities = (row["volatility"] for row in summary["legislative"] if row["volatility"] is not None)
    return max(volatilities, default=0.0) >= CHURN_VOLATILITY


def _is_alternation(summary: Summary) -> bool:
    return bool(summary["office"]["alternations"] >= ALTERNATION_COUNT)


ARCHETYPE_RULES: tuple[tuple[str, str, Callable[[Summary], bool]], ...] = (
    ("collapse", f"office occupancy below {COLLAPSE_OCCUPANCY}, or a legislative election that seated no party", _is_collapse),
    ("entrenchment", f"one holder kept office through {ENTRENCHMENT_HOLD} or more elections, or a refusal to leave succeeded", _is_entrenchment),
    ("recall_cycle", f"{RECALL_CYCLE_RECALLS} or more recalls", _is_recall_cycle),
    ("fragmentation", f"ENP by seats at least {FRAGMENTATION_ENP} at the last legislative election, and above the first's", _is_fragmentation),
    ("dominant_party", "one party held a majority of the seats at every legislative election (at least two)", _is_dominant_party),
    ("realignment", f"the population's mean moved {REALIGNMENT_SPREADS} or more of its own spread from the first census", _is_realignment),
    ("churn", f"a legislative volatility of {CHURN_VOLATILITY} or more (parties come and go; opinion need not move)", _is_churn),
    ("alternation", f"{ALTERNATION_COUNT} or more alternations in office", _is_alternation),
    ("stasis", "none of the above", lambda summary: True),
)
"""Label, the rule in words, and the predicate that applies it; first match wins."""


def archetype(summary: Summary) -> str:
    """The first ARCHETYPE_RULES row the summary (trajectory_summary's) satisfies."""
    return next(label for label, _, holds in ARCHETYPE_RULES if holds(summary))


def block_edges(duration_years: int) -> list[int]:
    """The census years that cut a run of `duration_years` years into blocks of ARCHETYPE_BLOCK_YEARS to twice
    that (one block for a run shorter than two blocks' worth), as [0, ..., duration_years]."""
    blocks = max(1, duration_years // ARCHETYPE_BLOCK_YEARS)
    return [round(i * duration_years / blocks) for i in range(blocks + 1)]


def run_archetype(whole: Summary, labels: Sequence[str]) -> str:
    """A collapse of the whole run is a collapse; else the most common label of the blocks, the earliest block
    deciding a tie. A run of one block is labelled exactly as `archetype` would label it."""
    if _is_collapse(whole):
        return "collapse"
    return max(dict.fromkeys(labels), key=labels.count)


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def plausibility(summary: Mapping[str, Any]) -> list[str]:
    """The PLAUSIBILITY_BAND checks the run fails; a check with nothing to read is skipped, not failed."""
    legislative = summary["legislative"]
    enp = [row["enp_seats"] for row in legislative if row["enp_seats"] is not None]
    readings = {
        "enp_seats": enp[-1] if enp else None,
        "turnout": _mean([row["turnout"] for row in summary["elections"]]),
        "volatility": _mean([row["volatility"] for row in legislative if row["volatility"] is not None]),
        "panel_stability": summary.get("panel_stability"),
    }
    failed = []
    for name, (low, high) in PLAUSIBILITY_BAND.items():
        value = readings[name]
        if value is not None and not low <= float(value) <= high:
            failed.append(name)
    return failed


def _carried(points: Sequence[Mapping[str, Any]], key: str, years: int, ticks_per_year: int) -> list[float | None]:
    """A per-election figure as a yearly series: the last election's value by the end of each year, None before
    any election and None again after an election that had none (an assembly that seated no party resets the
    ENP; it is not carried over as if the election had not happened)."""
    series: list[float | None] = []
    last: float | None = None
    for year in range(years):
        for point in points:
            if int(point["tick"]) < (year + 1) * ticks_per_year:
                last = None if point[key] is None else float(point[key])
        series.append(last)
    return series


def yearly_series(
    events: Sequence[Mapping[str, Any]], summary: Mapping[str, Any], *, population: int, ticks_per_year: int, last_tick: int,
) -> Series:
    """FEATURES as one list each, indexed by year up to the last tick: the sitting president's mean legitimacy,
    ENP by seats, turnout and volatility carried from the last election, the census polarization figures, and
    pressure acts (anything but "nothing") per citizen per tick."""
    years = last_tick // ticks_per_year + 1
    return {
        "legitimacy": _legitimacy_by_year(events, years, ticks_per_year),
        "enp_seats": _carried(summary["legislative"], "enp_seats", years, ticks_per_year),
        "turnout": _carried(summary["elections"], "turnout", years, ticks_per_year),
        "dispersion": _census_series(summary["polarization"], "dispersion", years),
        "bimodality": _census_series(summary["polarization"], "bimodality", years),
        "mean_shift": _census_series(summary["polarization"], "mean_shift", years),
        "pressure": _pressure_by_year(events, years, ticks_per_year, population, last_tick),
        "volatility": _carried(summary["legislative"], "volatility", years, ticks_per_year),
    }


def _legitimacy_by_year(events: Sequence[Mapping[str, Any]], years: int, ticks_per_year: int) -> list[float | None]:
    """The sitting president's mean legitimacy per year, None in a year with no reading."""
    readings: dict[int, list[float]] = defaultdict(list)
    for e in events:
        if e["event_type"] == "legitimacy_updated" and e["payload"].get("office") == "president":
            readings[int(e["tick"]) // ticks_per_year].append(float(e["payload"]["legitimacy"]))
    return [_mean(readings[year]) for year in range(years)]


def _pressure_by_year(
    events: Sequence[Mapping[str, Any]], years: int, ticks_per_year: int, population: int, last_tick: int,
) -> list[float | None]:
    """Pressure acts (anything but "nothing") per citizen per tick, the last year counting only its ticks."""
    acts: Counter[int] = Counter(
        int(e["tick"]) // ticks_per_year for e in events
        if e["event_type"] == "pressure_action" and int(e["payload"]["act"]) != 0
    )
    ticks_in = [min(ticks_per_year, last_tick + 1 - year * ticks_per_year) for year in range(years)]
    return [acts[year] / (population * ticks_in[year]) for year in range(years)]


def _census_series(rows: Sequence[Mapping[str, Any]], key: str, years: int) -> list[float | None]:
    """A census figure per year, None in a year without a census."""
    by_year = {int(row["year"]): row[key] for row in rows}
    return [by_year.get(year) for year in range(years)]


def _block_summary(
    summary: Mapping[str, Any], refusals: Sequence[int], snapshots: Sequence[Mapping[str, Any]], terms: Sequence[Term],
    years: tuple[int, int], ticks_per_year: int,
) -> dict[str, Any]:
    """The part of the run's summary the archetype rules read, restricted to census years [first, end): its
    terms (those that began in it: a streak or an alternation across the boundary is not seen, and a block of
    eight years holds two presidential terms), legislative elections, polarization (shifted from the block's own
    first census) and the ticks of successful refusals to leave. The occupancy is the run's: a collapse is
    judged on the whole."""
    first, end = years
    low, high = first * ticks_per_year, end * ticks_per_year
    return {
        "office_occupancy": summary["office_occupancy"],
        "office": office_summary([t for t in terms if low <= t.start_tick < high]),
        "legislative": [row for row in summary["legislative"] if low <= row["tick"] < high],
        "polarization": polarization_by_year([r for r in snapshots if first <= int(r["year"]) < end]),
        "refused_to_leave": any(low <= tick < high for tick in refusals),
    }


def trajectory_summary(
    events: Sequence[Mapping[str, Any]], snapshots: Sequence[Mapping[str, Any]], *,
    terms: Sequence[Term], population: int, ticks_per_year: int, last_tick: int, office_occupancy: float,
) -> dict[str, Any]:
    """Everything above for one run, plus its archetype (block by block: see `run_archetype`), the
    plausibility checks it fails and its yearly series: the digest's `trajectory` entry."""
    summary: dict[str, Any] = {
        "office_occupancy": office_occupancy,
        "office": office_summary(terms),
        "elections": election_points(events, population, last_tick),
        "legislative": legislative_points(events),
        "margins": presidential_margins(events),
        "polarization": polarization_by_year(snapshots),
        "panel_stability": panel_stability(
            snapshots, [(int(e["tick"]), int(e["citizen_id"])) for e in events if e["event_type"] == "citizen_replaced"], ticks_per_year,
        ),
    }
    refusals = [int(e["tick"]) for e in events if e["event_type"] == "extra_legal_act" and e["payload"]["success"]]
    summary["refused_to_leave"] = bool(refusals)
    edges = block_edges(last_tick // ticks_per_year)
    edges[-1] += 1  # the last block takes the final census year too
    labels = [archetype(_block_summary(summary, refusals, snapshots, terms, (a, b), ticks_per_year)) for a, b in zip(edges, edges[1:])]
    summary["archetype"] = run_archetype(summary, labels)
    summary["archetype_blocks"] = labels
    summary["archetype_version"] = ARCHETYPE_VERSION
    summary["plausibility_failed"] = plausibility(summary)
    summary["yearly"] = yearly_series(events, summary, population=population, ticks_per_year=ticks_per_year, last_tick=last_tick)
    return summary


# ── across runs ───────────────────────────────────────────────────────────


def feature_cube(series_by_run: Mapping[str, Series], features: Sequence[str] = FEATURES) -> tuple[list[str], np.ndarray]:
    """Runs × years × features, cut to the shortest run, each feature standardised over every run and year;
    an absent value sits at the feature's mean, so it adds nothing to a distance."""
    runs = sorted(series_by_run)
    years = min((len(series_by_run[r].get(f, ())) for r in runs for f in features), default=0)
    cube = np.full((len(runs), years, len(features)), np.nan)
    for i, run in enumerate(runs):
        for j, feature in enumerate(features):
            cube[i, :, j] = [np.nan if v is None else float(v) for v in series_by_run[run].get(feature, ())[:years]]
    present = ~np.isnan(cube)
    counts = present.sum(axis=(0, 1))
    filled = np.where(present, cube, 0.0)
    mean = np.where(counts > 0, filled.sum(axis=(0, 1)) / np.maximum(counts, 1), 0.0)
    spread = np.sqrt(np.where(counts > 0, (np.where(present, cube - mean, 0.0) ** 2).sum(axis=(0, 1)) / np.maximum(counts, 1), 0.0))
    z = np.where(present, (cube - mean) / np.where(spread > 0, spread, 1.0), 0.0)
    return runs, z


def distance_matrix(series_by_run: Mapping[str, Series], features: Sequence[str] = FEATURES) -> tuple[list[tuple[str, str]], np.ndarray]:
    """Every pair of runs, and their Euclidean distance in the standardised feature space at each year
    (pairs × years). The one definition of "distance" the two readings below share."""
    runs, z = feature_cube(series_by_run, features)
    pairs = list(combinations(range(len(runs)), 2))
    matrix = np.array([np.linalg.norm(z[i] - z[j], axis=1) for i, j in pairs]).reshape(len(pairs), z.shape[1])
    return [(runs[i], runs[j]) for i, j in pairs], matrix


def divergence_by_year(series_by_run: Mapping[str, Series], features: Sequence[str] = FEATURES) -> list[float]:
    """The mean distance between every pair of runs, year by year: the series the divergence test reads (it
    should grow). Empty below two runs."""
    pairs, matrix = distance_matrix(series_by_run, features)
    return [float(v) for v in matrix.mean(axis=0)] if pairs else []


def pairwise_distances(series_by_run: Mapping[str, Series], features: Sequence[str] = FEATURES) -> dict[tuple[str, str], float]:
    """The distance between every pair of runs: the per-year distance, averaged over the years both have.
    Empty when the runs share no year."""
    pairs, matrix = distance_matrix(series_by_run, features)
    return {pair: float(v) for pair, v in zip(pairs, matrix.mean(axis=1))} if matrix.shape[1] else {}


def diversity(labels: Mapping[str, str], distances: Mapping[tuple[str, str], float]) -> dict[str, Any]:
    """How varied an ensemble is: the archetype counts, their entropy in bits, the largest archetype's share
    and the mean pairwise distance."""
    counts = Counter(labels.values())
    n = sum(counts.values())
    return {
        "runs": n,
        "archetypes": dict(sorted(counts.items())),
        "archetype_entropy_bits": -sum(c / n * math.log2(c / n) for c in counts.values()) if n else 0.0,
        "largest_archetype_share": max(counts.values()) / n if n else None,
        "mean_pairwise_distance": _mean(list(distances.values())),
    }


def divergence_verdict(by_year: Sequence[float], ensemble: Mapping[str, Any], plausible_share: float | None) -> dict[str, bool | None]:
    """The divergence test (plan-scenarios-v1, step 2): the runs drift apart over time (the last third of the
    years is farther apart than the first third), the archetypes are varied enough, no archetype covers more
    than half the runs, and enough runs stay inside the plausibility band. None where there is too little to
    judge (under three years, or no runs)."""
    third = len(by_year) // 3
    return {
        "grows": (_mean(by_year[-third:]) or 0.0) > (_mean(by_year[:third]) or 0.0) if third else None,
        "varied": ensemble["archetype_entropy_bits"] >= DIVERGENCE_ENTROPY_BITS if ensemble["runs"] else None,
        "no_dominant_story": ensemble["largest_archetype_share"] <= DIVERGENCE_LARGEST_SHARE if ensemble["runs"] else None,
        "plausible": plausible_share >= DIVERGENCE_PLAUSIBLE_SHARE if plausible_share is not None else None,
    }
