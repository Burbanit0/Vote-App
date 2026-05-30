"""
election.py — Flask delegates for the /api/election/* routes.

The 35 compute workers (+ helpers + ElectionService) now live in
api_v2.domain.election (Phase 4.5.b.3). This blueprint registers thin delegates
via a small factory — every view runs its worker in eventlet's tpool (so heavy
simulations don't block the event loop) and JSON-encodes the (body, status)
result. Stays until app/ is deleted in the final teardown.
"""
from eventlet import tpool
from flask import Blueprint, Response, current_app, jsonify, request

from app.extensions import sim_limiter
from api_v2.domain.election import workers as _workers

election_bp = Blueprint("election", __name__, url_prefix="/api/election")

# (path, rate-limit) — the worker is derived as _<path>_worker.
_ROUTES = [
    ("/simulate",               "20 per minute"),
    ("/divergence",             "20 per minute"),
    ("/campaign-sensitivity",   "10 per minute"),
    ("/combined-effects",       "5 per minute"),
    ("/interpret",              "30 per minute"),
    ("/simulate-pipeline",      "10 per minute"),
    ("/coalition",              "20 per minute"),
    ("/districts",              "10 per minute"),
    ("/primary",                "15 per minute"),
    ("/adaptive",               "10 per minute"),
    ("/historical-replay",      "10 per minute"),
    ("/jury",                   "10 per minute"),
    ("/abstention",             "10 per minute"),
    ("/stv",                    "10 per minute"),
    ("/gerrymander",            "10 per minute"),
    ("/multiwinner_compare",    "10 per minute"),
    ("/hotelling",              "10 per minute"),
    ("/polarization",           "5 per minute"),
    ("/quadratic-funding",      "10 per minute"),
    ("/affective-polarization", "5 per minute"),
    ("/cascade",                "10 per minute"),
    ("/behavioral-biases",      "10 per minute"),
    ("/liquid-democracy",       "10 per minute"),
    ("/conviction-voting",      "10 per minute"),
    ("/nota",                   "10 per minute"),
    ("/ballot-complexity",      "10 per minute"),
    ("/shy-voter",              "10 per minute"),
    ("/electoral-fatigue",      "10 per minute"),
    ("/choice-overload",        "10 per minute"),
    ("/demographic-turnout",    "10 per minute"),
    ("/compulsory-voting",      "10 per minute"),
    ("/sortition",              "5 per minute"),
    ("/party-dynamics",         "5 per minute"),
    ("/deliberation",           "5 per minute"),
    ("/power-indices",          "10 per minute"),
]


def _register(path: str, limit: str) -> None:
    fname = "_" + path.lstrip("/").replace("-", "_") + "_worker"
    worker = getattr(_workers, fname)

    def _handler() -> tuple[Response, int]:
        data = request.get_json() or {}
        try:
            body, status = tpool.execute(worker, data)
            return jsonify(body), status
        except Exception as exc:  # noqa: BLE001
            current_app.logger.exception("%s crashed", fname)
            return jsonify({"error": f"Internal error: {exc}"}), 500

    _handler.__name__ = path.lstrip("/").replace("-", "_")  # unique Flask endpoint
    election_bp.route(path, methods=["POST"])(sim_limiter.limit(limit)(_handler))


for _path, _limit in _ROUTES:
    _register(_path, _limit)
