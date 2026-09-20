"""
api_public.py — Vote Lab Public Research API v1.

Provides unauthenticated endpoints for researchers and developers to
integrate Vote Lab's simulation engine into their own projects.

Rate limits (applied per remote IP):
    POST /api/v1/simulate : 10 requests/minute
    POST /api/v1/compare  :  5 requests/minute

All other endpoints are unlimited.
"""
from __future__ import annotations

from typing import Any


from api.engine.utils.demographic_data import unseeded_rng_pair
from api.engine.utils.simulation_voting_utils import create_voter, create_candidate
from api.engine.utils.simulation_metrics import compare_all_methods
from api.engine.constants import DEFAULT_ISSUES
from api.engine.utils.error_handling import log_and_error_response
from api.engine.utils.logger import get_logger
from api.engine.utils.method_registry import PUBLIC_METHOD_ALIASES

log = get_logger(__name__)


# ── Methods catalogue ─────────────────────────────────────────────────────────
#
# Every key here is either a name compare_all_methods reports under, or a
# public alias PUBLIC_METHOD_ALIASES resolves to one (see that constant's
# docstring in method_registry.py). test_public_v1.py's
# test_methods_catalog_matches_what_compare_all_methods_computes checks this
# set against compare_all_methods' real output, not a hand-copied list, so the
# two cannot drift silently again. "positional_score" used to be listed here
# too, but no key compare_all_methods reports answers to it -- filtering
# /simulate or /compare by that name silently returned an empty methods dict.

METHODS_CATALOG: dict[str, dict[str, str]] = {
    "plurality":          {"name": "Plurality (FPTP)",       "family": "ranked", "ref": "Duverger (1954)"},
    "two_round":          {"name": "Two-Round",              "family": "ranked", "ref": "Blais & Loewen (2009)"},
    "borda":              {"name": "Borda Count",            "family": "ranked", "ref": "Borda (1781)"},
    "approval":           {"name": "Approval Voting",        "family": "ranked", "ref": "Brams & Fishburn (1983)"},
    "irv":                {"name": "IRV (Ranked Choice)",    "family": "ranked", "ref": "Tideman (1987)"},
    "coombs":             {"name": "Coombs' Method",         "family": "ranked", "ref": "Coombs (1964)"},
    "bucklin":            {"name": "Bucklin Voting",         "family": "ranked", "ref": "Hoag & Hallett (1926)"},
    "minimax":            {"name": "Minimax",                "family": "ranked", "ref": "Young & Levenglick (1978)"},
    "schulze":            {"name": "Schulze Method",         "family": "ranked", "ref": "Schulze (2011)"},
    "kemeny_young":       {"name": "Kemeny-Young",           "family": "ranked", "ref": "Kemeny (1959)"},
    "condorcet":          {"name": "Condorcet (Copeland)",   "family": "ranked", "ref": "Condorcet (1785)"},
    "nanson":             {"name": "Nanson's Method",        "family": "ranked", "ref": "Nanson (1882)"},
    "baldwin":            {"name": "Baldwin's Method",       "family": "ranked", "ref": "Baldwin (1926)"},
    "ranked_pairs":       {"name": "Ranked Pairs",           "family": "ranked", "ref": "Tideman (1987)"},
    "black":              {"name": "Black's Method",         "family": "ranked", "ref": "Black (1958)"},
    "anti_plurality":     {"name": "Anti-Plurality (Veto)",  "family": "ranked", "ref": "Felsenthal (2012)"},
    "dowdall":            {"name": "Dowdall System",         "family": "ranked", "ref": "Fraenkel & Grofman (2014)"},
    "raynaud":            {"name": "Raynaud's Method",       "family": "ranked", "ref": "Raynaud (1981)"},
    "benham":             {"name": "Benham's Method",        "family": "ranked", "ref": "Tideman (2006)"},
    "river":              {"name": "River Method",           "family": "ranked", "ref": "Tideman (2006)"},
    "smith_irv":          {"name": "Smith/IRV",              "family": "ranked", "ref": "Tideman (2006)"},
    "split_cycle":        {"name": "Split Cycle",            "family": "ranked", "ref": "Holliday & Pacuit (2021)"},
    "simple_score":       {"name": "Simple Score",           "family": "score",  "ref": "Smith (2000)"},
    "star_voting":        {"name": "STAR Voting",            "family": "score",  "ref": "Equal Vote (2014)"},
    "median_voting":      {"name": "Median Judgment",        "family": "score",  "ref": "Balinski & Laraki (2010)"},
    "mean_median_hybrid": {"name": "Mean-Median Hybrid",     "family": "score",  "ref": "Merrill & Grofman (1999)"},
    "variance_based":     {"name": "Variance-Based",         "family": "score",  "ref": "Laslier (2006)"},
    "cumulative":         {"name": "Cumulative Voting",      "family": "score",  "ref": "Guinier (1994)"},
    "maximin":            {"name": "Maximin (Rawlsian)",     "family": "score",  "ref": "Rawls (1971)"},
    "nash":               {"name": "Nash (Proportional)",    "family": "score",  "ref": "Nash (1950)"},
    "majority_judgment":  {"name": "Majority Judgment",      "family": "score",  "ref": "Balinski & Laraki (2010)"},
    "evaluative":         {"name": "Evaluative Voting",      "family": "score",  "ref": "Baujard & Igersheim (2010)"},
    "quadratic":          {"name": "Quadratic Voting",       "family": "intensity", "ref": "Posner & Weyl (2018)"},
    "random_ballot":      {"name": "Random Ballot",          "family": "lottery",   "ref": "Gibbard (1977)"},
}

_REVERSE_PUBLIC_METHOD_ALIASES = {v: k for k, v in PUBLIC_METHOD_ALIASES.items()}


def _apply_public_aliases(methods: dict[str, Any]) -> dict[str, Any]:
    """Rewrite every engine-internal key PUBLIC_METHOD_ALIASES has a public
    name for (e.g. "copeland" -> "condorcet"), so a caller never sees a name
    the catalogue doesn't advertise -- including on the unfiltered "all" path,
    which used to return the engine's own "copeland" instead of the
    catalogue's documented "condorcet"."""
    return {_REVERSE_PUBLIC_METHOD_ALIASES.get(k, k): v for k, v in methods.items()}


def _filter_methods(methods: dict[str, Any], methods_req: Any) -> dict[str, Any]:
    """Keep only the requested methods (either name works for an aliased
    rule, e.g. "condorcet" or "copeland"). `methods_req` is "all", or any
    list containing "all", when nothing should be filtered -- a caller who
    sends `["all"]` (a schema-valid List[str]) means the same as the bare
    string "all", not "the one method literally named 'all'"."""
    if not isinstance(methods_req, list) or "all" in methods_req:
        return methods
    wanted = {PUBLIC_METHOD_ALIASES.get(m, m) for m in methods_req}
    return {k: v for k, v in methods.items() if k in wanted}


_CANDIDATE_NAMES = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hugo"]


def _build_simple_population(
    num_voters: int,
    num_candidates: int,
    ideology: str = "random",
) -> tuple[list[Any], list[Any], list[Any]]:
    """Create a synthetic population for API simulations.

    These endpoints take no seed, so the draws are genuinely random -- but from
    a call-scoped RNG pair, not the process-wide singletons another request may
    be drawing from at the same time.
    """
    issues     = DEFAULT_ISSUES
    names      = _CANDIDATE_NAMES[:num_candidates]
    rng, np_rng = unseeded_rng_pair()
    candidates = [
        create_candidate(issues, i, name, ["Green", "Conservative", "Liberal", "Independent"][i % 4],
                         rng=rng)
        for i, name in enumerate(names)
    ]
    voters = [create_voter(issues, i, ideology_distribution=ideology, rng=rng, np_rng=np_rng)
              for i in range(num_voters)]
    return voters, candidates, issues


# ── Pure-compute workers (shared by Flask + the FastAPI /api/v1 router) ─────────
#
# Phase 4.5.a.4: the request-handling logic lives in these framework-agnostic
# `_*_worker` / `_*_payload` functions so the FastAPI sibling (api/routes/
# public.py) can reuse it. The Flask routes below are thin delegates kept as a
# rollback target until Flask is fully retired.


def _methods_payload(family: str = "") -> dict[str, Any]:
    """Build the GET /methods response body. `family` filters by method family."""
    family = family.strip().lower()
    methods = [
        {"key": k} | v
        for k, v in METHODS_CATALOG.items()
        if not family or v["family"] == family
    ]
    return {
        "count":    len(methods),
        "methods":  methods,
        "families": sorted({v["family"] for v in METHODS_CATALOG.values()}),
    }


def _simulate_worker(data: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """
    Run a multi-method simulation on a synthetic population.

    `num_candidates` / `num_voters` are clamped silently (2–8 / 50–2000) so an
    out-of-range value returns 200 with a capped run, not an error.
    Returns (body, status_code).
    """
    try:
        num_candidates = max(2, min(8,    int(data.get("num_candidates", 4))))
        num_voters     = max(50, min(2000, int(data.get("num_voters", 500))))
        ideology       = str(data.get("ideology_distribution", "random"))
        methods_req    = data.get("methods", "all")
    except (TypeError, ValueError) as exc:
        return {"error": f"Invalid parameter: {exc}"}, 400

    try:
        voters, candidates, issues = _build_simple_population(num_voters, num_candidates, ideology)
        # v1 publishes strategic_vulnerability in its response envelope
        # (see this module's OPENAPI_SPEC example), so it opts in.
        result = compare_all_methods(voters, candidates, issues, compute_strategic=True)
    except Exception as exc:
        return log_and_error_response(
            log, "public.simulate.failed", {"error": f"Simulation failed: {exc}"},
        )

    result["methods"] = _apply_public_aliases(_filter_methods(result["methods"], methods_req))

    return result, 200


def _compare_worker(data: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """
    Multi-method comparison with optional blank-vote rule. Same shape as
    `_simulate_worker`, plus blank_pct + per-method blank_rule_applied when a
    blank rule is set. Returns (body, status_code).
    """
    from api.engine.utils.blank_vote_rules import BlankVoteRule, apply_blank_rule

    try:
        num_candidates = max(2, min(8,    int(data.get("num_candidates", 4))))
        num_voters     = max(50, min(2000, int(data.get("num_voters", 500))))
        ideology       = str(data.get("ideology_distribution", "random"))
        blank_rule_str = data.get("blank_rule", "")
        methods_req    = data.get("methods", "all")
    except (TypeError, ValueError) as exc:
        return {"error": f"Invalid parameter: {exc}"}, 400

    blank_vote = bool(blank_rule_str)
    blank_rule = BlankVoteRule.SYMBOLIC
    if blank_vote:
        try:
            blank_rule = BlankVoteRule(blank_rule_str)
        except ValueError:
            return {
                "error": f"Unknown blank_rule '{blank_rule_str}'. "
                         f"Options: {[r.value for r in BlankVoteRule]}"
            }, 400

    try:
        voters, candidates, issues = _build_simple_population(num_voters, num_candidates, ideology)
        result = compare_all_methods(
            voters, candidates, issues, blank_vote=blank_vote, compute_strategic=True,
        )
    except Exception as exc:
        return log_and_error_response(
            log, "public.compare.failed", {"error": f"Simulation failed: {exc}"},
        )

    if blank_vote:
        blank_pct = result.get("blank_pct", 0.0)
        for md in result["methods"].values():
            md["blank_rule_applied"] = apply_blank_rule(
                winner=md.get("winner"), blank_pct=blank_pct, rule=blank_rule,
            )

    result["methods"] = _apply_public_aliases(_filter_methods(result["methods"], methods_req))

    return result, 200


def _real_elections_payload() -> dict[str, Any]:
    """Build the GET /real-elections response body."""
    from api.engine.utils.real_election_data import REAL_ELECTIONS

    elections = [
        {
            "key":                  key,
            "name":                 data["name"],
            "year":                 data["year"],
            "country":              data["country"],
            "num_candidates":       len(data["candidates"]),
            "estimated_blank_pct":  data.get("estimated_blank_pct", 0),
            "source":               data.get("source", ""),
        }
        for key, data in REAL_ELECTIONS.items()
    ]

    return {"count": len(elections), "elections": elections}


# ── GET /api/v1/methods ───────────────────────────────────────────────────────



# ── POST /api/v1/simulate ─────────────────────────────────────────────────────



# ── POST /api/v1/compare ──────────────────────────────────────────────────────



# ── GET /api/v1/real-elections ────────────────────────────────────────────────



# ── GET /api/v1/openapi.json ──────────────────────────────────────────────────
# Hand-written on purpose, not `app.openapi()` filtered to /api/v1: this is the
# EXTERNAL contract, and the v1 response models carry extra="allow" so the app
# returns a superset of what it promises (see api/schemas/public_api.py). A
# generated spec would publish that superset -- every unmodeled field and every
# /api/v2 schema -- as the promise.

OPENAPI_SPEC: dict[str, Any] = {
    "openapi": "3.0.0",
    "info": {
        "title":       "Vote Lab Research API",
        "version":     "1.0.0",
        "description": (
            "Public API for the Vote Lab electoral simulation engine. "
            "Provides programmatic access to multi-method vote simulations, "
            "historical election data, and blank-vote analysis. "
            "No authentication required. Rate limits apply to POST endpoints."
        ),
        "contact": {"name": "Vote Lab", "url": "https://github.com/Burbanit0/Vote-App"},
        "license": {"name": "MIT"},
    },
    "servers": [
        {"url": "http://localhost:4434", "description": "Local development"},
    ],
    "paths": {
        "/api/v1/methods": {
            "get": {
                "summary": "List voting methods",
                "description": "Returns all 34 voting methods with name, family, and academic reference.",
                "operationId": "listMethods",
                "parameters": [
                    {
                        "name": "family",
                        "in": "query",
                        "description": "Filter by method family: 'ranked', 'score', 'intensity', or 'lottery'",
                        "required": False,
                        "schema": {"type": "string", "enum": ["ranked", "score", "intensity", "lottery"]},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "example": {
                                    "count": 34,
                                    "methods": [
                                        {"key": "plurality", "name": "Plurality (FPTP)", "family": "ranked", "ref": "Duverger (1954)"},
                                        {"key": "borda",     "name": "Borda Count",      "family": "ranked", "ref": "Borda (1781)"},
                                    ],
                                    "families": ["intensity", "lottery", "ranked", "score"],
                                }
                            }
                        },
                    }
                },
                "tags": ["Methods"],
            }
        },
        "/api/v1/simulate": {
            "post": {
                "summary": "Run a simulation",
                "description": "Runs a multi-method simulation on a synthetic population generated by the spatial utility model.",
                "operationId": "simulate",
                "x-ratelimit": "10 requests per minute per IP",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "num_candidates":         {"type": "integer", "minimum": 2, "maximum": 8,    "default": 4, "example": 4},
                                    "num_voters":             {"type": "integer", "minimum": 50, "maximum": 2000, "default": 500, "example": 500},
                                    "methods":                {"oneOf": [{"type": "string", "enum": ["all"]}, {"type": "array", "items": {"type": "string"}}], "default": "all"},
                                    "ideology_distribution":  {"type": "string", "enum": ["random", "centrist", "polarized", "left_skewed", "right_skewed"], "default": "random"},
                                }
                            },
                            "example": {"num_candidates": 4, "num_voters": 500, "methods": ["plurality", "borda", "schulze"]},
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Simulation results",
                        "content": {
                            "application/json": {
                                "example": {
                                    "condorcet_winner": "Alice",
                                    "methods": {
                                        "plurality": {"winner": "Alice", "bayesian_regret": 0.1234, "majority_satisfaction": 0.72, "condorcet_consistent": True, "strategic_vulnerability": 0.28},
                                        "borda":     {"winner": "Bob",   "bayesian_regret": 0.0876, "majority_satisfaction": 0.81, "condorcet_consistent": False, "strategic_vulnerability": 0.19},
                                    },
                                }
                            }
                        },
                    },
                    "400": {"description": "Invalid parameters"},
                    "429": {"description": "Rate limit exceeded (10 req/min)"},
                },
                "tags": ["Simulation"],
            }
        },
        "/api/v1/compare": {
            "post": {
                "summary": "Multi-method comparison with blank vote",
                "description": "Compare methods with optional blank-vote constitutional rules.",
                "operationId": "compare",
                "x-ratelimit": "5 requests per minute per IP",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "num_candidates":        {"type": "integer", "minimum": 2, "maximum": 8, "default": 4},
                                    "num_voters":            {"type": "integer", "minimum": 50, "maximum": 2000, "default": 500},
                                    "blank_rule":            {"type": "string", "enum": ["symbolic", "competitive", "threshold_30", "majority_required"], "description": "Leave empty to disable blank vote"},
                                    "methods":               {"oneOf": [{"type": "string", "enum": ["all"]}, {"type": "array", "items": {"type": "string"}}], "default": "all"},
                                    "ideology_distribution": {"type": "string", "default": "random"},
                                }
                            },
                            "example": {"num_candidates": 3, "num_voters": 800, "blank_rule": "threshold_30", "methods": "all"},
                        }
                    },
                },
                "responses": {
                    "200": {"description": "Comparison results (same shape as /simulate)"},
                    "400": {"description": "Invalid parameters"},
                    "429": {"description": "Rate limit exceeded (5 req/min)"},
                },
                "tags": ["Simulation"],
            }
        },
        "/api/v1/real-elections": {
            "get": {
                "summary": "List historical elections",
                "description": "Returns metadata for all historical elections in the Vote Lab dataset.",
                "operationId": "realElections",
                "responses": {
                    "200": {
                        "description": "Election list",
                        "content": {
                            "application/json": {
                                "example": {
                                    "count": 5,
                                    "elections": [
                                        {"key": "france_2022", "name": "Présidentielle française (1er tour)", "year": 2022, "country": "France", "num_candidates": 12, "estimated_blank_pct": 0.025, "source": "Ministère de l'Intérieur"},
                                    ],
                                }
                            }
                        },
                    }
                },
                "tags": ["Data"],
            }
        },
    },
    "tags": [
        {"name": "Methods",    "description": "Voting method catalogue"},
        {"name": "Simulation", "description": "Simulation and comparison endpoints"},
        {"name": "Data",       "description": "Historical election data"},
    ],
}
