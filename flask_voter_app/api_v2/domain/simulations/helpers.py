"""
Shared route-level helpers used by simulation_compare.py and simulation_advanced.py.

These are not simulation logic (that lives in app/utils/) — they are
request-parsing and population-building helpers specific to the route layer.
"""
import random as _rng

from api_v2.engine.utils.simulation_voting_utils import create_voter, create_candidate
from api_v2.engine.utils.simulation_metrics import compare_all_methods
from api_v2.engine.utils.blank_vote_rules import BlankVoteRule, apply_blank_rule

from api_v2.engine.constants import DEFAULT_ISSUES, ECONOMY_ISSUES, ENV_ISSUES, SOCIAL_ISSUES

_PRESET_TO_DISTRIBUTION = {
    "polarized": "polarized",
    "centrist":  "centrist",
    "left":      "left_skewed",
    "right":     "right_skewed",
    "random":    "random",
}

_SCENARIO_METHODS = ["plurality", "irv", "borda", "schulze", "approval"]


def _build_scenario_candidates(candidates_raw: list, issues: list) -> list:
    """
    Build backend candidate dicts from the 3-issue frontend format.
    Skips entries with is_blank=True (those are handled via blank_vote flag).
    """
    real = []
    for i, c in enumerate(candidates_raw):
        if c.get("is_blank"):
            continue
        ideology = max(-1.0, min(1.0, float(c.get("ideology", 0.0))))
        pos      = (ideology + 1) / 2
        positions = c.get("positions", {})
        eco = max(0.0, min(1.0, float(positions.get("economy",     pos))))
        env = max(0.0, min(1.0, float(positions.get("environment", 1 - pos))))
        soc = max(0.0, min(1.0, float(positions.get("social",      1 - pos))))
        policies = {
            iss: eco if iss in ECONOMY_ISSUES
                 else env if iss in ENV_ISSUES
                 else soc if iss in SOCIAL_ISSUES
                 else 0.5
            for iss in issues
        }
        real.append({
            "id": i, "name": c.get("name", f"Candidate {i + 1}"),
            "party": "Independent", "party_lean": ideology,
            "ideology_position": pos, "policies": policies,
            "charisma": 0.7, "scandals": 0,
            "campaign_funds": 500_000, "experience": 10, "popularity": 0.6,
        })
    return real


def _build_scenario_voters(
    electorate: dict,
    issues: list,
    dissatisfaction_override: float = None,
) -> list:
    """Build voters from an electorate config dict."""
    num_voters    = max(10, int(electorate.get("num_voters", 500)))
    ideology_dist = _PRESET_TO_DISTRIBUTION.get(electorate.get("ideology_preset", "random"), "random")
    dissatisfaction = (
        dissatisfaction_override if dissatisfaction_override is not None
        else max(0.0, min(1.0, float(electorate.get("dissatisfaction_rate", 0.2))))
    )
    voters = [create_voter(issues, i, ideology_distribution=ideology_dist) for i in range(num_voters)]
    if dissatisfaction > 0:
        for v in voters:
            extra = dissatisfaction * _rng.betavariate(2, 2)
            v["blank_threshold"] = min(0.95, v["blank_threshold"] + extra)
    return voters


def _run_five_methods(
    voters: list,
    candidates: list,
    issues: list,
    blank_vote: bool = False,
    blank_rule: BlankVoteRule = BlankVoteRule.COMPETITIVE,
) -> dict:
    """
    Run compare_all_methods and filter results to the 5 citizen-facing methods.
    When blank_vote=True, applies blank_rule to each method result.
    """
    result = compare_all_methods(voters, candidates, issues, blank_vote=blank_vote)
    filtered = {
        "condorcet_winner": result.get("condorcet_winner"),
        "methods": {m: result["methods"][m] for m in _SCENARIO_METHODS if m in result["methods"]},
    }
    if blank_vote:
        blank_pct = result.get("blank_pct", 0.0)
        filtered["blank_pct"] = blank_pct
        for method_data in filtered["methods"].values():
            method_data["blank_rule_applied"] = apply_blank_rule(
                winner=method_data.get("winner"),
                blank_pct=blank_pct,
                rule=blank_rule,
            )
    return filtered


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
    issues = DEFAULT_ISSUES
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
