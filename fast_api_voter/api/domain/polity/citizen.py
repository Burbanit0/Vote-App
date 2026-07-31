"""
api.domain.polity.citizen — the unified Citizen entity (Lot 2).

One entity, not separate Voter/Candidate/Party types (design doc §2.1):
role transitions in place as the simulation progresses. This module only
covers the entity shape and deterministic population generation; role
transitions themselves live in simple_rules.py (Lot 6).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

import numpy as np

from api.domain.polity.config import CitizensConfig


class Role(str, Enum):
    ELECTOR = "electeur"
    CANDIDATE = "candidat"
    ELECTED = "elu"


class Office(str, Enum):
    NONE = "aucun"
    PRESIDENT = "president"
    DEPUTY = "depute"


_BETA_SPEC_RE = re.compile(r"^beta\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)$")


def _parse_beta_params(spec: str) -> tuple[float, float]:
    match = _BETA_SPEC_RE.match(spec.strip())
    if not match:
        raise ValueError(f"unsupported distribution spec: {spec!r} (expected 'beta(a, b)')")
    return float(match.group(1)), float(match.group(2))


@dataclass
class Citizen:
    """design doc §2.2. `role`/`office`/`term_end_tick` resolve audit
    blocker A3 (an "élu" can be président or député — two different mandates).
    """

    citizen_id: int
    issue_positions: tuple[float, ...]
    issue_priorities: tuple[float, ...]
    blank_threshold: float
    ambition_score: float
    role: Role = Role.ELECTOR
    office: Office = Office.NONE
    term_end_tick: int | None = None
    party_affiliation: str | None = None
    # DEMARRAGE-polity-v0.md §3.1: unused in v0 (deviation is zero by
    # construction without an LLM) but added now to avoid a schema
    # migration when mandate limits (§6bis.1) and mandate deviation
    # (§7bis.5) activate in v4. In v0, revealed_position is always pinned
    # equal to pledged_platform the moment a candidacy is declared.
    mandates_served: int = 0
    pledged_platform: tuple[float, ...] | None = None
    revealed_position: tuple[float, ...] | None = None


def generate_population(config: CitizensConfig, population_size: int, seed: int) -> list[Citizen]:
    """Deterministic population generation: the same (config, population_size,
    seed) always produces field-for-field identical citizens (Lot 2 test
    contract) — required for the end-to-end reproducibility test (Lot 8)."""
    if config.position_dist != "uniform":
        raise NotImplementedError(f"citizens.position_dist {config.position_dist!r} not supported in v0")
    if config.priority_dist != "dirichlet":
        raise NotImplementedError(f"citizens.priority_dist {config.priority_dist!r} not supported in v0")

    rng = np.random.default_rng(seed)
    n, k = population_size, config.issue_count

    # Fixed draw order is itself part of the determinism contract: changing
    # it changes every downstream value even at the same seed.
    positions = rng.uniform(0.0, 1.0, size=(n, k))
    priorities = rng.dirichlet(np.ones(k), size=n)
    blank_a, blank_b = _parse_beta_params(config.blank_threshold_dist)
    blank_thresholds = rng.beta(blank_a, blank_b, size=n)
    ambition_a, ambition_b = _parse_beta_params(config.ambition_dist)
    ambitions = rng.beta(ambition_a, ambition_b, size=n)

    return [
        Citizen(
            citizen_id=i,
            issue_positions=tuple(float(x) for x in positions[i]),
            issue_priorities=tuple(float(x) for x in priorities[i]),
            blank_threshold=float(blank_thresholds[i]),
            ambition_score=float(ambitions[i]),
        )
        for i in range(n)
    ]
