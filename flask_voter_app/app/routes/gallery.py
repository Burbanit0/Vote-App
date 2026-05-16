"""
gallery.py — Public scenario gallery routes.

No authentication required — anyone can read and propose scenarios.
Featured / moderation is handled via direct DB access by admins.
"""
from __future__ import annotations

import json
from typing import Any

from flask import Blueprint, Response, jsonify, request
from sqlalchemy import cast, Text

from app import db
from app.models import GalleryScenario
from app.extensions import sim_limiter

gallery_bp = Blueprint("gallery", __name__, url_prefix="/api/scenarios/gallery")

# ── Helpers ───────────────────────────────────────────────────────────────────

def _tag_filter(query: Any, tag: str) -> Any:
    """
    Filter scenarios whose JSON tags array contains *tag*.

    Uses a text-cast LIKE search that works on both SQLite and PostgreSQL.
    Example: tag="condorcet" → WHERE CAST(tags AS TEXT) LIKE '%"condorcet"%'
    """
    safe = tag.replace('"', '').replace("'", '')[:50]
    return query.filter(cast(GalleryScenario.tags, Text).like(f'%"{safe}"%'))


# ── GET /api/scenarios/gallery/featured ──────────────────────────────────────

@gallery_bp.route("/featured", methods=["GET"])
@sim_limiter.limit("60 per minute")
def get_featured() -> tuple[Response, int]:
    """Return the 6 featured scenarios (highest views among is_featured=True)."""
    limit = min(int(request.args.get("limit", 6)), 20)
    scenarios = (
        GalleryScenario.query
        .filter(GalleryScenario.is_featured.is_(True))
        .order_by(GalleryScenario.views.desc())
        .limit(limit)
        .all()
    )
    return jsonify([s.to_dict() for s in scenarios]), 200


# ── GET /api/scenarios/gallery/<id> ──────────────────────────────────────────

@gallery_bp.route("/<int:scenario_id>", methods=["GET"])
@sim_limiter.limit("60 per minute")
def get_scenario(scenario_id: int) -> tuple[Response, int]:
    """Return full scenario details and increment the view counter."""
    scenario = db.session.get(GalleryScenario, scenario_id)
    if scenario is None:
        return jsonify({"error": "Scenario not found"}), 404
    scenario.views += 1  # type: ignore[assignment]
    db.session.commit()
    return jsonify(scenario.to_dict(include_params=True)), 200


# ── GET /api/scenarios/gallery/ ──────────────────────────────────────────────

@gallery_bp.route("/", methods=["GET"])
@sim_limiter.limit("60 per minute")
def list_gallery() -> tuple[Response, int]:
    """
    Paginated gallery list.

    Query params:
        page     int    1-based page number (default 1)
        per_page int    items per page (default 20, max 50)
        sort     str    "recent" | "popular" | "featured"
        tag      str    filter by tag
    """
    try:
        page     = max(1, int(request.args.get("page",     1)))
        per_page = min(50, max(1, int(request.args.get("per_page", 20))))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid pagination parameters"}), 400

    sort = request.args.get("sort", "recent")
    tag  = request.args.get("tag",  "").strip()

    query = GalleryScenario.query

    if tag:
        query = _tag_filter(query, tag)

    if sort == "popular":
        query = query.order_by(GalleryScenario.views.desc(), GalleryScenario.created_at.desc())
    elif sort == "featured":
        query = (query
                 .filter(GalleryScenario.is_featured.is_(True))
                 .order_by(GalleryScenario.views.desc()))
    else:
        # default: recent
        query = query.order_by(GalleryScenario.created_at.desc())

    total     = query.count()
    scenarios = query.offset((page - 1) * per_page).limit(per_page).all()
    pages     = max(1, (total + per_page - 1) // per_page)

    return jsonify({
        "items":    [s.to_dict() for s in scenarios],
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    pages,
    }), 200


# ── POST /api/scenarios/gallery/ ─────────────────────────────────────────────

@gallery_bp.route("/", methods=["POST"])
@sim_limiter.limit("20 per minute")
def create_gallery_scenario() -> tuple[Response, int]:
    """
    Save a simulation scenario to the public gallery.

    Body (JSON):
        title           str   required, max 200 chars
        description     str   required
        params          dict  simulation parameters
        results_summary dict  compact winner summary (no raw ballots)
        tags            list  up to 10 tag strings
    """
    data = request.get_json() or {}

    title       = (data.get("title")       or "").strip()[:200]
    description = (data.get("description") or "").strip()
    params      = data.get("params",          {})
    results_sum = data.get("results_summary", {})
    tags        = data.get("tags",            [])

    if not title:
        return jsonify({"error": "'title' is required"}), 400
    if not description:
        return jsonify({"error": "'description' is required"}), 400
    if not isinstance(tags, list):
        return jsonify({"error": "'tags' must be a list"}), 400
    if not isinstance(params, dict):
        return jsonify({"error": "'params' must be an object"}), 400

    # Sanitise: only keep string tags, max 10, each max 50 chars
    clean_tags = [str(t)[:50] for t in tags if isinstance(t, (str, int)) and str(t)][:10]

    scenario = GalleryScenario(
        title=title,
        description=description,
        params=params,
        results_summary=results_sum,
        tags=clean_tags,
        is_featured=False,
    )
    db.session.add(scenario)
    db.session.commit()

    return jsonify(scenario.to_dict(include_params=True)), 201
