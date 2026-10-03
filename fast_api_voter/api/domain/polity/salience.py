"""ADR-023: campaigning. A nominee raises one issue's salience among the citizens it reaches,
and the existing vote rule does the rest.

Why salience and not persuasion. `weighted_distance` already weights each issue by the voter's own
`issue_priorities`, so a voter who comes to weigh housing more compares candidates more by housing.
That makes a campaign a real choice rather than a free boost: raising an issue a rival owns helps
the rival. Nothing is added to the vote rule, and no second implementation of it exists to drift.

The invariant. Priorities are a Dirichlet draw that sums to 1 (`citizen.generate_population`), and
`weighted_distance`'s own docstring rests on it -- the result stays in [0, 1], comparable to
`blank_threshold`. Every function here returns a vector that still sums to 1.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from api.domain.polity.citizen import Citizen
from api.domain.polity.config import VoteConfig
from api.domain.polity.simple_rules import BLANK_LABEL, utility_ballot

BASE = "base"
UNDECIDED = "undecided"
AUDIENCES = (BASE, UNDECIDED)


def raise_salience(priorities: Sequence[float], issue: int, step: float) -> tuple[float, ...]:
    """`issue` takes `step` of the weight it does not already hold; the others keep their shares of
    what is left. The sum stays 1 by construction, so nothing needs clamping: the new weight is
    p + step*(1 - p) and every other weight is scaled by (1 - step), which together still sum to 1.
    `step` 0 changes nothing and 1 would hand the issue all the weight."""
    held = priorities[issue]
    return tuple(
        held + step * (1.0 - held) if d == issue else weight * (1.0 - step)
        for d, weight in enumerate(priorities)
    )


def sample_heard(heard: Sequence[Citizen], cap: int, rng: np.random.Generator) -> list[Citizen]:
    """At most `cap` of the audience actually hears the campaign, drawn by lot (`campaign_rng`);
    `cap` 0 means everyone, which is how campaigning shipped and what OBS-036 measured: the
    `undecided` audience is most of the electorate, so an uncapped campaign reached ~60 citizens
    of 100 and ~100 campaigns left every citizen hearing 45-54 of them. Drawn without replacement,
    ascending by citizen_id, like `select_sortition_chamber`."""
    if cap <= 0 or len(heard) <= cap:
        return list(heard)
    by_id = {c.citizen_id: c for c in heard}
    drawn = rng.choice(sorted(by_id), size=cap, replace=False)
    return [by_id[int(cid)] for cid in sorted(drawn)]


def reached(
    nominee: Citizen, citizens: Sequence[Citizen], field: list[Citizen], vote: VoteConfig, audience: str,
) -> list[Citizen]:
    """Who hears the campaign. `base` is the nominee's own party -- an independent nominee has no
    base and reaches nobody. `undecided` is the citizens no candidate currently speaks for: those
    whose ballot puts blank first and those who would not vote at all, read off `utility_ballot`
    rather than a second copy of the blank rule."""
    if audience == BASE:
        party = nominee.party_affiliation
        return [] if party is None else [c for c in citizens if c.party_affiliation == party]
    undecided = []
    for citizen in citizens:
        ballot = utility_ballot(citizen, field, vote)
        if ballot is None or ballot[0] == BLANK_LABEL:
            undecided.append(citizen)
    return undecided
