"""
api.domain.election — pure election compute, no Flask, no FastAPI, no DB.

All functions accept a `data: dict` and return `(body, http_status)`.
They are pure: same input = same output (modulo any `seed` field).

The actual worker implementations live in this package's sibling
`workers*.py` modules (workers.py plus the mechanisms/dynamics/behavioral/
playground/advanced decompositions). This `__init__.py` re-exports them under
the `api.domain.election` namespace, the only one the routes import from. Each
name used to arrive through a typed wrapper (`def nota(data): return
_nota_worker(data)`) whose docstring was the endpoint's one-liner; the aliases
below do the same job, and that one-liner now opens the worker's own docstring.
"""

from typing import Any
from api.domain.election.election_service import ElectionService

from api.domain.election.workers_playground import (
    _profile_simulate_worker as profile_simulate,
    _assembly_worker as assembly,
    _assembly_scorecard_worker as assembly_scorecard,
    _issue_voting_worker as issue_voting,
    _structural_fairness_worker as structural_fairness,
)
from api.domain.election.workers import (
    _combined_effects_worker as combined_effects,
    _campaign_sensitivity_worker as campaign_sensitivity,
    _coalition_worker as coalition,
    _simulate_pipeline_worker as simulate_pipeline,
    _districts_worker as districts,
    _primary_worker as primary,
    _divergence_worker as divergence,
    _interpret_worker as interpret,
)
from api.domain.election.workers_mechanisms import (
    _abstention_worker as abstention,
    _jury_worker as jury,
    _stv_worker as stv,
    _adaptive_worker as adaptive,
    _historical_replay_worker as historical_replay,
    _gerrymander_worker as gerrymander,
    _multiwinner_compare_worker as multiwinner_compare,
)
from api.domain.election.workers_behavioral import (
    _nota_worker as nota,
    _ballot_complexity_worker as ballot_complexity,
    _shy_voter_worker as shy_voter,
    _electoral_fatigue_worker as electoral_fatigue,
    _cascade_worker as cascade,
    _behavioral_biases_worker as behavioral_biases,
    _choice_overload_worker as choice_overload,
    _liquid_democracy_worker as liquid_democracy,
    _conviction_voting_worker as conviction_voting,
)
from api.domain.election.workers_advanced import (
    _deliberation_worker as deliberation,
    _sortition_worker as sortition,
    _demographic_turnout_worker as demographic_turnout,
    _compulsory_voting_worker as compulsory_voting,
    _party_dynamics_worker as party_dynamics,
    _power_indices_worker as power_indices,
)
from api.domain.election.workers_dynamics import (
    _hotelling_worker as hotelling,
    _polarization_worker as polarization,
    _affective_polarization_worker as affective_polarization,
)

# The namespace the routes import from — re-exported aliases need this to be
# explicit (a bare `X as Y` import reads as unused otherwise).
__all__ = [
    "abstention", "adaptive", "affective_polarization", "assembly",
    "assembly_scorecard", "ballot_complexity", "behavioral_biases",
    "campaign_sensitivity", "cascade", "choice_overload", "coalition",
    "combined_effects", "compulsory_voting", "conviction_voting", "deliberation",
    "demographic_turnout", "districts", "divergence", "electoral_fatigue",
    "gerrymander", "historical_replay", "hotelling", "interpret", "issue_voting",
    "jury", "liquid_democracy", "multiwinner_compare", "nota", "party_dynamics",
    "polarization", "power_indices", "primary", "profile_simulate", "shy_voter",
    "simulate", "simulate_pipeline", "sortition", "structural_fairness", "stv",
]

def simulate(data: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Run the unified election pipeline."""
    return ElectionService.simulate(data)
