"""
api.domain.polity.sortition_chamber — §6bis.3's selection mechanic (v6b
Lot 2): a two-tier eligible-pool draw for the sortition chamber.

`select_sortition_chamber` is a pure selection primitive, in the same
register as `shock.py`'s two generators -- it takes no `Journal`, mutates no
`Citizen`, and takes no `tick`. The caller (`run_polity_simulation.py`'s
`_run_sortition_rotation`) owns vacating the outgoing cohort, applying the
new one, and journaling the transition -- mirroring the existing
`attempt_rupture_candidacy` (pure) / `_attempt_rupture_candidacies`
(orchestration + IO) split.

Eligibility is `office is Office.NONE` alone -- the sole officeholder this
codebase tracks is the president (`Office.DEPUTY` is reserved, never
assigned), so this excludes exactly the sitting president and nobody else.
A currently-seated sortition member needs no separate exclusion check here:
the caller vacates every seated member (clearing `sortition_seat_until_tick`)
*before* calling this function, so there is never a tick where a still-
seated member and a fresh draw coexist to be filtered between.

**The pool-exhaustion finding (v6b Lot 2's own measurement, not an
estimate)**: at the shipped defaults (`population_size=100`, `seats=30`,
`term_years=1` => `sortition_term_ticks=4`), strict one-shot-ever
eligibility (`sortition_terms_served == 0`) exhausts the never-served pool
by tick 12 (9 of 30 seats fillable) and leaves the chamber **completely
empty from tick 16 onward** -- 105 of 120 ticks, 87.5% of a full 30-year
run. Silently shrinking the chamber (rather than relaxing eligibility)
would make it nonexistent for nearly the entire run, undermining the whole
elected-vs-sortition comparison v6b Lot 4 exists to run. Resolved: once the
strict pool can't fill `seats`, eligibility relaxes to "not currently
seated" -- already-served citizens become re-eligible, softening
"non-renewable" after the pool empties, the honest trade that keeps the
chamber populated at the shipped scale (`scripts/sortition_calibration_
results.md` reproduces these exact numbers from a real run, not just this
docstring's own arithmetic)."""
from __future__ import annotations

from typing import Sequence

import numpy as np

from api.domain.polity.citizen import Citizen, Office
from api.domain.polity.config import SortitionChamberConfig


def select_sortition_chamber(
    citizens: Sequence[Citizen], config: SortitionChamberConfig, rng: np.random.Generator,
) -> tuple[list[int], bool]:
    """Returns (drawn citizen_ids, ascending and distinct; relaxed: whether
    the strict never-served pool had to be relaxed for this draw). The
    caller must vacate every currently-seated member BEFORE calling this --
    the eligible pool assumes nobody is currently seated."""
    strict_pool = [c.citizen_id for c in citizens if c.sortition_terms_served == 0 and c.office is Office.NONE]
    relaxed = len(strict_pool) < config.seats
    pool = strict_pool if not relaxed else [c.citizen_id for c in citizens if c.office is Office.NONE]
    draw_size = min(config.seats, len(pool))
    if draw_size == 0:
        return [], relaxed
    drawn = rng.choice(pool, size=draw_size, replace=False)
    return sorted(int(cid) for cid in drawn), relaxed
