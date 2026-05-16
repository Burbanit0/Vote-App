"""
simulation_events.py — SocketIO event handlers for streaming simulations.

Monte Carlo streaming protocol
-------------------------------
Client emits  → 'start_monte_carlo'  { num_iterations, num_voters,
                                        num_candidates, ideology_distribution,
                                        candidates }
Server emits  → 'monte_carlo_progress'  { iteration, total, partial_results,
                                           condorcet_exists_rate }
              → 'monte_carlo_complete'   { final_results, num_iterations,
                                           num_voters, condorcet_exists_rate }
              → 'monte_carlo_stopped'    {}
              → 'monte_carlo_error'      { message }

Client emits  → 'stop_monte_carlo'  {}
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from flask import request
from flask_socketio import emit

from app import socketio
from app.utils.simulation_voting_utils import create_voter, create_candidate
from app.utils.simulation_metrics      import compare_all_methods_mc
from app.constants                     import DEFAULT_ISSUES

# ── Per-session stop flags ────────────────────────────────────────────────────
# Maps session-id → True when the client has requested an abort.
_stop_flags: dict[str, bool] = {}

_CANDIDATE_NAMES = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hugo"]
_PARTY_CYCLE     = ["Green", "Conservative", "Liberal", "Independent"]
_EMIT_EVERY      = 50   # progress events every N iterations


# ── Helper ────────────────────────────────────────────────────────────────────

def _run_one(
    candidate_configs: list[dict[str, Any]],
    num_voters: int,
    ideology: str,
) -> dict[str, Any]:
    """Execute a single Monte Carlo iteration and return raw method results."""
    issues     = DEFAULT_ISSUES
    candidates = [
        create_candidate(issues, i, cfg["name"], _PARTY_CYCLE[i % len(_PARTY_CYCLE)])
        for i, cfg in enumerate(candidate_configs)
    ]
    voters = [create_voter(issues, i, ideology_distribution=ideology)
              for i in range(num_voters)]
    return compare_all_methods_mc(voters, candidates, issues)


# ── Handlers ──────────────────────────────────────────────────────────────────

@socketio.on("start_monte_carlo")
def handle_start_monte_carlo(data: dict[str, Any]) -> None:
    """
    Stream Monte Carlo progress back to the caller.

    Runs up to 10 000 iterations sequentially (eventlet green-threads allow
    cooperative yielding so the socket remains responsive).  Emits a progress
    event every _EMIT_EVERY iterations and a completion event when done.
    """
    sid = request.sid   # type: ignore[attr-defined]
    _stop_flags[sid] = False

    # ── Parse + validate input ────────────────────────────────────────────
    try:
        num_iterations = max(1, min(10_000, int(data.get("num_iterations", 1_000))))
        num_voters     = max(10, min(2_000, int(data.get("num_voters",     150))))
        num_candidates = max(2, min(8,      int(data.get("num_candidates", 4))))
        ideology       = str(data.get("ideology_distribution", "random"))

        raw_cands = data.get("candidates")
        if raw_cands and isinstance(raw_cands, list) and len(raw_cands) >= 2:
            candidate_configs = [
                {"name": str(c)} if isinstance(c, str) else
                {"name": str(c.get("name", f"Cand{i}"))}
                for i, c in enumerate(raw_cands[:8])
            ]
        else:
            names             = _CANDIDATE_NAMES[:num_candidates]
            candidate_configs = [{"name": n} for n in names]
    except (TypeError, ValueError) as exc:
        emit("monte_carlo_error", {"message": f"Invalid parameters: {exc}"})
        return

    # ── Aggregation state ─────────────────────────────────────────────────
    winner_counts:    dict[str, dict[str, int]]   = defaultdict(lambda: defaultdict(int))
    regrets:          dict[str, list[float]]       = defaultdict(list)
    satisfactions:    dict[str, list[float]]       = defaultdict(list)
    condorcet_exists  = 0
    method_names:     list[str]                    = []

    # ── Streaming loop ────────────────────────────────────────────────────
    for i in range(num_iterations):
        if _stop_flags.get(sid):
            emit("monte_carlo_stopped", {})
            _stop_flags.pop(sid, None)
            return

        try:
            run = _run_one(candidate_configs, num_voters, ideology)
        except Exception as exc:
            emit("monte_carlo_error", {"message": str(exc)})
            return

        if not method_names and run.get("methods"):
            method_names = list(run["methods"].keys())

        if run.get("condorcet_winner"):
            condorcet_exists += 1

        for method, md in run.get("methods", {}).items():
            w = md.get("winner")
            if w:
                winner_counts[method][w] += 1
            r = md.get("bayesian_regret")
            if r is not None:
                regrets[method].append(r)
            s = md.get("majority_satisfaction")
            if s is not None:
                satisfactions[method].append(s)

        if (i + 1) % _EMIT_EVERY == 0 or i == num_iterations - 1:
            completed_runs = i + 1
            partial: dict[str, Any] = {}
            for m in method_names:
                wc = dict(winner_counts[m])
                most_common = max(wc, key=wc.get) if wc else None   # type: ignore[arg-type]
                partial[m] = {
                    "winner_distribution": {
                        c: round(cnt / completed_runs, 4) for c, cnt in wc.items()
                    },
                    "most_common_winner": most_common,
                    "bayesian_regret_mean": (
                        round(sum(regrets[m]) / len(regrets[m]), 6)
                        if regrets[m] else None
                    ),
                }

            emit("monte_carlo_progress", {
                "iteration":           i + 1,
                "total":               num_iterations,
                "partial_results":     partial,
                "condorcet_exists_rate": round(condorcet_exists / completed_runs, 4),
            })

    # ── Final result ──────────────────────────────────────────────────────
    final: dict[str, Any] = {}
    for m in method_names:
        wc = dict(winner_counts[m])
        most_common = max(wc, key=wc.get) if wc else None   # type: ignore[arg-type]
        final[m] = {
            "winner_distribution": {
                c: round(cnt / num_iterations, 4) for c, cnt in wc.items()
            },
            "most_common_winner": most_common,
            "bayesian_regret_mean": (
                round(sum(regrets[m]) / len(regrets[m]), 6) if regrets[m] else None
            ),
            "majority_satisfaction_mean": (
                round(sum(satisfactions[m]) / len(satisfactions[m]), 4)
                if satisfactions[m] else None
            ),
        }

    emit("monte_carlo_complete", {
        "final_results":         final,
        "num_iterations":        num_iterations,
        "num_voters":            num_voters,
        "condorcet_exists_rate": round(condorcet_exists / num_iterations, 4),
    })
    _stop_flags.pop(sid, None)


@socketio.on("stop_monte_carlo")
def handle_stop_monte_carlo(data: dict | None = None) -> None:
    """Request the running iteration loop to abort at the next checkpoint."""
    sid = request.sid   # type: ignore[attr-defined]
    _stop_flags[sid] = True


@socketio.on("disconnect")
def handle_disconnect() -> None:
    """Clean up stop-flag when a client disconnects."""
    sid = request.sid   # type: ignore[attr-defined]
    _stop_flags.pop(sid, None)
