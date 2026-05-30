"""
api_v2.domain.export — research dataset row generation (Phase 4.5.b.3).

Pure compute relocated from app/routes/export.py: deterministic, reproducible
generation of one row per (scenario, voting method). Flask-free. The Flask
blueprint in app/routes/export.py and the FastAPI router both import from here.
"""
from __future__ import annotations

import random as _random
from typing import Any

import numpy as _np

from api_v2.engine.constants import DEFAULT_ISSUES
from api_v2.engine.utils.simulation_metrics import compare_all_methods_mc
from api_v2.engine.utils.simulation_voting_utils import create_candidate, create_voter

_CANDIDATE_NAMES = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hugo"]
_PARTY_CYCLE     = ["Green", "Conservative", "Liberal", "Independent"]
_KEY_METHODS     = ["plurality", "borda", "irv", "schulze", "approval"]
_MAX_SCENARIOS   = 1_000

CSV_COLUMNS = [
    "scenario_id", "num_candidates", "num_voters",
    "method", "winner", "winner_score",
    "condorcet_exists", "condorcet_winner",
    "bayesian_regret", "blank_rate", "blank_rule",
    "plurality_winner", "borda_winner", "irv_winner",
    "schulze_winner", "approval_winner", "methods_agree",
]


def _generate_rows(
    num_scenarios:  int,
    num_candidates: int,
    num_voters:     int,
    seed:           int,
    ideology:       str = "random",
) -> list[dict[str, Any]]:
    """
    Generate one row per (scenario, method) deterministically from *seed*.

    The global random state is seeded once at the start so that the same
    (num_scenarios, num_candidates, num_voters, seed) triple always produces
    identical output — important for research reproducibility.
    """
    _random.seed(seed)
    _np.random.seed(seed)
    issues = DEFAULT_ISSUES
    rows: list[dict[str, Any]] = []

    for s_id in range(1, num_scenarios + 1):
        cand_names = _CANDIDATE_NAMES[:num_candidates]
        candidates = [
            create_candidate(issues, i, name, _PARTY_CYCLE[i % len(_PARTY_CYCLE)])
            for i, name in enumerate(cand_names)
        ]
        voters = [
            create_voter(issues, i, ideology_distribution=ideology)
            for i in range(num_voters)
        ]

        result           = compare_all_methods_mc(voters, candidates, issues)
        condorcet_winner = result.get("condorcet_winner")
        condorcet_exists = 1 if condorcet_winner else 0
        methods_data     = result.get("methods", {})

        # Cross-method winner columns (scenario-level, repeated per row)
        key_winners = {m: (methods_data.get(m) or {}).get("winner") for m in _KEY_METHODS}
        winner_vals = [v for v in key_winners.values() if v]
        methods_agree = 1 if winner_vals and len(set(winner_vals)) == 1 else 0

        for method_name, mdata in methods_data.items():
            winner  = mdata.get("winner") or ""
            regret  = mdata.get("bayesian_regret")
            satisf  = mdata.get("majority_satisfaction")

            rows.append({
                "scenario_id":      s_id,
                "num_candidates":   num_candidates,
                "num_voters":       num_voters,
                "method":           method_name,
                "winner":           winner,
                "winner_score":     round(satisf, 4) if satisf is not None else "",
                "condorcet_exists": condorcet_exists,
                "condorcet_winner": condorcet_winner or "",
                "bayesian_regret":  round(regret, 6) if regret is not None else "",
                "blank_rate":       0,
                "blank_rule":       "none",
                "plurality_winner": key_winners.get("plurality") or "",
                "borda_winner":     key_winners.get("borda") or "",
                "irv_winner":       key_winners.get("irv") or "",
                "schulze_winner":   key_winners.get("schulze") or "",
                "approval_winner":  key_winners.get("approval") or "",
                "methods_agree":    methods_agree,
            })

    return rows
