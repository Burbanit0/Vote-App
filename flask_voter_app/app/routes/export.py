"""
export.py — Research dataset export endpoints.

POST /api/export/simulation-dataset       → CSV download
POST /api/export/simulation-dataset-json  → JSON response

Both endpoints generate N reproducible scenarios (seeded) and return
one row per (scenario, voting method) with winner, quality metrics,
and cross-method comparison columns.
"""
from __future__ import annotations

import csv
import io
import random as _random
from typing import Any, cast

import numpy as _np

from flask import Blueprint, Response, jsonify, request

from app.constants import DEFAULT_ISSUES
from app.extensions import sim_limiter
from app.utils.simulation_metrics import compare_all_methods_mc
from app.utils.simulation_voting_utils import create_candidate, create_voter

export_bp = Blueprint("export", __name__, url_prefix="/api/export")

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


def _parse_request() -> tuple[int, int, int, int, str]:
    """Parse and validate the shared request body. Returns (num_scenarios, num_candidates, num_voters, seed, ideology)."""
    data          = request.get_json() or {}
    num_scenarios = int(data.get("num_scenarios",  100))
    num_candidates = int(data.get("num_candidates", 4))
    num_voters     = int(data.get("num_voters",     500))
    seed           = int(data.get("seed",           42))
    ideology       = str(data.get("ideology",       "random"))
    return num_scenarios, num_candidates, num_voters, seed, ideology


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


@export_bp.route("/simulation-dataset", methods=["POST"])
@sim_limiter.limit("10 per minute")
def export_csv() -> Response | tuple[Response, int]:
    """
    POST /api/export/simulation-dataset

    Body: { "num_scenarios": int, "num_candidates": int,
            "num_voters": int, "seed": int, "ideology": str }

    Returns a CSV file (text/csv) with one row per (scenario, method).
    """
    try:
        num_scenarios, num_candidates, num_voters, seed, ideology = _parse_request()
    except (TypeError, ValueError) as exc:
        return jsonify({"error": f"Invalid parameters: {exc}"}), 400

    if num_scenarios > _MAX_SCENARIOS:
        return jsonify({"error": f"num_scenarios must be ≤ {_MAX_SCENARIOS}"}), 400
    if num_scenarios < 1:
        return jsonify({"error": "num_scenarios must be ≥ 1"}), 400
    if not (2 <= num_candidates <= 8):
        return jsonify({"error": "num_candidates must be between 2 and 8"}), 400
    if not (10 <= num_voters <= 2_000):
        return jsonify({"error": "num_voters must be between 10 and 2000"}), 400

    rows = _generate_rows(num_scenarios, num_candidates, num_voters, seed, ideology)

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

    filename = f"votelab_dataset_{seed}.csv"
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@export_bp.route("/simulation-dataset-json", methods=["POST"])
@sim_limiter.limit("10 per minute")
def export_json() -> Response | tuple[Response, int]:
    """
    POST /api/export/simulation-dataset-json

    Same parameters as /simulation-dataset. Returns JSON for Python/R integration:
    { "meta": {...}, "columns": [...], "rows": [...] }
    """
    try:
        num_scenarios, num_candidates, num_voters, seed, ideology = _parse_request()
    except (TypeError, ValueError) as exc:
        return jsonify({"error": f"Invalid parameters: {exc}"}), 400

    if num_scenarios > _MAX_SCENARIOS:
        return jsonify({"error": f"num_scenarios must be ≤ {_MAX_SCENARIOS}"}), 400
    if num_scenarios < 1:
        return jsonify({"error": "num_scenarios must be ≥ 1"}), 400
    if not (2 <= num_candidates <= 8):
        return jsonify({"error": "num_candidates must be between 2 and 8"}), 400
    if not (10 <= num_voters <= 2_000):
        return jsonify({"error": "num_voters must be between 10 and 2000"}), 400

    rows = _generate_rows(num_scenarios, num_candidates, num_voters, seed, ideology)

    return cast(Response, jsonify({
        "meta": {
            "num_scenarios":  num_scenarios,
            "num_candidates": num_candidates,
            "num_voters":     num_voters,
            "seed":           seed,
            "ideology":       ideology,
            "total_rows":     len(rows),
        },
        "columns": CSV_COLUMNS,
        "rows":    rows,
    }))
