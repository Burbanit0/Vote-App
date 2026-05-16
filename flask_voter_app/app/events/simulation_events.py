"""
simulation_events.py — SocketIO event handlers for streaming simulations.

Monte Carlo streaming protocol
-------------------------------
Client emits  → 'start_monte_carlo'  { num_iterations, num_voters,
                                        num_candidates, ideology_distribution,
                                        candidates }
Server emits  → 'monte_carlo_progress'  { iteration, total, partial_results,
                                           condorcet_exists_rate,
                                           regret_history, agreement_rate,
                                           regret_ci_half, iteration_checkpoints }
              → 'monte_carlo_complete'   { final_results, num_iterations,
                                           num_voters, condorcet_exists_rate }
              → 'monte_carlo_stopped'    {}
              → 'monte_carlo_error'      { message }

Client emits  → 'stop_monte_carlo'  {}
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from flask import request
from flask_socketio import emit

from app import socketio
from app.utils.simulation_voting_utils import create_voter, create_candidate
from app.utils.simulation_metrics      import compare_all_methods_mc
from app.constants                     import DEFAULT_ISSUES

# ── Per-session stop flags ────────────────────────────────────────────────────
_stop_flags: dict[str, bool] = {}

_CANDIDATE_NAMES = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hugo"]
_PARTY_CYCLE     = ["Green", "Conservative", "Liberal", "Independent"]
_EMIT_EVERY      = 50


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


def _ci_half(m2: float, n: int) -> float | None:
    """
    95% CI half-width via Welford M2 accumulator.

    Returns None when n < 2 (not enough samples for variance).
    Formula: 1.96 × σ / √n  where  σ = sqrt(M2 / n)
    """
    if n < 2:
        return None
    variance = m2 / n
    std      = math.sqrt(max(0.0, variance))
    return round(1.96 * std / math.sqrt(n), 6)


# ── Handlers ──────────────────────────────────────────────────────────────────

@socketio.on("start_monte_carlo")
def handle_start_monte_carlo(data: dict[str, Any]) -> None:
    """
    Stream Monte Carlo progress back to the caller.

    Each progress event now carries three convergence metrics:
      regret_history       — mean regret at every checkpoint (for LineChart)
      agreement_rate       — fraction of runs where all methods agreed (cumulative)
      regret_ci_half       — 95% CI half-width per method at this checkpoint
      iteration_checkpoints — X-axis tick values matching regret_history length
    """
    sid = request.sid   # type: ignore[attr-defined]
    _stop_flags[sid] = False

    # ── Parse + validate input ────────────────────────────────────────────
    try:
        num_iterations = max(1, min(10_000, int(data.get("num_iterations", 1_000))))
        num_voters     = max(10, min(2_000, int(data.get("num_voters",     150))))
        num_candidates = max(2, min(8,      int(data.get("num_candidates", 4))))
        ideology       = str(data.get("ideology") or data.get("ideology_distribution") or "random")

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

    # ── Aggregation state (existing) ──────────────────────────────────────
    winner_counts:  dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    regrets:        dict[str, list[float]]    = defaultdict(list)
    satisfactions:  dict[str, list[float]]    = defaultdict(list)
    condorcet_exists = 0
    method_names:   list[str]                 = []

    # ── New convergence state ─────────────────────────────────────────────
    # Welford online algorithm per method: track (n, mean, M2)
    regret_n:     dict[str, int]   = defaultdict(int)
    regret_mean:  dict[str, float] = defaultdict(float)
    regret_m2:    dict[str, float] = defaultdict(float)

    # Checkpointed history (one entry per emit event)
    regret_history_pts: dict[str, list[float]] = defaultdict(list)
    iteration_checkpoints: list[int]            = []

    # Agreement: iterations where every method elected the same winner
    all_agree_count = 0

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

        # ── Existing aggregation ──────────────────────────────────────
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

        # ── New: Welford update for regret variance ───────────────────
        for method, md in run.get("methods", {}).items():
            r = md.get("bayesian_regret")
            if r is not None:
                n          = regret_n[method] + 1
                delta      = r - regret_mean[method]
                new_mean   = regret_mean[method] + delta / n
                delta2     = r - new_mean
                regret_n[method]    = n
                regret_mean[method] = new_mean
                regret_m2[method]  += delta * delta2

        # ── New: check all-method agreement ──────────────────────────
        run_winners = {
            m: md.get("winner")
            for m, md in run.get("methods", {}).items()
            if md.get("winner")
        }
        if run_winners and len(set(run_winners.values())) == 1:
            all_agree_count += 1

        # ── Emit checkpoint ───────────────────────────────────────────
        if (i + 1) % _EMIT_EVERY == 0 or i == num_iterations - 1:
            completed_runs = i + 1
            partial: dict[str, Any] = {}
            for m in method_names:
                wc          = dict(winner_counts[m])
                most_common = max(wc, key=wc.get) if wc else None   # type: ignore[arg-type]
                partial[m]  = {
                    "winner_distribution": {
                        c: round(cnt / completed_runs, 4) for c, cnt in wc.items()
                    },
                    "most_common_winner": most_common,
                    "bayesian_regret_mean": (
                        round(sum(regrets[m]) / len(regrets[m]), 6)
                        if regrets[m] else None
                    ),
                }

            # Snapshot convergence metrics at this checkpoint
            iteration_checkpoints.append(completed_runs)
            for m in method_names:
                if regret_n[m] > 0:
                    regret_history_pts[m].append(round(regret_mean[m], 6))

            ci_half_now: dict[str, float | None] = {
                m: _ci_half(regret_m2[m], regret_n[m])
                for m in method_names
            }
            agreement_rate = round(all_agree_count / completed_runs, 4)

            emit("monte_carlo_progress", {
                "iteration":              completed_runs,
                "total":                  num_iterations,
                "partial_results":        partial,
                "condorcet_exists_rate":  round(condorcet_exists / completed_runs, 4),
                # ── New convergence fields ──
                "regret_history":         {m: list(regret_history_pts[m]) for m in method_names},
                "agreement_rate":         agreement_rate,
                "regret_ci_half":         {m: ci_half_now[m] for m in method_names},
                "iteration_checkpoints":  list(iteration_checkpoints),
            })

    # ── Final result (unchanged format) ──────────────────────────────────
    final: dict[str, Any] = {}
    for m in method_names:
        wc          = dict(winner_counts[m])
        most_common = max(wc, key=wc.get) if wc else None   # type: ignore[arg-type]
        final[m]    = {
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
