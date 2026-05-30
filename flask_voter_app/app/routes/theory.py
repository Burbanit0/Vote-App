"""
theory.py — Flask delegates for the /api/theory/* routes.

The 15 compute workers now live in api_v2.domain.theory.workers (Phase 4.5.b.3).
This blueprint registers thin delegates (build via a small factory since they all
share the same try/except shape) and stays until app/ is deleted in the final
teardown.
"""
from flask import Blueprint, Response, current_app, jsonify, request

from app.extensions import sim_limiter
from api_v2.domain.theory.workers import (
    _agenda_manipulation_worker,
    _apportionment_worker,
    _arrow_worker,
    _assumption_testing_worker,
    _collective_will_worker,
    _democratic_backsliding_worker,
    _epistocracy_worker,
    _identity_voting_worker,
    _iia_rate_worker,
    _intergenerational_worker,
    _judgment_aggregation_worker,
    _majority_tyranny_worker,
    _manipulation_analysis_worker,
    _plott_chaos_worker,
    _sen_paradox_worker,
)

theory_bp = Blueprint("theory", __name__, url_prefix="/api/theory")

# (path, rate-limit, worker)
_ROUTES = [
    ("/arrow",                  "20 per minute", _arrow_worker),
    ("/iia-rate",               "10 per minute", _iia_rate_worker),
    ("/plott-chaos",            "5 per minute",  _plott_chaos_worker),
    ("/judgment-aggregation",   "10 per minute", _judgment_aggregation_worker),
    ("/agenda-manipulation",    "5 per minute",  _agenda_manipulation_worker),
    ("/apportionment",          "10 per minute", _apportionment_worker),
    ("/sen-paradox",            "10 per minute", _sen_paradox_worker),
    ("/manipulation-analysis",  "5 per minute",  _manipulation_analysis_worker),
    ("/majority-tyranny",       "5 per minute",  _majority_tyranny_worker),
    ("/democratic-backsliding", "5 per minute",  _democratic_backsliding_worker),
    ("/intergenerational",      "5 per minute",  _intergenerational_worker),
    ("/epistocracy",            "5 per minute",  _epistocracy_worker),
    ("/identity-voting",        "5 per minute",  _identity_voting_worker),
    ("/assumption-testing",     "5 per minute",  _assumption_testing_worker),
    ("/collective-will",        "5 per minute",  _collective_will_worker),
]


def _register(path: str, limit: str, worker) -> None:
    def _handler() -> tuple[Response, int]:
        try:
            body, status_code = worker(request.get_json() or {})
            return jsonify(body), status_code
        except Exception as exc:  # noqa: BLE001
            current_app.logger.exception("%s() crashed", worker.__name__)
            return jsonify({"error": f"Internal error: {exc}"}), 500

    _handler.__name__ = worker.__name__.lstrip("_")  # unique Flask endpoint name
    theory_bp.route(path, methods=["POST"])(sim_limiter.limit(limit)(_handler))


for _path, _limit, _worker in _ROUTES:
    _register(_path, _limit, _worker)
