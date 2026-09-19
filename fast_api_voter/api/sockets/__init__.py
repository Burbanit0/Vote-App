"""
api.sockets — python-socketio AsyncServer mounted on the FastAPI app.

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
v2 endpoint). The FastAPI app under api.main wraps itself with
`ASGIApp` so the two share a single uvicorn process.
"""
from __future__ import annotations

import asyncio
import math
from collections import defaultdict
from typing import Any

import socketio

from api.engine.utils.demographic_data import unseeded_rng_pair
from api.core.config import get_settings
from api.core.worker_dispatch import run_bounded
from api.engine.constants import DEFAULT_ISSUES
from api.engine.utils.logger import get_logger
from api.engine.utils.simulation_metrics      import compare_all_methods_mc
from api.engine.utils.simulation_voting_utils import create_candidate, create_voter

log = get_logger(__name__)


# ── Single AsyncServer for the v2 backend ──────────────────────────────────
# Mirrors the HTTP CORS setup in api/main.py — same CORS_ORIGINS env var,
# instead of the wildcard this used to carry.
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=get_settings().allowed_origins,
)


# ── Per-session stop flags ─────────────────────────────────────────────────
_stop_flags: dict[str, bool] = {}


_CANDIDATE_NAMES = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hugo"]
_PARTY_CYCLE     = ("Green", "Conservative", "Liberal", "Independent")
_EMIT_EVERY      = 50


# ── Helpers (copied from app.events.simulation_events) ─────────────────────

def _run_one(candidate_configs: list[dict[str, Any]],
             num_voters: int, ideology: str) -> dict[str, Any]:
    """Execute one Monte Carlo iteration and return raw method results.

    Deliberately unseeded (this streaming Monte Carlo has no reproducibility
    contract), but draws from a fresh local RNG pair rather than the shared
    random/np.random singletons: each call runs in its own worker thread
    (via asyncio.to_thread), and the old module-level-singleton draws meant
    this loop could both perturb, and be perturbed by, any other concurrent
    request in the same process (e.g. a seeded election_service.simulate()
    call elsewhere) — unrelated to whether this loop itself needs a seed.
    """
    rng, np_rng = unseeded_rng_pair()
    issues     = DEFAULT_ISSUES
    candidates = [
        create_candidate(issues, i, cfg["name"], _PARTY_CYCLE[i % len(_PARTY_CYCLE)], rng=rng)
        for i, cfg in enumerate(candidate_configs)
    ]
    voters = [create_voter(issues, i, ideology_distribution=ideology, rng=rng, np_rng=np_rng)
              for i in range(num_voters)]
    return compare_all_methods_mc(voters, candidates, issues)


def _ci_half(m2: float, n: int) -> float | None:
    """95% CI half-width via Welford M2 accumulator."""
    if n < 2:
        return None
    std = math.sqrt(max(0.0, m2 / n))
    return round(1.96 * std / math.sqrt(n), 6)


# ── Handlers ───────────────────────────────────────────────────────────────

@sio.event  # type: ignore[untyped-decorator]  # python-socketio decorators are untyped
async def disconnect(sid: str) -> None:
    """Signal any running iteration loop to stop.

    Popping the flag here (the previous behaviour) only erased it — with
    nothing left for the loop's own `_stop_flags.get(sid)` check to see, a
    client that disconnects mid-run left its Monte Carlo loop running
    unattended for up to num_iterations more rounds (each a real
    asyncio.to_thread compute call), burning CPU/a worker thread with
    nowhere left to send its events (Lot 3, PLAN_SOLIDITE_TECHNIQUE.md —
    "Timeouts & backpressure", the Socket.IO orphaned-run case). Setting it
    True instead makes the loop's own check catch it on the next iteration
    and exit; the loop pops its own entry once it does."""
    _stop_flags[sid] = True


@sio.on("stop_monte_carlo")  # type: ignore[untyped-decorator]  # untyped socketio decorator
async def stop_monte_carlo(sid: str, _data: Any = None) -> None:
    """Request the running iteration loop to abort at the next checkpoint."""
    _stop_flags[sid] = True


def _monte_carlo_parse_input(
    data: dict[str, Any],
) -> tuple[int, int, int, str, list[dict[str, Any]]]:
    """Parse + validate /start_monte_carlo input. Raises TypeError/ValueError
    on bad input — the caller catches and emits monte_carlo_error."""
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
    return num_iterations, num_voters, num_candidates, ideology, candidate_configs


def _monte_carlo_new_stats() -> dict[str, Any]:
    """Fresh aggregation state for one /start_monte_carlo run, threaded
    through the streaming loop and mutated in place each iteration."""
    return {
        "winner_counts":         defaultdict(lambda: defaultdict(int)),
        "regrets":                defaultdict(list),
        "satisfactions":          defaultdict(list),
        "condorcet_exists":       0,
        "method_names":           [],
        # Welford online algorithm per method
        "regret_n":               defaultdict(int),
        "regret_mean":            defaultdict(float),
        "regret_m2":              defaultdict(float),
        "regret_history_pts":     defaultdict(list),
        "iteration_checkpoints":  [],
        "all_agree_count":        0,
    }


def _monte_carlo_accumulate_run(run: dict[str, Any], stats: dict[str, Any]) -> None:
    """Fold one Monte Carlo iteration's raw method results into `stats`
    (mutated in place): per-method winner counts, regret/satisfaction
    samples, the Welford regret mean/variance accumulator, the Condorcet-
    exists counter, and the all-methods-agree counter."""
    if not stats["method_names"] and run.get("methods"):
        stats["method_names"] = list(run["methods"].keys())

    if run.get("condorcet_winner"):
        stats["condorcet_exists"] += 1

    for method, md in run.get("methods", {}).items():
        w = md.get("winner")
        if w:
            stats["winner_counts"][method][w] += 1
        r = md.get("bayesian_regret")
        if r is not None:
            stats["regrets"][method].append(r)
        s_val = md.get("majority_satisfaction")
        if s_val is not None:
            stats["satisfactions"][method].append(s_val)

        if r is not None:
            n          = stats["regret_n"][method] + 1
            delta      = r - stats["regret_mean"][method]
            new_mean   = stats["regret_mean"][method] + delta / n
            delta2     = r - new_mean
            stats["regret_n"][method]    = n
            stats["regret_mean"][method] = new_mean
            stats["regret_m2"][method]  += delta * delta2

    run_winners = {
        m: md.get("winner")
        for m, md in run.get("methods", {}).items()
        if md.get("winner")
    }
    if run_winners and len(set(run_winners.values())) == 1:
        stats["all_agree_count"] += 1


def _monte_carlo_checkpoint_payload(
    stats: dict[str, Any], completed_runs: int, num_iterations: int,
) -> dict[str, Any]:
    """Build the `monte_carlo_progress` emit payload for one checkpoint, and
    record it into `stats["iteration_checkpoints"]`/`["regret_history_pts"]`."""
    method_names = stats["method_names"]
    partial: dict[str, Any] = {}
    for m in method_names:
        wc          = stats["winner_counts"][m].copy()
        most_common = max(wc, key=wc.get) if wc else None
        partial[m]  = {
            "winner_distribution": {
                c: round(cnt / completed_runs, 4) for c, cnt in wc.items()
            },
            "most_common_winner": most_common,
            "bayesian_regret_mean": (
                round(sum(stats["regrets"][m]) / len(stats["regrets"][m]), 6)
                if stats["regrets"][m] else None
            ),
        }

    stats["iteration_checkpoints"].append(completed_runs)
    for m in method_names:
        if stats["regret_n"][m] > 0:
            stats["regret_history_pts"][m].append(round(stats["regret_mean"][m], 6))

    ci_half_now: dict[str, float | None] = {
        m: _ci_half(stats["regret_m2"][m], stats["regret_n"][m])
        for m in method_names
    }
    agreement_rate = round(stats["all_agree_count"] / completed_runs, 4)

    return {
        "iteration":             completed_runs,
        "total":                 num_iterations,
        "partial_results":       partial,
        "condorcet_exists_rate": round(stats["condorcet_exists"] / completed_runs, 4),
        "regret_history":        {m: stats["regret_history_pts"][m].copy()
                                  for m in method_names},
        "agreement_rate":        agreement_rate,
        "regret_ci_half":        {m: ci_half_now[m] for m in method_names},
        "iteration_checkpoints": stats["iteration_checkpoints"].copy(),
    }


def _monte_carlo_final_payload(
    stats: dict[str, Any], num_iterations: int, num_voters: int,
) -> dict[str, Any]:
    """Build the `monte_carlo_complete` emit payload from the final `stats`."""
    final: dict[str, Any] = {}
    for m in stats["method_names"]:
        wc          = stats["winner_counts"][m].copy()
        most_common = max(wc, key=wc.get) if wc else None
        final[m]    = {
            "winner_distribution": {
                c: round(cnt / num_iterations, 4) for c, cnt in wc.items()
            },
            "most_common_winner": most_common,
            "bayesian_regret_mean": (
                round(sum(stats["regrets"][m]) / len(stats["regrets"][m]), 6)
                if stats["regrets"][m] else None
            ),
            "majority_satisfaction_mean": (
                round(sum(stats["satisfactions"][m]) / len(stats["satisfactions"][m]), 4)
                if stats["satisfactions"][m] else None
            ),
        }

    return {
        "final_results":         final,
        "num_iterations":        num_iterations,
        "num_voters":            num_voters,
        "condorcet_exists_rate": round(stats["condorcet_exists"] / num_iterations, 4),
    }


@sio.on("start_monte_carlo")  # type: ignore[untyped-decorator]  # untyped socketio decorator
async def start_monte_carlo(sid: str, data: dict[str, Any]) -> None:
    """Stream Monte Carlo progress back to the caller.

    Each progress event carries:
      regret_history       — mean regret at every checkpoint (LineChart)
      agreement_rate       — fraction of runs where all methods agreed
      regret_ci_half       — 95% CI half-width per method
      iteration_checkpoints — X-axis tick values matching regret_history

    Input parsing, per-run aggregation and payload building are now private
    `_monte_carlo_*` helpers — same names, same computation, same order as
    before (CODE_AUDIT.md §5/§8 complexity decomposition)."""
    _stop_flags[sid] = False

    try:
        num_iterations, num_voters, num_candidates, ideology, candidate_configs = (
            _monte_carlo_parse_input(data)
        )
    except (TypeError, ValueError) as exc:
        await sio.emit("monte_carlo_error",
                       {"message": f"Invalid parameters: {exc}"}, to=sid)
        return

    stats = _monte_carlo_new_stats()

    # ── Streaming loop ────────────────────────────────────────────────────
    for i in range(num_iterations):
        if _stop_flags.get(sid):
            await sio.emit("monte_carlo_stopped", {}, to=sid)
            _stop_flags.pop(sid, None)
            return

        try:
            # _run_one is CPU-bound — offload to a worker thread through the
            # same shared semaphore + timeout every HTTP route goes through
            # (api.core.worker_dispatch.run_bounded), not a raw
            # asyncio.to_thread: this loop used to bypass that bound
            # entirely, so a flood of concurrent socket sessions could pile
            # up unlimited CPU-bound threads with no timeout at all.
            run = await run_bounded(_run_one, candidate_configs, num_voters, ideology)
        except asyncio.TimeoutError:
            log.error("sockets.monte_carlo_run_timeout", sid=sid)
            await sio.emit(
                "monte_carlo_error", {"message": "Run took too long to process"}, to=sid,
            )
            return
        except Exception as exc:  # noqa: BLE001
            log.warning("sockets.monte_carlo_run_failed", sid=sid, exc_info=True)
            await sio.emit("monte_carlo_error", {"message": str(exc)}, to=sid)
            return

        _monte_carlo_accumulate_run(run, stats)

        # ── Emit checkpoint ───────────────────────────────────────────────
        if (i + 1) % _EMIT_EVERY == 0 or i == num_iterations - 1:
            payload = _monte_carlo_checkpoint_payload(stats, i + 1, num_iterations)
            await sio.emit("monte_carlo_progress", payload, to=sid)
            # No explicit yield needed — emit is awaited and asyncio.to_thread
            # is naturally yielding.

    # ── Final result ──────────────────────────────────────────────────────
    await sio.emit(
        "monte_carlo_complete",
        _monte_carlo_final_payload(stats, num_iterations, num_voters),
        to=sid,
    )
    _stop_flags.pop(sid, None)


# ── ASGI app wrapper for FastAPI mounting ──────────────────────────────────
asgi_app = socketio.ASGIApp(sio, socketio_path="/api/v2/socket.io")
