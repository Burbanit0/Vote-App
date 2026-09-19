"""
Shared route-level helpers used by compare.py and advanced.py.

These are not simulation logic (that lives in api/engine/utils/) — they are
request-parsing and population-building helpers specific to the route layer.
"""
import random as _rng
from typing import Any, Optional

import numpy as np

from api.engine.utils.simulation_voting_utils import create_voter, create_candidate

from api.engine.constants import DEFAULT_ISSUES




_PARTY_CYCLE = ("Green", "Conservative", "Liberal", "Independent")


def _parse_candidate_configs(raw: list[Any]) -> list[dict[str, Any]]:
    """
    Normalise the candidates field from the request body.

    Accepts two formats:
      - List of strings:  ["Alice", "Bob"]
      - List of dicts:    [{"name": "Alice", "party": "Liberal",
                            "ideology_position": 0.3}, ...]

    Always returns a list of dicts with at least {"name", "party"} keys.
    """
    configs = []
    for i, item in enumerate(raw):
        if isinstance(item, str):
            configs.append({
                "name": item,
                "party": _PARTY_CYCLE[i % len(_PARTY_CYCLE)],
                "ideology_position": None,
            })
        else:
            configs.append({
                # str(): the schema accepts any JSON name, and an int name made the
                # engine return int winners in some runs and str in others.
                "name": str(item.get("name", f"Candidate {i + 1}")),
                "party": item.get("party", _PARTY_CYCLE[i % len(_PARTY_CYCLE)]),
                "ideology_position": item.get("ideology_position"),
            })
    return configs


def _build_population(
    candidate_configs: list[dict[str, Any]],
    num_voters: int,
    ideology_distribution: str = "random",
    rng: Optional[_rng.Random] = None,
    np_rng: Optional[np.random.RandomState] = None,
) -> tuple[list[Any], list[Any], list[str]]:
    """
    Create voters and candidates for a simulation run.

    candidate_configs — output of _parse_candidate_configs().
    Returns (voters, candidates, issues).

    rng/np_rng: optional local RNG instances threaded through to
    create_candidate/create_voter. Pass these when the caller runs several
    populations concurrently (e.g. Monte Carlo over a thread pool) so draws
    don't come from the shared random/np.random singletons — see
    api.domain.simulations.advanced._monte_carlo_worker for the pattern.
    """
    issues = DEFAULT_ISSUES
    candidates = [
        create_candidate(
            issues,
            i,
            cfg["name"],
            cfg["party"],
            ideology_position=cfg.get("ideology_position"),
            rng=rng,
        )
        for i, cfg in enumerate(candidate_configs)
    ]
    voters = [
        create_voter(issues, i, ideology_distribution=ideology_distribution, rng=rng, np_rng=np_rng)
        for i in range(num_voters)
    ]
    return voters, candidates, issues
