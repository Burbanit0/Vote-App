"""ADR-035: generations turn over. Each tick a small share of ordinary citizens is replaced, in place.

Replacing a citizen *in their slot* keeps what the rest of the engine indexes by: the citizen id (so `range(n)`
still holds, which opinion dynamics require), the social ties (the newcomer is born into the circle the slot had)
and the slot's idiosyncratic issue residuals (`LatentStructure.residuals`, the part of a person's views no factor
explains, regenerated from the seed on every resume and so not redrawn here). Everything else about the person is
new: their views (the average of the circle they grew up in, plus noise: political socialisation, so a cohort
inherits what its elders came to think, hardened or not), their priorities, tolerance, ambition and awakening
threshold, their party (the nearest platform), a fresh emotional state, and their own anchor (`anchor_factors`),
which opinion dynamics then draw them back to instead of the slot's founding views.

Who is exempt: anyone holding an office or standing as a candidate (a former president, who is an elector with a
record, can be replaced, and the newcomer has none), and the sitting sortition chamber (it is seated for a year).

The stream is drawn once per slot per tick whoever is eligible, so its position never depends on who held office.
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
    """An ordinary citizen: no office, not a candidate, not seated in the sortition chamber."""
    return citizen.role == Role.ELECTOR and citizen.office == Office.NONE and citizen.sortition_seat_until_tick is None


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


def replace_generation(
    citizens: list[Citizen], structure: LatentStructure, graph: SocialGraph | None, parties: Sequence[Party],
    config: CitizensConfig, ticks_per_year: int, rng: np.random.Generator,
) -> list[Replacement]:
    """Replace, in place in `citizens`, each ordinary citizen the year's rate picks this tick (ascending id), and
    return who. A newcomer's circle is read as the generation stood before any of this tick's replacements."""
    draws = rng.random(len(citizens))
    chance = config.replacement_per_year / ticks_per_year
    chosen = [i for i, draw in enumerate(draws) if draw < chance and replaceable(citizens[i])]
    if not chosen:
        return []
    before = current_factors(citizens, structure)
    everyone, leaving = before.mean(axis=0), set(chosen)
    replaced = []
    for i in chosen:
        circle = sorted(j for j in (graph.neighbors[i] if graph is not None else ()) if j not in leaving)
        centre = before[circle].mean(axis=0) if circle else everyone
        factors = centre + rng.normal(0.0, config.newcomer_spread, size=centre.shape)
        citizens[i] = _born(citizens[i], factors, structure, parties, config, rng)
        replaced.append(Replacement(citizen_id=i, party_id=citizens[i].party_affiliation, circle=len(circle)))
    return replaced
