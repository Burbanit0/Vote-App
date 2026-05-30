"""
api_public.py — Flask delegates for the public research API (/api/v1).

The compute (catalogue, workers, OpenAPI spec, dataset payloads) now lives in
api_v2.domain.public (Phase 4.5.b.3). This blueprint keeps the Flask-Limiter
rate limits and stays thin until app/ is deleted in the final teardown.
"""
from __future__ import annotations

import os
from typing import Any

from flask import Blueprint, Response, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from api_v2.domain.public import (  # noqa: F401  (write_openapi_json re-exported)
    OPENAPI_SPEC,
    METHODS_CATALOG,
    _compare_worker,
    _methods_payload,
    _real_elections_payload,
    _simulate_worker,
    write_openapi_json,
)

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


@api_public_bp.route("/methods", methods=["GET"])
def list_methods() -> tuple[Response, int]:
    """List all voting methods supported by the Vote Lab engine."""
    return jsonify(_methods_payload(request.args.get("family", ""))), 200


@api_public_bp.route("/simulate", methods=["POST"])
@_api_limiter.limit("10 per minute")
def simulate() -> tuple[Response, int]:
    """Run a multi-method simulation on a synthetic population."""
    body, status = _simulate_worker(request.get_json() or {})
    return jsonify(body), status


@api_public_bp.route("/compare", methods=["POST"])
@_api_limiter.limit("5 per minute")
def compare() -> tuple[Response, int]:
    """Run a multi-method comparison with optional blank-vote rule."""
    body, status = _compare_worker(request.get_json() or {})
    return jsonify(body), status


@api_public_bp.route("/real-elections", methods=["GET"])
def real_elections_public() -> tuple[Response, int]:
    """List all historical elections in the Vote Lab dataset."""
    return jsonify(_real_elections_payload()), 200


@api_public_bp.route("/openapi.json", methods=["GET"])
def openapi_spec() -> tuple[Response, int]:
    """Serve the hand-written OpenAPI 3.0 specification."""
    return jsonify(OPENAPI_SPEC), 200
