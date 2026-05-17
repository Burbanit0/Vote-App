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

import json
import os
from typing import Any

from flask import Blueprint, Response, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.utils.simulation_voting_utils import create_voter, create_candidate
from app.utils.simulation_metrics import compare_all_methods
from app.constants import DEFAULT_ISSUES

api_public_bp = Blueprint("public_api", __name__, url_prefix="/api/v1")

# ── Module-level limiter — init_app() called in create_app() ──────────────────
_API_STORAGE = os.environ.get('REDIS_URL') or 'memory://'
_api_limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_API_STORAGE,
    default_limits=[],
)


def init_api_limiter(app: Any) -> None:
    """Bind the public-API limiter to the Flask app (called from create_app)."""
    _api_limiter.init_app(app)


# ── Methods catalogue ─────────────────────────────────────────────────────────

METHODS_CATALOG: dict[str, dict[str, str]] = {
    "plurality":          {"name": "Plurality (FPTP)",    "family": "ranked", "ref": "Duverger (1954)"},
    "two_round":          {"name": "Two-Round",           "family": "ranked", "ref": "Blais & Loewen (2009)"},
    "borda":              {"name": "Borda Count",         "family": "ranked", "ref": "Borda (1781)"},
    "approval":           {"name": "Approval Voting",     "family": "ranked", "ref": "Brams & Fishburn (1983)"},
    "irv":                {"name": "IRV (Ranked Choice)", "family": "ranked", "ref": "Tideman (1987)"},
    "coombs":             {"name": "Coombs' Method",      "family": "ranked", "ref": "Coombs (1964)"},
    "bucklin":            {"name": "Bucklin Voting",      "family": "ranked", "ref": "Hoag & Hallett (1926)"},
    "minimax":            {"name": "Minimax",             "family": "ranked", "ref": "Young & Levenglick (1978)"},
    "schulze":            {"name": "Schulze Method",      "family": "ranked", "ref": "Schulze (2011)"},
    "kemeny_young":       {"name": "Kemeny-Young",        "family": "ranked", "ref": "Kemeny (1959)"},
    "condorcet":          {"name": "Condorcet",           "family": "ranked", "ref": "Condorcet (1785)"},
    "positional_score":   {"name": "Positional Score",   "family": "score",  "ref": "Saari (1995)"},
    "simple_score":       {"name": "Simple Score",        "family": "score",  "ref": "Smith (2000)"},
    "star_voting":        {"name": "STAR Voting",         "family": "score",  "ref": "Equal Vote (2014)"},
    "median_voting":      {"name": "Median Judgment",     "family": "score",  "ref": "Balinski & Laraki (2010)"},
    "mean_median_hybrid": {"name": "Mean-Median Hybrid",  "family": "score",  "ref": "Merrill & Grofman (1999)"},
    "variance_based":     {"name": "Variance-Based",      "family": "score",  "ref": "Laslier (2006)"},
    "quadratic":          {"name": "Quadratic Voting",    "family": "intensity", "ref": "Posner & Weyl (2018)"},
}

_CANDIDATE_NAMES = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hugo"]


def _build_simple_population(
    num_voters: int,
    num_candidates: int,
    ideology: str = "random",
) -> tuple[list[Any], list[Any], list[Any]]:
    """Create a synthetic population for API simulations."""
    issues     = DEFAULT_ISSUES
    names      = _CANDIDATE_NAMES[:num_candidates]
    candidates = [
        create_candidate(issues, i, name, ["Green", "Conservative", "Liberal", "Independent"][i % 4])
        for i, name in enumerate(names)
    ]
    voters = [create_voter(issues, i, ideology_distribution=ideology) for i in range(num_voters)]
    return voters, candidates, issues


def _err(msg: str, code: int = 400) -> tuple[Response, int]:
    return jsonify({"error": msg}), code


# ── GET /api/v1/methods ───────────────────────────────────────────────────────

@api_public_bp.route("/methods", methods=["GET"])
def list_methods() -> tuple[Response, int]:
    """
    List all voting methods supported by the Vote Lab engine.

    Returns a catalogue of 16+ methods with name, family, and academic reference.
    """
    family = request.args.get("family", "").strip().lower()
    methods = [
        {"key": k, **v}
        for k, v in METHODS_CATALOG.items()
        if not family or v["family"] == family
    ]
    return jsonify({
        "count":   len(methods),
        "methods": methods,
        "families": sorted({v["family"] for v in METHODS_CATALOG.values()}),
    }), 200


# ── POST /api/v1/simulate ─────────────────────────────────────────────────────

@api_public_bp.route("/simulate", methods=["POST"])
@_api_limiter.limit("10 per minute")
def simulate() -> tuple[Response, int]:
    """
    Run a multi-method simulation on a synthetic population.

    Body (JSON):
        num_candidates      int   2–8      default 4
        num_voters          int   50–2000  default 500
        methods             list  subset of method keys, or "all"
        ideology_distribution str default "random"

    Returns:
        condorcet_winner : str | null
        methods          : { <key>: { winner, bayesian_regret, majority_satisfaction,
                                      condorcet_consistent, strategic_vulnerability } }
    """
    data = request.get_json() or {}

    try:
        num_candidates = max(2, min(8,    int(data.get("num_candidates", 4))))
        num_voters     = max(50, min(2000, int(data.get("num_voters", 500))))
        ideology       = str(data.get("ideology_distribution", "random"))
        methods_req    = data.get("methods", "all")
    except (TypeError, ValueError) as exc:
        return _err(f"Invalid parameter: {exc}")

    try:
        voters, candidates, issues = _build_simple_population(num_voters, num_candidates, ideology)
        result = compare_all_methods(voters, candidates, issues)
    except Exception as exc:
        return _err(f"Simulation failed: {exc}", 500)

    # Filter requested methods
    if methods_req != "all" and isinstance(methods_req, list):
        result["methods"] = {
            k: v for k, v in result["methods"].items() if k in methods_req
        }

    return jsonify(result), 200


# ── POST /api/v1/compare ──────────────────────────────────────────────────────

@api_public_bp.route("/compare", methods=["POST"])
@_api_limiter.limit("5 per minute")
def compare() -> tuple[Response, int]:
    """
    Run a multi-method comparison with optional blank-vote rule.

    Body (JSON):
        num_candidates      int    2–8      default 4
        num_voters          int    50–2000  default 500
        blank_rule          str    symbolic|competitive|threshold_30|majority_required
        methods             list   subset of method keys, or "all"
        ideology_distribution str  default "random"

    Returns same shape as /simulate, plus blank_pct when blank_vote is enabled.
    """
    from app.utils.blank_vote_rules import BlankVoteRule, apply_blank_rule

    data = request.get_json() or {}

    try:
        num_candidates = max(2, min(8,    int(data.get("num_candidates", 4))))
        num_voters     = max(50, min(2000, int(data.get("num_voters", 500))))
        ideology       = str(data.get("ideology_distribution", "random"))
        blank_rule_str = data.get("blank_rule", "")
        methods_req    = data.get("methods", "all")
    except (TypeError, ValueError) as exc:
        return _err(f"Invalid parameter: {exc}")

    blank_vote = bool(blank_rule_str)
    blank_rule = BlankVoteRule.SYMBOLIC
    if blank_vote:
        try:
            blank_rule = BlankVoteRule(blank_rule_str)
        except ValueError:
            return _err(f"Unknown blank_rule '{blank_rule_str}'. "
                        f"Options: {[r.value for r in BlankVoteRule]}")

    try:
        voters, candidates, issues = _build_simple_population(num_voters, num_candidates, ideology)
        result = compare_all_methods(voters, candidates, issues, blank_vote=blank_vote)
    except Exception as exc:
        return _err(f"Simulation failed: {exc}", 500)

    if blank_vote:
        blank_pct = result.get("blank_pct", 0.0)
        for md in result["methods"].values():
            md["blank_rule_applied"] = apply_blank_rule(
                winner=md.get("winner"), blank_pct=blank_pct, rule=blank_rule,
            )

    if methods_req != "all" and isinstance(methods_req, list):
        result["methods"] = {k: v for k, v in result["methods"].items() if k in methods_req}

    return jsonify(result), 200


# ── GET /api/v1/real-elections ────────────────────────────────────────────────

@api_public_bp.route("/real-elections", methods=["GET"])
def real_elections_public() -> tuple[Response, int]:
    """
    List all historical elections in the Vote Lab dataset.

    Returns metadata + estimated blank vote percentages for each election.
    """
    from app.utils.real_election_data import REAL_ELECTIONS

    elections = []
    for key, data in REAL_ELECTIONS.items():
        elections.append({
            "key":                  key,
            "name":                 data["name"],
            "year":                 data["year"],
            "country":              data["country"],
            "num_candidates":       len(data["candidates"]),
            "estimated_blank_pct":  data.get("estimated_blank_pct", 0),
            "source":               data.get("source", ""),
        })

    return jsonify({
        "count":     len(elections),
        "elections": elections,
    }), 200


# ── GET /api/v1/openapi.json ──────────────────────────────────────────────────

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
        {"url": "http://localhost:4433", "description": "Local development"},
    ],
    "paths": {
        "/api/v1/methods": {
            "get": {
                "summary": "List voting methods",
                "description": "Returns all 16+ voting methods with name, family, and academic reference.",
                "operationId": "listMethods",
                "parameters": [
                    {
                        "name": "family",
                        "in": "query",
                        "description": "Filter by method family: 'ranked', 'score', or 'intensity'",
                        "required": False,
                        "schema": {"type": "string", "enum": ["ranked", "score", "intensity"]},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "example": {
                                    "count": 18,
                                    "methods": [
                                        {"key": "plurality", "name": "Plurality (FPTP)", "family": "ranked", "ref": "Duverger (1954)"},
                                        {"key": "borda",     "name": "Borda Count",      "family": "ranked", "ref": "Borda (1781)"},
                                    ],
                                    "families": ["intensity", "ranked", "score"],
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


@api_public_bp.route("/openapi.json", methods=["GET"])
def openapi_spec() -> tuple[Response, int]:
    """Serve the OpenAPI 3.0 specification."""
    return jsonify(OPENAPI_SPEC), 200


def write_openapi_json(filepath: str) -> None:
    """Write the OpenAPI spec to disk (called from create_app)."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True) if os.path.dirname(filepath) else None
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(OPENAPI_SPEC, f, ensure_ascii=False, indent=2)
