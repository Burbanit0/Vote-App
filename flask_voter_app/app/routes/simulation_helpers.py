"""
Shared route-level helpers used by simulation_compare.py and simulation_advanced.py.

These are not simulation logic (that lives in app/utils/) — they are
request-parsing and population-building helpers specific to the route layer.
"""
from app.utils.simulation_voting_utils import create_voter, create_candidate

_DEFAULT_ISSUES = [
    "economy", "environment", "healthcare", "education", "taxes",
    "social_welfare", "agriculture", "public_transport", "defense",
    "gender_equality", "pensions", "climate_change", "housing",
    "immigration", "crime_safety", "technology_innovation",
    "minimum_wage", "business_regulation", "jobs", "infrastructure",
]

_PARTY_CYCLE = ["Green", "Conservative", "Liberal", "Independent"]


def _parse_candidate_configs(raw: list) -> list:
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
                "name": item.get("name", f"Candidate {i + 1}"),
                "party": item.get("party", _PARTY_CYCLE[i % len(_PARTY_CYCLE)]),
                "ideology_position": item.get("ideology_position"),
            })
    return configs


def _build_population(
    candidate_configs: list,
    num_voters: int,
    ideology_distribution: str = "random",
):
    """
    Create voters and candidates for a simulation run.

    candidate_configs — output of _parse_candidate_configs().
    Returns (voters, candidates, issues).
    """
    issues = _DEFAULT_ISSUES
    candidates = [
        create_candidate(
            issues,
            i,
            cfg["name"],
            cfg["party"],
            ideology_position=cfg.get("ideology_position"),
        )
        for i, cfg in enumerate(candidate_configs)
    ]
    voters = [
        create_voter(issues, i, ideology_distribution=ideology_distribution)
        for i in range(num_voters)
    ]
    return voters, candidates, issues
