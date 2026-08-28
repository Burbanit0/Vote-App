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
    party_affiliation: int | None = None
    # DEMARRAGE-polity-v0.md §3.1: unused in v0 (deviation is zero by
    # construction without an LLM) but added now to avoid a schema
    # migration when mandate limits (§6bis.1) and mandate deviation
    # (§7bis.5) activate in v4. In v0, revealed_position is always pinned
    # equal to pledged_platform the moment a candidacy is declared.
    mandates_served: int = 0
    pledged_platform: tuple[float, ...] | None = None
    revealed_position: tuple[float, ...] | None = None
    # v4 Lot 2: same "add now to avoid a schema migration later" precedent as the
    # fields above. base_threshold is always set to a real drawn value by
    # generate_population; the 0.0 default only exists because five call sites
    # outside this module construct Citizen without it (Lot 4's awakening gate
    # tests must set it explicitly -- 0.0 means "always awake"). legitimacy_capital
    # stays unread until Lot 3's initial_legitimacy/update_legitimacy.
    base_threshold: float = 0.0
    legitimacy_capital: float = 0.0
    # v4 Lot 3: support(t) = (1-decay)*m needs m (mandate strength) to
    # survive independently of legitimacy_capital, which update_legitimacy
    # overwrites every tick. Set once at election by
    # _hold_presidential_election, read every tick thereafter -- never
    # drawn by generate_population, so no RNG-order change.
    mandate_strength: float = 0.0
    # v4 Lot 4 (§7bis.4b): officeholder-scoped, like legitimacy_capital/
    # mandate_strength -- reset to 0.0 at election so a re-elected incumbent
    # doesn't carry over a previous term's accumulated street pressure.
    # Never drawn by generate_population, deliberately unclamped.
    street_pressure: float = 0.0
    # v4 Lot 5 (§7bis.4a): officeholder-scoped petition state -- at most one
    # open petition per target (concurrent_allowed is TRANCHÉ false), so a
    # single nullable "opened_since" tick plus a signer set express it
    # exactly. Reset (including the cooldown) at election by
    # reset_petition_state, never at vacate_office -- a defeated incumbent's
    # stale petition state stays for post-mortem journal legibility, same
    # precedent as pledged_platform/revealed_position not being cleared on a
    # term-end vacate. frozenset() is a legal bare dataclass default (only
    # list/dict/set are rejected); every mutation is a rebind, never
    # in-place, so there is no aliasing hazard between citizens.
    petition_open_since_tick: int | None = None
    petition_signers: frozenset[int] = frozenset()
    petition_cooldown_until_tick: int | None = None
    # v5 Lot 3 (§8): citizen-level, NOT officeholder-scoped -- unlike
    # street_pressure/legitimacy_capital/petition state, a citizen's own
    # residual awareness of a scandal or economic shock has no natural
    # attachment to whichever officeholder happens to be sitting, so it is
    # NEVER reset at _hold_presidential_election (contrast that function's
    # winner-reset block). Decays purely on events.salience_decay's own
    # schedule (accountability.update_event_salience). Never drawn by
    # generate_population, deliberately unclamped (same reasoning as
    # street_pressure/shock.py's x(t)).
    event_salience: float = 0.0
    # v6b Lot 2 (§6bis.3): sortition-chamber state -- deliberately NOT
    # Office/Role fields (a drawn citizen never holds an elected mandate;
    # see sortition_chamber.py's own docstring). sortition_seat_until_tick
    # is None when not currently seated; sortition_terms_served counts
    # PAST terms (incremented at seating time, not vacate time, mirroring
    # mandates_served's own "count at the start of the term" precedent).
    # Never drawn by generate_population.
    sortition_seat_until_tick: int | None = None
    sortition_terms_served: int = 0
    # v6b Lot 3 (§6bis.3, dt=11): a seated member's own currently-stated position,
    # distinct from issue_positions (the sincere anchor a sortition member never
    # campaigns to diverge from -- there is no pledged_platform to keep or break).
    # Set to issue_positions at each new seating (_run_sortition_rotation) -- a
    # fresh start every term, so a redrawn member (Lot 2's relaxed-pool fallback)
    # never inherits a previous, unrelated term's own drift. Never reset at vacate
    # (stale value has no live reader once sortition_seat_until_tick clears -- same
    # post-mortem-legibility precedent as pledged_platform/revealed_position).
    # Never drawn by generate_population.
    chamber_position: tuple[float, ...] | None = None


# plan-distribution-positions-seeds.md, Phase 1 (2026-08-25): position_dist
# is uniform's only alternative, added because a maximally-dispersed
# population (uniform, independent per dimension) has no center of mass a
# single candidate can realistically be close to for a majority of voters —
# root cause of the Blank-wins-outright finding (THEORY.md §10.10). Chosen
# over a plain multi-modal mixture specifically because a mixture would
# presuppose the answer to the question design doc §14.2 says the meso view
# exists to *observe* (do parties converge to a Downsian center, or settle
# into Kollman-Miller-Page polarized equilibria?) — factor scores are drawn
# from a single, unimodal Gaussian, so nothing about the starting population
# forces either outcome; only the correlation structure between issues is
# imposed, addressing the independent-dimensions critique a plain Gaussian
# doesn't. N_FACTORS=2 is not an arbitrary tuning knob: it matches the
# "axe économique / axe sociétal" pair design doc §14.2 already names for
# the meso visualization.
_FACTOR_STRUCTURE_N_FACTORS = 2
_FACTOR_STRUCTURE_FACTOR_STD = 1.0
_FACTOR_STRUCTURE_LOADING_STD = 1.0
_FACTOR_STRUCTURE_NOISE_STD = 0.3


def _generate_factor_structure_positions(rng: np.random.Generator, n: int, k: int) -> np.ndarray:
    """Low-rank factor model, sigmoid-squashed into (0, 1): position(i, j) =
    sigmoid(factors(i) . loadings(j) + noise(i, j)). loadings are drawn once
    per population (shared structure every citizen's positions are built
    from — this is what correlates the k issue dimensions, unlike uniform's
    independent per-dimension draw); factors and noise are drawn once per
    citizen. Calibrated (not guessed) against the shipped population_size=100/
    issue_count=20: 0/40 seeds ever let Blank win the two_round runoff, mean
    best-candidate population-wide acceptability 0.712 (stdev 0.054 across
    seeds — comparable in scale to uniform's own seed-to-seed variability,
    not artificially collapsed into a false consensus). Sigmoid, not clipping:
    compresses smoothly into the open interval, no artificial mass exactly at
    0 or 1 the way clipping a Gaussian would produce."""
    loadings = rng.normal(0.0, _FACTOR_STRUCTURE_LOADING_STD, size=(k, _FACTOR_STRUCTURE_N_FACTORS))
    factors = rng.normal(0.0, _FACTOR_STRUCTURE_FACTOR_STD, size=(n, _FACTOR_STRUCTURE_N_FACTORS))
    noise = rng.normal(0.0, _FACTOR_STRUCTURE_NOISE_STD, size=(n, k))
    raw = factors @ loadings.T + noise
    result: np.ndarray = 1.0 / (1.0 + np.exp(-raw))
    return result


def generate_population(config: CitizensConfig, population_size: int, seed: int) -> list[Citizen]:
    """Deterministic population generation: the same (config, population_size,
    seed) always produces field-for-field identical citizens (Lot 2 test
    contract) — required for the end-to-end reproducibility test (Lot 8)."""
    if config.position_dist not in ("uniform", "factor_structure"):
        raise NotImplementedError(f"citizens.position_dist {config.position_dist!r} not supported in v0")
    if config.priority_dist != "dirichlet":
        raise NotImplementedError(f"citizens.priority_dist {config.priority_dist!r} not supported in v0")

    rng = np.random.default_rng(seed)
    n, k = population_size, config.issue_count

    # Fixed draw order is itself part of the determinism contract: changing
    # it changes every downstream value even at the same seed. The two
    # position_dist branches consume DIFFERENT quantities from rng
    # (factor_structure draws loadings + per-citizen factors + noise, not one
    # flat (n, k) array), so priorities/thresholds/ambitions genuinely differ
    # between position_dist choices at the same seed -- nothing in this
    # codebase requires cross-branch agreement, only that a fixed (config,
    # population_size, seed) always reproduces the same population, which
    # holds independently for each branch.
    if config.position_dist == "uniform":
        positions = rng.uniform(0.0, 1.0, size=(n, k))
    else:
        positions = _generate_factor_structure_positions(rng, n, k)
    priorities = rng.dirichlet(np.ones(k), size=n)
    blank_a, blank_b = _parse_beta_params(config.blank_threshold_dist)
    blank_thresholds = rng.beta(blank_a, blank_b, size=n)
    ambition_a, ambition_b = _parse_beta_params(config.ambition_dist)
    ambitions = rng.beta(ambition_a, ambition_b, size=n)
    # v4 Lot 2: appended LAST -- draw order before this point is unchanged, so
    # every pre-existing field stays field-for-field identical at a fixed seed.
    base_a, base_b = _parse_beta_params(config.base_threshold_dist)
    base_thresholds = rng.beta(base_a, base_b, size=n)

    return [
        Citizen(
            citizen_id=i,
            issue_positions=tuple(float(x) for x in positions[i]),
            issue_priorities=tuple(float(x) for x in priorities[i]),
            blank_threshold=float(blank_thresholds[i]),
            ambition_score=float(ambitions[i]),
            base_threshold=float(base_thresholds[i]),
        )
        for i in range(n)
    ]
