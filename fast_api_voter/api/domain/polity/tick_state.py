"""The simulation's cross-tick state (S3.4): everything a tick reads from the ticks
before it and leaves for the ticks after.

run_simulation used to hold these as nine local variables, threaded by hand through
the tick loop, the checkpoint save call and the resume path. Adding one meant
editing all three, and forgetting the checkpoint lost it silently on resume.
TickState is that set as one object: the tick phases read and update it,
checkpoint.py serialises it whole (a test fails when a field has no serialisation),
and resume restores it in one step.

Not in here, because it never changes during a run and is regenerated from the
config on resume: the social graph and the institutional clock (see checkpoint.py).
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np

from api.domain.polity.citizen import Citizen
from api.domain.polity.legislation import Legislature
from api.domain.polity.parties import Party


@dataclass(frozen=True)
class PendingRerun:
    """v4 Lot 9 (§6bis.2): local, run-scoped state for the invalidate ->
    rerun -> bar cycle, deliberately NOT a Citizen field: unlike every other
    officeholder-scoped piece of state this project has added since Lot 3
    (legitimacy_capital, street_pressure, petition state), an invalidated
    election has no officeholder to attach state to by construction. Held on
    TickState, read by _attempt_rupture_candidacies and replaced by
    _hold_presidential_election every tick -- the same register as rupture_rng.

    `attempt` is the rerun's own 1-indexed number: the ORIGINAL scheduled
    election is never tracked as a PendingRerun at all (there is no pending
    state until the first invalidation). attempt=1 is the first rerun,
    attempt=2 the second. Attempts 1..reelection_max_attempts get the full
    invalidation check; attempt reelection_max_attempts+1 is FORCED (see
    _is_forced_attempt) -- §6bis.2's "au-delà, un résultat est forcé".

    `barred_candidate_ids` unions the candidate set of every invalidated
    election within this one cycle, but ONLY when
    config.institutions.barred_from_immediate_rerun is true -- that key is
    its own toggle, independent of blank_vote_competitive (shipped true,
    the doc's own recommended default, but a real comparison arm). Cleared
    (the whole PendingRerun discarded, back to None) the instant the cycle
    resolves: a real winner elected, or the forced attempt's outcome
    (winner or election_no_winner) accepted.

    `next_tick` REPLACES the fixed calendar for the presidency while this is
    active (see run_simulation's own tick loop), rather than being OR'd into
    it -- OR-ing a rerun tick into the fixed calendar is reachable at
    non-default reelection_delay_ticks/president_term_years combinations
    and produces two independent elections for one vacancy, with no journal
    event marking the discard."""

    attempt: int
    next_tick: int
    barred_candidate_ids: frozenset[int]
    incumbent_id: int | None = None
    """S4.1: the president whose record this rerun judges -- the recalled one for a snap
    election, the outgoing one carried through an invalidation cycle."""


@dataclass
class TickState:
    citizens: list[Citizen]
    parties: list[Party]
    rupture_rng: np.random.Generator
    events_rng: np.random.Generator
    sortition_rng: np.random.Generator
    pending_rerun: PendingRerun | None = None
    """An invalidated presidential election's rerun cycle, while one is open."""
    staggered_declared_cids: set[int] | None = None
    """Track E: who declared at this cycle's declaration tick, awaiting nomination."""
    economy_x: float = 0.0
    """The economy's AR(1) state, driving economic shocks."""
    mobilized_last_tick: Mapping[int, int] = field(default_factory=dict)
    """citizen_id -> targeted officeholder, from the previous tick's mobilization."""
    dynamics_rng: np.random.Generator | None = None
    """S4.3: the opinion-dynamics stream, None unless dynamics.enabled."""
    legislature: Legislature | None = None
    """S4.2: policy, the assembly's seats and coalition, and any suspended bill; None unless
    legislation.enabled."""
