"""
api.domain.polity.leaders -- ADR-040: party leaders who move their platform (Laver and Sergenti 2012, "Party
Competition: An Agent-Based Model"). Until this ADR a party's platform was where k-means put it at the start.

Once a year every party's leader follows one rule:

- **sticker**: never moves (the default, and every run before this ADR).
- **aggregator**: steps toward the centroid of its supporters' positions.
- **hunter**: keeps its heading while its poll share grows; when it falls, turns to a random heading in the half of the
  space it came from (Laver and Sergenti's hunter).
- **explorer**: polls `EXPLORER_PROBES` positions one step away in random directions, with every other platform where
  it is, and moves to the best if it beats where it stands.

A citizen's supporter is the party nearest them by the legislative ballot's own distance (`simple_rules.weighted_distance`:
Euclidean, weighted by their priorities); a party's poll share is the share of citizens it is nearest to (sincere first
preferences, before strategic voting and the incumbents' record). Every leader decides from the same snapshot of
platforms, so the order of the parties does not matter, and a platform stays in [0, 1] on every issue. Laver and
Sergenti's predator is not built.
"""
from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from api.domain.polity.citizen import Citizen
from api.domain.polity.config import LEADER_RULES
from api.domain.polity.parties import Party

RULES = LEADER_RULES
EXPLORER_PROBES = 5


@dataclass(frozen=True)
class LeaderMove:
    party_id: int
    rule: str
    share: float
    """The party's poll share that the leader read, before moving."""
    shift: float
    """How far the platform moved (Euclidean, over the issues)."""


def nearest(positions: np.ndarray, priorities: np.ndarray, platforms: np.ndarray) -> np.ndarray:
    """Each citizen's nearest platform (its row in `platforms`) by the ballot's priority-weighted distance; the lower
    row wins a tie, as `assign_party_affiliation` breaks ties on the lower party id."""
    gaps = positions[:, None, :] - platforms[None, :, :]
    return np.argmin((priorities[:, None, :] * gaps**2).sum(axis=2), axis=1)


def shares(positions: np.ndarray, priorities: np.ndarray, platforms: np.ndarray) -> np.ndarray:
    """Each platform's share of the citizens it is nearest to."""
    return np.bincount(nearest(positions, priorities, platforms), minlength=len(platforms)) / len(positions)


def _unit(rng: np.random.Generator, dimensions: int) -> np.ndarray:
    v = rng.normal(size=dimensions)
    return np.asarray(v / np.linalg.norm(v))


def _toward(platform: np.ndarray, target: np.ndarray, step: float) -> np.ndarray:
    gap = target - platform
    distance = float(np.linalg.norm(gap))
    return target if distance <= step else platform + gap * (step / distance)


def reposition(
    parties: Sequence[Party], citizens: Sequence[Citizen], rule: str, step: float, rng: np.random.Generator,
) -> tuple[list[Party], list[LeaderMove]]:
    """Every party's leader follows `rule` once; the parties as they now stand, and one move per party (a sticker's
    move is a shift of 0)."""
    if rule not in RULES:
        raise ValueError(f"unknown leader rule {rule!r}")
    positions = np.array([c.issue_positions for c in citizens], dtype=float)
    priorities = np.array([c.issue_priorities for c in citizens], dtype=float)
    platforms = np.array([p.platform for p in parties], dtype=float)
    now = shares(positions, priorities, platforms)
    supporters = nearest(positions, priorities, platforms)
    moved, moves = [], []
    for i, party in enumerate(parties):
        here = platforms[i]
        target, kept = _decide(i, party, rule, step, here, now, supporters, positions, priorities, platforms, rng)
        target = np.clip(target, 0.0, 1.0)
        moved.append(dataclasses.replace(kept, platform=tuple(float(x) for x in target)))
        moves.append(LeaderMove(party_id=party.party_id, rule=rule, share=float(now[i]), shift=float(np.linalg.norm(target - here))))
    return moved, moves


def _decide(
    i: int, party: Party, rule: str, step: float, here: np.ndarray, now: np.ndarray, supporters: np.ndarray,
    positions: np.ndarray, priorities: np.ndarray, platforms: np.ndarray, rng: np.random.Generator,
) -> tuple[np.ndarray, Party]:
    """Where `rule` takes party `i`, and the party with the state its leader keeps (a hunter's heading and share)."""
    if rule == "aggregator":
        own = positions[supporters == i]
        return (_toward(here, own.mean(axis=0), step) if len(own) else here), party
    if rule == "hunter":
        return _hunt(party, step, here, float(now[i]), rng)
    if rule == "explorer":
        return _explore(i, step, here, float(now[i]), positions, priorities, platforms, rng), party
    return here, party


def _hunt(party: Party, step: float, here: np.ndarray, share: float, rng: np.random.Generator) -> tuple[np.ndarray, Party]:
    """Keep going while the share grows; else a random heading in the half-space behind the old one."""
    heading = _unit(rng, len(here))
    if party.heading is not None and party.last_share is not None:
        old = np.array(party.heading)
        if share > party.last_share:
            heading = old
        elif float(heading @ old) > 0:
            heading = -heading
    return here + step * heading, dataclasses.replace(party, heading=tuple(float(x) for x in heading), last_share=share)


def _explore(
    i: int, step: float, here: np.ndarray, share: float, positions: np.ndarray, priorities: np.ndarray,
    platforms: np.ndarray, rng: np.random.Generator,
) -> np.ndarray:
    """Poll EXPLORER_PROBES positions a step away, the other platforms where they are; take the best if it beats `share`."""
    best, best_share = here, share
    for _ in range(EXPLORER_PROBES):
        probe = np.clip(here + step * _unit(rng, len(here)), 0.0, 1.0)
        trial = platforms.copy()
        trial[i] = probe
        probe_share = float(shares(positions, priorities, trial)[i])
        if probe_share > best_share:
            best, best_share = probe, probe_share
    return best
