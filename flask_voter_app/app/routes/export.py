"""
export.py — Flask delegates for the research dataset export endpoints.

POST /api/export/simulation-dataset       → CSV download
POST /api/export/simulation-dataset-json  → JSON response

Row generation now lives in api_v2.domain.export (Phase 4.5.b.3); this blueprint
stays thin until app/ is deleted in the final teardown.
"""
from __future__ import annotations

import csv
import io
from typing import cast

from flask import Blueprint, Response, jsonify, request

from app.extensions import sim_limiter
from api_v2.domain.export import CSV_COLUMNS, _MAX_SCENARIOS, _generate_rows

export_bp = Blueprint("export", __name__, url_prefix="/api/export")


def _parse_request() -> tuple[int, int, int, int, str]:
    """Parse the shared request body. Returns (num_scenarios, num_candidates, num_voters, seed, ideology)."""
    data           = request.get_json() or {}
    num_scenarios  = int(data.get("num_scenarios",  100))
    num_candidates = int(data.get("num_candidates", 4))
    num_voters     = int(data.get("num_voters",     500))
    seed           = int(data.get("seed",           42))
    ideology       = str(data.get("ideology",       "random"))
    return num_scenarios, num_candidates, num_voters, seed, ideology


def _validate(num_scenarios: int, num_candidates: int, num_voters: int):
    if num_scenarios > _MAX_SCENARIOS:
        return f"num_scenarios must be ≤ {_MAX_SCENARIOS}"
    if num_scenarios < 1:
        return "num_scenarios must be ≥ 1"
    if not (2 <= num_candidates <= 8):
        return "num_candidates must be between 2 and 8"
    if not (10 <= num_voters <= 2_000):
        return "num_voters must be between 10 and 2000"
    return None


@export_bp.route("/simulation-dataset", methods=["POST"])
@sim_limiter.limit("10 per minute")
def export_csv() -> Response | tuple[Response, int]:
    """Returns a CSV file (text/csv) with one row per (scenario, method)."""
    try:
        num_scenarios, num_candidates, num_voters, seed, ideology = _parse_request()
    except (TypeError, ValueError) as exc:
        return jsonify({"error": f"Invalid parameters: {exc}"}), 400

    err = _validate(num_scenarios, num_candidates, num_voters)
    if err:
        return jsonify({"error": err}), 400

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
    """Same parameters as /simulation-dataset. Returns JSON for Python/R integration."""
    try:
        num_scenarios, num_candidates, num_voters, seed, ideology = _parse_request()
    except (TypeError, ValueError) as exc:
        return jsonify({"error": f"Invalid parameters: {exc}"}), 400

    err = _validate(num_scenarios, num_candidates, num_voters)
    if err:
        return jsonify({"error": err}), 400

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
