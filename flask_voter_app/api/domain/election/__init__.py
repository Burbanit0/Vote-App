"""
api.domain.election — pure election compute, no Flask, no FastAPI, no DB.

All functions accept a `data: dict` and return `(body, http_status)`.
They are pure: same input = same output (modulo any `seed` field).

The bodies of these functions were already extracted as workers in
Sprint A2 (combined-effects / campaign-sensitivity / simulate-pipeline)
and Sprint C1 (simulate). This module re-exports them under the
`api.domain` namespace so the FastAPI side can import them without
reaching back into `app.routes.election` (Flask-era namespace).

When Phase 4 retires Flask, these aliases will be replaced with the
canonical implementations moved here for real, and the corresponding
Flask workers will be deleted.
"""
from api.domain.election.workers import (
    _abstention_worker,
    _adaptive_worker,
    _campaign_sensitivity_worker,
    _coalition_worker,
    _combined_effects_worker,
    _districts_worker,
    _divergence_worker,
    _gerrymander_worker,
    _historical_replay_worker,
    _interpret_worker,
    _jury_worker,
    _multiwinner_compare_worker,
    _primary_worker,
    _simulate_pipeline_worker,
    _stv_worker,
)
# Spatial-dynamics / equilibrium workers (workers.py decomposition).
from api.domain.election.workers_dynamics import (
    _affective_polarization_worker,
    _hotelling_worker,
    _polarization_worker,
    _quadratic_funding_worker,
)
# Behavioural / research-panel workers (workers.py decomposition).
from api.domain.election.workers_behavioral import (
    _ballot_complexity_worker,
    _behavioral_biases_worker,
    _cascade_worker,
    _choice_overload_worker,
    _conviction_voting_worker,
    _electoral_fatigue_worker,
    _liquid_democracy_worker,
    _nota_worker,
    _shy_voter_worker,
)
# Lab-reshape playground workers, split into their own module (workers.py decomposition).
from api.domain.election.workers_playground import (
    _assembly_scorecard_worker,
    _assembly_worker,
    _issue_voting_worker,
    _profile_simulate_worker,
    _structural_fairness_worker,
    _temporal_worker,
)
# Governance / advanced-mechanism workers (workers.py decomposition).
from api.domain.election.workers_advanced import (
    _compulsory_voting_worker,
    _deliberation_worker,
    _demographic_turnout_worker,
    _party_dynamics_worker,
    _power_indices_worker,
    _sortition_worker,
)
from api.domain.election.election_service import ElectionService


def simulate(data: dict) -> tuple[dict, int]:
    """Run the unified election pipeline."""
    return ElectionService.simulate(data)


def profile_simulate(data: dict) -> tuple[dict, int]:
    """Lab reshape P1: run every method over a profile built from a user-chosen
    preference source (spatial / impartial / mallows / urn / handcrafted)."""
    return _profile_simulate_worker(data)


def assembly(data: dict) -> tuple[dict, int]:
    """Lab reshape P3: party-level seats under PR / FPTP / MMP over one shared
    electorate — proportionality, fragmentation, wasted votes, coalitions."""
    return _assembly_worker(data)


def assembly_scorecard(data: dict) -> tuple[dict, int]:
    """Lab reshape P5: Monte-Carlo scorecard — six [0,1] axes with bands for
    each structure (pr/fptp/mmp) over re-rolled electorates."""
    return _assembly_scorecard_worker(data)


def temporal(data: dict) -> tuple[dict, int]:
    """Frontier FA-3: N sequential elections with party adaptation and voter
    attachment — is the system still good after repeated play?"""
    return _temporal_worker(data)


def issue_voting(data: dict) -> tuple[dict, int]:
    """Frontier FB-2: issue-by-issue majorities vs the bundled platform vote —
    the Ostrogorski paradox / discursive dilemma."""
    return _issue_voting_worker(data)


def structural_fairness(data: dict) -> tuple[dict, int]:
    """Frontier FC-2: malapportionment, efficiency gap, Penrose square-root
    council, and cumulative-vs-bloc at-large voting."""
    return _structural_fairness_worker(data)


def combined_effects(data: dict) -> tuple[dict, int]:
    """2x2x2 factorial: run the same electorate under all 8 combinations
    of blank-vote / campaign / information-model ON-OFF."""
    return _combined_effects_worker(data)


def campaign_sensitivity(data: dict) -> tuple[dict, int]:
    """Snapshot the same electorate at multiple campaign days to measure
    method-by-method winner stability over time."""
    return _campaign_sensitivity_worker(data)


def coalition(data: dict) -> tuple[dict, int]:
    """Per-method D'Hondt seat allocation + greedy coalition formation."""
    return _coalition_worker(data)


def abstention(data: dict) -> tuple[dict, int]:
    """Iterated abstention model with poll-feedback over N rounds."""
    return _abstention_worker(data)


# ── Perturber endpoints (Phase 3 batch 3) ──────────────────────────────────

def nota(data: dict) -> tuple[dict, int]:
    """NOTA (None Of The Above) as an official ballot option."""
    return _nota_worker(data)


def ballot_complexity(data: dict) -> tuple[dict, int]:
    """Null-vote rate per method as a function of ballot complexity."""
    return _ballot_complexity_worker(data)


def shy_voter(data: dict) -> tuple[dict, int]:
    """Bradley / Shy Tory effect: socially-sensitive candidates underpolled."""
    return _shy_voter_worker(data)


def electoral_fatigue(data: dict) -> tuple[dict, int]:
    """Turnout decay over repeated elections; residual electorate drifts toward partisans."""
    return _electoral_fatigue_worker(data)


# ── Perturber endpoints (Phase 3 batch 4) ──────────────────────────────────

def cascade(data: dict) -> tuple[dict, int]:
    """Sequential voting with information cascades (Bikhchandani 1992)."""
    return _cascade_worker(data)


def behavioral_biases(data: dict) -> tuple[dict, int]:
    """Expressive voting + bullet voting + primacy effect on outcomes."""
    return _behavioral_biases_worker(data)


def choice_overload(data: dict) -> tuple[dict, int]:
    """Schwartz 2004 paradox: heuristics dominate beyond overload_threshold."""
    return _choice_overload_worker(data)


def deliberation(data: dict) -> tuple[dict, int]:
    """DeGroot opinion update across a network, then vote."""
    return _deliberation_worker(data)


# ── Perturber endpoints (Phase 3 batch 5) ──────────────────────────────────

def jury(data: dict) -> tuple[dict, int]:
    """Condorcet Jury Theorem: P(majority correct | per-voter competence p)."""
    return _jury_worker(data)


def hotelling(data: dict) -> tuple[dict, int]:
    """Hotelling-Downs iterative best-response Nash equilibrium."""
    return _hotelling_worker(data)


def polarization(data: dict) -> tuple[dict, int]:
    """Per-ideology Esteban-Ray index + method robustness scan."""
    return _polarization_worker(data)


def sortition(data: dict) -> tuple[dict, int]:
    """Elected vs sortition pure vs stratified assembly comparison."""
    return _sortition_worker(data)


# ── Perturber endpoints (Phase 3 batch 6) ──────────────────────────────────

def affective_polarization(data: dict) -> tuple[dict, int]:
    """Iyengar 2019: voters penalise candidates from the opposing political camp."""
    return _affective_polarization_worker(data)


def demographic_turnout(data: dict) -> tuple[dict, int]:
    """Full population vs effective electorate via age × education turnout gaps."""
    return _demographic_turnout_worker(data)


def compulsory_voting(data: dict) -> tuple[dict, int]:
    """Voluntary vs compulsory voting: reluctant voters add null/random ballots."""
    return _compulsory_voting_worker(data)


def party_dynamics(data: dict) -> tuple[dict, int]:
    """Multi-election party-system evolution (Duverger's Law)."""
    return _party_dynamics_worker(data)


# ── Phase 3 batch 7 ─────────────────────────────────────────────────────────

def simulate_pipeline(data: dict) -> tuple[dict, int]:
    """Step-by-step pipeline animation for the simulation hub."""
    return _simulate_pipeline_worker(data)


def districts(data: dict) -> tuple[dict, int]:
    """N districts with locally shifted ideology, FPTP vs proportional."""
    return _districts_worker(data)


def primary(data: dict) -> tuple[dict, int]:
    """Internal primaries + general election."""
    return _primary_worker(data)


def stv(data: dict) -> tuple[dict, int]:
    """Single Transferable Vote + D'Hondt + FPTP comparison."""
    return _stv_worker(data)


# ── Phase 3 batch 8 ─────────────────────────────────────────────────────────

def adaptive(data: dict) -> tuple[dict, int]:
    """N rounds of adaptive/tactical voting with poll feedback."""
    return _adaptive_worker(data)


def historical_replay(data: dict) -> tuple[dict, int]:
    """Day-by-day historical replay with candidate overrides."""
    return _historical_replay_worker(data)


def gerrymander(data: dict) -> tuple[dict, int]:
    """Voters assigned to user-drawn rectangular districts."""
    return _gerrymander_worker(data)


def multiwinner_compare(data: dict) -> tuple[dict, int]:
    """STV / D'Hondt / SPAV / Phragmén / FPTP on the same electorate."""
    return _multiwinner_compare_worker(data)


# ── Phase 3 batch 9 (final) ────────────────────────────────────────────────

def divergence(data: dict) -> tuple[dict, int]:
    """Same electorate, with vs without blank vote."""
    return _divergence_worker(data)


def interpret(data: dict) -> tuple[dict, int]:
    """Deterministic interpretation of a /simulate result."""
    return _interpret_worker(data)


def quadratic_funding(data: dict) -> tuple[dict, int]:
    """Buterin/Hitzig/Weyl 2019 quadratic funding."""
    return _quadratic_funding_worker(data)


def liquid_democracy(data: dict) -> tuple[dict, int]:
    """Transitive delegation up to max_chain_length hops."""
    return _liquid_democracy_worker(data)


def conviction_voting(data: dict) -> tuple[dict, int]:
    """Polkadot-style conviction voting: tokens × multiplier(lock_days)."""
    return _conviction_voting_worker(data)


def power_indices(data: dict) -> tuple[dict, int]:
    """Shapley-Shubik and Banzhaf power indices for coalition bargaining."""
    return _power_indices_worker(data)
