"""
campaign_dynamics.py — Day-by-day electoral campaign simulation.

Model
-----
* Candidate utilities start random in [0.3, 0.7].
* Each day Brownian noise N(0, σ²) with σ = 0.02 is added to every utility
  (applied *after* computing that day's scores so events show their effect
  cleanly on the day they occur).
* Events instantly modify a candidate's utility on the scheduled day.
* Vote shares are derived from a softmax over utilities (smooth, bounded).
* The daily leader is computed via the requested voting method.
"""
from __future__ import annotations

import math
import random
from typing import Any, Optional

# ── Constants ────────────────────────────────────────────────────────────────

_NAMES: list[str] = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hugo"]

# Number of synthetic voters used for ballot-based methods (kept low for speed)
_BALLOT_SAMPLE = 150

# Standard deviation of daily Brownian noise
_SIGMA = 0.02

# ── Event effect functions ────────────────────────────────────────────────────

def _apply_event(utility: float, event_type: str, magnitude: float) -> float:
    """Return the new utility after applying one campaign event."""
    magnitude = max(0.0, min(1.0, magnitude))
    effects: dict[str, float] = {
        "scandal":      -magnitude,          # deliberate wrongdoing — heavy hit
        "gaffe":        -0.10,               # verbal slip — fixed penalty
        "good_debate":  +magnitude,          # strong debate performance
        "announcement": +magnitude * 0.5,    # policy announcement — moderate boost
        "bad_poll":     -magnitude * 0.3,    # demoralising polling number
    }
    delta = effects.get(event_type, -magnitude)   # default: negative
    return max(0.05, min(0.95, utility + delta))


# ── Voting-method helpers ─────────────────────────────────────────────────────

def _softmax(values: list[float]) -> list[float]:
    """Numerically stable softmax."""
    max_v = max(values)
    exp_v = [math.exp(v - max_v) for v in values]
    total = sum(exp_v)
    return [v / total for v in exp_v]


def _plurality_winner(utilities: dict[str, float]) -> str:
    """Deterministic: candidate with highest utility wins."""
    return max(utilities, key=lambda n: utilities[n])


def _borda_winner(utilities: dict[str, float], names: list[str]) -> str:
    """Deterministic Borda: rank by utility, award n−1 … 0 points."""
    ranked = sorted(names, key=lambda n: -utilities[n])
    n = len(names)
    borda = {name: n - 1 - i for i, name in enumerate(ranked)}
    return max(borda, key=lambda n: borda[n])


def _balloted_winner(
    utilities: dict[str, float],
    names: list[str],
    method: str,
    rng: random.Random,
) -> str:
    """
    Generate _BALLOT_SAMPLE synthetic ranked ballots from utilities (with
    per-voter noise) and apply the requested ranked voting method.
    Falls back to plurality on error.
    """
    from api.engine.utils.simulation_ranked_utils import (
        get_plurality_winner,
        get_borda_winner,
        get_irv_winner,
        get_approval_winner,
        get_schulze_winner,
        get_coombs_winner,
        get_bucklin_winner,
        get_minimax_winner,
    )

    method_fns: dict[str, Any] = {
        "plurality": get_plurality_winner,
        "borda":     get_borda_winner,
        "irv":       get_irv_winner,
        "approval":  get_approval_winner,
        "schulze":   get_schulze_winner,
        "coombs":    get_coombs_winner,
        "bucklin":   get_bucklin_winner,
        "minimax":   get_minimax_winner,
    }
    fn = method_fns.get(method, get_plurality_winner)

    ballots = []
    for _ in range(_BALLOT_SAMPLE):
        voter_utils = {n: utilities[n] + rng.gauss(0, 0.08) for n in names}
        ranking = sorted(names, key=lambda n: -voter_utils[n])
        ballots.append(ranking)

    try:
        winner = fn(ballots)
        return winner if winner else _plurality_winner(utilities)
    except Exception:
        return _plurality_winner(utilities)


# ── Public API ────────────────────────────────────────────────────────────────

def simulate_campaign(
    num_candidates: int,
    num_voters: int,
    num_days: int,
    events: list[dict[str, Any]],
    method: str = "plurality",
    seed: Optional[int] = None,
) -> dict[str, Any]:
    """
    Simulate a day-by-day electoral campaign.

    Parameters
    ----------
    num_candidates : int   2–8
    num_voters     : int   10–2 000 (used for context; ballot methods use _BALLOT_SAMPLE)
    num_days       : int   1–90
    events         : list  of dicts with keys:
                        day       (int, 0 … num_days)
                        type      (str, see _apply_event)
                        candidate (int index, 0-based)
                        magnitude (float 0–1)
    method         : str   voting method key ("plurality", "borda", "irv", …)
    seed           : int | None  for reproducibility in tests

    Returns
    -------
    {
        "days":         list[int]              # [0, 1, …, num_days]
        "daily_leader": list[str]              # one leader per day
        "daily_scores": dict[str, list[float]] # vote share (%) per candidate per day
        "events":       list[dict]             # original events + measured_impact
        "final_winner": str
        "lead_changes": int
        "candidates":   list[str]
    }
    """
    rng = random.Random(seed)

    num_candidates = max(2, min(8,  num_candidates))
    num_days       = max(1, min(90, num_days))
    names          = _NAMES[:num_candidates]

    # Initial utilities: random in [0.3, 0.7]
    utilities: dict[str, float] = {name: rng.uniform(0.3, 0.7) for name in names}

    # Index events by day for O(1) lookup
    events_by_day: dict[int, list[dict[str, Any]]] = {}
    for ev in events:
        day = max(0, min(num_days, int(ev.get("day", 0))))
        events_by_day.setdefault(day, []).append(ev)

    # --- Day-by-day loop ---
    days_list:    list[int]       = []
    daily_leader: list[str]       = []
    daily_scores: dict[str, list[float]] = {n: [] for n in names}

    prev_leader: Optional[str] = None
    lead_changes = 0

    for day in range(num_days + 1):
        # 1. Apply events for this day (before computing scores)
        for ev in events_by_day.get(day, []):
            cand_idx = int(ev.get("candidate", 0))
            if 0 <= cand_idx < num_candidates:
                cand      = names[cand_idx]
                etype     = str(ev.get("type", "scandal"))
                magnitude = float(ev.get("magnitude", 0.2))
                utilities[cand] = _apply_event(utilities[cand], etype, magnitude)

        # 2. Vote shares via softmax of current utilities
        shares = _softmax([utilities[n] for n in names])
        for name, share in zip(names, shares):
            daily_scores[name].append(round(share * 100, 2))

        # 3. Daily leader (method-specific)
        if method in ("plurality",):
            leader = _plurality_winner(utilities)
        elif method == "borda":
            leader = _borda_winner(utilities, names)
        else:
            leader = _balloted_winner(utilities, names, method, rng)

        daily_leader.append(leader)
        days_list.append(day)

        if prev_leader is not None and leader != prev_leader:
            lead_changes += 1
        prev_leader = leader

        # 4. Brownian noise for *next* day
        if day < num_days:
            for name in names:
                noise = rng.gauss(0, _SIGMA)
                utilities[name] = max(0.05, min(0.95, utilities[name] + noise))

    # Annotate events with measured impact direction
    annotated: list[dict[str, Any]] = []
    for ev in events:
        ev_copy = dict(ev)
        etype   = str(ev.get("type", "scandal"))
        mag     = float(ev.get("magnitude", 0.2))
        # Positive for boosts, negative for penalties
        impacts: dict[str, float] = {
            "scandal":      -mag,
            "gaffe":        -0.10,
            "good_debate":  +mag,
            "announcement": +mag * 0.5,
            "bad_poll":     -mag * 0.3,
        }
        ev_copy["measured_impact"] = round(impacts.get(etype, -mag), 3)
        annotated.append(ev_copy)

    return {
        "days":         days_list,
        "daily_leader": daily_leader,
        "daily_scores": daily_scores,
        "events":       annotated,
        "final_winner": daily_leader[-1] if daily_leader else None,
        "lead_changes": lead_changes,
        "candidates":   names,
    }
