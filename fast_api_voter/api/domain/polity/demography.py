"""ADR-035: generations turn over. Each tick a small share of ordinary citizens is replaced, in place.

Replacing a citizen *in their slot* keeps what the rest of the engine indexes by: the citizen id (so `range(n)`
still holds, which opinion dynamics require), the social ties (the newcomer is born into the circle the slot had)
and the slot's idiosyncratic issue residuals (`LatentStructure.residuals`, the part of a person's views no factor
explains, regenerated from the seed on every resume and so not redrawn here). Everything else about the person is
new: their views (the average of the circle they grew up in, plus noise: political socialisation, so a cohort
inherits what its elders came to think, hardened or not), their priorities, tolerance, ambition and awakening
threshold, their party (the nearest platform), a fresh emotional state, and their own anchor (`anchor_factors`),
which opinion dynamics then draw them back to instead of the slot's founding views.

Who is exempt: anyone holding an office or standing as a candidate, anyone who has been president (the newcomer
would share their id in the office history), the sitting sortition chamber (it is seated for a year), and the
citizens the election in progress still counts on (the declared and the barred).

The stream is drawn for every slot the rate picks, exempt or not, so its position never depends on who held office.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from api.domain.polity.citizen import ACTIVE, Citizen, LatentStructure, Office, Role, _parse_beta_params
from api.domain.polity.config import CitizensConfig
from api.domain.polity.opinion_dynamics import current_factors
from api.domain.polity.parties import Party
from api.domain.polity.simple_rules import assign_party_affiliation
from api.domain.polity.social_graph import SocialGraph


@dataclass(frozen=True)
class Replacement:
    citizen_id: int
    party_id: int | None
    circle: int
    """How many citizens the newcomer's views were averaged over (0: the whole population's mean, for a slot with no tie left)."""


def replaceable(citizen: Citizen) -> bool:
    """An ordinary citizen: no office, never held the presidency (a newcomer sharing a former president's id
    would read as the same person in the office history and escape the term limit), not seated in the
    sortition chamber."""
    return (
        citizen.role == Role.ELECTOR and citizen.office == Office.NONE and citizen.mandates_served == 0
        and citizen.sortition_seat_until_tick is None
    )


def _traits(config: CitizensConfig, rng: np.random.Generator) -> tuple[np.ndarray, float, float, float]:
    """A newcomer's priorities, tolerance, ambition and awakening threshold, from the distributions the founding
    population was drawn from."""
    priorities = rng.dirichlet(np.ones(config.issue_count))
    blank = float(rng.beta(*_parse_beta_params(config.blank_threshold_dist)))
    ambition = float(rng.beta(*_parse_beta_params(config.ambition_dist)))
    awakening = float(rng.beta(*_parse_beta_params(config.base_threshold_dist)))
    return priorities, blank, ambition, awakening


def _newcomer(old: Citizen, factors: np.ndarray, structure: LatentStructure, config: CitizensConfig, rng: np.random.Generator) -> Citizen:
    """The slot's new person. Emotions and engagement start fresh where the run tracks them and stay untracked where it does not."""
    priorities, blank, ambition, awakening = _traits(config, rng)
    positions = structure.positions(factors[None, :], [old.citizen_id])[0]
    return Citizen(
        citizen_id=old.citizen_id,
        issue_positions=tuple(float(x) for x in positions),
        issue_priorities=tuple(float(x) for x in priorities),
        blank_threshold=blank,
        ambition_score=ambition,
        base_threshold=awakening,
        latent_factors=tuple(float(x) for x in factors),
        anchor_factors=tuple(float(x) for x in factors),
        anger=None if old.anger is None else 0.0,
        anxiety=None if old.anxiety is None else 0.0,
        enthusiasm=None if old.enthusiasm is None else 0.0,
        engagement=None if old.engagement is None else ACTIVE,
    )


def _born(old: Citizen, factors: np.ndarray, structure: LatentStructure, parties: Sequence[Party], config: CitizensConfig, rng: np.random.Generator) -> Citizen:
    """The slot's newcomer, with the party whose platform is nearest (none when there are no parties)."""
    newcomer = _newcomer(old, factors, structure, config, rng)
    if parties:
        newcomer.party_affiliation = assign_party_affiliation(newcomer, list(parties))
    return newcomer


def _socialised(
    slot: int, before: np.ndarray, everyone: np.ndarray, leaving: set[int], graph: SocialGraph | None, spread: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, int]:
    """The views a newcomer grows into: the mean of the neighbours who stay (the whole population's, for a slot with
    no tie left) plus noise, and how many neighbours that was."""
    circle = sorted(j for j in (graph.neighbors[slot] if graph is not None else ()) if j not in leaving)
    centre = before[circle].mean(axis=0) if circle else everyone
    return centre + rng.normal(0.0, spread, size=centre.shape), len(circle)


def replace_generation(
    citizens: list[Citizen], structure: LatentStructure, graph: SocialGraph | None, parties: Sequence[Party],
    config: CitizensConfig, ticks_per_year: int, rng: np.random.Generator, exempt: frozenset[int] = frozenset(),
) -> list[Replacement]:
    """Replace, in place in `citizens`, each ordinary citizen the year's rate picks this tick (ascending id), and
    return who. `exempt` are citizens the run is still counting on (a declared candidate, a barred one). A
    newcomer's circle is read as the generation stood before any of this tick's replacements. Every slot the
    rate picks gets its newcomer drawn, exempt or not, so the stream's position never depends on who held what."""
    draws = rng.random(len(citizens))
    chance = config.replacement_per_year / ticks_per_year
    picked = [i for i, draw in enumerate(draws) if draw < chance]
    if not picked:
        return []
    before = current_factors(citizens, structure)
    everyone, leaving = before.mean(axis=0), set(picked)
    replaced = []
    for i in picked:
        factors, circle = _socialised(i, before, everyone, leaving, graph, config.newcomer_spread, rng)
        newcomer = _born(citizens[i], factors, structure, parties, config, rng)
        if replaceable(citizens[i]) and i not in exempt:
            citizens[i] = newcomer
            replaced.append(Replacement(citizen_id=i, party_id=newcomer.party_affiliation, circle=circle))
    return replaced
