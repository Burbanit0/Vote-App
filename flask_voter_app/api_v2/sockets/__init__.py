"""
api_v2.sockets — python-socketio AsyncServer mounted on the FastAPI app.

Re-implements the Flask `simulation_events.py` Socket.IO handlers using
the asyncio backend (no eventlet). Wire protocol is identical, so
existing `socket.io-client` consumers swap URLs and nothing else.

Streaming protocol (same as Flask):
    Client → 'start_monte_carlo'  { num_iterations, num_voters,
                                     num_candidates, ideology, candidates }
    Server → 'monte_carlo_progress' …
           → 'monte_carlo_complete' …
           → 'monte_carlo_stopped' / 'monte_carlo_error'
    Client → 'stop_monte_carlo'  {}

Mount URL: /api/v2/socket.io  (matches the convention of every other
v2 endpoint). The FastAPI app under api_v2.main wraps itself with
`ASGIApp` so the two share a single uvicorn process.
"""
from __future__ import annotations

import asyncio
import math
from collections import defaultdict
from typing import Any

import socketio

from app.constants import DEFAULT_ISSUES
from app.utils.simulation_metrics      import compare_all_methods_mc
from app.utils.simulation_voting_utils import create_candidate, create_voter


# ── Single AsyncServer for the v2 backend ──────────────────────────────────
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",   # tighten in main.py once CORS settings flow in
)


# ── Per-session stop flags ─────────────────────────────────────────────────
_stop_flags: dict[str, bool] = {}


_CANDIDATE_NAMES = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hugo"]
_PARTY_CYCLE     = ["Green", "Conservative", "Liberal", "Independent"]
_EMIT_EVERY      = 50


# ── Helpers (copied from app.events.simulation_events) ─────────────────────

def _run_one(candidate_configs: list[dict[str, Any]],
             num_voters: int, ideology: str) -> dict[str, Any]:
    """Execute one Monte Carlo iteration and return raw method results."""
    issues     = DEFAULT_ISSUES
    candidates = [
        create_candidate(issues, i, cfg["name"], _PARTY_CYCLE[i % len(_PARTY_CYCLE)])
        for i, cfg in enumerate(candidate_configs)
    ]
    voters = [create_voter(issues, i, ideology_distribution=ideology)
              for i in range(num_voters)]
    return compare_all_methods_mc(voters, candidates, issues)


def _ci_half(m2: float, n: int) -> float | None:
    """95% CI half-width via Welford M2 accumulator."""
    if n < 2:
        return None
    std = math.sqrt(max(0.0, m2 / n))
    return round(1.96 * std / math.sqrt(n), 6)


# ── Handlers ───────────────────────────────────────────────────────────────

@sio.event
async def disconnect(sid: str) -> None:
    """Drop any pending stop flag on disconnect."""
    _stop_flags.pop(sid, None)


@sio.on("stop_monte_carlo")
async def stop_monte_carlo(sid: str, _data: Any = None) -> None:
    """Request the running iteration loop to abort at the next checkpoint."""
    _stop_flags[sid] = True


@sio.on("start_monte_carlo")
async def start_monte_carlo(sid: str, data: dict[str, Any]) -> None:
    """Stream Monte Carlo progress back to the caller.

    Each progress event carries:
      regret_history       — mean regret at every checkpoint (LineChart)
      agreement_rate       — fraction of runs where all methods agreed
      regret_ci_half       — 95% CI half-width per method
      iteration_checkpoints — X-axis tick values matching regret_history
    """
    _stop_flags[sid] = False

    # ── Parse + validate input ────────────────────────────────────────────
    try:
        num_iterations = max(1, min(10_000, int(data.get("num_iterations", 1_000))))
        num_voters     = max(10, min(2_000, int(data.get("num_voters",     150))))
        num_candidates = max(2, min(8,      int(data.get("num_candidates", 4))))
        ideology       = str(data.get("ideology")
                             or data.get("ideology_distribution")
                             or "random")

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
        await sio.emit("monte_carlo_error",
                       {"message": f"Invalid parameters: {exc}"}, to=sid)
        return

    # ── Aggregation state ─────────────────────────────────────────────────
    winner_counts:  dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    regrets:        dict[str, list[float]]    = defaultdict(list)
    satisfactions:  dict[str, list[float]]    = defaultdict(list)
    condorcet_exists = 0
    method_names:   list[str]                 = []

    # Welford online algorithm per method
    regret_n:     dict[str, int]   = defaultdict(int)
    regret_mean:  dict[str, float] = defaultdict(float)
    regret_m2:    dict[str, float] = defaultdict(float)

    regret_history_pts: dict[str, list[float]] = defaultdict(list)
    iteration_checkpoints: list[int]            = []
    all_agree_count = 0

    # ── Streaming loop ────────────────────────────────────────────────────
    for i in range(num_iterations):
        if _stop_flags.get(sid):
            await sio.emit("monte_carlo_stopped", {}, to=sid)
            _stop_flags.pop(sid, None)
            return

        try:
            # _run_one is CPU-bound — offload to a worker thread so we
            # don't block the asyncio loop. Same role as eventlet's
            # cooperative scheduling on the Flask side.
            run = await asyncio.to_thread(
                _run_one, candidate_configs, num_voters, ideology,
            )
        except Exception as exc:  # noqa: BLE001
            await sio.emit("monte_carlo_error", {"message": str(exc)}, to=sid)
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
            s_val = md.get("majority_satisfaction")
            if s_val is not None:
                satisfactions[method].append(s_val)

            if r is not None:
                n          = regret_n[method] + 1
                delta      = r - regret_mean[method]
                new_mean   = regret_mean[method] + delta / n
                delta2     = r - new_mean
                regret_n[method]    = n
                regret_mean[method] = new_mean
                regret_m2[method]  += delta * delta2

        run_winners = {
            m: md.get("winner")
            for m, md in run.get("methods", {}).items()
            if md.get("winner")
        }
        if run_winners and len(set(run_winners.values())) == 1:
            all_agree_count += 1

        # ── Emit checkpoint ───────────────────────────────────────────────
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

            iteration_checkpoints.append(completed_runs)
            for m in method_names:
                if regret_n[m] > 0:
                    regret_history_pts[m].append(round(regret_mean[m], 6))

            ci_half_now: dict[str, float | None] = {
                m: _ci_half(regret_m2[m], regret_n[m])
                for m in method_names
            }
            agreement_rate = round(all_agree_count / completed_runs, 4)

            await sio.emit("monte_carlo_progress", {
                "iteration":             completed_runs,
                "total":                 num_iterations,
                "partial_results":       partial,
                "condorcet_exists_rate": round(condorcet_exists / completed_runs, 4),
                "regret_history":        {m: list(regret_history_pts[m])
                                          for m in method_names},
                "agreement_rate":        agreement_rate,
                "regret_ci_half":        {m: ci_half_now[m] for m in method_names},
                "iteration_checkpoints": list(iteration_checkpoints),
            }, to=sid)
            # No explicit yield needed — emit is awaited and asyncio.to_thread
            # is naturally yielding.

    # ── Final result ──────────────────────────────────────────────────────
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

    await sio.emit("monte_carlo_complete", {
        "final_results":         final,
        "num_iterations":        num_iterations,
        "num_voters":            num_voters,
        "condorcet_exists_rate": round(condorcet_exists / num_iterations, 4),
    }, to=sid)
    _stop_flags.pop(sid, None)


# ── ASGI app wrapper for FastAPI mounting ──────────────────────────────────
asgi_app = socketio.ASGIApp(sio, socketio_path="/api/v2/socket.io")
